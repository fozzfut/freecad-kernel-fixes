#!/bin/bash
# one1.sh <rc> <set>: review-r1 stand rv1/rvb2.py (unchanged) -> rv2/out/rv1-<set>-<rc>.txt
RC=$1; S=$2; O=/c/dev/occt8-mig/offset-034b2/rv2/out
export FC_OUT=$(cygpath -w $O/rv1-$S-$RC.txt) RV_SET=$S
bash /c/dev/occt8-mig/fcD/tools/fcrun.sh $RC C:/dev/occt8-mig/fcD/runs/rv2b2r1-$S-$RC cmd /c/dev/occt8-mig/offset-034b2/rv1/rvb2.py | tail -1
