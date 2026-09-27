#!/bin/bash
# uvrun.sh <rc name> <run name> <fresh|owner> -- one offscreen GUI run of probe/uvprobe.py from the run copy
# C:/dev/occt8-mig/undovis/rc/<rc>. fresh = empty config made by FreeCAD; owner = COPIES of the delivery's userdata
# user.cfg/system.cfg (never links) + Mod/HybridDesign junction to the HD repo (owner setup). Work dir
# C:/dev/occt8-mig/undovis/runs/<run>. Gate, fcslot, timeout 600, runguard (1 GB/process, 120 s watchdog).
# Extra env for the probe (UV_ONLY, UV_PREF_OFF) is passed through.
set -u
RC=$1; NAME=$2; MODE=$3
FC=/c/dev/occt8-mig/undovis/rc/$RC
W=/c/dev/occt8-mig/undovis/runs/$NAME
[ -x "$FC/bin/FreeCAD.exe" ] || { echo "no run copy $FC"; exit 2; }
BF=C:/dev/fckf-d/build-freecad
rm -rf "$W"; mkdir -p "$W/home" "$W/data/Mod" "$W/tmp"
if [ "$MODE" = owner ]; then
  cp /c/dev/FreeCAD-occt8-perf/userdata/user.cfg "$W/user.cfg"
  cp /c/dev/FreeCAD-occt8-perf/userdata/system.cfg "$W/system.cfg"
  cmd //c mklink //J "$(cygpath -w "$W/data/Mod/HybridDesign")" "C:\Users\B72A~1\AppData\Roaming\FreeCAD\Mod\HybridDesign" > /dev/null
fi
export FREECAD_USER_HOME="$(cygpath -w "$W/home")" FREECAD_USER_DATA="$(cygpath -w "$W/data")"
export TEMP="$(cygpath -w "$W/tmp")" TMP="$(cygpath -w "$W/tmp")" PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen
export UV_OUT="$(cygpath -w "$W/probe.txt")" UV_WORK="$(cygpath -w "$W")"
bash C:/dev/occt8-mig/hd-compat/bin/gate.sh > "$W/gate.txt" || { cat "$W/gate.txt"; exit 75; }
cd "$W" && RUNGUARD_QUIET=1 RUNGUARD_BELOWNORMAL=1 bash $BF/runguard.sh gui "$W" "$W" "$W" \
  bash C:/dev/tools/fcslot.sh timeout -k 15 600 "$FC/bin/FreeCAD.exe" --log-file "$(cygpath -w "$W/fc.log")" \
  -u "$(cygpath -w "$W/user.cfg")" -s "$(cygpath -w "$W/system.cfg")" "$(cygpath -w /c/dev/occt8-mig/undovis/probe/uvprobe.py)" > "$W/stdout.log" 2>&1
R=$?
cat "$W/runguard.txt"
if [ $R -ne 0 ]; then powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $BF/orphans.ps1)" -Marker "$(cygpath -w "$W")"; fi
[ -L "$W/data/Mod/HybridDesign" ] || [ -d "$W/data/Mod/HybridDesign" ] && cmd //c rmdir "$(cygpath -w "$W/data/Mod/HybridDesign")" 2>/dev/null
echo "exit=$R rc=$RC work=$W"; cat "$W/probe.txt" 2>/dev/null
exit $R
