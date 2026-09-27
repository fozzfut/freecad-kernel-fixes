#!/bin/bash
# fcrun.sh <rc name> <work dir> <cmd|gui> <script.py|-t:TestModule> -- one FreeCAD run of lane vr6-asm on 26.3 from the
# hard-link run copy C:/dev/occt8-mig/fcD/rc/<rc name> (never the weekly folder). Fresh isolated user dirs in
# <work dir> (FREECAD_USER_HOME/FREECAD_USER_DATA/TEMP, empty user.cfg/system.cfg made by FreeCAD itself, -u/-s),
# offscreen for gui, Report view -> <work dir>/fc.log, stdout -> <work dir>/stdout.log. Gate RAM >= 1 GB / commit
# >= 4 GB (<= 10 min, else exit 75 NOT RUN), fcslot, timeout -k 15 600, runguard (1 GB per process cap, gui: CPU-aware
# 120 s watchdog) from plan D's build-freecad; after a non-zero exit, orphans of THIS work dir are stopped.
set -u
RC=$1; W=$2; MODE=$3; WHAT=$4
FC=/c/dev/occt8-mig/vr6asm/rc/$RC
[ -x "$FC/bin/FreeCADCmd.exe" ] || { echo "no run copy $FC"; exit 2; }
case "$W" in C:/dev/occt8-mig/vr6asm/runs/*) ;; *) echo "work dir must be under C:/dev/occt8-mig/vr6asm/runs/"; exit 2;; esac
BF=C:/dev/fckf-d/build-freecad
rm -rf "$W"; mkdir -p "$W/home" "$W/data" "$W/tmp"
export FREECAD_USER_HOME="$(cygpath -w "$W/home")" FREECAD_USER_DATA="$(cygpath -w "$W/data")"
export TEMP="$(cygpath -w "$W/tmp")" TMP="$(cygpath -w "$W/tmp")" PYTHONDONTWRITEBYTECODE=1
EXE="$FC/bin/FreeCADCmd.exe"
if [ "$MODE" = gui ]; then EXE="$FC/bin/FreeCAD.exe"; export QT_QPA_PLATFORM=offscreen; fi
case "$WHAT" in -t:*) ARG=(-t "${WHAT#-t:}");; *) ARG=("$(cygpath -w "$WHAT")");; esac
bash C:/dev/occt8-mig/hd-compat/bin/gate.sh > "$W/gate.txt" || { cat "$W/gate.txt"; exit 75; }
cd "$W" && RUNGUARD_QUIET=1 RUNGUARD_BELOWNORMAL=1 bash $BF/runguard.sh "$MODE" "$W" "$W" "$W" \
  bash C:/dev/tools/fcslot.sh timeout -k 15 600 "$EXE" --log-file "$(cygpath -w "$W/fc.log")" \
  -u "$(cygpath -w "$W/user.cfg")" -s "$(cygpath -w "$W/system.cfg")" "${ARG[@]}" > "$W/stdout.log" 2>&1
R=$?
cat "$W/runguard.txt"
if [ $R -ne 0 ]; then powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $BF/orphans.ps1)" -Marker "$(cygpath -w "$W")"; fi
echo "exit=$R rc=$RC work=$W"
exit $R
