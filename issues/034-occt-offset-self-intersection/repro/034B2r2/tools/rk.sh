#!/bin/bash
# rk.sh <variant dirs under v/> <caselist> [grep-filter] : one b2h per case/variant, ref volume + ref shape (sd)
VS=$1; L=$2; F=${3:-.}
C=/c/dev/occt8-mig/offset-034b2/r2/cases
grep -E "$F" $L | while read -r tag f op t join rem ref rs; do
  [ -z "$tag" ] && continue; [[ "$tag" == \#* ]] && continue
  case $rs in -|?:*|/*) ;; *) rs=$C/$rs;; esac
  case $f in ?:*|/*) ;; *) f=$C/$f;; esac
  for v in $VS; do
    out=$(/c/dev/occt8-mig/offset-034b2/tools/r.sh $v b2h "$f" $op $t $join $rem - ${MC:-0} ${ref:-0} $rs | tail -1)
    printf "%-28s %-3s %s\n" "$tag" "$v" "$out"
  done
done
