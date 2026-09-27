#!/bin/bash
# drive3.sh <dlldir> <tag> <keys> : filsweep3 over the keys with that TKFillet; after a HANG (watchdog exit) it goes
# on with the keys after the hung one. -> runs/d3-<tag>.txt
D=$1; T=$2; K=$3; R=/c/dev/occt8-mig/fillet-corner-r3
O=$R/runs/d3-$T.txt; : > $O; cp $K $R/runs/.k-$T
s=$(date +%s)
while true; do
  PATH="$D:/c/dev/FreeCAD-occt8-perf/bin:$PATH" FS3_HANG_MS=${HANGMS:-60000} timeout 590 $R/bin/filsweep3.exe $(cygpath -w $O) $(cygpath -w $R/runs/.k-$T) 2>> $R/runs/d3-$T.stderr
  rc=$?
  tail -1 $O | grep -q FS3-DONE && break
  last=$(grep -v '^HANG' $O | tail -1 | awk '{print $1" "$2" "$3" "$4" "$5}')
  h=$(tail -1 $O | grep '^HANG' | awk '{print $2" "$3" "$4" "$5" "$6}')
  [ -n "$h" ] && last="$h"
  [[ "$last" == CASE* ]] && last=$(echo "$last" | awk '{print $1" "$2}')
  n=$(grep -n -F "$last" $R/runs/.k-$T | head -1 | cut -d: -f1)
  echo "rc=$rc resume after line $n ($last)" >> $R/runs/d3-$T.stderr
  [ -z "$n" ] && { echo "DRIVE-STOP cannot resume" >> $O; break; }
  tail -n +$((n+1)) $R/runs/.k-$T > $R/runs/.k-$T.2; mv $R/runs/.k-$T.2 $R/runs/.k-$T
  [ -s $R/runs/.k-$T ] || { echo FS3-DONE >> $O; break; }
done
echo "wall=$(( $(date +%s)-s ))s" >> $R/runs/d3-$T.stderr
echo "$T done wall=$(( $(date +%s)-s ))s lines=$(wc -l < $O) hangs=$(grep -c ^HANG $O)"
