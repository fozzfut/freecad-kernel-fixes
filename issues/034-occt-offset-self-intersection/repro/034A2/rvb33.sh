#!/bin/bash
# rvstock.sh <binDir> <out.txt> : e1.exe step 1 (the plain offset/thick call) on the 33 stage-B cases with the OCCT DLLs of <binDir>
R=/c/dev/occt8-mig/offset-034b
B=$1; O=$2; : > $O
while read -r tag in op t join rem; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  wi=$(cygpath -w $in); od=$(cygpath -w /c/dev/occt8-mig/offset-034a2/out/b33); mkdir -p /c/dev/occt8-mig/offset-034a2/out/b33
  raw=$(PATH="$B:/usr/bin" timeout 90 "$R/bin/e1.exe" "$wi" $op $t $join $rem "$od" "$tag" 2>/dev/null); rc=$?
  echo "== $tag rc=$rc" >> $O; echo "$raw" | grep -E "^(IN|STOCK)" >> $O
done < $R/runs/k-eval.txt
