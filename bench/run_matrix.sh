#!/bin/sh
# run_matrix.sh <series> <variant> <FC_DIR> [reps=3]
# run_matrix.sh --alternate <series> <reps> <variant>=<FC_DIR> <variant>=<FC_DIR> [...]
#
# The fixed set of files x profiles x actions, repeated <reps> times, under one SERIES id. Tags:
# <series>-<variant>-<label>-<profile>-r<k>; report.py <runs> <series> <base> <variant> compares two variants of one
# series. The series id keeps a new series from ever reusing the tag of an earlier one (final review I3: the tags had
# no series id, and run_bench.sh deleted runs/<tag> first); run_bench.sh also refuses to overwrite a COUNTED run.
# The stock baseline of 22.09 (reports/BASELINE.md) was made before series ids: its tags are <variant>-<label>-...,
# report.py and tools/baseline.py address it as series "baseline", and that name is reserved (it is never run again).
# Series and variant names: letters, digits, "_".
#
# --alternate (spec §11, ruling of 22.09 on I3): several variants in ONE session, interleaved per file, profile and
# rep, so every variant sees the same machine load. The variant order is rotated per rep: with A and B each file and
# profile runs A B in rep 1, B A in rep 2, A B in rep 3 (A-B-B-A-A-B over the reps: neither side always goes first).
# DRY=1 prints the planned order (one line per run, with its FC_DIR) and runs nothing.
#
# Order (ruling 22.09): one full pass over every file x profile first (rep 1), then reps 2..<reps>.
# One FreeCAD at a time (fcslot inside run_bench.sh).
# A run counts only if its result.json has an EMPTY errors object (ruling 22.09), not just exit=0. A counted run is
# never run again: its tag is skipped (SKIP-counted), so a series that stopped half-way is resumed by the same call.
# Env:
#   ONLY="<tag> <tag> ..."  run just these tags (reruns of failed runs; the failed directory is kept as
#                           runs/<tag>.old-<time> by run_bench.sh);
#   REPS_FROM=<k>           start at rep k (default 1);
#   SET=small|big|all       only the runs that fit in 4 GB free RAM, only the 8 GB ones (s5000, holes), or all
#                           (default). When 8 GB is not free, run SET=small for every rep first and SET=big last, so
#                           a wait for RAM does not hold up the rest (stock baseline, 22.09).
#   DRY=1                   print the plan, run nothing.
# s1000/s5000 are the *_vis copies: the synthetic files were written by FreeCADCmd (no GuiDocument.xml), so in the GUI
# every part opened hidden and the runs measured an empty scene (runs/stock-s1000-fc-r1: 0 hover hits, 0 select
# targets); files/synthetic_1000_copies_vis.FCStd = tools/make_visible.sh, files/synthetic_5000_copies_vis.FCStd =
# tools/add_gui_visibility.py (same scene: runs/t4-s1000vis-probe vs runs/t4-s1000xml-probe). Parts get the owner's
# default tessellation (6.4 deg); a visible s1000 opens in ~155 s and peaks at 2 GB working set, so s5000 also waits
# for 8 GB free RAM.
# fixture:holes1024 (open peaks at 7.1 GB working set) starts only with >= 8 GB free RAM (ruling 22.09): ramgate
# waits at most 10 min, ONE try (ruling 22.09 15:35, final review I5: the waits hold fcslot slots), then the run is
# recorded as SKIP-lowmem (runs/<tag>/SKIP-lowmem), and the later 8 GB runs of the same matrix call are recorded
# SKIP-lowmem at once (the machine's RAM did not free up); rerun them later with SET=big.
# The owner's 600 s ceiling per FreeCAD run (ruling 22.09): the holes run does 2 fillet edits per run
# (BENCH_FILLET_REPS=2; 4 edits took 540 of 600 s at 78 % load, runs/t3-holes-r1), never a longer timeout.
# Prints one line per run: "<time> <tag> <verdict> <run_bench line> wall=<s>", verdict COUNTED | FAILED | SKIP-lowmem
# | SKIP-counted | KEPT-counted.
set -u
usage() {
  echo "usage: run_matrix.sh <series> <variant> <FC_DIR> [reps=3]" >&2
  echo "       run_matrix.sh --alternate <series> <reps> <variant>=<FC_DIR> <variant>=<FC_DIR> [...]" >&2
  exit 2
}
okname() { case "$1" in ""|*[!A-Za-z0-9_]*) return 1 ;; esac; return 0; }
VARS=""
addvar() {  # addvar <variant> <FC_DIR>
  okname "$1" || { echo "bad variant name '$1': letters, digits, _ only" >&2; exit 2; }
  case " $VARS " in *" $1 "*) echo "variant '$1' given twice" >&2; exit 2 ;; esac
  [ -x "$2/bin/FreeCAD.exe" ] || [ -f "$2/bin/FreeCAD.exe" ] || { echo "no $2/bin/FreeCAD.exe (variant $1)" >&2; exit 2; }
  VARS="$VARS $1"
  eval "FC_$1=\$2"
}
if [ "${1:-}" = "--alternate" ]; then
  shift
  [ $# -ge 4 ] || usage
  SERIES=$1; REPS=$2; shift 2
  for pair in "$@"; do
    case "$pair" in *=*) addvar "${pair%%=*}" "${pair#*=}" ;; *) usage ;; esac
  done
