# План A. Набор действий владельца и замер базы — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** воспроизводимый замер восьми действий владельца на его файлах (стоковый FreeCAD 1.1.1, профили без HD и с HD) и отчёт «было → стало», по которому меряется цель 10×+.

**Architecture:** скрипт-драйвер выполняется внутри `FreeCAD.exe` (оффскрин, `QT_QPA_PLATFORM=offscreen`) и мерит действия на настоящем графе сцены вьюера (кадры — `SoOffscreenRenderer` с рендер-действием самого вьюера, как в `C:/dev/hybriddesign-render/phase1`). Оболочка `run_bench.sh` готовит песочницу настроек и запускает FreeCAD через `fcslot.sh`. `report.py` сводит JSON в таблицу с отношениями и средним геометрическим.

**Tech Stack:** FreeCAD 1.1.1 Python 3.11 (Pivy/Coin, PySide6), Python 3.13 системный (отчёт, unittest), bash (Git for Windows).

**Spec:** `C:/dev/freecad-kernel-fixes/docs/superpowers/specs/2026-09-21-mesh-pick-performance-design.md`, раздел 11.

## Global Constraints

- Не больше 5 процессов FreeCAD на машине: каждый запуск только через `bash C:/dev/tools/fcslot.sh timeout -k 15 <сек> <команда>`; от одного исполнителя — один FreeCAD одновременно.
- Только копии файлов владельца (`bench/files/`, md5 в `bench/files/MD5SUMS.txt`); исходники в `C:/dev/hybriddesign-*` и `%APPDATA%` — только чтение.
- Пути только ASCII: профиль пользователя кириллический, FreeCAD его не открывает; короткий путь — `C:/Users/B72A~1`.
- Без видимых окон и без глобального ввода мыши/клавиатуры: оффскрин; оконные прогоны — только после отдельного разрешения владельца.
- Живой `%APPDATA%/FreeCAD/v1-1/user.cfg` только читается и копируется в песочницу.
- Принцип владельца: замер ничего не упрощает в модели (те же файлы, те же параметры, в т.ч. 6,4° у VR6).
- Коммиты только в `C:/dev/freecad-kernel-fixes`, с строкой `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`; `bench/files/` и `bench/runs/` в git не попадают (уже в `.gitignore`).

## Структура файлов

| Файл | Ответственность |
|---|---|
| `bench/README.md` | как запускать, что мерится, где результаты |
| `bench/fcbench/__init__.py` | пакет |
| `bench/fcbench/stats.py` | медиана/p90/геосреднее — чистый Python, общий для драйвера и отчёта |
| `bench/fcbench/common.py` | память, загрузка CPU, ожидание простоя, `Renderer` (кадр, облёт, наведение) |
| `bench/fcbench/fixtures.py` | плита 32×32 отверстий + Body + Fillet; выбор базы для разреза в VR6 |
| `bench/fcbench/actions.py` | восемь действий, каждое возвращает словарь метрик |
| `bench/fcbench/driver.py` | точка входа внутри FreeCAD: читает env, выполняет действия, пишет JSON |
| `bench/tools/cfg_sandbox.py` | копия настроек владельца в песочницу (+ отметка миграции CAM, иначе модальное окно) |
| `bench/run_bench.sh` | один запуск: песочница, профиль fc/hd, оффскрин, fcslot, таймаут |
| `bench/run_matrix.sh` | серия: файлы × профили × повторы, чередование вариантов |
| `bench/report.py` | сводка `runs/*/result.json` → `bench/reports/<имя>.md` |
| `bench/tests/test_stats.py`, `bench/tests/test_report.py` | unittest для чистой части |

---

### Task 1: Статистика и отчёт (чистый Python, TDD)

**Files:**
- Create: `bench/fcbench/__init__.py`, `bench/fcbench/stats.py`, `bench/report.py`
- Test: `bench/tests/test_stats.py`, `bench/tests/test_report.py`

**Interfaces:**
- Produces: `stats.summary(xs) -> {"median","p90","min","max","n"}` (мс или с — как пришло); `stats.geomean(xs) -> float`; `report.load_runs(root) -> list[dict]`; `report.table(runs, base_variant, variant) -> str` (markdown); формат `result.json` описан в Task 2.

- [ ] **Step 1: Написать падающие тесты**

`bench/tests/test_stats.py`:
```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fcbench import stats  # noqa: E402


class StatsTest(unittest.TestCase):
    def test_summary_odd(self):
        s = stats.summary([5.0, 1.0, 3.0])
        self.assertEqual(s["median"], 3.0)
        self.assertEqual(s["min"], 1.0)
        self.assertEqual(s["max"], 5.0)
        self.assertEqual(s["n"], 3)

    def test_summary_p90(self):
        s = stats.summary(list(range(1, 11)))
        self.assertEqual(s["p90"], 10)
        self.assertEqual(s["median"], 6)

    def test_summary_empty(self):
        self.assertIsNone(stats.summary([]))

    def test_geomean(self):
        self.assertAlmostEqual(stats.geomean([1.0, 100.0]), 10.0)
        self.assertAlmostEqual(stats.geomean([10.0]), 10.0)


if __name__ == "__main__":
    unittest.main()
```

