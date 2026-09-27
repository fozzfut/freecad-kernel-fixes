#!/bin/bash
# buildr2.sh: round 2 FreeCADGui builds (gui2 ctl = 3eccec5 sources, gui2 fix = mig/vr6-view2) under the machine build lock
cd /c/dev/occt8-mig/vr6unconf
for v in ctl fix; do
  echo "=== gui2 $v $(date +%T)"
  bash C:/dev/tools/buildlock.sh cmd //c "$(cygpath -w tools/build.bat)" gui2 $v
done
echo "=== ALL-DONE $(date +%T)"
