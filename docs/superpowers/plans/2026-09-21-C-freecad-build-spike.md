# План C. Спайк: собственная сборка модуля Part FreeCAD 1.1.1, неотличимая от релиза — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** доказать (или опровергнуть с причинами), что мы собираем `Part.pyd` и `PartGui.pyd` FreeCAD 1.1.1, которые, подменённые в копии установки, неотличимы от релизных по тестам, формам и сеткам — это фундамент для патчей 013–017 и 019.

**Architecture:** окружение сборки воспроизводится **явным списком пакетов** из `package/rattler-build/pixi.lock` коммита релиза (`0108fd4`): те же URL и хэши conda-forge для win-64. Конфигурация — пресет `conda-windows-release` плюс флаги `package/rattler-build/build.bat`, т.е. всё как у релиза; собираются только цели `Part` и `PartGui` (Ninja тянет их зависимости). Результат подменяется в полной копии установки, сравнивается со второй копией-стоком.

**Tech Stack:** micromamba (портативный exe), CMake/Ninja/SWIG из окружения, MSVC 2022 (v143), Python 3.13 (скрипты), FreeCAD 1.1.1.

**Spec:** `C:/dev/freecad-kernel-fixes/docs/superpowers/specs/2026-09-21-mesh-pick-performance-design.md`, раздел 4.

## Global Constraints

- Решение владельца: только вариант A («до победного»), без облегчённой сборки против установленных DLL. Если спайк упирается в препятствие — искать, как его снять в рамках варианта A, и докладывать; к B не переходить.
- Установленный FreeCAD не меняется; всё — в `C:/dev/fc-build` (исходники, окружение, сборка) и `C:/dev/fc-test/{stock,spike}` (копии).
- Диск: свободно ~44 ГБ; бюджет спайка ≤ 20 ГБ; перед каждым крупным шагом проверять `df -h /c` и останавливаться при < 12 ГБ свободных.
- Не больше 5 FreeCAD: запуски FreeCAD — через `bash C:/dev/tools/fcslot.sh timeout -k 15 <сек> ...`; сборка ninja — не более 8 потоков (`-j8`), чтобы не отнимать у владельца всю машину.
- Никаких изменений исходников FreeCAD в этом плане (патчи — отдельными планами после успеха спайка).
- Коммиты — только скрипты и отчёты в `C:/dev/freecad-kernel-fixes/build-freecad/` с `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`; дерево `C:/dev/fc-build` в git не входит.

## Структура файлов

| Файл | Ответственность |
|---|---|
| `build-freecad/README.md` | как воспроизвести сборку, что проверено, результаты |
| `build-freecad/inventory.py` | версии DLL установки (ресурсы версии PE) против пинов lock-файла |
| `build-freecad/lock2explicit.py` | `pixi.lock` релиза → явный список `@EXPLICIT` для micromamba (win-64, окружение `default`) |
| `build-freecad/extra-build-tools.txt` | пакеты только для сборки, которых нет в окружении запуска (cmake, ninja, swig, eigen, pybind11) — с версиями из корневого `pixi.lock` того же коммита |
| `build-freecad/build.bat` | конфигурация (как `package/rattler-build/build.bat`) и сборка целей Part/PartGui |
| `build-freecad/abi-check.ps1` | экспорт наших FreeCADBase/App/Gui против релизных; импорт наших Part/PartGui ⊆ экспорт релиза |
| `build-freecad/equivalence.py` | в FreeCAD: формы (объём, площадь, число граней) и массивы Coin всех видимых объектов → дайджест |
| `build-freecad/SPIKE.md` | итог спайка |

---

### Task 1: Совпадают ли версии установки с lock-файлом релиза

**Files:**
- Create: `build-freecad/inventory.py`, `build-freecad/VERSIONS.md`

**Interfaces:**
- Produces: `VERSIONS.md` — таблица «пакет | версия в установке (DLL) | версия в lock | совпадает»; вердикт.

- [ ] **Step 1: Исходные файлы коммита** (только два файла, без клонирования)

