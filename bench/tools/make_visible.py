"""FreeCAD.exe (offscreen, tools/make_visible.sh): save a GUI copy of a headless-made document with every part shown.
The synthetic files (synthetic_<N>_copies.FCStd) were written by FreeCADCmd: no GuiDocument.xml, so in the GUI every
object opens hidden and the bench measured an empty scene (runs/stock-s1000-fc-r1: 0 of 144 hover points hit a
part, 0 select targets, orbit frame 9 ms). This opens the file in the GUI with a copy of the owner's cfg, so each
part's view provider takes the owner's own tessellation preferences, shows every Part::Feature, and saves to a new
file (the source is never written). Env: BENCH_VIS_SRC, BENCH_VIS_DST, BENCH_OUT (make_visible.json, make.pid)."""
import json
import os
import sys
import time
import traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import FreeCAD as App  # noqa: E402
from PySide import QtCore  # noqa: E402
from fcbench import common as C  # noqa: E402

E = os.environ
with open(os.path.join(E["BENCH_OUT"], "make.pid"), "w") as _f:
    _f.write(str(os.getpid()))


T0 = time.perf_counter()


def _step(what):
    """progress.log: seconds since start and the step begun (a run killed by the timeout says where it was)."""
    with open(os.path.join(E["BENCH_OUT"], "progress.log"), "a", encoding="utf-8") as f:
        f.write("%8.1f %s mem=%s\n" % (time.perf_counter() - T0, what, C.mem_mb()))


def main():
    res = {"src": E["BENCH_VIS_SRC"], "dst": E["BENCH_VIS_DST"]}
    try:
        _step("open")
        t = time.perf_counter()
        doc = App.openDocument(res["src"])
        C.pump()
        res["open_s"] = round(time.perf_counter() - t, 2)
        vps = [o.ViewObject for o in doc.Objects if o.ViewObject is not None]
        res["objects"] = len(doc.Objects)
        res["visible_before"] = sum(1 for v in vps if v.Visibility)
        _step("show")
        for o in doc.Objects:
            if o.ViewObject is not None and o.isDerivedFrom("Part::Feature"):
                o.ViewObject.Visibility = True
        C.pump()
        res["visible_after"] = sum(1 for v in vps if v.Visibility)
        res["deflection"] = sorted({(round(float(v.AngularDeflection), 3), round(float(v.Deviation), 4))
                                    for v in vps if "AngularDeflection" in v.PropertiesList})
        _step("save")
        tmp = res["dst"] + ".writing.FCStd"
        t = time.perf_counter()
        doc.saveAs(tmp)
        res["save_s"] = round(time.perf_counter() - t, 2)
        App.closeDocument(doc.Name)
        os.replace(tmp, res["dst"])
        res["bytes"] = os.path.getsize(res["dst"])
        _step("end")
    except Exception:
        res["error"] = traceback.format_exc()
    with open(os.path.join(E["BENCH_OUT"], "make_visible.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    C.hard_exit(0)


QtCore.QTimer.singleShot(2500, main)
