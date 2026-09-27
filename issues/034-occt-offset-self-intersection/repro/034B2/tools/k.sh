#!/bin/bash
# k.sh <variants "w a d"> <caselist> [mcN] : one b2h process per case and variant; caselist lines: tag file op t join remove [ref]
VS=$1; L=$2; N=${3:-3000}
while read -r tag f op t join rem ref; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  case $f in /*|?:*) p=$f;; *) p=C:/dev/occt8-mig/offset-034b2/cases/$f;; esac
  for v in $VS; do
    out=$(/c/dev/occt8-mig/offset-034b2/tools/r.sh $v b2h "$p" $op $t $join $rem - $N ${ref:-0} | tail -1)
    printf "%-26s %-2s %s\n" "$tag" "$v" "$out"
  done
done < $L