`bench/tests/test_report.py`:
```python
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import report  # noqa: E402


def _run(root, tag, variant, file_label, open_s, orbit_ms):
    d = os.path.join(root, tag)
    os.makedirs(d)
    with open(os.path.join(d, "result.json"), "w") as f:
        json.dump({"variant": variant, "profile": "fc", "file_label": file_label,
                   "actions": {"open": {"open_s": open_s},
                               "orbit": {"overview": {"median": orbit_ms}}}}, f)


class ReportTest(unittest.TestCase):
    def test_ratio_and_geomean(self):
        with tempfile.TemporaryDirectory() as root:
            _run(root, "a1", "stock", "vr6", 50.0, 40.0)
            _run(root, "a2", "stock", "vr6", 54.0, 44.0)
            _run(root, "b1", "p012", "vr6", 5.0, 4.0)
            _run(root, "b2", "p012", "vr6", 5.4, 4.4)
            runs = report.load_runs(root)
            self.assertEqual(len(runs), 4)
            md = report.table(runs, "stock", "p012")
            # median rule s[len(s)//2]: [50, 54] -> 54, [5.0, 5.4] -> 5.4, so 10.0x; orbit 44 / 4.4 = 10.0x
            self.assertIn("| vr6 | fc | open.open_s | 54 | 5.4 | 10.0× |", md)
            self.assertIn("| vr6 | fc | orbit.overview.median | 44 | 4.4 | 10.0× |", md)
            self.assertIn("геосреднее ускорения по 2 метрикам: 10.00×", md)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Запустить — должны упасть**

Run: `cd C:/dev/freecad-kernel-fixes/bench && python -m unittest discover -s tests -v`
Expected: FAIL/ERROR (`ModuleNotFoundError: No module named 'fcbench'` / `report`).

- [ ] **Step 3: Реализация**

`bench/fcbench/__init__.py`: пустой файл с одной строкой docstring `"""FreeCAD action benchmark (plan A)."""`.

`bench/fcbench/stats.py`:
```python
"""Summaries shared by the in-FreeCAD driver and the report (no FreeCAD imports here)."""
import math


