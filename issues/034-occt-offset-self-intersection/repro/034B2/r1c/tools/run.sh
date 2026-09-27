#!/bin/bash
# run.sh <keys> <out.txt> <variant: stock|p034|t034|m034|control> [outdir]
# one offstudy process per key line "tag in op t join inter self remove"; DLL of the variant first in PATH
# (stock = FreeCAD weekly 2026.09.23 bin, untouched). 60 s watchdog -> HANG. Saves result BREPs into outdir if given.
R=/c/dev/occt8-mig/offset-034a2
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
V=$3; OD=$4
if [ "$V" = stock ]; then P="$W"; elif [ -d "$V" ]; then P="$V:$W"; else P="$R/build/$V:$W"; fi
: > $2
[ -n "$OD" ] && mkdir -p $OD
while read -r tag in op t join inter self rem; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  sv=""; [ -n "$OD" ] && sv=$(cygpath -w $OD/$tag.sig) && rm -f $OD/$tag.sig
  raw=$(PATH="$P:$PATH" timeout 60 $R/bin/off034.exe run "$(cygpath -w $in)" $op $t $join $inter $self $rem $sv 2>/c/dev/occt8-mig/offset-034b2/r1c/runs/stderr.tmp)
  rc=$?
  o=$(echo "$raw" | grep '^RES\|READ')
  if [ -z "$o" ]; then k=CRASH; [ $rc = 124 ] && k=HANG; o="RES op=$op t=$t join=$join inter=$inter self=$self grade=$k rc=$rc"; fi
  g=$(grep G034 /c/dev/occt8-mig/offset-034b2/r1c/runs/stderr.tmp | tr '\n' ' ')
  echo "$tag $o ${g:+TRACE[ $g]}" >> $2
done < $1
echo "done $(wc -l < $2)"
