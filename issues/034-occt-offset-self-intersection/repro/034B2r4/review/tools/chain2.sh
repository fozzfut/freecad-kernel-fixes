#!/bin/bash
R=/c/dev/occt8-mig/offset-034b2/rv4
until grep -q "^oq_n_off-1.5_ctl\|START oq_n_off-1.5_ctl" $R/out/o034r2-new/summary.txt 2>/dev/null; do sleep 10; done
FC_OUT=C:/dev/occt8-mig/offset-034b2/rv4/out TMO=300 bash /c/dev/occt8-mig/offset-034b2/rv3/tools/fcrun_t.sh o034b2rv4 C:/dev/occt8-mig/fcD/runs/rv4b2-prof cmd $R/tools/profr4.py > $R/out/profr4.log 2>&1
rm -rf C:/dev/occt8-mig/fcD/runs/rv4b2-prof
TMO=240 bash $R/tools/loop4.sh o034b2rv4 $R/tools/imp4.lst imp > $R/out/loop-imp-d0.log 2>&1
TMO=240 bash $R/tools/loop4.sh o034b2rv4 $R/tools/rv3m.lst rv3m > $R/out/loop-rv3m-d0.log 2>&1
echo CHAIN2-DONE > $R/out/chain2.done
