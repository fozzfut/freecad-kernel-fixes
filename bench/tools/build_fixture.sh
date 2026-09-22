#!/bin/sh
# build_fixture.sh <FC_DIR> [name=holes1024] - build a bench fixture once into bench/files, in FreeCAD.exe
# offscreen with a fresh copy of the owner's cfg (a FreeCADCmd build would open with every object hidden, see
# fcbench/fixtures.py). One FreeCAD run through fcslot, 600 s ceiling.
# Prints: exit=<code> fixture=<path> seconds=<s> | exit=<code> ERROR <traceback> | exit=<code> no build.json (124 =
# timeout). After the run, FreeCAD.exe processes left from it are stopped (leftovers.log) and a half-built
# files/fixture_<name>-*.building-<pid> of this run is removed. BENCH_BUILD_TO: timeout, s (600 and at most 600).
set -u
if [ $# -lt 1 ]; then echo "usage: build_fixture.sh <FC_DIR> [name]" >&2; exit 2; fi
FC_DIR=$1; NAME=${2:-holes1024}
HERE=C:/dev/freecad-kernel-fixes/bench
RUN=$HERE/runs/build-$NAME
rm -rf "$RUN"; mkdir -p "$RUN/work" "$RUN/userdata"
REAL=C:/Users/B72A~1/AppData/Roaming/FreeCAD/v1-1
"$FC_DIR/bin/python.exe" $HERE/tools/cfg_sandbox.py "$REAL/user.cfg" "$RUN" "$REAL/system.cfg" > "$RUN/cfg.log" 2>&1
if [ ! -f "$RUN/user.cfg" ] || [ ! -f "$RUN/system.cfg" ]; then echo "exit=3 cfg copy failed, see $RUN/cfg.log"; exit 3; fi
export FREECAD_USER_DATA="$(cygpath -w "$RUN/userdata")" FREECAD_USER_TEMP="$RUN/work" QT_QPA_PLATFORM=offscreen
export BENCH_FIXTURE="$NAME" BENCH_OUT="$RUN"
TO=${BENCH_BUILD_TO:-600}
if [ "$TO" -gt 600 ]; then echo "BENCH_BUILD_TO=$TO is above the owner's 600 s ceiling: 600 is used" >&2; TO=600; fi
START=$(date '+%Y-%m-%dT%H:%M:%S')
cd "$RUN/work" && bash C:/dev/tools/fcslot.sh sh $HERE/tools/ramgate.sh ${BENCH_MIN_FREE_MB:-4096} timeout -k 15 $TO \
  "$FC_DIR/bin/FreeCAD.exe" --log-file "$RUN/fc.log" -u "$RUN/user.cfg" -s "$RUN/system.cfg" \
  "$HERE/tools/build_fixture.py" > "$RUN/stdout.log" 2>&1
RC=$?
END=$(date '+%Y-%m-%dT%H:%M:%S')
# timeout kills the wrapper, not FreeCAD: stop the FreeCAD.exe of this build (by its pid, or by this run's own -u
# path) and its FreeCAD.exe children, started while it ran (the time window keeps out a later process reusing a pid)
PS_STOP='$a=[datetime]$env:B_START; $b=([datetime]$env:B_END).AddSeconds(1); $u=$env:B_UCFG; $p=[int]$env:B_PID; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "FreeCAD.exe" -and $_.CreationDate -ge $a -and $_.CreationDate -le $b -and ($_.ProcessId -eq $p -or $_.ParentProcessId -eq $p -or ($_.CommandLine -and $_.CommandLine.Contains($u))) } | ForEach-Object { "stopped leftover " + $_.ProcessId + ": " + $_.CommandLine; Stop-Process -Id $_.ProcessId -Force }'
B_START=$START B_END=$END B_PID=$(cat "$RUN/build.pid" 2>/dev/null || echo -1) B_UCFG="$RUN/user.cfg" \
  powershell -NoProfile -Command "$PS_STOP" > "$RUN/leftovers.log" 2>&1
if [ -f "$RUN/build.pid" ]; then
  for d in $HERE/files/fixture_$NAME-*.building-$(cat "$RUN/build.pid"); do
    if [ -d "$d" ]; then rm -rf "$d" && echo "removed half-built $d" >> "$RUN/leftovers.log"; fi
  done
fi
if [ -s "$RUN/leftovers.log" ]; then cat "$RUN/leftovers.log" >&2; fi
if [ -f "$RUN/build.json" ]; then
  "$FC_DIR/bin/python.exe" -c "import json,sys; r=json.load(open(sys.argv[1],encoding='utf-8')); print('exit=%s fixture=%s seconds=%s' % (sys.argv[2], r['path'], r['seconds']) if 'error' not in r else 'exit=%s ERROR %s' % (sys.argv[2], r['error']))" "$RUN/build.json" "$RC" \
    || echo "exit=$RC build.json unreadable, see $RUN"
else
  echo "exit=$RC no build.json (124 = timeout), see $RUN/stdout.log and $RUN/fc.log"
fi
exit $RC
