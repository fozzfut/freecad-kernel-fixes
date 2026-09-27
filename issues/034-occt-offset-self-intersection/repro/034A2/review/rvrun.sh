#!/bin/bash
# rvrun.sh <dll dir|stock> <out> : one rva2 process per case, 60 s cap
R=/c/dev/occt8-mig/offset-034a2/review
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
if [ "$1" = stock ]; then P="$W"; else P="$1:$W"; fi
: > $2
for c in $(PATH="$W:$PATH" $R/rva2.exe list | tr -d '\r'); do
  o=$(PATH="$P:$PATH" timeout 60 $R/rva2.exe run $c 2>/dev/null | grep '^RV'); rc=$?
  [ -z "$o" ] && o="RV $c CRASH-OR-HANG rc=$rc"
  echo "$o" >> $2
done
echo "done $(wc -l < $2)"