def summary(xs):
    s = sorted(x for x in xs if x is not None)
    if not s:
        return None
    return {"median": s[len(s) // 2], "p90": s[min(len(s) - 1, int(len(s) * 0.9))],
            "min": s[0], "max": s[-1], "n": len(s)}


def geomean(xs):
    xs = [x for x in xs if x and x > 0]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else float("nan")
```

`bench/report.py`:
```python
"""Aggregate bench/runs/*/result.json into a markdown table: per file, profile and metric the median over
runs of each variant, the ratio base/variant and the geometric mean of the ratios.

    python report.py <runs_dir> <base_variant> <variant> [out.md]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fcbench import stats  # noqa: E402

# (action, path in the action dict) -> metric name. Lower is better for all of them.
METRICS = [
    ("open", ("open_s",)), ("open", ("idle_s",)), ("open", ("first_frame_ms",)),
    ("orbit", ("overview", "median")), ("orbit", ("closeup", "median")),
    ("hover", ("all", "median")), ("hover", ("all", "max")), ("hover", ("heavy", "median")),
    ("select", ("select", "median")),
    ("edit_body", ("edit", "median")), ("edit_cut", ("edit", "median")),
    ("fillet_holes", ("edit", "median")),
    ("save", ("save_s",)),
]


def load_runs(root):
    runs = []
    for tag in sorted(os.listdir(root)):
        p = os.path.join(root, tag, "result.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
            r["tag"] = tag
            runs.append(r)
    return runs


def _get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d if isinstance(d, (int, float)) else None


def table(runs, base, variant):
    keys = sorted({(r["file_label"], r["profile"]) for r in runs})
    lines = ["| файл | профиль | метрика | %s | %s | × |" % (base, variant), "|---|---|---|---|---|---|"]
    ratios = []
    for fl, prof in keys:
        for action, path in METRICS:
            vals = {}
            for v in (base, variant):
                xs = [_get(r["actions"].get(action, {}), path) for r in runs
                      if r["variant"] == v and r["file_label"] == fl and r["profile"] == prof]
                s = stats.summary([x for x in xs if x is not None])
                vals[v] = s["median"] if s else None
            if vals[base] is None or vals[variant] is None:
                continue
            ratio = vals[base] / vals[variant] if vals[variant] > 0 else float("inf")
            ratios.append(ratio)
            name = action + "." + ".".join(path)
            lines.append("| %s | %s | %s | %g | %g | %.1f× |" % (fl, prof, name, vals[base], vals[variant], ratio))
    lines.append("")
    lines.append("геосреднее ускорения по %d метрикам: %.2f×" % (len(ratios), stats.geomean(ratios)))
    return "\n".join(lines)


def main():
    root, base, variant = sys.argv[1], sys.argv[2], sys.argv[3]
    md = table(load_runs(root), base, variant)
    if len(sys.argv) > 4:
        with open(sys.argv[4], "w", encoding="utf-8") as f:
            f.write(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Запустить — должны пройти**

Run: `cd C:/dev/freecad-kernel-fixes/bench && python -m unittest discover -s tests -v`
Expected: 5 tests OK.

- [ ] **Step 5: Commit**

```bash
cd C:/dev/freecad-kernel-fixes
git add bench/fcbench/__init__.py bench/fcbench/stats.py bench/report.py bench/tests
git commit -m "bench: сводка замеров и отчёт «было → стало» (план A, задача 1)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Драйвер внутри FreeCAD, оболочка запуска и дымовой прогон

**Files:**
- Create: `bench/fcbench/common.py`, `bench/fcbench/actions.py`, `bench/fcbench/driver.py`, `bench/tools/cfg_sandbox.py`, `bench/run_bench.sh`, `bench/README.md`

**Interfaces:**
- Consumes: `stats.summary`.
- Produces: `result.json` вида `{"variant","profile","file","file_label","env":{...},"actions":{<имя>:{...}},"errors":{...}}`; имена действий: `open, orbit, hover, select, edit_body, edit_cut, fillet_holes, save`; `run_bench.sh <tag> <variant> <profile fc|hd> <FC_DIR> <file|fixture:...> <label> <actions,через,запятую>` → `bench/runs/<tag>/result.json`.

- [ ] **Step 1: `common.py`** — перенос проверенных помощников из `C:/dev/hybriddesign-render/phase1/scripts/rc_common.py` (класс `Renderer` без изменений: `fit_iso`, `autoclip`, `frame`, `orbit`, `hover`; функции `mem_mb`, `pump`, `sel_target`) плюс новое:

```python
"""FreeCAD-side helpers of the action benchmark.

Renderer, mem_mb, pump and sel_target are copied from C:/dev/hybriddesign-render/phase1/scripts/rc_common.py
(measured there: the viewer's own GL render action makes frames reproducible; hover goes through
SoHandleEventAction inside this process, no OS input). New here: CPU load, idle wait, environment record.
"""
import ctypes
import ctypes.wintypes
import hashlib
import os
import sys
import time

import FreeCAD as App
from PySide import QtWidgets

# ... (скопировать из rc_common.py: GL, _PMC, _K32, _PSAPI, mem_mb, pump, class Renderer, sel_target) ...


class _FT(ctypes.Structure):
    _fields_ = [("lo", ctypes.wintypes.DWORD), ("hi", ctypes.wintypes.DWORD)]


def _systimes():
    idle, kern, user = _FT(), _FT(), _FT()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
    f = lambda t: (t.hi << 32) | t.lo  # noqa: E731
    return f(idle), f(kern) + f(user)


class CpuLoad(object):
    """Machine-wide CPU busy % between start() and stop() (the machine is shared: record, don't assume)."""

    def start(self):
        self.a = _systimes()
        return self

    def stop(self):
        i0, t0 = self.a
        i1, t1 = _systimes()
        dt = t1 - t0
        return round(100.0 * (1.0 - (i1 - i0) / dt), 1) if dt > 0 else None


def wait_idle(quiet_ms=200, slice_ms=2.0, max_s=600):
    """Pump the event loop until it has been quiet for quiet_ms: every processEvents() call in that window took
    under slice_ms. Returns seconds spent. A heavy job posted to the loop (meshing, HD refinement) keeps it busy."""
    t0 = time.perf_counter()
    quiet_since = None
    while time.perf_counter() - t0 < max_s:
        a = time.perf_counter()
        QtWidgets.QApplication.processEvents()
        took = (time.perf_counter() - a) * 1000.0
        now = time.perf_counter()
        if took < slice_ms:
            quiet_since = quiet_since or now
            if (now - quiet_since) * 1000.0 >= quiet_ms:
                return quiet_since - t0
        else:
            quiet_since = None
        time.sleep(0.001)
    return time.perf_counter() - t0


def _md5(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except OSError:
        return None


def environment():
    bindir = os.path.dirname(sys.executable)
    libdir = os.path.join(os.path.dirname(bindir), "lib")
    return {
        "freecad": ".".join(App.Version()[:3]) + " " + App.Version()[3],
        "exe": sys.executable,
        "md5": {n: _md5(os.path.join(bindir, n)) for n in ("TKMesh.dll", "TKTopAlgo.dll", "TKBO.dll",
                                                          "TKFillet.dll", "FreeCADGui.dll")}
               | {n: _md5(os.path.join(libdir, n)) for n in ("Part.pyd", "PartGui.pyd")},
        "hd_loaded": "hybriddesign" in sys.modules,
        "mem": mem_mb(),
    }
```

- [ ] **Step 2: `actions.py`** — действия (каждое возвращает словарь; время — `time.perf_counter()`):

```python
"""The owner's actions. Every function returns a dict of metrics; nothing here simplifies the model."""
import math
import os
import time

import FreeCAD as App
import FreeCADGui as Gui
from pivy import coin

from . import common as C
from .stats import summary


def open_doc(path, rd_factory):
    with open(path, "rb") as f:          # warm the disk cache: we measure FreeCAD, not the disk
        while f.read(1 << 24):
            pass
    t = time.perf_counter()
    doc = App.openDocument(path)
    open_s = time.perf_counter() - t
    idle_s = C.wait_idle()
    Gui.ActiveDocument.ActiveView.viewIsometric()
    C.pump(5)
    rd = rd_factory()
    rd.fit_iso()
    first = rd.frame()
    second = rd.frame()
    return doc, rd, {"open_s": round(open_s, 3), "idle_s": round(idle_s, 3),
                     "first_frame_ms": round(first, 1), "second_frame_ms": round(second, 1),
                     "objects": len(doc.Objects), "mem": C.mem_mb()}


def orbit(rd, steps=24, warm=3):
    rd.fit_iso()
    over = rd.orbit(steps=steps, warm=warm)
    cam = rd.camera()
    if cam.isOfType(coin.SoOrthographicCamera.getClassTypeId()):
        h = cam.height.getValue()
        cam.height = h / 6.0
    else:
        cam.heightAngle = cam.heightAngle.getValue() / 6.0
    close = rd.orbit(steps=steps, warm=warm)
    rd.fit_iso()
    rename = lambda d: {"median": d["median_ms"], "p90": d["p90_ms"], "min": d["min_ms"], "max": d["max_ms"]}  # noqa: E731
    return {"overview": rename(over), "closeup": rename(close)}


def _grid(rd, nx=16, ny=9):
    return [(int(rd.viewer_size[0] * (i + 0.5) / nx), int(rd.viewer_size[1] * (j + 0.5) / ny))
            for j in range(ny) for i in range(nx)]


def hover(doc, rd, heavy_object=None):
    view = Gui.ActiveDocument.ActiveView
    times, heavy = [], []
    for (x, y) in _grid(rd):
        info = view.getObjectInfo((x, y))
        t = time.perf_counter()
        rd.hover(x, y)
        rd.frame(clip=False)
        ms = (time.perf_counter() - t) * 1000.0
        times.append(ms)
        if heavy_object and info and heavy_object in (info.get("Object"), info.get("SubName") or ""):
            heavy.append(ms)
    rd.hover(0, 0)
    Gui.Selection.clearPreselection()
    C.pump(3)
    return {"all": summary(times), "heavy": summary(heavy) if heavy else None, "points": len(times)}


def select(doc, rd, n=20):
    view = Gui.ActiveDocument.ActiveView
    targets = []
    for (x, y) in _grid(rd):
        info = view.getObjectInfo((x, y))
        if info:
            targets.append(C.sel_target(doc, info))
        if len(targets) >= n:
            break
    times = []
    for obj, sub in targets:
        t = time.perf_counter()
        Gui.Selection.addSelection(obj, sub)
        C.pump(2)
        rd.frame(clip=False)
        times.append((time.perf_counter() - t) * 1000.0)
        Gui.Selection.clearSelection()
        C.pump(2)
    return {"select": summary(times), "targets": len(targets)}


def _edit(doc, rd, setter, reps):
    times = []
    for k in range(reps):
        t = time.perf_counter()
        setter(k)
        doc.recompute()
        C.wait_idle()
        rd.frame(clip=False)
        times.append((time.perf_counter() - t) * 1000.0)
    return {"edit": summary(times), "reps": reps}


def edit_body(doc, rd, obj_name="Pad", prop="Length", delta=0.3, reps=6):
    obj = doc.getObject(obj_name)
    v0 = getattr(obj, prop).Value
    res = _edit(doc, rd, lambda k: setattr(obj, prop, v0 + (delta if k % 2 == 0 else 0.0)), reps)
    setattr(obj, prop, v0)
    doc.recompute()
    C.wait_idle()
    return res


def edit_cut(doc, rd, base_name, reps=6):
    """Part::Cut of a STEP body by a cylinder through its bounding-box centre; the timed edit changes the
    cylinder radius by +-5 % (setup is not timed)."""
    base = doc.getObject(base_name)
    bb = base.Shape.BoundBox
    r0 = 0.15 * min(bb.XLength, bb.YLength, bb.ZLength)
    cyl = doc.addObject("Part::Cylinder", "BenchTool")
    cyl.Radius = r0
    cyl.Height = bb.ZLength * 3.0
    cyl.Placement.Base = App.Vector(bb.Center.x, bb.Center.y, bb.ZMin - bb.ZLength)
    cut = doc.addObject("Part::Cut", "BenchCut")
    cut.Base = base
    cut.Tool = cyl
    doc.recompute()
    C.wait_idle()
    res = _edit(doc, rd, lambda k: setattr(cyl, "Radius", r0 * (1.05 if k % 2 == 0 else 1.0)), reps)
    res["base"] = base_name
    res["faces"] = len(base.Shape.Faces)
    res["cut_valid"] = cut.Shape.isValid()
    return res


def fillet_holes(doc, rd, fillet_name="BenchFillet", reps=4):
    fil = doc.getObject(fillet_name)
    r0 = fil.Radius.Value
    res = _edit(doc, rd, lambda k: setattr(fil, "Radius", r0 * (1.2 if k % 2 == 0 else 1.0)), reps)
    res["valid"] = fil.Shape.isValid()
    return res


def save(doc, out_dir):
    path = os.path.join(out_dir, "saved.FCStd")
    t = time.perf_counter()
    doc.saveAs(path)
    s = time.perf_counter() - t
    return {"save_s": round(s, 3), "bytes": os.path.getsize(path)}
```

- [ ] **Step 3: `driver.py`**

```python
"""In-FreeCAD entry of the action benchmark. Run as a script argument of FreeCAD.exe (offscreen); starts from a
Qt timer so the GUI is up (the pattern of C:/dev/hybriddesign-render/phase1/scripts/bench.py).

Env: BENCH_FILE (path | fixture:holes1024), BENCH_LABEL, BENCH_VARIANT, BENCH_PROFILE, BENCH_ACTIONS,
     BENCH_OUT (dir), BENCH_CUT_BASE (object name for edit_cut), BENCH_BODY_OBJ (default Pad),
     BENCH_HEAVY (object name whose hover is reported separately), BENCH_W/BENCH_H (1920x1080).
"""
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import FreeCAD as App  # noqa: E402
import FreeCADGui as Gui  # noqa: E402
from PySide import QtCore  # noqa: E402
from fcbench import actions as A, common as C, fixtures as F  # noqa: E402

E = os.environ
OUT = E["BENCH_OUT"]
R = {"variant": E.get("BENCH_VARIANT", "stock"), "profile": E.get("BENCH_PROFILE", "fc"),
     "file": E["BENCH_FILE"], "file_label": E.get("BENCH_LABEL", "x"), "actions": {}, "errors": {}}


def run():
    load = C.CpuLoad().start()
    R["env"] = C.environment()
    todo = [a for a in E.get("BENCH_ACTIONS", "open,orbit,hover,select,save").split(",") if a]
    size = (int(E.get("BENCH_W", "1920")), int(E.get("BENCH_H", "1080")))
    make_rd = lambda: C.Renderer(Gui.ActiveDocument.ActiveView, size)  # noqa: E731
    if R["file"].startswith("fixture:"):
        path = F.build(R["file"][len("fixture:"):], OUT)
    else:
        path = R["file"]
    doc, rd, R["actions"]["open"] = A.open_doc(path, make_rd)
    R["env"]["gl"] = rd.gl
    for name in todo:
        if name == "open":
            continue
        try:
            if name == "orbit":
                R["actions"][name] = A.orbit(rd)
            elif name == "hover":
                R["actions"][name] = A.hover(doc, rd, E.get("BENCH_HEAVY"))
            elif name == "select":
                R["actions"][name] = A.select(doc, rd)
            elif name == "edit_body":
                R["actions"][name] = A.edit_body(doc, rd, E.get("BENCH_BODY_OBJ", "Pad"))
            elif name == "edit_cut":
                R["actions"][name] = A.edit_cut(doc, rd, E["BENCH_CUT_BASE"])
            elif name == "fillet_holes":
                R["actions"][name] = A.fillet_holes(doc, rd)
            elif name == "save":
                R["actions"][name] = A.save(doc, OUT)
        except Exception:
            R["errors"][name] = traceback.format_exc()
    R["cpu_load_pct"] = load.stop()
    R["mem_end"] = C.mem_mb()


def main():
    try:
        run()
    except Exception:
        R["errors"]["_run"] = traceback.format_exc()
    with open(os.path.join(OUT, "result.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, indent=1, default=str)
    os._exit(0)


QtCore.QTimer.singleShot(2500, main)
```

`bench/fcbench/fixtures.py` на этом шаге — заглушка только для `pad` (полная — в Task 3):
```python
"""Test documents built inside FreeCAD. build(name, out_dir) -> path of a saved FCStd."""
import os

import FreeCAD as App


def build(name, out_dir):
    if name == "pad":
        return _pad(out_dir)
    raise ValueError("unknown fixture " + name)


def _pad(out_dir):
    import Part
    import Sketcher
    d = App.newDocument("BenchPad")
    body = d.addObject("PartDesign::Body", "Body")
    sk = body.newObject("Sketcher::SketchObject", "Sketch")
    pts = [App.Vector(0, 0, 0), App.Vector(40, 0, 0), App.Vector(40, 25, 0), App.Vector(0, 25, 0)]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sk
    pad.Length = 10
    d.recompute()
    path = os.path.join(out_dir, "fixture_pad.FCStd")
    d.saveAs(path)
    App.closeDocument(d.Name)
    return path
```

- [ ] **Step 4: `tools/cfg_sandbox.py`** — скопировать `C:/dev/hybriddesign-perf/scripts/cfg_sandbox.py` без изменений (кодировка UTF-8 с BOM сохраняется) и добавить первой строкой комментарий `# copied from C:/dev/hybriddesign-perf/scripts/cfg_sandbox.py (2026-09-15): marks CAM migration as offered so no modal dialog blocks an offscreen FreeCAD`.

- [ ] **Step 5: `run_bench.sh`**

```bash
#!/bin/sh
# run_bench.sh <tag> <variant> <profile fc|hd> <FC_DIR> <file|fixture:name> <label> <actions>
# One offscreen FreeCAD run of the action benchmark. Fresh copies of the owner's cfg per run; profile fc = no
# add-ons (empty user data), hd = + HybridDesign loaded read-only from its installed repo via -M.
# Extra env passed through: BENCH_CUT_BASE, BENCH_BODY_OBJ, BENCH_HEAVY, BENCH_W, BENCH_H, BENCH_TO (s, 1800).
set -u
TAG=$1; VARIANT=$2; PROFILE=$3; FC_DIR=$4; FILE=$5; LABEL=$6; ACTIONS=$7
HERE=C:/dev/freecad-kernel-fixes/bench
RUN=$HERE/runs/$TAG
rm -rf "$RUN"; mkdir -p "$RUN/work" "$RUN/userdata/Mod"
REAL=C:/Users/B72A~1/AppData/Roaming/FreeCAD/v1-1
"$FC_DIR/bin/python.exe" $HERE/tools/cfg_sandbox.py "$REAL/user.cfg" "$RUN" "$REAL/system.cfg" > "$RUN/cfg.log" 2>&1
EXTRA=""
if [ "$PROFILE" = "hd" ]; then EXTRA="-M C:/Users/B72A~1/AppData/Roaming/FreeCAD/Mod/HybridDesign"; fi
export FREECAD_USER_DATA="$(cygpath -w "$RUN/userdata")"
export FREECAD_USER_TEMP="$RUN/work"
export QT_QPA_PLATFORM=offscreen
export BENCH_FILE="$FILE" BENCH_LABEL="$LABEL" BENCH_VARIANT="$VARIANT" BENCH_PROFILE="$PROFILE"
export BENCH_ACTIONS="$ACTIONS" BENCH_OUT="$RUN"
cd "$RUN/work" && bash C:/dev/tools/fcslot.sh timeout -k 15 ${BENCH_TO:-1800} "$FC_DIR/bin/FreeCAD.exe" \
  --log-file "$RUN/fc.log" -u "$RUN/user.cfg" -s "$RUN/system.cfg" $EXTRA "$HERE/fcbench/driver.py" \
  > "$RUN/stdout.log" 2>&1
echo "exit=$? tag=$TAG result=$(test -f "$RUN/result.json" && echo yes || echo NO)"
```

- [ ] **Step 6: Дымовой прогон на `fixture:pad` (профиль fc)**

Run:
```bash
cd C:/dev/freecad-kernel-fixes/bench && chmod +x run_bench.sh && \
  ./run_bench.sh smoke-fc stock fc "C:/Program Files/FreeCAD 1.1" fixture:pad pad open,orbit,hover,select,edit_body,save && \
  python -c "import json;r=json.load(open('runs/smoke-fc/result.json'));print(sorted(r['actions']), r['errors'], r['env']['gl'])"
```
Expected: `exit=0 ... result=yes`; действия `edit_body, hover, open, orbit, save, select` без ошибок; `gl.renderer` содержит `RTX 3050`. Если `gl.renderer` — AMD, прогон недействителен: проверить `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` для `FreeCAD.exe` (владелец выставил GpuPreference=2) и путь к exe копии.

- [ ] **Step 7: Дымовой прогон профиля hd**

Run: `./run_bench.sh smoke-hd stock hd "C:/Program Files/FreeCAD 1.1" fixture:pad pad open,orbit && python -c "import json;print(json.load(open('runs/smoke-hd/result.json'))['env']['hd_loaded'])"`
Expected: `True`. Если `False` (ключ `-M` не подгрузил верстак) — заменить в `run_bench.sh` для hd: `EXTRA=""` и в `userdata/Mod` создать junction на репозиторий HD (`cmd //c mklink /J "$(cygpath -w "$RUN/userdata/Mod/HybridDesign")" "C:\Users\B72A~1\AppData\Roaming\FreeCAD\Mod\HybridDesign"`), а в начало `run_bench.sh` перед `rm -rf "$RUN"` добавить снятие ссылки: `[ -d "$RUN/userdata/Mod/HybridDesign" ] && cmd //c rmdir "$(cygpath -w "$RUN/userdata/Mod/HybridDesign")"` — иначе `rm -rf` сотрёт сам репозиторий HD. Повторить Step 7.

- [ ] **Step 8: README и commit**

`bench/README.md` — назначение, команды `run_bench.sh` / `run_matrix.sh` / `report.py`, список действий и метрик (таблица из спека §11), предупреждение про junction из Step 7, где лежат результаты.

```bash
cd C:/dev/freecad-kernel-fixes
git add bench/fcbench bench/tools bench/run_bench.sh bench/README.md
git commit -m "bench: драйвер действий внутри FreeCAD и запуск в песочнице (план A, задача 2)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Фикстура «плита 32×32 отверстий + Fillet» и разрез STEP-детали VR6

**Files:**
- Modify: `bench/fcbench/fixtures.py`
- Create: `bench/tools/list_bodies.py`

**Interfaces:**
- Consumes: `actions.fillet_holes(doc, rd, "BenchFillet")`, `actions.edit_cut(doc, rd, base_name)`.
- Produces: `fixtures.build("holes1024", out_dir)` → FCStd с `Body` (BaseFeature = `HolesPlate`, Part::Feature 200×200×10 с 1024 сквозными отверстиями Ø3) и `BenchFillet` (PartDesign::Fillet одной кромки одного отверстия, R 0.5); переменная `BENCH_CUT_BASE` для VR6, выбранная и записанная в README.

- [ ] **Step 1: Фикстура в `fixtures.py`**

```python
def build(name, out_dir):
    if name == "pad":
        return _pad(out_dir)
    if name == "holes1024":
        return _holes(out_dir, 32)
    raise ValueError("unknown fixture " + name)


def _holes(out_dir, n):
    """A 200 x 200 x 10 plate with n x n through holes (d 3) - the top face has n*n inner wires, the case where
    BRepCheck_Face classifies wires pairwise (spec section 8b) - as the BaseFeature of a PartDesign Body, and a
    PartDesign::Fillet R0.5 on the top edge of one hole."""
    import Part
    d = App.newDocument("BenchHoles")
    plate = Part.makeBox(200, 200, 10)
    step = 200.0 / n
    tools = [Part.makeCylinder(1.5, 30, App.Vector(step * (i + 0.5), step * (j + 0.5), -10))
             for i in range(n) for j in range(n)]
    shape = plate.cut(Part.makeCompound(tools))
    base = d.addObject("Part::Feature", "HolesPlate")
    base.Shape = shape
    body = d.addObject("PartDesign::Body", "Body")
    body.BaseFeature = base
    d.recompute()
    # Setting Body.BaseFeature makes a PartDesign::FeatureBase inside the body; the fillet references its edges.
    fb = next(o for o in body.Group if o.TypeId == "PartDesign::FeatureBase")
    edge = None
    for k, e in enumerate(fb.Shape.Edges):
        c = e.Curve
        if c.__class__.__name__ == "Circle" and abs(c.Radius - 1.5) < 1e-6 and abs(c.Center.z - 10) < 1e-6:
            edge = "Edge%d" % (k + 1)
            break
    assert edge is not None, "no top hole edge found"
    fil = body.newObject("PartDesign::Fillet", "BenchFillet")
    fil.Base = (fb, [edge])
    fil.Radius = 0.5
    d.recompute()
    assert fil.Shape.isValid(), "fillet fixture is invalid"
    top = max(fb.Shape.Faces, key=lambda f: (f.CenterOfMass.z, f.Area))
    assert len(top.Wires) == n * n + 1, "top face should have %d wires, has %d" % (n * n + 1, len(top.Wires))
    path = os.path.join(out_dir, "fixture_holes%d.FCStd" % (n * n))
    d.saveAs(path)
    App.closeDocument(d.Name)
    return path
```
Фикстура сама проверяет себя тремя `assert`: кромка найдена, скругление валидно, у верхней грани 1025 проводов (внешний + 1024 отверстия). Упавший `assert` попадает в `errors._run` отчёта.

- [ ] **Step 2: Прогон фикстуры (fc)**

Run: `cd C:/dev/freecad-kernel-fixes/bench && ./run_bench.sh smoke-holes stock fc "C:/Program Files/FreeCAD 1.1" fixture:holes1024 holes open,fillet_holes`
Expected: `result=yes`, `actions.fillet_holes.valid == true`, `actions.fillet_holes.edit.median` порядка секунд (прошлый замер — 7,4–12,2 с). Если меньше 1 с — фикстура не воспроизводит случай 1024 петель на одной грани: проверить, что отверстия сквозные (верхняя грань с 1024 проводами: `len(top.Wires) == 1025`).

- [ ] **Step 3: Выбор базы для разреза VR6** — `bench/tools/list_bodies.py`:

```python
"""FreeCADCmd: list Part::Feature bodies of a file with face counts, largest first (choose BENCH_CUT_BASE).
The file comes from env BENCH_LIST_FILE: FreeCADCmd opens every .FCStd on its own command line itself."""
import os
import FreeCAD as App
doc = App.openDocument(os.environ["BENCH_LIST_FILE"])
rows = sorted(((len(o.Shape.Faces), o.Name, o.Label) for o in doc.Objects
               if o.TypeId == "Part::Feature" and not o.Shape.isNull()), reverse=True)
for r in rows[:15]:
    print("%5d  %-22s %s" % r)
```
Run: `BENCH_LIST_FILE=C:/dev/freecad-kernel-fixes/bench/files/VR6-350-new.FCStd bash C:/dev/tools/fcslot.sh timeout -k 15 300 "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" C:/dev/freecad-kernel-fixes/bench/tools/list_bodies.py`
Выбрать самое «тяжёлое по граням» тело, **кроме** `Part__Feature014` (винт ШВП: его перемешивание при 6,4° — минуты, это отдельное действие «открыть»). Записать в `bench/README.md` отдельной строкой ровно в формате `BENCH_CUT_BASE для VR6 = <Name> (<N> граней)` — `run_matrix.sh` читает имя из этой строки.

- [ ] **Step 4: Прогон разреза**

Run: `BENCH_CUT_BASE=<имя> ./run_bench.sh smoke-cut stock fc "C:/Program Files/FreeCAD 1.1" C:/dev/freecad-kernel-fixes/bench/files/VR6-350-new.FCStd vr6 open,edit_cut`
Expected: `edit_cut.cut_valid == true`, `edit_cut.edit.median` — сотни мс или больше (прошлый замер Part::Cut в VR6 — 0,93–1,13 с).

- [ ] **Step 5: Commit**

```bash
cd C:/dev/freecad-kernel-fixes
git add bench/fcbench/fixtures.py bench/tools/list_bodies.py bench/README.md
git commit -m "bench: плита 32×32 отверстий со скруглением и разрез STEP-детали VR6 (план A, задача 3)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Серия замеров базы и отчёт BASELINE

**Files:**
- Create: `bench/run_matrix.sh`, `bench/reports/BASELINE.md`

**Interfaces:**
- Consumes: `run_bench.sh`, `report.py`.
- Produces: `bench/reports/BASELINE.md` — медианы всех метрик на стоке (fc и hd) для: VR6-350-new (6,4° из файла), owner_oring, synthetic_1000_copies, synthetic_5000_copies, fixture:holes1024; эта таблица — «было» для всех следующих этапов.

- [ ] **Step 1: `run_matrix.sh`**

```bash
#!/bin/sh
# run_matrix.sh <variant> <FC_DIR> <reps> — the fixed set of files x profiles x actions, repeated <reps> times.
# Runs one FreeCAD at a time (fcslot inside run_bench.sh). Tags: <variant>-<label>-<profile>-r<k>.
set -u
V=$1; FC=$2; REPS=${3:-3}
F=C:/dev/freecad-kernel-fixes/bench/files
CUT=$(sed -n 's/^BENCH_CUT_BASE для VR6 = \([A-Za-z0-9_]*\).*/\1/p' C:/dev/freecad-kernel-fixes/bench/README.md)
for k in $(seq 1 $REPS); do
  for P in fc hd; do
    BENCH_HEAVY=Part__Feature014 BENCH_CUT_BASE=$CUT BENCH_TO=2400 ./run_bench.sh $V-vr6-$P-r$k $V $P "$FC" $F/VR6-350-new.FCStd vr6 open,orbit,hover,select,edit_cut,save
    ./run_bench.sh $V-oring-$P-r$k $V $P "$FC" $F/owner_oring.FCStd oring open,orbit,hover,select,edit_body,save
    ./run_bench.sh $V-s1000-$P-r$k $V $P "$FC" $F/synthetic_1000_copies.FCStd s1000 open,orbit,hover,select,save
    ./run_bench.sh $V-s5000-$P-r$k $V $P "$FC" $F/synthetic_5000_copies.FCStd s5000 open,orbit,hover,select
    ./run_bench.sh $V-holes-$P-r$k $V $P "$FC" fixture:holes1024 holes open,fillet_holes
  done
done
```
Проверить имя тела O-ring для `edit_body`: `BENCH_BODY_OBJ` по умолчанию `Pad` (прошлое исследование правило `Pad.Length`); если в файле другое имя — открыть его `list_bodies.py`-подобным однострочником и поправить.

- [ ] **Step 2: Прогон базы на стоке** (установленный FreeCAD: у владельца стоят патченые TKBO 009 и TKFillet 001 — `env.md5` их зафиксирует; это и есть его «было»).

Run: `cd C:/dev/freecad-kernel-fixes/bench && chmod +x run_matrix.sh && ./run_matrix.sh stock "C:/Program Files/FreeCAD 1.1" 3 2>&1 | tee runs/matrix-stock.log`
Expected: 30 строк `exit=0 ... result=yes`. Время серии — часы (VR6 GUI-открытие ~50 с при 6,4°, s5000 ~40 с). Прогоны с `errors` не пустыми — разобрать и перезапустить только их.

- [ ] **Step 3: Отчёт базы**

Скрипт свода «одного варианта» — это `report.table(runs, "stock", "stock")` (отношения 1.0×, медианы — база). Run: `python report.py runs stock stock reports/BASELINE.md`. Дописать в начало `BASELINE.md`: дату, `env.freecad`, md5 DLL, GPU, диапазон `cpu_load_pct` по прогонам, и абзац «что это значит для владельца» (какие действия самые медленные). Разброс: для каждой метрики min–max по трём повторам — если max/min > 1.5, пометить метрику «шумная» и указать фоновую загрузку.

- [ ] **Step 4: Commit**

```bash
cd C:/dev/freecad-kernel-fixes
git add bench/run_matrix.sh bench/reports/BASELINE.md
git commit -m "bench: замер базы на стоковом FreeCAD 1.1.1 — 8 действий, 5 файлов, профили fc/hd (план A, задача 4)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```
