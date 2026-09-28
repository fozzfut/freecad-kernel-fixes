#!/bin/bash
# loop.sh <rc> <set> <case...> : each case in its own FreeCADCmd run (TMO cap, default 120 s), results merged into out/<rc>-<set>/
RC=$1; S=$2; shift 2; M=/c/dev/occt8-mig/offset-034b2/rv3/out/$RC-$S; mkdir -p $M; : > $M/summary.txt
for c in "$@"; do
  TMO=${TMO:-120} bash /c/dev/occt8-mig/offset-034b2/rv3/one.sh $RC $S $c > /dev/null 2>&1
  D=/c/dev/occt8-mig/offset-034b2/rv3/out/$RC-$S-$c
  if grep -q "^$c " $D/summary.txt 2>/dev/null; then grep "^$c " $D/summary.txt >> $M/summary.txt; else echo "START $c $(grep "^STEP" $D/summary.txt | tail -1)" >> $M/summary.txt; fi
  cp $D/${c}_s*.txt $M/ 2>/dev/null
  rm -rf /c/dev/occt8-mig/fcD/runs/rv3b2-$S-$c-$RC
  tail -1 $M/summary.txt
done
