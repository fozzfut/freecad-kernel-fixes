#!/bin/bash
# FreeCAD 26.3 checks on the run copy fcD/rc/o034r2 (o034a2 with the round-2 TKOffset), one run at a time via fcrun.sh
R=/c/dev/occt8-mig/offset-034a2; T=/c/dev/occt8-mig/fcD/tools
for s in TestPartApp TestPartDesignApp; do
  bash $T/fcrun.sh o034r2 C:/dev/occt8-mig/fcD/runs/t-$s-o034r2 cmd -t:$s | tail -1
done
for p in encl rv034 fcconf034; do
  export FC_OUT=$(cygpath -w $R/r2/runs/fc-$p-o034r2.txt)
  bash $T/fcrun.sh o034r2 C:/dev/occt8-mig/fcD/runs/a2r2-$p-o034r2 cmd $R/fc/$p.py | tail -1
done
echo FC-DONE
