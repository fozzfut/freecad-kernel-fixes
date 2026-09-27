#!/bin/bash
# idset.sh <dll dir> <tag>: class 144, corpus, probe 116, b33 (delivery context) with the TKOffset of <dll dir>
D=$1; T=$2; B=/c/dev/occt8-mig/offset-034b2/r2/tools; A=/c/dev/occt8-mig/offset-034a2; O=/c/dev/occt8-mig/offset-034b2/r2/runs
DLV=/c/dev/FreeCAD-occt8-perf/bin
cd $A
bash $B/runa2.sh runs/k-class.txt $O/class-$T.txt $D
bash $B/run.sh runs/k-corpus.txt $O/corp-$T.txt $D > /dev/null
bash review/rvrun.sh $D $O/rv116-$T.txt
bash $B/rvb33.sh "$D:$DLV" $O/b33-$T.txt
echo "IDSET-DONE $T"
