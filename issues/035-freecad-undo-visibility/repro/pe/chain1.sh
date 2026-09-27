#!/bin/bash
# chain1.sh: the lane's probe runs one after another (one FreeCAD at a time)
cd /c/dev/occt8-mig/undovis-pe
PV=C:/dev/occt8-mig/undovis-pe/probe/pvprobe.py
UV=C:/dev/occt8-mig/undovis/probe/uvprobe.py
bash tools/pvrun.sh fix uv-fix-fresh fresh $UV > runs/uv-fix-fresh.out 2>&1
UV_PREF_OFF=1 bash tools/pvrun.sh fix pv-fix-prefoff fresh $PV > runs/pv-fix-prefoff.out 2>&1
bash tools/pvrun.sh dlv pv-dlv-fresh fresh $PV > runs/pv-dlv-fresh.out 2>&1
PV_ATV=1 bash tools/pvrun.sh dlv pv-dlv-atv fresh $PV > runs/pv-dlv-atv.out 2>&1
PV_ATV=1 bash tools/pvrun.sh fix pv-fix-atv fresh $PV > runs/pv-fix-atv.out 2>&1
bash tools/pvrun.sh fix pv-fix-owner owner $PV > runs/pv-fix-owner.out 2>&1
bash tools/pvrun.sh fix uv-fix-owner owner $UV > runs/uv-fix-owner.out 2>&1
echo CHAIN-DONE > runs/chain1.done
