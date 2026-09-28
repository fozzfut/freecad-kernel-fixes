#!/bin/bash
R=/c/dev/occt8-mig/offset-034b2/rv4; F=/c/dev/occt8-mig/offset-034b2/rv3/tools/fcrun_t.sh
until [ -f $R/out/chain3.done ]; do sleep 10; done
FC_OUT=C:/dev/occt8-mig/offset-034b2/rv4/out TMO=580 bash $F o034b2rv4 C:/dev/occt8-mig/fcD/runs/rv4b2-bc cmd $R/tools/boolchk.py > $R/out/boolchk.log 2>&1
rm -rf C:/dev/occt8-mig/fcD/runs/rv4b2-bc
TMO=240 bash $R/tools/loop4.sh o034r2 $R/tools/imp4.lst imp ring_a_off-1.5 ring_a_off-2.5 rv2_w_off-1.5 rv3_w_off-2 tr5_w_off-3 ob2_w_off-3 > $R/out/loop-imp-a2.log 2>&1
echo CHAIN4 > $R/out/chain4.done
