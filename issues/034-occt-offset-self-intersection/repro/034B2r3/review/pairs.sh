#!/bin/bash
# pairs.sh: paired alternating kernel timing (RV_NOCHK: offset call only), free RAM/commit recorded before each run
cd /c/dev/occt8-mig/offset-034b2/rv3; : > out/pairs.txt
CASES=${CASES:-"rev_a_off-0.8_ctl rev_a_off-2 rev_a_off-2_int tri_a_off-1.5_ctl"}
for i in 1 2; do for rc in o034b2rv3 o034r2; do
  m=$(powershell -NoProfile -Command "\$o=Get-CimInstance Win32_OperatingSystem; ''+[int](\$o.FreePhysicalMemory/1024)+'/'+[int](\$o.FreeVirtualMemory/1024)" | tr -d '\r')
  RV_NOCHK=1 TMO=150 bash loop.sh $rc rev,tri.pair$i $CASES > /dev/null 2>&1
  sed "s#^#$rc round$i freeRAM/commit=${m}MB #" out/$rc-rev,tri.pair$i/summary.txt >> out/pairs.txt
done; done
cat out/pairs.txt
