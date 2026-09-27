#!/bin/bash
# e1run.sh <keys> <out.txt> : key line "tag in op t join remove" -> e1.exe on the stock weekly bin, 60 s watchdog
R=/c/dev/occt8-mig/offset-034b
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
: > $2
mkdir -p $R/out/e1
while read -r tag in op t join rem; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  raw=$(PATH="$W:$PATH" timeout 60 $R/bin/e1.exe "$(cygpath -w $in)" $op $t $join $rem "$(cygpath -w $R/out/e1)" $tag 2>/dev/null)
  rc=$?
  [ $rc = 124 ] && raw="$raw HANG"
  echo "== $tag rc=$rc" >> $2; echo "$raw" >> $2
done < $1
echo done
