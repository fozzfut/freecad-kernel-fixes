#!/bin/bash
# insp.sh <keys> <out.txt>: exact-offset distance test (offstudy inspect) on every saved result of the keys
R=/c/dev/occt8-mig/offset-study
W=${OCCBIN:-/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin}
: > $2
while read -r tag in op t rest; do f=$R/out/$tag.brep; [ -f "$f" ] || continue
  o=$(PATH="$W:$PATH" timeout 120 $R/bin/offstudy.exe inspect "$(cygpath -w $f)" "$(cygpath -w $in)" $t 2>/dev/null | grep ^INS); echo "$tag ${o:-INS TIMEOUT/CRASH rc=$?}" >> $2
done < $1