else
  [ $# -ge 3 ] && [ $# -le 4 ] || usage
  case "$2" in */*|*:*) echo "the first argument is now the series id: run_matrix.sh <series> <variant> <FC_DIR> [reps]" >&2; exit 2 ;; esac
  SERIES=$1; REPS=${4:-3}
  addvar "$2" "$3"
fi
okname "$SERIES" || { echo "bad series id '$SERIES': letters, digits, _ only" >&2; exit 2; }
[ "$SERIES" != baseline ] || { echo "series 'baseline' is the stock baseline of 22.09 (tags without a series id): reserved" >&2; exit 2; }
case "$REPS" in ""|*[!0-9]*) echo "bad reps '$REPS'" >&2; exit 2 ;; esac
HERE=C:/dev/freecad-kernel-fixes/bench
F=$HERE/files
cd "$HERE" || exit 2
CUT_VR6=$(sed -n 's/^BENCH_CUT_BASE для VR6 = \([A-Za-z0-9_]*\).*/\1/p' README.md)
CUT_CUR=$(sed -n 's/^BENCH_CUT_BASE для VR6-current = \([A-Za-z0-9_]*\).*/\1/p' README.md)
if [ -z "$CUT_VR6" ] || [ -z "$CUT_CUR" ]; then echo "BENCH_CUT_BASE lines not found in README.md" >&2; exit 2; fi
FIRST=$(echo $VARS | cut -d' ' -f1)
eval "PY=\"\$FC_$FIRST/bin/python.exe\""

counted() {   # runs/<tag>/result.json exists and its errors object is empty
  [ -f "runs/$1/result.json" ] && "$PY" -c "import json,sys; r=json.load(open(sys.argv[1],encoding='utf-8')); sys.exit(0 if not (r.get('errors') or {}) and r.get('actions') else 1)" "runs/$1/result.json" 2>/dev/null
}

kill_orphans() {  # FreeCAD.exe still running with this run's own -u path (timeout kills the wrapper, not FreeCAD)
  T=$1 powershell -NoProfile -Command '$p = "freecad-kernel-fixes/bench/runs/" + $env:T + "/"; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "FreeCAD.exe" -and $_.CommandLine -and $_.CommandLine.Replace([string][char]92, "/").Contains($p) } | ForEach-Object { "killed orphan " + $_.ProcessId + ": " + $_.CommandLine; Stop-Process -Id $_.ProcessId -Force }' 2>&1
}

one() {  # one <tag> <variant> <FC_DIR> <profile> <file> <label> <actions> [ENV=VAL ...]
  TAG=$1; V=$2; FC=$3; P=$4; FILE=$5; LBL=$6; ACT=$7; shift 7
  if [ -n "${ONLY:-}" ]; then case " $ONLY " in *" $TAG "*) ;; *) return ;; esac; fi
  if [ "${DRY:-0}" = 1 ]; then echo "DRY $TAG variant=$V fc=\"$FC\" $P $FILE $ACT $*"; return; fi
  if counted "$TAG"; then echo "$(date '+%F %T') $TAG SKIP-counted"; return; fi
  T0=$(date +%s)
  case " $* " in *" BENCH_MIN_FREE_MB=8192 "*)
    if [ -f "runs/.lowmem-$$" ]; then   # this matrix already waited 10 min for 8 GB in vain: the machine has not changed
      mkdir -p "runs/$TAG"; echo "not started: $(cat "runs/.lowmem-$$")" > "runs/$TAG/SKIP-lowmem"
      echo "$(date '+%F %T') $TAG SKIP-lowmem (after $(cat "runs/.lowmem-$$"))"; return
    fi ;;
  esac
  LINE=$(env BENCH_SERIES="$SERIES" "$@" ./run_bench.sh "$TAG" "$V" "$P" "$FC" "$FILE" "$LBL" "$ACT" 2>"runs/.$TAG.stderr" | tail -n 1)
  ORPH=$(kill_orphans "$TAG")
  mkdir -p "runs/$TAG"; mv -f "runs/.$TAG.stderr" "runs/$TAG/run_bench.stderr" 2>/dev/null
  if [ -n "$ORPH" ]; then echo "$ORPH" > "runs/$TAG/orphans.log"; fi
  case "$LINE" in
    exit=75*) VERDICT=SKIP-lowmem; echo "ramgate gave up after 10 min waiting for free RAM ($*)" > "runs/$TAG/SKIP-lowmem"
              echo "$TAG waited 10 min for 8 GB free RAM, $(date '+%F %T')" > "runs/.lowmem-$$" ;;
    exit=4*) VERDICT=KEPT-counted ;;
    *) if counted "$TAG"; then VERDICT=COUNTED; else VERDICT=FAILED; fi ;;
  esac
  echo "$(date '+%F %T') $TAG $VERDICT $LINE wall=$(( $(date +%s) - T0 ))${ORPH:+ ORPHANS-KILLED}"
}

