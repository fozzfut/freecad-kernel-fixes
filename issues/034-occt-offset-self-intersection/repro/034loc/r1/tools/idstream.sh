#!/bin/bash
# idstream.sh <dll dir (unix path)> <tag> : native identity suites of the 034 lanes on one TKOffset (weekly context for the rest)
R=/c/dev/occt8-mig/offset-034a3; T=$R/tools; O=/c/dev/occt8-mig/offset-034loc/id; A=/c/dev/occt8-mig/offset-034a2
D=$1; v=$2
case "$D" in /c/*) ;; *) echo "DLL dir must be a /c/... path (MSYS PATH split pitfall)"; exit 2;; esac
bash $T/runoff.sh $R/runs/k-corpus51.txt $O/corp-$v.txt $D $O/sig-corp-$v
bash $T/runoff.sh $R/runs/k-b33.txt $O/b33-$v.txt $D $O/sig-b33-$v
bash $T/runoff.sh $R/runs/k-study129.txt $O/s129-$v.txt $D $O/sig-s129-$v
bash $T/runa2.sh $R/runs/k-a2class.txt $O/a2c-$v.txt $D
bash $A/rv2/tools/rvxrun.sh $D $O/rvx-$v.txt
bash $A/review/rvrun.sh $D $O/fp-$v.txt
bash $A/r2/x3run.sh $D $O/x3-$v.txt
bash $T/run.sh $R/r3/k-all.txt $O/fam-$v.txt $D
echo IDSTREAM-DONE
