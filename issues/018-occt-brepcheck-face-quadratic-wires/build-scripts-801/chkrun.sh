#!/usr/bin/env bash
# chkrun.sh <variant> <list> <tag> [par 0|1] [env...]: checkcmp801 check (status dump of every sub-shape) on every
# shape of <list>, one process per shape, TKTopAlgo.dll from C:/dev/occt8-mig/k018/nat/<variant> first in PATH (the
# rest from the weekly bin copy; variant "weekly" = an empty dir, i.e. the weekly's own TKTopAlgo), 1 GB cap.
# out: runs/<tag>/<variant>.tsv, dumps in runs/<tag>/<variant>.d/, rc per shape in runs/<tag>/<variant>.log
K=/c/dev/occt8-mig/k018
V=$1; LIST=$2; TAG=$3; PAR=${4:-0}; shift 4 2>/dev/null || shift $#
mkdir -p $K/runs/$TAG/$V.d
OUT=$K/runs/$TAG/$V
rm -f $OUT.tsv $OUT.log; rm -rf $OUT.d/*
export PATH="$K/nat/$V:/c/dev/occt8-mig/kb1/rc/weekly/bin:$PATH" CHECKCMP_CAP_MB=1024
for kv in "$@"; do export "$kv"; done
cd $K/runs/$TAG
s=$(date +%s)
i=0
while read -r f; do
  [ -z "$f" ] && continue
  echo "$f" > $OUT.one.txt; mkdir -p $OUT.d/tmp
  timeout -k 5 120 $K/bin-tools/checkcmp801.exe check "$(cygpath -m $OUT.one.txt)" 0 1 "$(cygpath -m $OUT.part.tsv)" "$(cygpath -m $OUT.d/tmp)" $PAR >> $OUT.log 2>&1
  rc=$?
  sed "s/^0\t/$i\t/; s/^BEGIN\t0\t/BEGIN\t$i\t/" $OUT.part.tsv >> $OUT.tsv; rm -f $OUT.part.tsv
  mkdir -p $OUT.d/tmp; for d in $OUT.d/tmp/0_*; do [ -e "$d" ] && mv "$d" "$OUT.d/${i}_${d#$OUT.d/tmp/0_}"; done
  echo "RC $rc $i $f" >> $OUT.log
  i=$((i+1))
done < <(tr -d '\r' < $LIST)
rm -f $OUT.one.txt
echo "$V $TAG wall=$(( $(date +%s)-s ))s shapes=$i ok=$(grep -c $'\tOK\t' $OUT.tsv) fail=$(grep -c $'\tFAIL\t' $OUT.tsv) rcX=$(grep -c '^RC [1-9]' $OUT.log)"
