#!/bin/bash
# evalrun.sh <keys> <method db|su|eu> <out.txt> [from] [to] : one harness process per case (weekly stock bin, job cap 1 GB,
# watchdog TMO s, default 120). db = e1 (deblend), su = e5 stock self-union, eu = e5 element union.
R=/c/dev/occt8-mig/offset-034b
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
M=$2; O=$3; FROM=${4:-1}; TO=${5:-999}
mkdir -p $R/out/eval
n=0
while read -r tag in op t join rem; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  n=$((n+1)); [ $n -lt $FROM ] && continue; [ $n -gt $TO ] && break
  wi=$(cygpath -w $in); od=$(cygpath -w $R/out/eval)
  case $M in
    db) cmd=("$R/bin/e1.exe" "$wi" $op $t $join $rem "$od" "$tag");;
    su) cmd=("$R/bin/e5.exe" "$wi" $op $t $join $rem stock 4 "$od" "$tag");;
    eu) cmd=("$R/bin/e5.exe" "$wi" $op $t $join $rem union 4 "$od" "$tag");;
  esac
  s0=$(date +%s)
  raw=$(PATH="$W:$PATH" timeout ${TMO:-120} "${cmd[@]}" 2>/dev/null)
  rc=$?
  k=""; [ $rc = 124 ] && k=HANG; [ $rc -ne 0 ] && [ $rc -ne 124 ] && k="CRASH($rc)"
  echo "== $tag $M rc=$rc $k wall=$(( $(date +%s) - s0 ))s" >> $O; echo "$raw" >> $O
done < $1
echo done $n
