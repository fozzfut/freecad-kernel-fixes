"""In-FreeCAD entry of the action benchmark. Run as a script argument of FreeCAD.exe (offscreen); starts from a
Qt timer so the GUI is up (the pattern of C:/dev/hybriddesign-render/phase1/scripts/bench.py).

Env: BENCH_FILE (path | fixture:holes1024), BENCH_LABEL, BENCH_VARIANT, BENCH_PROFILE, BENCH_ACTIONS,
     BENCH_OUT (dir), BENCH_CUT_BASE (object name for edit_cut), BENCH_BODY_OBJ (default Pad),
     BENCH_HEAVY (object name whose hover is reported separately), BENCH_W/BENCH_H (1920x1080).
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
            else:
                R["errors"][name] = "unknown action"     # a typo in BENCH_ACTIONS must not vanish from the result
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
    C.hard_exit(0)


QtCore.QTimer.singleShot(2500, main)
