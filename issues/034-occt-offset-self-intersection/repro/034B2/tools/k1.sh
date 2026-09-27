#!/bin/bash
# k1.sh <variant> <mcN> tag f op t join rem [ref] : one case, one line
v=$1; N=$2; tag=$3; f=$4; op=$5; t=$6; join=$7; rem=$8; ref=${9:-0}
case $f in /*|?:*) p=$f;; *) p=C:/dev/occt8-mig/offset-034b2/cases/$f;; esac
rs=${10:--}; case $rs in -) ;; /*|?:*) ;; *) rs=C:/dev/occt8-mig/offset-034b2/cases/$rs;; esac
out=$(/c/dev/occt8-mig/offset-034b2/tools/r.sh $v b2h "$p" $op $t $join $rem - $N $ref $rs | tail -1)
printf "%-26s %-2s %s\n" "$tag" "$v" "$out"
