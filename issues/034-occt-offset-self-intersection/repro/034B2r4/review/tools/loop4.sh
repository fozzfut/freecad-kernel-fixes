#!/bin/bash
# loop4.sh <rc> <list> <tag> [names...]: each case in its own FreeCADCmd (fcrun_t: fcslot, cfg copies, runguard 1 GB), TMO default 150 s
RC=$1; L=$(realpath $2); T=$3; shift 3
R=/c/dev/occt8-mig/offset-034b2/rv4; M=$R/out/$RC-$T; mkdir -p $M; touch $M/summary.txt
NAMES="$*"; [ -z "$NAMES" ] && NAMES=$(grep -v '^#' $L | awk 'NF{print $1}')
for c in $NAMES; do
  grep -q "^$c " $M/summary.txt && continue
  O=$R/out/$RC-$T-$c; rm -rf $O
  FC_OUT=$(cygpath -m $O) RV_LIST=$(cygpath -m $L) RV_ONLY=$c TMO=${TMO:-150} bash /c/dev/occt8-mig/offset-034b2/rv3/tools/fcrun_t.sh $RC C:/dev/occt8-mig/fcD/runs/rv4b2-$c-$RC cmd $R/tools/rv4run.py > $O.log 2>&1
  if grep -q "^$c " $O/summary.txt 2>/dev/null; then grep "^$c " $O/summary.txt >> $M/summary.txt; else echo "START $c HANG $(grep '^STEP' $O/summary.txt 2>/dev/null | tail -1 | cut -c1-60) $(grep RUNGUARD $O.log | cut -c1-80)" >> $M/summary.txt; fi
  cp $O/${c}_s*.txt $O/$c.brep $M/ 2>/dev/null
  rm -rf C:/dev/occt8-mig/fcD/runs/rv4b2-$c-$RC $O
  tail -1 $M/summary.txt
done
