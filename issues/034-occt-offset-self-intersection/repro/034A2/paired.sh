#!/bin/bash
# paired.sh <keys> <out.txt> <dirA> <dirB> : per key, offtime with DLL dir A then B back to back (one run each),
# prints "tag msA msB doneA doneB errA errB"; 60 s cap per process
R=/c/dev/occt8-mig/offset-034a2
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
: > $2
while read -r tag in op t join inter self rem; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  line="$tag"
  for d in $3 $4; do
    o=$(PATH="$d:$W:$PATH" timeout 60 $R/bin/offtime.exe run "$(cygpath -w $in)" $op $t $join $inter $self $rem 2>/dev/null | grep '^RES')
    ms=$(echo "$o" | grep -o ' ms=[0-9]*' | cut -d= -f2); dn=$(echo "$o" | grep -o ' done=[0-9]*' | cut -d= -f2); er=$(echo "$o" | grep -o ' err=[-0-9]*' | cut -d= -f2)
    line="$line ${ms:-HANG}/${dn:--}/${er:--}"
  done
  echo "$line" >> $2
done < $1
echo "done $(wc -l < $2)"
