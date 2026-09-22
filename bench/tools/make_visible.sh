#!/bin/sh
# make_visible.sh <FC_DIR> <src.FCStd> <dst.FCStd> - GUI copy of a headless-made file with every part shown
# (tools/make_visible.py says why). One FreeCAD.exe offscreen through fcslot, copies of the owner's cfg, 600 s ceiling.
# Prints: exit=<code> dst=<path> visible=<n>/<objects> | exit=<code> ERROR ... | exit=<code> no make_visible.json.
set -u
if [ $# -ne 3 ]; then echo "usage: make_visible.sh <FC_DIR> <src> <dst>" >&2; exit 2; fi
FC_DIR=$1; SRC=$2; DST=$3
HERE=C:/dev/freecad-kernel-fixes/bench
RUN=$HERE/runs/make-visible-$(basename "$DST" .FCStd)
rm -rf "$RUN"; mkdir -p "$RUN/work" "$RUN/userdata"
REAL=C:/Users/B72A~1/AppData/Roaming/FreeCAD/v1-1
"$FC_DIR/bin/python.exe" $HERE/tools/cfg_sandbox.py "$REAL/user.cfg" "$RUN" "$REAL/system.cfg" > "$RUN/cfg.log" 2>&1
if [ ! -f "$RUN/user.cfg" ] || [ ! -f "$RUN/system.cfg" ]; then echo "exit=3 cfg copy failed, see $RUN/cfg.log"; exit 3; fi
export FREECAD_USER_DATA="$(cygpath -w "$RUN/userdata")" FREECAD_USER_TEMP="$RUN/work" QT_QPA_PLATFORM=offscreen
export BENCH_VIS_SRC="$SRC" BENCH_VIS_DST="$DST" BENCH_OUT="$RUN"
START=$(date '+%Y-%m-%dT%H:%M:%S')
cd "$RUN/work" && bash C:/dev/tools/fcslot.sh sh $HERE/tools/ramgate.sh 4096 timeout -k 15 600 \
  "$FC_DIR/bin/FreeCAD.exe" --log-file "$RUN/fc.log" -u "$RUN/user.cfg" -s "$RUN/system.cfg" \
  "$HERE/tools/make_visible.py" > "$RUN/stdout.log" 2>&1
RC=$?
END=$(date '+%Y-%m-%dT%H:%M:%S')
# timeout kills the wrapper, not FreeCAD: stop a FreeCAD.exe of this run (by its pid or its own -u path)
PS_STOP='$a=[datetime]$env:B_START; $b=([datetime]$env:B_END).AddSeconds(1); $u=$env:B_UCFG; $p=[int]$env:B_PID; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "FreeCAD.exe" -and $_.CreationDate -ge $a -and $_.CreationDate -le $b -and ($_.ProcessId -eq $p -or ($_.CommandLine -and $_.CommandLine.Contains($u))) } | ForEach-Object { "stopped leftover " + $_.ProcessId + ": " + $_.CommandLine; Stop-Process -Id $_.ProcessId -Force }'
B_START=$START B_END=$END B_PID=$(cat "$RUN/make.pid" 2>/dev/null || echo -1) B_UCFG="$RUN/user.cfg" \
  powershell -NoProfile -Command "$PS_STOP" > "$RUN/leftovers.log" 2>&1
if [ -s "$RUN/leftovers.log" ]; then cat "$RUN/leftovers.log" >&2; fi
if [ -f "$RUN/make_visible.json" ]; then
  "$FC_DIR/bin/python.exe" -c "import json,sys; r=json.load(open(sys.argv[1],encoding='utf-8')); print('exit=%s dst=%s visible=%s/%s open_s=%s save_s=%s' % (sys.argv[2], r['dst'], r['visible_after'], r['objects'], r['open_s'], r['save_s']) if 'error' not in r else 'exit=%s ERROR %s' % (sys.argv[2], r['error']))" "$RUN/make_visible.json" "$RC"
else
  echo "exit=$RC no make_visible.json (124 = timeout), see $RUN/stdout.log"
fi
exit $RC
