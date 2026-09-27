#!/bin/bash
# kp.sh <variants> <caselist> [mcN] [P] : parallel (P processes, default 3), output sorted by tag then variant
VS=$1; L=$2; N=${3:-800}; P=${4:-3}
grep -v '^#' $L | grep -v '^\s*$' | while read -r line; do for v in $VS; do echo "$v $N $line"; done; done \
 | xargs -P $P -L 1 /c/dev/occt8-mig/offset-034b2/tools/k1.sh | sort -k1,1 -k2,2