```bash
mkdir -p C:/dev/fc-build/meta && cd C:/dev/fc-build/meta
REF="ref=0108fd4b4850cc46e625b60e53cea7a7bbe69f8d"; R="repos/FreeCAD/FreeCAD/contents"
gh api "$R/package/rattler-build/pixi.lock?$REF" -H "Accept: application/vnd.github.raw" > rb_pixi.lock
gh api "$R/pixi.lock?$REF" -H "Accept: application/vnd.github.raw" > root_pixi.lock
gh api "$R/package/rattler-build/build.bat?$REF" -H "Accept: application/vnd.github.raw" > rb_build.bat
gh api "$R/CMakePresets.json?$REF" -H "Accept: application/vnd.github.raw" > CMakePresets.json
ls -la
```

- [ ] **Step 2: `inventory.py`**

```python
"""Versions of the DLLs FreeCAD 1.1.1 ships vs the win-64 pins of package/rattler-build/pixi.lock (commit 0108fd4).
python inventory.py <FreeCAD dir> <rb_pixi.lock>  -> markdown table on stdout"""
import ctypes
import os
import re
import sys

DLLS = {  # package in the lock -> a DLL of the installation that carries its version resource
    "occt": "TKernel.dll", "qt6-main": "Qt6Core.dll", "coin3d": "Coin4.dll", "xerces-c": "xerces-c_3_3.dll",
    "tbb": "tbb12.dll", "yaml-cpp": "yaml-cpp.dll", "libboost": "boost_filesystem.dll", "python": "python311.dll",
    "pyside6": "pyside6.abi3.dll", "vtk": "vtkCommonCore-9.3.dll", "fmt": "fmt.dll", "zlib": "zlib.dll",
}


def file_version(path):
    v = ctypes.windll.version
    size = v.GetFileVersionInfoSizeW(path, None)
    if not size:
        return None
    buf = ctypes.create_string_buffer(size)
    v.GetFileVersionInfoW(path, 0, size, buf)
    p = ctypes.c_void_p(); n = ctypes.c_uint()
    if not v.VerQueryValueW(buf, "\\", ctypes.byref(p), ctypes.byref(n)):
        return None
    ffi = ctypes.cast(p, ctypes.POINTER(ctypes.c_uint32 * 13)).contents
    ms, ls = ffi[4], ffi[5]   # dwProductVersionMS/LS
    return "%d.%d.%d.%d" % (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)


def lock_versions(lock_path):
    text = open(lock_path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"conda-forge/win-64/([A-Za-z0-9_.+-]+?)-(\d[^-]*)-([^-/]+)\.conda", text):
        out.setdefault(m.group(1), m.group(2) + " (" + m.group(3) + ")")
    return out


def main():
    fc, lock = sys.argv[1], sys.argv[2]
    pins = lock_versions(lock)
    print("| пакет | DLL установки | версия DLL | пин lock | совпадает |")
    print("|---|---|---|---|---|")
    for pkg, dll in DLLS.items():
        path = os.path.join(fc, "bin", dll)
        ver = file_version(path) if os.path.exists(path) else "нет файла"
        pin = pins.get(pkg, "нет в lock")
        same = "?" if ver in (None, "нет файла") else ("да" if pin.split(" ")[0].split(".")[:2] == ver.split(".")[:2] else "НЕТ")
        print("| %s | %s | %s | %s | %s |" % (pkg, dll, ver, pin, same))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Прогон**

Run: `python C:/dev/freecad-kernel-fixes/build-freecad/inventory.py "C:/Program Files/FreeCAD 1.1" C:/dev/fc-build/meta/rb_pixi.lock | tee C:/dev/freecad-kernel-fixes/build-freecad/VERSIONS.md`
Expected: OCCT 7.8.1, Qt 6.8.3, Coin 4.0.3, Python 3.11 совпадают по major.minor. DLL без ресурса версии («?») сверить по имени пакета из lock и наличию файла с тем же именем в `bin`. Если нужного имени DLL в `bin` нет — найти `ls "C:/Program Files/FreeCAD 1.1/bin" | grep -i <пакет>` и поправить `DLLS`.

**Точка решения:** хотя бы одно «НЕТ» среди `occt`, `qt6-main`, `coin3d`, `libboost`, `xerces-c`, `python`, `pyside6` — lock-файл не описывает релиз. Тогда найти точные версии сборки в журнале GitHub Actions релиза 1.1.1 (`gh run list -R FreeCAD/FreeCAD --workflow <release workflow> --branch 1.1.1`, лог шага rattler-build содержит решённое окружение `host`) и собрать явный список из него; доложить владельцу, если журналы недоступны.

- [ ] **Step 4: Commit** (`inventory.py`, `VERSIONS.md`).

---

### Task 2: Инструменты и исходники

**Files:**
- Create: `build-freecad/README.md` (заготовка с командами этого задания)

- [ ] **Step 1: micromamba** (один exe, без установки в систему)

```bash
mkdir -p C:/dev/fc-build/tools && cd C:/dev/fc-build/tools
curl -L -o micromamba.exe https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-win-64
./micromamba.exe --version
```
Expected: печатается версия. Корень пакетов — внутри `C:/dev/fc-build` (задаётся `-r` в Task 3), профиль пользователя не трогается.

- [ ] **Step 2: Исходники коммита с подмодулями**

```bash
cd C:/dev/fc-build && df -h /c | tail -1
git clone --filter=blob:none --no-checkout https://github.com/FreeCAD/FreeCAD.git src
cd src && git checkout 0108fd4b4850cc46e625b60e53cea7a7bbe69f8d && git submodule update --init --depth 1
git log -1 --format="%H %s" && git submodule status
```
Expected: `0108fd4b4850... Build: Update version to 1.1.1`; четыре подмодуля (`src/3rdParty/OndselSolver`, `src/3rdParty/GSL`, `src/Mod/AddonManager`, `tests/lib`) на зафиксированных коммитах.

---

### Task 3: Окружение из lock-файла релиза

**Files:**
- Create: `build-freecad/lock2explicit.py`, `build-freecad/extra-build-tools.txt`

**Interfaces:**
- Produces: окружение `C:/dev/fc-build/env` с теми же пакетами, что у релиза + инструменты сборки.

- [ ] **Step 1: `lock2explicit.py`**

```python
"""package/rattler-build/pixi.lock (pixi lock v6) -> micromamba explicit spec for one environment/platform.
python lock2explicit.py <lock> <environment> <platform> <extra_urls.txt|-> > explicit.txt
Every conda URL listed for the platform under environments.<env>.packages is written with its md5 from the
packages section (micromamba verifies it)."""
import sys

