#!/bin/bash
# vrun.sh <rc name> <run name> <nohd|hd> <probe.py> -- lane vr6-unconf (from undovis/uvrun.sh): one offscreen GUI run of
# a probe from run copy C:/dev/occt8-mig/vr6unconf/rc/<rc>. Config = COPIES of the delivery's user.cfg/system.cfg (never
# links). hd = Mod/HybridDesign junction to the HD deploy, nohd = empty user data. Gate, fcslot, timeout 600, runguard.
# Work dir C:/dev/occt8-mig/vr6unconf/runs/<run>; probe writes $PROBE_OUT. WIN=1 -> real window (no QT_QPA offscreen).
set -u
RC=$1; NAME=$2; MODE=$3; PROBE=$(cd "$(dirname "$4")" && pwd)/$(basename "$4")
FC=/c/dev/occt8-mig/vr6unconf/rc/$RC
W=/c/dev/occt8-mig/vr6unconf/runs/$NAME
[ -x "$FC/bin/FreeCAD.exe" ] || { echo "no run copy $FC"; exit 2; }
BF=C:/dev/fckf-d/build-freecad
rm -rf "$W"; mkdir -p "$W/home" "$W/data/Mod" "$W/tmp"
cp /c/dev/FreeCAD-occt8-perf/userdata/user.cfg "$W/user.cfg"
cp /c/dev/FreeCAD-occt8-perf/userdata/system.cfg "$W/system.cfg"
if [ "$MODE" = hd ]; then
  cmd //c mklink //J "$(cygpath -w "$W/data/Mod/HybridDesign")" "C:\Users\B72A~1\AppData\Roaming\FreeCAD\Mod\HybridDesign" > /dev/null
fi
export FREECAD_USER_HOME="$(cygpath -w "$W/home")" FREECAD_USER_DATA="$(cygpath -w "$W/data")"
export TEMP="$(cygpath -w "$W/tmp")" TMP="$(cygpath -w "$W/tmp")" PYTHONDONTWRITEBYTECODE=1
[ "${WIN:-0}" = 1 ] || export QT_QPA_PLATFORM=offscreen
export PROBE_OUT="$(cygpath -w "$W/probe.txt")" PROBE_WORK="$(cygpath -w "$W")"
bash C:/dev/occt8-mig/hd-compat/bin/gate.sh > "$W/gate.txt" || { cat "$W/gate.txt"; exit 75; }
cd "$W" && RUNGUARD_QUIET=1 RUNGUARD_BELOWNORMAL=1 bash $BF/runguard.sh gui "$W" "$W" "$W" \
  bash C:/dev/tools/fcslot.sh timeout -k 15 600 "$FC/bin/FreeCAD.exe" --log-file "$(cygpath -w "$W/fc.log")" \
  -u "$(cygpath -w "$W/user.cfg")" -s "$(cygpath -w "$W/system.cfg")" "$(cygpath -w "$PROBE")" > "$W/stdout.log" 2>&1
R=$?
cat "$W/runguard.txt" 2>/dev/null
if [ $R -ne 0 ]; then powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $BF/orphans.ps1)" -Marker "$(cygpath -w "$W")"; fi
[ -L "$W/data/Mod/HybridDesign" ] || [ -d "$W/data/Mod/HybridDesign" ] && cmd //c rmdir "$(cygpath -w "$W/data/Mod/HybridDesign")" 2>/dev/null
echo "exit=$R rc=$RC work=$W"
exit $R
