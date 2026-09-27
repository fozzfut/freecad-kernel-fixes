#!/bin/bash
# suite.sh <rc-name> <tag> <TestModule> [gui|cmd] - FreeCAD test module on run copy rc/<rc-name>, fresh cfg copy.
# Layout for fcD/gui/gcompare.py: runs/s-<tag>/{stdout.log,fc.log}
set -u
V=C:/dev/occt8-mig/vr6body
RC=$V/rc/$1; W=$V/runs/s-$2; M=$3; KIND=${4:-gui}
read FREE COMMIT < <(powershell -NoProfile -Command '$o=Get-CimInstance Win32_OperatingSystem; "{0} {1}" -f [int]($o.FreePhysicalMemory/1024),[int]($o.FreeVirtualMemory/1024)' | tr -d '\r')
echo "gate freeRAM=${FREE}MB commit=${COMMIT}MB"
if [ "$FREE" -lt 1000 ] || [ "$COMMIT" -lt 4000 ]; then echo "GATE FAIL"; exit 3; fi
rm -rf "$W"; mkdir -p "$W/cfg"
export FREECAD_USER_HOME=$W/cfg FREECAD_USER_DATA=$V/rc/empty-ud QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1
EXE=$RC/bin/freecad.exe; [ "$KIND" = cmd ] && EXE=$RC/bin/FreeCADCmd.exe
t0=$(date +%s)
bash C:/dev/tools/fcslot.sh timeout -k 15 590 "$EXE" -u "$W/cfg/user.cfg" -s "$W/cfg/system.cfg" \
  --log-file "$W/fc.log" -t "$M" > "$W/stdout.log" 2>&1
echo "rc=$? wall=$(( $(date +%s)-t0 ))s"
grep -E "^Ran |^OK|^FAILED" "$W/stdout.log"