order() {  # the variants in rep <k>'s order: rotated by k-1
  n=$(echo $VARS | wc -w); s=$(( ($1 - 1) % n )); i=0; head=""; tail=""
  for v in $VARS; do
    if [ $i -lt $s ]; then tail="$tail $v"; else head="$head $v"; fi
    i=$((i + 1))
  done
  echo $head $tail
}

cell() {  # cell <profile> <file> <label> <actions> [ENV=VAL ...]: this file and profile for every variant, rep k
  P=$1; FILE=$2; LBL=$3; ACT=$4; shift 4
  for v in $(order "$k"); do
    eval "FCV=\"\$FC_$v\""
    one "$SERIES-$v-$LBL-$P-r$k" "$v" "$FCV" "$P" "$FILE" "$LBL" "$ACT" "$@"
  done
}

echo "$(date '+%F %T') series $SERIES, variants:$VARS, reps $REPS"
k=${REPS_FROM:-1}
while [ "$k" -le "$REPS" ]; do
  [ "${SET:-all}" = big ] || for P in fc hd; do
    cell $P $F/VR6-current.FCStd vr6cur open,orbit,hover,select,edit_cut,save BENCH_CUT_BASE=$CUT_CUR
    cell $P $F/VR6-350-new.FCStd vr6 open,orbit,hover,select,edit_cut,save BENCH_CUT_BASE=$CUT_VR6
    cell $P $F/owner_oring.FCStd oring open,orbit,hover,select,edit_body,save BENCH_BODY_OBJ=Pad
    cell $P $F/synthetic_1000_copies_vis.FCStd s1000 open,orbit,hover,select,save
  done
  [ "${SET:-all}" = small ] || for P in fc hd; do   # the runs that need 8 GB free RAM go last in a pass: a wait for RAM does not hold up the rest
    cell $P $F/synthetic_5000_copies_vis.FCStd s5000 open,orbit,hover,select BENCH_MIN_FREE_MB=8192
    cell $P fixture:holes1024 holes open,fillet_holes BENCH_FILLET_REPS=2 BENCH_MIN_FREE_MB=8192
  done
  k=$((k + 1))
done
rm -f "runs/.lowmem-$$"
echo "$(date '+%F %T') matrix done"
