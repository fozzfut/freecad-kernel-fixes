#!/bin/bash
# one.sh <rc> <set> : one FreeCADCmd run of rv3run.py (fcrun.sh: fcslot, cfg copies, 600 s cap, 1 GB runguard)
RC=$1; S=$2; ONLY=${3:-}; TAG=$S${ONLY:+-$ONLY}; O=C:/dev/occt8-mig/offset-034b2/rv3/out/$RC-$TAG
rm -rf /c/dev/occt8-mig/offset-034b2/rv3/out/$RC-$TAG
export FC_OUT=$O RV_SET=${S%%.*} RV_ONLY=$ONLY
bash /c/dev/occt8-mig/offset-034b2/rv3/tools/fcrun_t.sh $RC C:/dev/occt8-mig/fcD/runs/rv3b2-$TAG-$RC cmd /c/dev/occt8-mig/offset-034b2/rv3/rv3run.py | tail -2
cat /c/dev/occt8-mig/offset-034b2/rv3/out/$RC-$TAG/summary.txt
