#!/bin/bash
# run.sh <rc-name> <tag> <probe.py> [hd]   - offscreen GUI run of a probe on run copy rc/<rc-name>.
#   cfg: a fresh COPY per run (fresh = empty cfg dir; hd = copy of the delivery cfg + real userdata with HD).
#   Output: runs/<tag>.txt (PROBE_OUT), runs/<tag>.fc.log. Launch via fcslot, 600 s ceiling, gates checked.
set -u
V=C:/dev/occt8-mig/vr6body
RC=$V/rc/$1; TAG=$2; PROBE=$3; MODE=${4:-fresh}
read FREE COMMIT < <(powershell -NoProfile -Command '$o=Get-CimInstance Win32_OperatingSystem; "{0} {1}" -f [int]($o.FreePhysicalMemory/1024),[int]($o.FreeVirtualMemory/1024)' | tr -d '\r')
echo "gate freeRAM=${FREE}MB commit=${COMMIT}MB"
if [ "$FREE" -lt 1000 ] || [ "$COMMIT" -lt 4000 ]; then echo "GATE FAIL"; exit 3; fi
CFG=$V/runs/cfg-$TAG
rm -rf "$CFG"; mkdir -p "$CFG"
if [ "$MODE" = hd ]; then
  cp $V/rc/dlv-cfg/user.cfg $V/rc/dlv-cfg/system.cfg "$CFG/"
  UD=C:/dev/FreeCAD-occt8-perf/userdata
else
  UD=$V/rc/empty-ud
fi
export FREECAD_USER_HOME=$CFG FREECAD_USER_DATA=$UD QT_QPA_PLATFORM=offscreen PROBE_OUT=$V/runs/$TAG.txt
rm -f "$PROBE_OUT"
bash C:/dev/tools/fcslot.sh timeout -k 15 300 "$RC/bin/freecad.exe" -u "$CFG/user.cfg" -s "$CFG/system.cfg" \
  --log-file "$V/runs/$TAG.fc.log" "$PROBE"
echo "rc=$?"
[ -f "$PROBE_OUT" ] && cat "$PROBE_OUT" || echo "NO PROBE OUTPUT"
