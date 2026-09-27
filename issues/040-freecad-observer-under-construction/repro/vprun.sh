#!/bin/bash
# vprun.sh <rc> <run> <nohd|obs|hd|hdfull|hdobs> [HD tree] [probe] -- lane vr6-asm: one offscreen GUI run of a probe
# from run copy vr6asm/rc/<rc>. nohd/obs = fresh config, empty user data (obs adds a no-op Gui observer);
# hd = COPY of C:/dev/thk-vr6-model/cfg (owner's trimmed cfg: only HybridDesign), hdfull = copy of cfg_full;
# HD tree (default: live repo) is junctioned as Mod/HybridDesign. fcslot, 600 s, runguard (1 GB, 120 s watchdog).
set -u
RC=$1; NAME=$2; MODE=$3; HD=${4:-C:/Users/B72A~1/AppData/Roaming/FreeCAD/Mod/HybridDesign}
PROBE=${5:-C:/dev/occt8-mig/vr6asm/probe/vpprobe.py}
FC=${FCROOT:-/c/dev/occt8-mig/vr6asm/rc/$RC}
W=/c/dev/occt8-mig/vr6asm/runs/$NAME
[ -x "$FC/bin/FreeCAD.exe" ] || { echo "no run copy $FC"; exit 2; }
BF=C:/dev/fckf-d/build-freecad
rm -rf "$W"; mkdir -p "$W/home" "$W/data/Mod" "$W/tmp"
case $MODE in
  hd|hdobs) cp /c/dev/thk-vr6-model/cfg/user.cfg /c/dev/thk-vr6-model/cfg/system.cfg "$W/";;
  hdfull) cp /c/dev/thk-vr6-model/cfg_full/user.cfg /c/dev/thk-vr6-model/cfg_full/system.cfg "$W/";;
esac
case $MODE in hd*) cmd //c mklink //J "$(cygpath -w "$W/data/Mod/HybridDesign")" "$(cygpath -w "$HD")" > /dev/null;; esac
case $MODE in obs|hdobs) export VP_OBS=1;; *) export VP_OBS=0;; esac
export FREECAD_USER_HOME="$(cygpath -w "$W/home")" FREECAD_USER_DATA="$(cygpath -w "$W/data")"
export TEMP="$(cygpath -w "$W/tmp")" TMP="$(cygpath -w "$W/tmp")" PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen
export VP_OUT="$(cygpath -w "$W/probe.txt")" VP_WORK="$(cygpath -w "$W")"
bash C:/dev/occt8-mig/hd-compat/bin/gate.sh > "$W/gate.txt" || { cat "$W/gate.txt"; exit 75; }
cd "$W" && RUNGUARD_QUIET=1 RUNGUARD_BELOWNORMAL=1 bash $BF/runguard.sh gui "$W" "$W" "$W" \
  bash C:/dev/tools/fcslot.sh timeout -k 15 600 "$FC/bin/FreeCAD.exe" --log-file "$(cygpath -w "$W/fc.log")" \
  -u "$(cygpath -w "$W/user.cfg")" -s "$(cygpath -w "$W/system.cfg")" "$(cygpath -w "$PROBE")" > "$W/stdout.log" 2>&1
R=$?
cat "$W/runguard.txt" 2>/dev/null | tail -2
if [ $R -ne 0 ]; then powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $BF/orphans.ps1)" -Marker "$(cygpath -w "$W")"; fi
[ -e "$W/data/Mod/HybridDesign" ] && cmd //c rmdir "$(cygpath -w "$W/data/Mod/HybridDesign")" 2>/dev/null
echo "exit=$R rc=$RC mode=$MODE work=$W"
exit $R
