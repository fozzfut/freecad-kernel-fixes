#!/bin/bash
# buildr3.sh: round 3 FreeCADGui builds (gui3 ctl = 3eccec5 sources, gui3 fix = mig/vr6-view3) under the machine build lock
cd /c/dev/occt8-mig/vr6unconf
for v in ctl fix; do
  echo "=== gui3 $v $(date +%T)"
  bash C:/dev/tools/buildlock.sh cmd //c "$(cygpath -w tools/build.bat)" gui3 $v
done
echo "=== ALL-DONE $(date +%T)"
