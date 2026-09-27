#!/bin/bash
# hdrun.sh <rc> <run> <module> [trim|full] [HD tree] -- lane vr6-asm: one HD GUI unittest module (tests/gui/run_smoke.ps1,
# offscreen) from run copy vr6asm/rc/<rc>, HD tree junctioned as the ONLY user Mod (FREECAD_USER_DATA), settings = COPY
# of the owner's trimmed cfg (C:/dev/thk-vr6-model/cfg) or cfg_full. fcslot 600 s, runguard 1 GB / 120 s watchdog.
set -u
RC=$1; NAME=$2; MOD=$3; CFG=${4:-trim}; HD=${5:-C:/dev/hd-vr6asm}
FC=/c/dev/occt8-mig/vr6asm/rc/$RC
W=/c/dev/occt8-mig/vr6asm/runs/$NAME
[ -x "$FC/bin/FreeCAD.exe" ] || { echo "no run copy $FC"; exit 2; }
BF=C:/dev/fckf-d/build-freecad
rm -rf "$W"; mkdir -p "$W/home" "$W/data/Mod" "$W/tmp" "$W/wd"
S=/c/dev/thk-vr6-model/cfg; [ "$CFG" = full ] && S=/c/dev/thk-vr6-model/cfg_full
cp $S/user.cfg "$W/user.cfg"; cp $S/system.cfg "$W/home/system.cfg"
cmd //c mklink //J "$(cygpath -w "$W/data/Mod/HybridDesign")" "$(cygpath -w "$HD")" > /dev/null
export FREECAD_USER_HOME="$(cygpath -w "$W/home")" FREECAD_USER_DATA="$(cygpath -w "$W/data")"
export TEMP="$(cygpath -w "$W/tmp")" TMP="$(cygpath -w "$W/tmp")" PYTHONDONTWRITEBYTECODE=1 QT_QPA_FONTDIR=C:/Windows/Fonts
export HD_TEST_WORKDIR="$(cygpath -w "$W/wd")" HD_SMOKE_OUT="$(cygpath -w "$W/result.json")"
bash C:/dev/occt8-mig/hd-compat/bin/gate.sh > "$W/gate.txt" || { cat "$W/gate.txt"; exit 75; }
cd "$W" && RUNGUARD_BELOWNORMAL=1 RUNGUARD_QUIET=1 bash $BF/runguard.sh gui "$W" "$W" "$W/tmp" \
  bash C:/dev/tools/fcslot.sh timeout -k 15 600 powershell -NoProfile -ExecutionPolicy Bypass \
  -File "$(cygpath -w "$HD/tests/gui/run_smoke.ps1")" -Module $MOD -FreeCAD "$(cygpath -w "$FC/bin/FreeCAD.exe")" \
  -UserConfig "$(cygpath -w "$W/user.cfg")" -Offscreen -KeepLog > "$W/run.log" 2>&1
R=$?
tail -2 "$W/runguard.txt" 2>/dev/null
if [ $R -ne 0 ]; then powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $BF/orphans.ps1)" -Marker "$(cygpath -w "$W")"; fi
cmd //c rmdir "$(cygpath -w "$W/data/Mod/HybridDesign")" 2>/dev/null
grep -a -h "EXIT CODE\|^Ran \|^OK\|FAILED\|HD-VPW\|HD-TREE\|skipped" "$W/run.log" "$W"/tmp/hd_smoke_*.log 2>/dev/null | sort -u | head -30
echo "exit=$R rc=$RC mod=$MOD cfg=$CFG work=$W"
exit $R
