#!/bin/bash
# one.sh <rc> <set> [script] -> rv2/out/<set>-<rc>.txt ; one FreeCADCmd via fcrun.sh (fcslot, cfg copies, 600 s cap, runguard 1 GB)
RC=$1; S=$2; SC=${3:-/c/dev/occt8-mig/offset-034b2/rv2/rvn_full.py}; O=/c/dev/occt8-mig/offset-034b2/rv2/out; mkdir -p $O
export FC_OUT=$(cygpath -w $O/$S-$RC.txt) RV_SET=$S
bash /c/dev/occt8-mig/fcD/tools/fcrun.sh $RC C:/dev/occt8-mig/fcD/runs/rv2b2-$S-$RC cmd $SC | tail -2
cat $O/$S-$RC.txt
