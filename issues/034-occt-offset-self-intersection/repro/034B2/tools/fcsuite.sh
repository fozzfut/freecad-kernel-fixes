#!/bin/bash
# FreeCAD 26.3 checks, one run at a time via fcrun.sh: suites + fcb2 (class in FreeCAD) + fcconf034 (stage A rows)
# on the run copies o034p (delivery bin with 034A TKOffset c5e4db40 = base of this branch) and o034b2 (B2 r1).
R=/c/dev/occt8-mig/offset-034b2; T=/c/dev/occt8-mig/fcD/tools
for rc in ${RCS:-o034b2 o034p}; do
  for s in TestPartApp TestPartDesignApp; do
    bash $T/fcrun.sh $rc C:/dev/occt8-mig/fcD/runs/b2-$s-$rc cmd -t:$s | tail -1
  done
  for p in fcb2 fcconf034; do
    export FC_OUT=$(cygpath -w $R/fc/$p-$rc.txt)
    src=$R/fc/$p.py; [ $p = fcconf034 ] && src=/c/dev/occt8-mig/offset-034/tools/fcconf034.py
    bash $T/fcrun.sh $rc C:/dev/occt8-mig/fcD/runs/b2-$p-$rc cmd $src | tail -1
  done
done
echo FC-DONE
