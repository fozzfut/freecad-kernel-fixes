#!/bin/sh
# run_bench.sh <tag> <variant> <profile fc|hd> <FC_DIR> <file|fixture:name> <label> <actions>
# One offscreen FreeCAD run of the action benchmark. Fresh copies of the owner's cfg per run; profile fc = no
# add-ons (user data holds only BenchNoPyc, see below), hd = + HybridDesign loaded read-only from its installed repo
# via -M.
# Extra env passed through: BENCH_CUT_BASE, BENCH_BODY_OBJ, BENCH_HEAVY, BENCH_W, BENCH_H, BENCH_TO (s, 1800).
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
cd "$RUN/work" && bash C:/dev/tools/fcslot.sh timeout -k 15 ${BENCH_TO:-1800} "$FC_DIR/bin/FreeCAD.exe" \
  --log-file "$RUN/fc.log" -u "$RUN/user.cfg" -s "$RUN/system.cfg" $EXTRA "$HERE/fcbench/driver.py" \
  > "$RUN/stdout.log" 2>&1
echo "exit=$? tag=$TAG result=$(test -f "$RUN/result.json" && echo yes || echo NO)"
