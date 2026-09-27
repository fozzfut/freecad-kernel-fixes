#!/bin/bash
# run.sh <keys> <out.txt> : each key line "tag in op t join inter self remove" -> one offstudy process on STOCK
# OCCT 8.0.1 (FreeCAD weekly 2026.09.23 bin, untouched), watchdog 60 s (HANG), crash -> CRASH rc
R=/c/dev/occt8-mig/offset-study
W=${OCCBIN:-/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin}
: > $2
while read -r tag in op t join inter self rem; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  raw=$(PATH="$W:$PATH" timeout 60 $R/bin/offstudy.exe run "$(cygpath -w $in)" $op $t $join $inter $self $rem ${SAVE:+$(cygpath -w $R/out/$tag.brep)} 2>/dev/null)
  rc=$?
  o=$(echo "$raw" | grep '^RES\|READ')
  if [ -z "$o" ]; then k=CRASH; [ $rc = 124 ] && k=HANG; o="RES op=$op t=$t join=$join inter=$inter self=$self grade=$k rc=$rc"; fi
  echo "$tag $o" >> $2
done < $1
echo "done $(wc -l < $2)"
