#!/bin/bash
# mk.sh: rvn_full.py = rvhelp.py + rvn.py (FreeCADCmd runs a script with split globals/locals; one flat file avoids exec)
cd /c/dev/occt8-mig/offset-034b2/rv2 && { cat rvhelp.py; grep -v '^#HELPERS' rvn.py; } > rvn_full.py
