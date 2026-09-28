#!/bin/bash
# locrun.sh <dll dir (/c/.. form)|stock> <out> [case regex] : one loc034 process per case, 60 s cap
R=/c/dev/occt8-mig/offset-034loc
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
if [ "$1" = stock ]; then P="$W"; else P="$(cygpath -u "$1"):$W"; fi
PAT="${3:-.}"
: > $2
for c in $(PATH="$W:$PATH" $R/bin/${EXE:-loc034}.exe list | tr -d '\r' | grep -E "$PAT"); do
  o=$(PATH="$P:$PATH" timeout 60 $R/bin/${EXE:-loc034}.exe run $c 2>/dev/null | grep '^LOC'); rc=$?
  [ -z "$o" ] && o="LOC $c CRASH-OR-HANG rc=$rc"
  echo "$o" >> $2
done
echo "done $(wc -l < $2)"
