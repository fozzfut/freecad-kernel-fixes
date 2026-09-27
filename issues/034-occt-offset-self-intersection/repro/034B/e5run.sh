#!/bin/bash
# e5run.sh <keys> <out.txt> : key line "tag in op t join remove src N" -> e5.exe on the stock weekly bin, 120 s watchdog
R=/c/dev/occt8-mig/offset-034b
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
: > $2
mkdir -p $R/out/e5
while read -r tag in op t join rem src n; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  raw=$(PATH="$W:$PATH" timeout ${TMO:-120} $R/bin/e5.exe "$(cygpath -w $in)" $op $t $join $rem $src ${n:-4} "$(cygpath -w $R/out/e5)" $tag 2>/dev/null)
  rc=$?
  [ $rc = 124 ] && raw="$raw HANG"
  echo "== $tag $src rc=$rc" >> $2; echo "$raw" >> $2
done < $1
echo done
