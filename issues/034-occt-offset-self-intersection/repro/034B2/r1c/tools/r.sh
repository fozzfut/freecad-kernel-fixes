#!/bin/bash
# r.sh <variant w|a|d|...> <prog> <args...> : run with the weekly OCCT on PATH; the variant dir's TKOffset.dll (if any) wins
V=$1; shift; P=$1; shift
W=/c/dev/FreeCAD-occt8/FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental/bin
D=/c/dev/occt8-mig/offset-034b2/v/$V
PATH="$D:$W:/usr/bin" timeout -k 5 ${TMO:-60} "$D/$P.exe" "$@"
rc=$?; [ $rc = 124 ] && echo "R HANG rc=124"; [ $rc -ne 0 ] && [ $rc -ne 124 ] && echo "R CRASH rc=$rc"; exit 0
