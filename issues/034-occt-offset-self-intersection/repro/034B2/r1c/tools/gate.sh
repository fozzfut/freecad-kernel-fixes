#!/bin/bash
# gate.sh <dll dir> <tag> : identity gates of lane B2 r1 (continuation) for one TKOffset build, one process per case
#   class 144 + corpus 51 + study 129 + stage-B 33 (b33, delivery bin context) of offset-034a2, review probe 116,
#   x3 50, rvx 204 (delivery bin context), B2 r1 families famall 552 + k33 (b2h, MC 1000)
case "$1" in *:*) echo "gate: dll dir must be a POSIX path without a colon (PATH split)"; exit 2;; esac
D=$1; T=$2; B=/c/dev/occt8-mig/offset-034b2/r1c/tools
A=/c/dev/occt8-mig/offset-034a2; O=/c/dev/occt8-mig/offset-034b2/r1c/runs; mkdir -p $O
DLV=/c/dev/FreeCAD-occt8-perf/bin; W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
cd $A
bash $B/runa2.sh runs/k-class.txt $O/class-$T.txt $D
bash $B/run.sh runs/k-corpus.txt $O/corp-$T.txt $D /c/dev/occt8-mig/offset-034b2/r1c/out/corp-$T > /dev/null
bash $B/run.sh runs/k-study129.txt $O/s129-$T.txt $D /c/dev/occt8-mig/offset-034b2/r1c/out/s129-$T > /dev/null
bash $B/rvb33.sh "$D:$DLV" $O/b33-$T.txt
bash review/rvrun.sh $D $O/rv116-$T.txt
bash r2/x3run.sh $D $O/x3-$T.txt
bash rv2/tools/rvxrun.sh "$D:$DLV" $O/rvx-$T.txt
cd /c/dev/occt8-mig/offset-034b2
V=${D##*/}; (cd cases && bash ../tools/k.sh "$V" ../runs/famall.txt 1000) > $O/famall-$T.txt 2>&1
(cd cases && bash ../tools/k.sh "$V" ../runs/k33.txt 1000) > $O/k33-$T.txt 2>&1
echo "GATE-DONE $T"
