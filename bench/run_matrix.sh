#!/bin/sh
# run_matrix.sh <variant> <FC_DIR> [reps=3] - the fixed set of files x profiles x actions, repeated <reps> times.
# Order (ruling 22.09): one full pass over every file x profile first (rep 1), then reps 2..<reps>.
# One FreeCAD at a time (fcslot inside run_bench.sh). Tags: <variant>-<label>-<profile>-r<k>.
#
# A run counts only if its result.json has an EMPTY errors object (ruling 22.09), not just exit=0.
# Env:
#   ONLY="<tag> <tag> ..."  run just these tags (reruns of failed runs);
#   RESUME=1                skip a tag whose runs/<tag>/result.json already counts;
#   REPS_FROM=<k>           start at rep k (default 1);
#   SET=small|big|all       only the runs that fit in 4 GB free RAM, only the 8 GB ones (s5000, holes), or all
#                           (default). When 8 GB is not free, run SET=small for every rep first and SET=big last, so
#                           a wait for RAM does not hold up the rest (stock baseline, 22.09).
# s1000/s5000 are the *_vis copies: the synthetic files were written by FreeCADCmd (no GuiDocument.xml), so in the GUI
# every part opened hidden and the runs measured an empty scene (runs/stock-s1000-fc-r1: 0 hover hits, 0 select
# targets); files/synthetic_1000_copies_vis.FCStd = tools/make_visible.sh, files/synthetic_5000_copies_vis.FCStd =
# tools/add_gui_visibility.py (same scene: runs/t4-s1000vis-probe vs runs/t4-s1000xml-probe). Parts get the owner's
# default tessellation (6.4 deg); a visible s1000 opens in ~155 s and peaks at 2 GB working set, so s5000 also waits
# for 8 GB free RAM.
# fixture:holes1024 (open peaks at 7.1 GB working set) starts only with >= 8 GB free RAM (ruling 22.09): ramgate
# waits 30 min per try, two tries = 60 min, then the run is recorded as SKIP-lowmem (runs/<tag>/SKIP-lowmem), and the
# later 8 GB runs of the same matrix call are recorded SKIP-lowmem at once (60 min each would add hours on a machine
# whose RAM did not free up); rerun them later with SET=big RESUME=1.
# The owner's 600 s ceiling per FreeCAD run (ruling 22.09): the holes run does 2 fillet edits per run
# (BENCH_FILLET_REPS=2; 4 edits took 540 of 600 s at 78 % load, runs/t3-holes-r1), never a longer timeout.
# Prints one line per run: "<time> <tag> <verdict> <run_bench line> wall=<s>", verdict COUNTED | FAILED | SKIP-lowmem.
set -u
if [ $# -lt 2 ]; then echo "usage: run_matrix.sh <variant> <FC_DIR> [reps]" >&2; exit 2; fi
V=$1; FC=$2; REPS=${3:-3}
HERE=C:/dev/freecad-kernel-fixes/bench
F=$HERE/files
cd "$HERE" || exit 2
CUT_VR6=$(sed -n 's/^BENCH_CUT_BASE для VR6 = \([A-Za-z0-9_]*\).*/\1/p' README.md)
CUT_CUR=$(sed -n 's/^BENCH_CUT_BASE для VR6-current = \([A-Za-z0-9_]*\).*/\1/p' README.md)
if [ -z "$CUT_VR6" ] || [ -z "$CUT_CUR" ]; then echo "BENCH_CUT_BASE lines not found in README.md" >&2; exit 2; fi
PY="$FC/bin/python.exe"

counted() {   # runs/<tag>/result.json exists and its errors object is empty
  [ -f "runs/$1/result.json" ] && "$PY" -c "import json,sys; r=json.load(open(sys.argv[1],encoding='utf-8')); sys.exit(0 if not (r.get('errors') or {}) and r.get('actions') else 1)" "runs/$1/result.json" 2>/dev/null
}

kill_orphans() {  # FreeCAD.exe still running with this run's own -u path (timeout kills the wrapper, not FreeCAD)
  T=$1 powershell -NoProfile -Command '$p = "freecad-kernel-fixes/bench/runs/" + $env:T + "/"; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "FreeCAD.exe" -and $_.CommandLine -and $_.CommandLine.Replace([string][char]92, "/").Contains($p) } | ForEach-Object { "killed orphan " + $_.ProcessId + ": " + $_.CommandLine; Stop-Process -Id $_.ProcessId -Force }' 2>&1
}

one() {  # one <tag> <profile> <file> <label> <actions> [ENV=VAL ...]
  TAG=$1; P=$2; FILE=$3; LBL=$4; ACT=$5; shift 5
  if [ -n "${ONLY:-}" ]; then case " $ONLY " in *" $TAG "*) ;; *) return ;; esac; fi
  if [ "${RESUME:-0}" = 1 ] && counted "$TAG"; then echo "$(date '+%F %T') $TAG SKIP-counted"; return; fi
  T0=$(date +%s)
  case " $* " in *" BENCH_MIN_FREE_MB=8192 "*)
    if [ -f "runs/.lowmem-$$" ]; then   # this matrix already waited 60 min for 8 GB in vain: the machine has not changed
      mkdir -p "runs/$TAG"; echo "not started: $(cat "runs/.lowmem-$$")" > "runs/$TAG/SKIP-lowmem"
      echo "$(date '+%F %T') $TAG SKIP-lowmem (after $(cat "runs/.lowmem-$$"))"; return
    fi ;;
  esac
  tries=1
  while :; do
    LINE=$(env "$@" ./run_bench.sh "$TAG" "$V" "$P" "$FC" "$FILE" "$LBL" "$ACT" 2>"runs/.$TAG.stderr" | tail -n 1)
    case "$LINE" in exit=75*) if [ $tries -lt 2 ]; then tries=$((tries + 1)); continue; fi ;; esac
    break
  done
  ORPH=$(kill_orphans "$TAG")
  mkdir -p "runs/$TAG"; mv -f "runs/.$TAG.stderr" "runs/$TAG/run_bench.stderr" 2>/dev/null
  if [ -n "$ORPH" ]; then echo "$ORPH" > "runs/$TAG/orphans.log"; fi
  case "$LINE" in
    exit=75*) VERDICT=SKIP-lowmem; echo "ramgate gave up twice (60 min) waiting for free RAM ($*)" > "runs/$TAG/SKIP-lowmem"
              echo "$TAG waited 60 min for 8 GB free RAM, $(date '+%F %T')" > "runs/.lowmem-$$" ;;
    *) if counted "$TAG"; then VERDICT=COUNTED; else VERDICT=FAILED; fi ;;
  esac
  echo "$(date '+%F %T') $TAG $VERDICT $LINE wall=$(( $(date +%s) - T0 ))${ORPH:+ ORPHANS-KILLED}"
}

