#!/bin/bash
# lane vr6-asm: stock FreeCAD suites, delivery (dlv) vs fix, one at a time
R=C:/dev/occt8-mig/vr6asm/runs
for t in Document TestGuiBase TestAssemblyWorkbench TestPartDesignGui; do
  for rc in dlv fix; do
    W=$R/s-$t-$rc
    echo "== $(date +%T) $rc $t"
    bash C:/dev/occt8-mig/vr6asm/tools/fcrun.sh $rc $W gui -t:$t 2>&1 | tail -2
    tail -4 $W/stdout.log | tr '\n' ' '; echo
  done
done
echo ALLDONE
