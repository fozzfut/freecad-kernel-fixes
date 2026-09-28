#!/bin/bash
# fam.sh <dll dir> <list> <out.txt> [outdir] : issue 034 B2 r3 family runner (test side)
# list line: name in op t join rem refArea axis pos plc   (refArea 0 = no exact reference)
# verdict: ERR (the kernel reports an error), EXACT (valid + BOP clean + every result face at |t| or on S by the
# distance oracle + MC membership 0 bad + the cross-section area = the exact reference within 1e-7 rel),
# ORACLE (the same without an exact reference), WRONG (anything else with a result).
DLL=$1; LIST=$2; OUT=$3; OD=${4:-/c/dev/occt8-mig/offset-034b2/r3c/res}
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
B=/c/dev/occt8-mig/offset-034b2/r3/bin/b2h.exe
X=/c/dev/occt8-mig/offset-034b2/r3c/bin/xa.exe
mkdir -p $OD; : > $OUT
while read -r name in op t join rem ref ax pos plc rest; do
  [ -z "$name" ] && continue; case "$name" in \#*) continue;; esac
  case "$in" in /*|C:*) ;; *) in=/c/dev/occt8-mig/offset-034b2/r3c/cases/$in;; esac
  rm -f $OD/$name.brep
  line=$(PATH="$DLL:$W:/usr/bin" timeout -k 5 ${TMO:-150} "$B" "$in" $op $t $join $rem "$(cygpath -w $OD/$name.brep)" ${MC:-300} 0 2>/dev/null | grep "^R " | tail -1)
  [ -z "$line" ] && line="R HANG/CRASH"
  v=$(echo "$line" | awk '{print $2}')
  area="-"; rel="-"
  if [ "$v" = "EXACT" ] || [ "$v" = "EXACT?" ]; then
    if [ "$ref" != "0" ] && [ -f $OD/$name.brep ]; then
      area=$(PATH="$W:/usr/bin" timeout 60 $X $OD/$name.brep $ax $pos $plc | sed -n 's/.*area=//p')
      rel=$(python -c "a=float('${area:-0}'); r=float('$ref'); print('%.2e' % (abs(a-r)/r))")
      ok=$(python -c "print(1 if float('$rel')<=1e-7 else 0)")
      [ "$ok" = 1 ] && [ "$v" = "EXACT" ] && V=EXACT || V=WRONG
    else
      [ "$v" = "EXACT" ] && V=ORACLE || V=WRONG
    fi
  elif [ "$v" = "ERROR" ]; then V=ERR
  else V=WRONG; fi
  printf "%-26s %-6s xa=%s rel=%s | %s\n" "$name" "$V" "$area" "$rel" "$(echo "$line" | cut -c3-190)" | tee -a $OUT
done < $LIST
