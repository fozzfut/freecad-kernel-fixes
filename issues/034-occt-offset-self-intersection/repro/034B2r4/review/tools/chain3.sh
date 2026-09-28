#!/bin/bash
R=/c/dev/occt8-mig/offset-034b2/rv4; F=/c/dev/occt8-mig/offset-034b2/rv3/tools/fcrun_t.sh
until [ -f $R/out/chain2.done ]; do sleep 10; done
FC_OUT=C:/dev/occt8-mig/offset-034b2/rv4/out TMO=300 bash $F o034b2rv4 C:/dev/occt8-mig/fcD/runs/rv4b2-gw cmd $R/tools/gen4w.py > $R/out/gen4w.log 2>&1
FC_OUT=C:/dev/occt8-mig/offset-034b2/rv4/out TMO=500 bash $F o034b2rv4 C:/dev/occt8-mig/fcD/runs/rv4b2-dg cmd $R/tools/diag4.py > $R/out/diag4.log 2>&1
FC_OUT=C:/dev/occt8-mig/offset-034b2/rv4/out DC_LIST=C:/dev/occt8-mig/offset-034b2/rv4/tools/dense.lst TMO=580 bash $F o034b2rv4 C:/dev/occt8-mig/fcD/runs/rv4b2-dc cmd $R/tools/densechk.py > $R/out/dense.log 2>&1
rm -rf C:/dev/occt8-mig/fcD/runs/rv4b2-gw C:/dev/occt8-mig/fcD/runs/rv4b2-dg C:/dev/occt8-mig/fcD/runs/rv4b2-dc
TMO=240 bash $R/tools/loop4.sh o034b2rv4 $R/tools/new4b.lst new4b > $R/out/loop-new4b-d0.log 2>&1
TMO=240 bash $R/tools/loop4.sh o034r2 $R/tools/new4b.lst new4b > $R/out/loop-new4b-a2.log 2>&1
echo CHAIN3 > $R/out/chain3.done
