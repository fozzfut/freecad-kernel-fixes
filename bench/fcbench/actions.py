"""The owner's actions. Every function returns a dict of metrics; nothing here simplifies the model."""
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
    # The offscreen renderer's GL context is the harness's stand-in for the viewer's own (which has none offscreen):
    # made before the first frame and reported apart. Measured: the first context of the process takes ~1.5 s
    # (driver load); inside first_frame_ms it made the pad fixture's first frame 1801 ms, outside it 29 ms (smoke-fc).
    t = time.perf_counter()
    rd.r.render(coin.SoSeparator())
    rd.r.getBuffer()
    gl_init = (time.perf_counter() - t) * 1000.0
    rd.fit_iso()
    first = rd.frame()
    second = rd.frame()
    return doc, rd, {"open_s": round(open_s, 3), "idle_s": round(idle_s, 3), "gl_init_ms": round(gl_init, 1),
                     "first_frame_ms": round(first, 1), "second_frame_ms": round(second, 1),
                     "objects": len(doc.Objects), "mem": C.mem_mb()}


def orbit(rd, steps=24, warm=3):
    rd.fit_iso()
    over = rd.orbit(steps=steps, warm=warm)
    cam = rd.camera()
    if cam.isOfType(coin.SoOrthographicCamera.getClassTypeId()):
        field, zoom0 = cam.height, cam.height.getValue()
    else:
        field, zoom0 = cam.heightAngle, cam.heightAngle.getValue()
    field.setValue(zoom0 / 6.0)
    close = rd.orbit(steps=steps, warm=warm)
    field.setValue(zoom0)     # a perspective camera keeps its angle through fit_iso's viewAll: give it back
    rd.fit_iso()
    rename = lambda d: {"median": d["median_ms"], "p90": d["p90_ms"], "min": d["min_ms"], "max": d["max_ms"]}  # noqa: E731
    return {"overview": rename(over), "closeup": rename(close)}


def _grid(rd, nx=16, ny=9):
    """Points over the region getObjectInfo and hover pick in. That is the viewer's GL render action's region, and
    the offscreen renderer sets it to its own W x H at its first frame: measured in probe 1, rd.viewer_size (read
    before, 400x635) left the grid in one corner of the 1920x1080 pick region and select found 0 targets on the pad."""
    w, h = rd.rm.getViewportRegion().getViewportSizePixels().getValue()
    return [(int(w * (i + 0.5) / nx), int(h * (j + 0.5) / ny)) for j in range(ny) for i in range(nx)]


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
    """Edit -> recompute -> event loop busy until quiet -> frame. The quiet window wait_idle waits out to know the
    loop is done (200 ms) is the harness's wait and is not counted: measured in probe 1 it was 200 of the pad's
    ~360 ms per edit. The parts are kept next to the total ("recompute" includes setting the property)."""
    times, parts = [], {"recompute": [], "idle": [], "frame": []}
    for k in range(reps):
        t = time.perf_counter()
        setter(k)
        doc.recompute()
        rc = (time.perf_counter() - t) * 1000.0
        idle = C.wait_idle() * 1000.0
        fr = rd.frame(clip=False)
        times.append(rc + idle + fr)
        parts["recompute"].append(rc)
        parts["idle"].append(idle)
        parts["frame"].append(fr)
    res = {"edit": summary(times), "reps": reps}
    res.update({k: summary(v) for k, v in parts.items()})
    return res


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
