#!/bin/bash
cd /c/dev/occt8-mig/offset-034a2
A=$PWD/build/a2; M=$PWD/build/m034a2; F=/c/dev/occt8-mig/offset-034/build/final
bash tools/runa2.sh runs/k-class.txt runs/class-a2.txt $A
bash tools/runa2.sh runs/k-class.txt runs/class-m034a2.txt $M
for v in "$A:a2" "$M:m034a2"; do d=${v%:*}; n=${v##*:}; bash tools/run.sh runs/k-corpus.txt runs/corp-$n.txt $d out/corp-$n >/dev/null; done
bash tools/run.sh runs/k-study129.txt runs/s129-a2.txt $A out/s129-a2 >/dev/null
for v in "$F:final" "$A:a2"; do d=${v%:*}; n=${v##*:}; bash tools/run.sh runs/k-tanint.txt runs/tanint-$n.txt $d out/tanint-$n >/dev/null; done
bash tools/rvb33.sh "$A:/c/dev/FreeCAD-occt8-perf/bin" runs/b33-a2.txt
echo SUITE-DONE
