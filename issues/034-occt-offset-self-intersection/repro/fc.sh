#!/bin/bash
# fc.sh <tag>: one FreeCADCmd run of fcconf.py on the delivery C:/dev/FreeCAD-occt8-perf (TKOffset = stock weekly md5 67f22d0d)
R=C:/dev/occt8-mig/offset-study; T=$1
export FREECAD_USER_HOME=$(cygpath -w $R/home) PYTHONDONTWRITEBYTECODE=1 FC_OUT="$(cygpath -w $R/runs/$T.txt)"
bash C:/dev/occt8-mig/hd-compat/bin/gate.sh >/dev/null || { echo "NOT RUN gate"; exit 75; }
t0=$(date +%s)
bash C:/dev/tools/fcslot.sh timeout -k 15 300 C:/dev/FreeCAD-occt8-perf/bin/FreeCADCmd.exe -u "$(cygpath -w $R/home/user.cfg)" -s "$(cygpath -w $R/home/system.cfg)" "$(cygpath -w $R/tools/fcconf.py)" > $R/runs/$T.stdout 2>&1
echo "rc=$? wall=$(( $(date +%s)-t0 ))s"
