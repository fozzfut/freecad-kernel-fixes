#!/bin/bash
# one.sh <rc> <set> -> r2/out/<set>-<rc>.txt ; reviewer stand rv1/rvb2.py, one FreeCADCmd via fcrun.sh
RC=$1; S=$2; O=/c/dev/occt8-mig/offset-034b2/r2/${OUTD:-out}; mkdir -p $O
export FC_OUT=$(cygpath -w $O/$S-$RC.txt) RV_SET=$S
bash /c/dev/occt8-mig/fcD/tools/fcrun.sh $RC C:/dev/occt8-mig/fcD/runs/b2r2-$S-$RC cmd /c/dev/occt8-mig/offset-034b2/rv1/rvb2.py | tail -1
