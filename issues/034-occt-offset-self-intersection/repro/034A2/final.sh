#!/bin/bash
cd /c/dev/occt8-mig/offset-034a2
bash C:/dev/tools/buildlock.sh cmd //c "$(cygpath -w build/m034a2/build.bat)" | tail -1
md5sum build/a2/TKOffset.dll build/m034a2/TKOffset.dll
bash tools/suite.sh
bash tools/fcsuite.sh
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
for f in /c/dev/occt8-mig/corpus/bop_plate_1024.brep /c/dev/occt8-mig/corpus/VR6-350-new-part4.step /c/dev/occt8-mig/fillet-corner/sweep/in/hicmos_peltier.brep /c/dev/occt8-mig/fillet-corner/sweep/in/Top.brep; do for i in 1 2; do PATH="$W:$PATH" bin/a2probe.exe stime "$(cygpath -w $f)"; done; done > runs/stime.txt
echo FINAL-DONE
