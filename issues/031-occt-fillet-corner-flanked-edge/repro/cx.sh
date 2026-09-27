#!/bin/bash
# cx.sh <tag> <mode> [split] [floor]: the 6 fixed cases with the experimental DLL; dumps; regularity/crease report
R=/c/dev/occt8-mig/fillet-corner-r3; T=$1
mkdir -p $R/out/x/$T; rm -f $R/out/x/$T/*
CHFI3D_031_MODE=$2 CHFI3D_031_SPLIT=${3:-10} CHFI3D_031_FLOOR=${4:-10} FS3_DUMP=$(cygpath -m $R/out/x/$T) bash $R/tools/drive3.sh ${DLL:-$R/build/exp1} x-$T ${KEYS:-$R/runs/cases.txt} | tail -1
for f in $R/out/x/$T/case_*.brep; do echo "== $(basename $f)"; PATH="${DLL:-$R/build/exp1}:/c/dev/FreeCAD-occt8-perf/bin:$PATH" /c/dev/occt8-mig/fillet-corner-rv2/bin/rv2reg.exe $(cygpath -w $f) | grep -v "^REG" ; done > $R/runs/reg-$T.txt
