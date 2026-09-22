#!/bin/sh
# build_fixture.sh <FC_DIR> [name=holes1024] - build a bench fixture once into bench/files, in FreeCAD.exe
# offscreen with a fresh copy of the owner's cfg (a FreeCADCmd build would open with every object hidden, see
# fcbench/fixtures.py). One FreeCAD run through fcslot, 600 s ceiling. Prints: fixture=<path> or the error.
set -u
FC_DIR=$1; NAME=${2:-holes1024}
HERE=C:/dev/freecad-kernel-fixes/bench
RUN=$HERE/runs/build-$NAME
rm -rf "$RUN"; mkdir -p "$RUN/work" "$RUN/userdata"
REAL=C:/Users/B72A~1/AppData/Roaming/FreeCAD/v1-1
"$FC_DIR/bin/python.exe" $HERE/tools/cfg_sandbox.py "$REAL/user.cfg" "$RUN" "$REAL/system.cfg" > "$RUN/cfg.log" 2>&1
if [ ! -f "$RUN/user.cfg" ] || [ ! -f "$RUN/system.cfg" ]; then echo "cfg copy failed, see $RUN/cfg.log"; exit 3; fi
export FREECAD_USER_DATA="$(cygpath -w "$RUN/userdata")" FREECAD_USER_TEMP="$RUN/work" QT_QPA_PLATFORM=offscreen
export BENCH_FIXTURE="$NAME" BENCH_OUT="$RUN"
cd "$RUN/work" && bash C:/dev/tools/fcslot.sh sh $HERE/tools/ramgate.sh ${BENCH_MIN_FREE_MB:-4096} timeout -k 15 600 \
  "$FC_DIR/bin/FreeCAD.exe" --log-file "$RUN/fc.log" -u "$RUN/user.cfg" -s "$RUN/system.cfg" \
  "$HERE/tools/build_fixture.py" > "$RUN/stdout.log" 2>&1
RC=$?
"$FC_DIR/bin/python.exe" -c "import json,sys; r=json.load(open(sys.argv[1],encoding='utf-8')); print('exit=%s fixture=%s seconds=%s' % (sys.argv[2], r['path'], r['seconds']) if 'error' not in r else 'exit=%s ERROR %s' % (sys.argv[2], r['error']))" "$RUN/build.json" "$RC" 2>/dev/null || echo "exit=$RC no build.json, see $RUN"