import yaml   # pip install pyyaml into a venv under C:/dev/fc-build/tools if missing


def main():
    lock, env, plat, extra = sys.argv[1:5]
    d = yaml.safe_load(open(lock, encoding="utf-8"))
    md5 = {}
    for p in d["packages"]:
        if "conda" in p:
            md5[p["conda"]] = p.get("md5")
    urls = [e["conda"] for e in d["environments"][env]["packages"][plat] if "conda" in e]
    print("@EXPLICIT")
    for u in urls:
        print(u + ("#" + md5[u] if md5.get(u) else ""))
    if extra != "-":
        for line in open(extra, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                print(line)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Инструменты сборки** — в `root_pixi.lock` (окружение `default`, `win-64`) найти URL пакетов `cmake`, `ninja`, `swig`, `eigen`, `pybind11`, `pybind11-global`, `doxygen` не нужен:

Run: `grep -oE "https://conda.anaconda.org/conda-forge/win-64/(cmake|ninja|swig|eigen|pybind11|pybind11-global)-[0-9][^ ]*\.conda" C:/dev/fc-build/meta/root_pixi.lock | sort -u | tee C:/dev/freecad-kernel-fixes/build-freecad/extra-build-tools.txt`
Expected: по одной строке на пакет (`eigen` и `pybind11` могут быть `noarch` — тогда повторить grep с `noarch` вместо `win-64` и добавить). Проверить, что `swig` — 4.3.x (рецепт требует `swig>=4.3,<4.4`).

- [ ] **Step 3: Список и окружение**

```bash
cd C:/dev/fc-build && python -m venv tools/venv && tools/venv/Scripts/pip install pyyaml
tools/venv/Scripts/python C:/dev/freecad-kernel-fixes/build-freecad/lock2explicit.py meta/rb_pixi.lock default win-64 \
  C:/dev/freecad-kernel-fixes/build-freecad/extra-build-tools.txt > meta/explicit-win64.txt
grep -c conda meta/explicit-win64.txt; grep -E "occt-7.8.1|qt6-main-6.8.3|libboost-1.86" meta/explicit-win64.txt
df -h /c | tail -1
tools/micromamba.exe create -y -r C:/dev/fc-build/mamba -p C:/dev/fc-build/env -f meta/explicit-win64.txt 2>&1 | tail -5
du -sh C:/dev/fc-build/env; df -h /c | tail -1
```
Expected: ~200+ пакетов, среди них `occt-7.8.1-all_hae6dad1_203`, `qt6-main-6.8.3`, `libboost-1.86.0`; окружение создано без ошибок md5. Если `default` в lock содержит источник `freecad` (source package) без URL — он пропускается (`if "conda" in e`), это ожидаемо.

- [ ] **Step 4: Сверка окружения с установкой** — `inventory.py` против окружения:

Run: `python C:/dev/freecad-kernel-fixes/build-freecad/inventory.py C:/dev/fc-build/env/Library C:/dev/fc-build/meta/rb_pixi.lock`
Expected: те же версии DLL, что в `VERSIONS.md` для установки (в conda DLL лежат в `env/Library/bin`). Дополнительно побайтная проверка ключевых DLL:
`for f in TKernel.dll TKBRep.dll Qt6Core.dll Coin4.dll; do md5sum "C:/Program Files/FreeCAD 1.1/bin/$f" C:/dev/fc-build/env/Library/bin/$f; done`
Expected: md5 совпадают (у `TKBO.dll`/`TKFillet.dll` — нет: у владельца патчи 009/001). Совпадение md5 — прямое доказательство, что это те же пакеты.

- [ ] **Step 5: Commit** (`lock2explicit.py`, `extra-build-tools.txt`, дополнение README).

---

### Task 4: Конфигурация как у релиза и сборка Part/PartGui

**Files:**
- Create: `build-freecad/build.bat`

**Interfaces:**
- Produces: `C:/dev/fc-build/build/Mod/Part/Part.pyd` и `PartGui.pyd` (точные пути внутри дерева сборки уточняются по выводу Ninja и записываются в README), а также наши `bin/FreeCADBase.dll`, `FreeCADApp.dll`, `FreeCADGui.dll` — для проверки ABI.

- [ ] **Step 1: `build.bat`**

```bat
@echo off
rem build.bat [configure] -- FreeCAD 1.1.1 (0108fd4) configured like package/rattler-build/build.bat, Part targets only.
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set CONDA_PREFIX=C:\dev\fc-build\env
set LIBRARY_PREFIX=%CONDA_PREFIX%\Library
set PYTHON=%CONDA_PREFIX%\python.exe
set PATH=%CONDA_PREFIX%;%LIBRARY_PREFIX%\bin;%CONDA_PREFIX%\Scripts;%PATH%
set SRC=C:\dev\fc-build\src
set BLD=C:\dev\fc-build\build
if "%1"=="configure" (
  cmake --preset conda-windows-release -S %SRC% -B %BLD% ^
    -D CMAKE_C_COMPILER:STRING=cl -D CMAKE_CXX_COMPILER:STRING=cl ^
    -D CMAKE_INCLUDE_PATH:FILEPATH="%LIBRARY_PREFIX%/include" ^
    -D CMAKE_INSTALL_LIBDIR:FILEPATH="%LIBRARY_PREFIX%/lib" ^
    -D CMAKE_INSTALL_PREFIX:FILEPATH="C:/dev/fc-build/install" ^
    -D CMAKE_LIBRARY_PATH:FILEPATH="%LIBRARY_PREFIX%/lib" ^
    -D CMAKE_PREFIX_PATH:FILEPATH="%LIBRARY_PREFIX%" ^
    -D FREECAD_USE_EXTERNAL_FMT:BOOL=OFF ^
    -D INSTALL_TO_SITEPACKAGES:BOOL=ON ^
    -D OCC_INCLUDE_DIR:FILEPATH="%LIBRARY_PREFIX%/include/opencascade" ^
    -D OCC_LIBRARY_DIR:FILEPATH="%LIBRARY_PREFIX%/lib" ^
    -D Python_EXECUTABLE:FILEPATH="%PYTHON%" ^
    -D Python3_EXECUTABLE:FILEPATH="%PYTHON%" ^
    -D SMESH_INCLUDE_DIR:FILEPATH="%LIBRARY_PREFIX%/include/smesh" ^
    -D SMESH_LIBRARY:FILEPATH="%LIBRARY_PREFIX%/lib/SMESH.lib" > %BLD%-configure.log 2>&1
  if errorlevel 1 (echo CONFIGURE FAILED, see %BLD%-configure.log & exit /b 1)
  echo CONFIGURE OK
)
ninja -C %BLD% -j8 Part PartGui > %BLD%-build.log 2>&1
if errorlevel 1 (echo BUILD FAILED, see %BLD%-build.log & exit /b 1)
echo BUILD OK
```
(Отличие от релиза — только `CMAKE_INSTALL_PREFIX`: релиз ставит в окружение conda, мы — в отдельную папку, которая не используется; на код это не влияет. `%CMAKE_ARGS%` rattler-build на Windows добавляет `-DCMAKE_BUILD_TYPE=Release` и пути префикса — они покрыты пресетом и строками выше.)

- [ ] **Step 2: Конфигурация**

Run: `mkdir -p C:/dev/fc-build/build && cmd //c "C:\dev\freecad-kernel-fixes\build-freecad\build.bat configure"`
Expected: `CONFIGURE OK`. Типичные препятствия и как их снимать **в рамках варианта A**: не найден пакет, которого нет в окружении запуска (заголовочный/только для сборки) — добавить его URL той же версии из `root_pixi.lock` в `extra-build-tools.txt`, досоздать окружение (`micromamba install -p ... -f`), повторить; несовпадение генератора — в пресете `conda` генератор Ninja, `ninja` должен быть из окружения. Каждое препятствие и решение — в README.

- [ ] **Step 3: Сборка**

Run: `cmd //c "C:\dev\freecad-kernel-fixes\build-freecad\build.bat"` (долго: зависимости Base/App/Gui/Part; запуск в фоне с таймаутом 3 ч)
Expected: `BUILD OK`; найти результаты: `find C:/dev/fc-build/build -iname "Part.pyd" -o -iname "PartGui.pyd" -o -iname "FreeCADApp.dll" -o -iname "FreeCADBase.dll" -o -iname "FreeCADGui.dll"`; записать пути в README. `du -sh C:/dev/fc-build/build`.

- [ ] **Step 4: Commit** (`build.bat`, README с путями, журналом препятствий и временем сборки).

---

### Task 5: Двоичная совместимость с релизом

**Files:**
- Create: `build-freecad/abi-check.ps1`, `build-freecad/ABI.md`

- [ ] **Step 1: Скрипт**

```powershell
# abi-check.ps1 -- can our Part.pyd / PartGui.pyd load against the RELEASE FreeCAD DLLs?
# 1) our FreeCADBase/App/Gui export the same names as the release ones (same headers, same compiler => same
#    mangled names); 2) every symbol our Part.pyd / PartGui.pyd import from FreeCAD*.dll and TK*.dll is exported
#    by the release DLL of that name.
param([string]$Build = "C:\dev\fc-build\build", [string]$FreeCAD = "C:\Program Files\FreeCAD 1.1")
$vc = (Get-ChildItem "C:\Program Files\Microsoft Visual Studio\2022\*\VC\Tools\MSVC\*\bin\Hostx64\x64\dumpbin.exe" | Select-Object -First 1).FullName
function Exports($dll) { & $vc /nologo /exports $dll | Select-String '^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+(\S+)' | ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique }
function Find($name) { (Get-ChildItem -Recurse -Filter $name $Build | Select-Object -First 1).FullName }
foreach ($n in "FreeCADBase.dll", "FreeCADApp.dll", "FreeCADGui.dll") {
  $ours = Exports (Find $n); $rel = Exports (Join-Path $FreeCAD "bin\$n")
  $onlyOurs = @($ours | Where-Object { $rel -notcontains $_ }); $onlyRel = @($rel | Where-Object { $ours -notcontains $_ })
  "{0}: ours {1}, release {2}, only in ours {3}, only in release {4}" -f $n, $ours.Count, $rel.Count, $onlyOurs.Count, $onlyRel.Count
  $onlyOurs | Select-Object -First 10 | ForEach-Object { "   +" + $_ }
  $onlyRel | Select-Object -First 10 | ForEach-Object { "   -" + $_ }
}
foreach ($m in "Part.pyd", "PartGui.pyd") {
  $path = Find $m
  $cur = $null; $missing = 0; $checked = 0; $cache = @{}
  foreach ($line in (& $vc /nologo /imports $path)) {
    if ($line -match '^\s{4}(\S+\.dll)$') { $cur = $Matches[1]; continue }
    if ($cur -and ($cur -like "FreeCAD*" -or $cur -like "TK*" -or $cur -like "Part*") -and $line -match '^\s+[0-9A-F]+\s+(\S+)$') {
      $rp = Join-Path $FreeCAD "bin\$cur"; if (-not (Test-Path $rp)) { $rp = Join-Path $FreeCAD "lib\$cur" }
      if (-not $cache.ContainsKey($cur)) { $cache[$cur] = Exports $rp }
      $checked++
      if ($cache[$cur] -notcontains $Matches[1]) { $missing++; if ($missing -le 10) { "   missing in release $cur : " + $Matches[1] } }
    }
  }
  "{0}: imported symbols checked {1}, missing in release {2}" -f $m, $checked, $missing
}
```

- [ ] **Step 2: Прогон**

Run: `powershell -ExecutionPolicy Bypass -File C:/dev/freecad-kernel-fixes/build-freecad/abi-check.ps1 | tee C:/dev/freecad-kernel-fixes/build-freecad/ABI.md`
Expected: для трёх DLL `only in ours 0` и `only in release 0`; для `Part.pyd` и `PartGui.pyd` `missing in release 0`. Любое расхождение — **остановка спайка до выяснения**: имя символа укажет, чей заголовок или флаг отличается (например, другой `_ITERATOR_DEBUG_LEVEL`, версия boost в сигнатуре), исправить конфигурацию и пересобрать.

- [ ] **Step 3: Commit** (`abi-check.ps1`, `ABI.md`).

---

### Task 6: Две копии установки и проверка неотличимости

**Files:**
- Create: `build-freecad/equivalence.py`, `build-freecad/SPIKE.md`

**Interfaces:**
- Consumes: план A (`bench/`), раннеры HD (`tests/run_headless.ps1 -FreeCADCmd`, `tests/gui/run_smoke.ps1 -FreeCAD`).
- Produces: `SPIKE.md` с вердиктом «неотличима / отличается чем».

- [ ] **Step 1: Копии**

```bat
robocopy "C:\Program Files\FreeCAD 1.1" "C:\dev\fc-test\stock" /E /NFL /NDL /NJH /NJS
robocopy "C:\Program Files\FreeCAD 1.1" "C:\dev\fc-test\spike" /E /NFL /NDL /NJH /NJS
```
Затем подменить в `spike` `lib\Part.pyd` и `lib\PartGui.pyd` нашими (пути из README). Проверки: `md5sum` двух файлов в `spike` = нашим; в `stock` = установке; `find /c/dev/fc-test -type l | wc -l` = 0 (без ссылок-junction — их можно удалять как обычные папки).

- [ ] **Step 2: Собственные тесты FreeCAD** (оба варианта, через fcslot)

Run:
```bash
for V in stock spike; do
  bash C:/dev/tools/fcslot.sh timeout -k 15 1800 C:/dev/fc-test/$V/bin/FreeCADCmd.exe -t TestPartApp > C:/dev/fc-build/test-$V-app.log 2>&1
  QT_QPA_PLATFORM=offscreen bash C:/dev/tools/fcslot.sh timeout -k 15 1800 C:/dev/fc-test/$V/bin/FreeCAD.exe -t TestPartGui > C:/dev/fc-build/test-$V-gui.log 2>&1
done
tail -3 C:/dev/fc-build/test-*-app.log C:/dev/fc-build/test-*-gui.log
```
Expected: одинаковые строки итога (`Ran N tests`, `OK`/`FAILED (failures=K)`) у stock и spike; отказы, если есть, одни и те же по именам.

- [ ] **Step 3: Наборы HybridDesign** — headless (`run_headless.ps1 -FreeCADCmd C:\dev\fc-test\<V>\bin\FreeCADCmd.exe`) и все GUI-модули (`run_smoke.ps1 -Module <m> -FreeCAD C:\dev\fc-test\<V>\bin\FreeCAD.exe`) для V = stock и spike.
Expected: одинаковые итоги.

- [ ] **Step 4: `equivalence.py`** — дайджест моделей внутри FreeCAD (оффскрин):

```python
"""Open a file in FreeCAD.exe (offscreen), wait until idle, and write for every object with a Shape: volume, area,
face/edge counts, and an FNV digest of its view provider's Coin arrays (coordinates, normals, face-set coordIndex
and partIndex, edge-set coordIndex). Env: EQ_FILE, EQ_OUT. Compare two outputs with a plain diff."""
import json
import os
import struct
import time

import FreeCAD as App
import FreeCADGui as Gui
from pivy import coin
from PySide import QtCore, QtWidgets


def fnv(data):
    h = 1469598103934665603
    for b in data:
        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return "%016x" % h


def arrays(vp):
    out = []
    for tname, field in (("SoCoordinate3", "point"), ("SoNormal", "vector"),
                         ("SoBrepFaceSet", "coordIndex"), ("SoBrepFaceSet", "partIndex"), ("SoBrepEdgeSet", "coordIndex")):
        sa = coin.SoSearchAction(); sa.setType(coin.SoType.fromName(tname)); sa.setInterest(coin.SoSearchAction.FIRST)
        sa.apply(vp.RootNode)
        p = sa.getPath()
        if p is None:
            out.append("-"); continue
        f = getattr(p.getTail(), field)
        vals = f.getValues()
        if vals and hasattr(vals[0], "getValue"):
            raw = b"".join(struct.pack("<3f", *v.getValue()) for v in vals)
        else:
            raw = struct.pack("<%di" % len(vals), *vals)
        out.append("%d:%s" % (len(vals), fnv(raw)))
    return out


def main():
    doc = App.openDocument(os.environ["EQ_FILE"])
    t = time.time()
    while time.time() - t < 5:
        QtWidgets.QApplication.processEvents()
    res = {}
    for o in doc.Objects:
        sh = getattr(o, "Shape", None)
        if sh is None or sh.isNull():
            continue
        vp = o.ViewObject
        res[o.Name] = {"vol": round(sh.Volume, 6), "area": round(sh.Area, 6), "faces": len(sh.Faces),
                       "edges": len(sh.Edges), "coin": arrays(vp) if vp is not None else None}
    json.dump(res, open(os.environ["EQ_OUT"], "w"), indent=1, sort_keys=True)
    os._exit(0)


QtCore.QTimer.singleShot(2500, main)
```
Run для файлов `owner_oring.FCStd`, `synthetic_1000_copies.FCStd`, `VR6-350-new.FCStd` (6,4° — ждать открытия до 10 мин) и фикстуры `fixture_holes1024.FCStd` (из прогона плана A) — на stock и spike (оффскрин, fcslot, песочница cfg как в `bench/run_bench.sh`); затем `diff eq-stock-<f>.json eq-spike-<f>.json`.
Expected: `diff` пуст для всех файлов. Допускается расхождение массивов Coin только у форм, у которых такое же расхождение даёт повторный прогон stock против stock (параллельный мешинг: 8 треугольников на миллион) — проверить отдельным повтором stock.

- [ ] **Step 5: `SPIKE.md`** — вердикт, таблицы Tasks 1, 5, 6, время сборки, объём диска (`du -sh C:/dev/fc-build/{env,build,src}`), препятствия и решения, что оставить на диске для следующих планов (окружение и дерево сборки — нужны для инкрементальных пересборок патчей 013–019; `C:/dev/fc-test/spike` — удалить после приёмки, `stock` — оставить как эталон).

- [ ] **Step 6: Commit** (`equivalence.py`, `SPIKE.md`, README).

---

## После плана C

Если спайк неотличим от релиза, следующие планы (по одному на дефект, тем же форматом): 013 (перемешивание только изменённых граней), 014 (`ControlSurfaceDeflection`), 015 (сетка в файле), 016 (BVH для выбора — сначала профиль), 017 (ленивые проверки входов), 019 (рендер — дизайн уточняется по профилю базы плана A); и отдельно ядро: 018 (`BRepCheck_Face`). Каждый — с замером по набору действий плана A «было → стало».
