#!/bin/sh
# ramgate.sh <min_free_mb> <command...> - run the command once the machine has at least min_free_mb of free RAM.
# The machine rule: a run expected to take more than 1 GB starts only with 4 GB free (VR6 in the GUI takes 1.5-2 GB,
# and 12 parallel test runs once left 2.2 GB of 15.4 GB). run_bench.sh calls this INSIDE its fcslot slot, so the
# check is made right before FreeCAD starts, not before a wait for a slot. Gives up after 30 min (exit 75).
MIN=$1; shift
waited=0
while :; do
  free=$(powershell -NoProfile -Command "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)" 2>/dev/null | tr -d '\r')
  if [ -n "$free" ] && [ "$free" -ge "$MIN" ]; then break; fi
  if [ $((waited % 60)) -eq 0 ]; then echo "[ramgate] free RAM ${free:-?} MB < ${MIN} MB, waiting (${waited}s)" >&2; fi
  if [ "$waited" -ge 1800 ]; then echo "[ramgate] gave up after ${waited}s" >&2; exit 75; fi
  sleep 10; waited=$((waited + 10))
done
echo "[ramgate] free RAM ${free} MB >= ${MIN} MB after ${waited}s" >&2
exec "$@"
