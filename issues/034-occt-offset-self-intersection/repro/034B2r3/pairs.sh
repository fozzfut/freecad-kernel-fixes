#!/bin/bash
# pairs.sh <out> : paired alternating timing (kernel ms from b2h) A2 f5fcd5a0 / r2 81223015 / r3 candidate, 2 rounds
O=$1; : > $O
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
B=/c/dev/occt8-mig/offset-034b2/r3/bin/b2h.exe
D=/c/dev/occt8-mig/offset-034b2/r3c/dll
while read -r name in op t join rem; do
  [ -z "$name" ] && continue
  for round in 1 2; do
    for v in a2 r2 ${CAND:-c1}; do
      ms=$(PATH="$D/$v:$W:/usr/bin" timeout 150 $B "$in" $op $t $join $rem - 0 0 2>/dev/null | grep "^R " | sed -n 's/.* ms=\([0-9]*\) .*/\1/p')
      printf "%-22s round%d %-3s ms=%s\n" "$name" $round $v "${ms:-TIMEOUT}" | tee -a $O
    done
  done
done <<'L'
owner031_off-1 /c/dev/occt8-mig/offset-034b2/r2/cases/owner031.brep offset -1 arc none
owner031_off-0.3 /c/dev/occt8-mig/offset-034b2/r2/cases/owner031.brep offset -0.3 arc none
5829l_thk-1 /c/dev/occt8-mig/offset-034b/cases/f5829_local.brep thick -1 arc 8
bump_d2.8 /c/dev/occt8-mig/offset-034b2/r3c/cases/t_bump_12_12.brep offset -2.8 arc none
ell_d2 /c/dev/occt8-mig/offset-034b2/r3c/cases/ell_a0.brep offset -2 arc none
wave_d1ctl /c/dev/occt8-mig/offset-034b2/r3c/cases/wave_a0.brep offset -1 arc none
L
