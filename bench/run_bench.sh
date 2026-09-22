#!/bin/sh
# run_bench.sh <tag> <variant> <profile fc|hd> <FC_DIR> <file|fixture:name> <label> <actions>
# One offscreen FreeCAD run of the action benchmark. Fresh copies of the owner's cfg per run; profile fc = no
# add-ons (user data holds only BenchNoPyc, see below), hd = + HybridDesign loaded read-only from its installed repo
# via -M.
# Extra env passed through: BENCH_CUT_BASE, BENCH_FILLET_REPS, BENCH_BODY_OBJ, BENCH_W, BENCH_H, BENCH_TO (s, 600 and at
# most 600: the owner's ceiling for one FreeCAD run, C:/dev/tools/fcslot.sh, 22.09.2026), BENCH_REFINE_TO (s, 300),
# BENCH_MIN_FREE_MB (4096: FreeCAD starts only with that much free RAM, checked inside the slot by tools/ramgate.sh;
# 0 for a run known to stay under 1 GB, such as fixture:pad).
# Prints: exit=<code> tag=<tag> result=yes|NO errors=<names of the errors in result.json, comma-separated, or ->.
set -u
if [ $# -ne 7 ]; then echo "usage: run_bench.sh <tag> <variant> <fc|hd> <FC_DIR> <file|fixture:name> <label> <actions>" >&2; exit 2; fi
TAG=$1; VARIANT=$2; PROFILE=$3; FC_DIR=$4; FILE=$5; LABEL=$6; ACTIONS=$7
case "$TAG" in ""|*/*|*..*) echo "bad tag '$TAG': the run directory runs/<tag> is deleted first" >&2; exit 2 ;; esac
HERE=C:/dev/freecad-kernel-fixes/bench
RUN=$HERE/runs/$TAG
rm -rf "$RUN"; mkdir -p "$RUN/work" "$RUN/userdata/Mod/BenchNoPyc"
# The HD repo is read-only for the bench, and importing it writes __pycache__ for stale modules. FreeCAD's Python
# ignores PYTHON* variables (sys.flags.ignore_environment=1, probe 1), so the switch goes in an Init.py: every
# Init.py runs before the first InitGui.py, which is where HD imports its package.
echo "import sys; sys.dont_write_bytecode = True" > "$RUN/userdata/Mod/BenchNoPyc/Init.py"
REAL=C:/Users/B72A~1/AppData/Roaming/FreeCAD/v1-1
"$FC_DIR/bin/python.exe" $HERE/tools/cfg_sandbox.py "$REAL/user.cfg" "$RUN" "$REAL/system.cfg" > "$RUN/cfg.log" 2>&1
# without the copies FreeCAD would start on default preferences (not the owner's 6.4 deg): no run then
if [ ! -f "$RUN/user.cfg" ] || [ ! -f "$RUN/system.cfg" ]; then echo "exit=3 tag=$TAG cfg copy failed, see $RUN/cfg.log"; exit 3; fi
EXTRA=""
if [ "$PROFILE" = "hd" ]; then EXTRA="-M C:/Users/B72A~1/AppData/Roaming/FreeCAD/Mod/HybridDesign"; fi
export FREECAD_USER_DATA="$(cygpath -w "$RUN/userdata")"
export FREECAD_USER_TEMP="$RUN/work"
export QT_QPA_PLATFORM=offscreen
export BENCH_FILE="$FILE" BENCH_LABEL="$LABEL" BENCH_VARIANT="$VARIANT" BENCH_PROFILE="$PROFILE"
export BENCH_ACTIONS="$ACTIONS" BENCH_OUT="$RUN"
# An hd run can be two FreeCAD processes: on a heavy file HD re-meshes the parts it drew coarse in a FreeCAD.exe of
# its own (hybriddesign/gui/mesh_process.py, offscreen, started by HD, not through fcslot). So an hd run holds two
# of the machine's five slots: the outer fcslot keeps one while the inner one takes the second and starts FreeCAD.
SLOTS="bash C:/dev/tools/fcslot.sh"
if [ "$PROFILE" = "hd" ]; then SLOTS="bash C:/dev/tools/fcslot.sh bash C:/dev/tools/fcslot.sh"; fi
TO=${BENCH_TO:-600}
if [ "$TO" -gt 600 ]; then echo "BENCH_TO=$TO is above the owner's 600 s ceiling for a FreeCAD run: 600 is used" >&2; TO=600; fi
START=$(date '+%Y-%m-%dT%H:%M:%S')
cd "$RUN/work" && $SLOTS sh $HERE/tools/ramgate.sh ${BENCH_MIN_FREE_MB:-4096} timeout -k 15 $TO "$FC_DIR/bin/FreeCAD.exe" \
  --log-file "$RUN/fc.log" -u "$RUN/user.cfg" -s "$RUN/system.cfg" $EXTRA "$HERE/fcbench/driver.py" \
  > "$RUN/stdout.log" 2>&1
RC=$?
END=$(date '+%Y-%m-%dT%H:%M:%S')
# The driver stops HD's worker itself (children_at_exit in result.json). A FreeCAD killed by the timeout cannot, and
# its worker would go on meshing outside any slot: stop the FreeCAD.exe children of the driver's process that were
# started while it ran (the time window keeps out a later process that reuses the pid).
if [ -f "$RUN/driver.pid" ]; then
  PS_STOP='$a=[datetime]$env:B_START; $b=([datetime]$env:B_END).AddSeconds(1); Get-CimInstance Win32_Process -Filter ("ParentProcessId=" + $env:B_PID) | Where-Object { $_.Name -eq "FreeCAD.exe" -and $_.CreationDate -ge $a -and $_.CreationDate -le $b } | ForEach-Object { "stopped leftover child " + $_.ProcessId + ": " + $_.CommandLine; Stop-Process -Id $_.ProcessId -Force }'
  B_START=$START B_END=$END B_PID=$(cat "$RUN/driver.pid") powershell -NoProfile -Command "$PS_STOP" > "$RUN/leftovers.log" 2>&1
  if [ -s "$RUN/leftovers.log" ]; then cat "$RUN/leftovers.log" >&2; fi
fi
ERRS=-
if [ -f "$RUN/result.json" ]; then
  ERRS=$("$FC_DIR/bin/python.exe" -c "import json,sys; e=json.load(open(sys.argv[1],encoding='utf-8')).get('errors') or {}; print(','.join(sorted(e)) or '-')" "$RUN/result.json" 2>/dev/null || echo unreadable)
fi
echo "exit=$RC tag=$TAG result=$(test -f "$RUN/result.json" && echo yes || echo NO) errors=$ERRS"
