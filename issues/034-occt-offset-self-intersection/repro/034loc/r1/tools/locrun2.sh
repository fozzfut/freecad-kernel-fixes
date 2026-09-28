#!/bin/bash
# locrun2.sh <dll dir (/c/.. form) | dlv> <out> [case regex] [variant] : one loc034 process per case (per variant if given), 60 s cap
# context = delivered OCCT set (C:/dev/FreeCAD-occt8-perf/bin) then weekly; <dll dir> first when given (dlv = delivery as is)
R=/c/dev/occt8-mig/offset-034loc
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
DL=/c/dev/FreeCAD-occt8-perf/bin
if [ "$1" = dlv ]; then P="$DL:$W"; else P="$1:$DL:$W"; fi
PAT="${3:-.}"; VAR="$4"
: > $2
for c in $(PATH="$W:$PATH" $R/bin/${EXE:-loc034}.exe list | tr -d '\r' | grep -E "$PAT"); do
  for v in ${VAR:-all}; do
    a=""; [ "$v" != all ] && a=$v
    o=$(PATH="$P:/usr/bin" timeout 60 $R/bin/${EXE:-loc034}.exe run $c $a 2>/dev/null | tr -d '\r' | grep '^LOC'); rc=$?
    [ -z "$o" ] && o="LOC $c CRASH-OR-HANG rc=$rc var=$v"
    echo "$o" >> $2
  done
done
echo "done $(wc -l < $2)"
