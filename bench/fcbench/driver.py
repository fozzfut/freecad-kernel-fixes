"""In-FreeCAD entry of the action benchmark. Run as a script argument of FreeCAD.exe (offscreen); starts from a
Qt timer so the GUI is up (the pattern of C:/dev/hybriddesign-render/phase1/scripts/bench.py).

Env: BENCH_FILE (path | fixture:holes1024), BENCH_LABEL, BENCH_VARIANT, BENCH_PROFILE, BENCH_ACTIONS,
     BENCH_OUT (dir), BENCH_CUT_BASE (object name for edit_cut), BENCH_FILLET_REPS (fillet_holes edits, default 4),
     BENCH_BODY_OBJ (default Pad),
     BENCH_W/BENCH_H (1920x1080), BENCH_REFINE_TO (s, 300: how long open waits for HybridDesign's stage-2
     refinement; VR6 took 111.5 s in C:/dev/hybriddesign-rework/progressive/NOTES.md, and the whole run has the
     owner's 600 s ceiling).
The heavy part of hover is chosen by the run itself (actions.hover); BENCH_HEAVY, which the plan's run_matrix.sh
still sets, is not read, and a run that has it says so in "notes".
Writes driver.pid first (run_bench.sh stops a child of a FreeCAD that was killed by the timeout), progress.log and
result.partial.json as each action ends (a run killed by the owner's 600 s ceiling still says how far it got), and
result.json last.
"""
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import FreeCADGui as Gui  # noqa: E402
from PySide import QtCore  # noqa: E402
from fcbench import actions as A, common as C, fixtures as F  # noqa: E402

E = os.environ
OUT = E["BENCH_OUT"]
R = {"variant": E.get("BENCH_VARIANT", "stock"), "profile": E.get("BENCH_PROFILE", "fc"),
     "file": E["BENCH_FILE"], "file_label": E.get("BENCH_LABEL", "x"), "actions": {}, "errors": {}}
REFINE_TO = float(E.get("BENCH_REFINE_TO", "300"))
with open(os.path.join(OUT, "driver.pid"), "w") as _f:
    _f.write(str(os.getpid()))
T0 = time.perf_counter()


def _step(what):
    """One line of progress.log (seconds since the driver started) and the result so far in result.partial.json."""
    with open(os.path.join(OUT, "progress.log"), "a", encoding="utf-8") as f:
        f.write("%8.1f %s\n" % (time.perf_counter() - T0, what))
    tmp = os.path.join(OUT, "result.partial.json.writing")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=1, default=str)
    os.replace(tmp, os.path.join(OUT, "result.partial.json"))


def _refine_error(hd):
    """Why HD's stage 2 did not bring the picture to the file's own quality (actions.open_doc, hd_refine)."""
    if hd["state"] == "timeout":
        return ("HD's refinement queue was not empty after %.0f s; still owed: %s"
                % (hd["wait_s"], ", ".join(hd.get("pending") or []) or "-"))
    if hd["state"] == "stuck":
        return ("HD's refinement queue is empty but %d shown part(s) stayed coarse: %s"
                % (len(hd.get("coarse") or []), ", ".join(hd.get("coarse") or [])))
    return "HD's refinement could not be followed (%s): %s" % (hd["state"], hd.get("error") or "-")


def run():
    load = C.CpuLoad().start()
    R["env"] = C.environment()
    todo = [a for a in E.get("BENCH_ACTIONS", "open,orbit,hover,select,save").split(",") if a]
    size = (int(E.get("BENCH_W", "1920")), int(E.get("BENCH_H", "1080")))
    make_rd = lambda: C.Renderer(Gui.ActiveDocument.ActiveView, size)  # noqa: E731
    if R["file"].startswith("fixture:"):
        try:                                     # a timed run never builds a cached fixture itself
            path = F.build(R["file"][len("fixture:"):], OUT, build_missing=False)
        except F.FixtureMissing as e:
            R["errors"]["fixture"] = "run tools/build_fixture.sh first: %s is missing" % e
            R["cpu_load_pct"] = load.stop()
            _step("end")
            return
    else:
        path = R["file"]
    if E.get("BENCH_HEAVY"):
        R["notes"] = ["BENCH_HEAVY=%s is not read: hover.heavy is the part with the most drawn triangles among the "
                      "parts the hover grid hits (hover.heavy_object)" % E["BENCH_HEAVY"]]
    _step("open")
    doc, rd, R["actions"]["open"] = A.open_doc(path, make_rd, REFINE_TO)
    R["env"]["gl"] = rd.gl
    hd = R["actions"]["open"].get("hd_refine")
    if hd and hd["state"] not in ("done", "no-session"):     # the later actions do not run on the file's quality
        R["errors"]["open_hd_refine"] = _refine_error(hd)
    for name in todo:
        if name == "open":
            continue
        _step(name)
        try:
            if name == "orbit":
                R["actions"][name] = A.orbit(rd)
            elif name == "hover":
                R["actions"][name] = A.hover(doc, rd)
                if R["actions"][name].get("heavy_error"):
                    R["errors"]["hover_heavy"] = R["actions"][name]["heavy_error"]
            elif name == "select":
                R["actions"][name] = A.select(doc, rd)
            elif name == "edit_body":
                R["actions"][name] = A.edit_body(doc, rd, E.get("BENCH_BODY_OBJ", "Pad"))
            elif name == "edit_cut":
                R["actions"][name] = A.edit_cut(doc, rd, E["BENCH_CUT_BASE"], refine_max_s=REFINE_TO)
                setup = R["actions"][name].get("hd_refine_setup")
                if setup and setup["state"] not in ("done", "no-session"):
                    R["errors"]["edit_cut_hd_refine"] = "before the timed edits: " + _refine_error(setup)
            elif name == "fillet_holes":
                R["actions"][name] = A.fillet_holes(doc, rd, reps=int(E.get("BENCH_FILLET_REPS", "4")))
            elif name == "save":
                R["actions"][name] = A.save(doc, OUT)
            else:
                R["errors"][name] = "unknown action"     # a typo in BENCH_ACTIONS must not vanish from the result
        except Exception:
            R["errors"][name] = traceback.format_exc()
        act = R["actions"].get(name)
        after = act.get("hd_refine_after") if isinstance(act, dict) else None
        if after and after["state"] not in ("done", "no-session"):
            R["errors"][name + "_hd_refine_after"] = "after the timed edits: " + _refine_error(after)
    R["cpu_load_pct"] = load.stop()
    R["mem_end"] = C.mem_mb()
    _step("end")


def main():
    try:
        run()
    except Exception:
        R["errors"]["_run"] = traceback.format_exc()
    try:
        R["children_at_exit"] = C.end_children()     # HD's mesh worker must not outlive this process
    except Exception:
        R["errors"]["_children"] = traceback.format_exc()
    with open(os.path.join(OUT, "result.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, indent=1, default=str)
    try:
        os.remove(os.path.join(OUT, "result.partial.json"))
    except OSError:
        pass
    C.hard_exit(0)


QtCore.QTimer.singleShot(2500, main)