k=${REPS_FROM:-1}
while [ "$k" -le "$REPS" ]; do
  [ "${SET:-all}" = big ] || for P in fc hd; do
    one $V-vr6cur-$P-r$k $P $F/VR6-current.FCStd vr6cur open,orbit,hover,select,edit_cut,save BENCH_CUT_BASE=$CUT_CUR
    one $V-vr6-$P-r$k $P $F/VR6-350-new.FCStd vr6 open,orbit,hover,select,edit_cut,save BENCH_CUT_BASE=$CUT_VR6
    one $V-oring-$P-r$k $P $F/owner_oring.FCStd oring open,orbit,hover,select,edit_body,save BENCH_BODY_OBJ=Pad
    one $V-s1000-$P-r$k $P $F/synthetic_1000_copies_vis.FCStd s1000 open,orbit,hover,select,save
  done
  [ "${SET:-all}" = small ] || for P in fc hd; do   # the runs that need 8 GB free RAM go last in a pass: a wait for RAM does not hold up the rest
    one $V-s5000-$P-r$k $P $F/synthetic_5000_copies_vis.FCStd s5000 open,orbit,hover,select BENCH_MIN_FREE_MB=8192
    one $V-holes-$P-r$k $P fixture:holes1024 holes open,fillet_holes BENCH_FILLET_REPS=2 BENCH_MIN_FREE_MB=8192
  done
  k=$((k + 1))
done
rm -f "runs/.lowmem-$$"
echo "$(date '+%F %T') matrix done"
