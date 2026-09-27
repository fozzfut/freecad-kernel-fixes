#!/bin/bash
# runa2.sh <keys> <out.txt> <dll dir or 'stock'> : one a2probe process per key "tag case op t join rem"; 60 s cap
R=/c/dev/occt8-mig/offset-034a2
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
if [ "$3" = stock ]; then P="$W"; else P="$3:$W"; fi
: > $2
while read -r tag c op t join rem; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  o=$(PATH="$P:$PATH" timeout 60 $R/bin/a2probe.exe run "$(cygpath -w $R/cases/$c.brep)" $op $t $join $rem 2>/dev/null | grep '^A2\|READ')
  rc=$?
  [ -z "$o" ] && o="A2 op=$op t=$t join=$join CRASH-OR-HANG"
  echo "$tag $o" >> $2
done < $1
echo "done $(wc -l < $2)"
