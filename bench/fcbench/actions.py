"""The owner's actions. Every function returns a dict of metrics; nothing here simplifies the model."""
import os
import time

import FreeCAD as App
import FreeCADGui as Gui
from pivy import coin

from . import common as C
from .stats import summary


def open_doc(path, rd_factory, refine_max_s=300.0):
    """Open, wait for the event loop, and with HybridDesign loaded wait for its stage 2 as well (common.hd_refinement):
    every later action then runs on the file's own display quality in both profiles.

    With HD (profile hd) three more numbers: hd_refine_s - seconds from the openDocument call until HD's refinement
    queue was empty with every shown part drawn at the file's own quality (HD's first, coarse picture is at
    open_s + idle_s); None when the wait (refine_max_s, 300 s) ran out or HD left shown parts coarse.
    hd_refine_wait_s - how long the driver waited for it after idle_s. hd_workers - how many worker processes
    (FreeCAD.exe) HD started for it. hd_refine keeps the state, the worker pids, HD's own end mark and HD's report
    per part."""
    with open(path, "rb") as f:          # warm the disk cache: we measure FreeCAD, not the disk
        while f.read(1 << 24):
            pass
    t0 = time.perf_counter()
    doc = App.openDocument(path)
    open_s = time.perf_counter() - t0
    idle_s = C.wait_idle()
    hd = C.hd_refinement(doc.Name, refine_max_s)
    if hd is not None and hd["state"] in ("done", "stuck"):
        hd["idle_after_s"] = round(C.wait_idle(), 3)      # HD's last slices; a quiet loop for what follows
    Gui.ActiveDocument.ActiveView.viewIsometric()
    C.pump(5)
    rd = rd_factory()
    # The offscreen renderer's GL context is the harness's stand-in for the viewer's own (which has none offscreen):
    # made before the first frame and reported apart. Measured: the first context of the process took 1550.7 ms and
    # the second 63.3 ms (runs/probe-p1/probe.json); with it inside, the pad's first frame was 709.0 ms
    # (runs/smoke-fc-before/result.json, the brief's code), with it outside tens of ms (runs/smoke-fc/result.json).
    t = time.perf_counter()
    rd.r.render(coin.SoSeparator())
    rd.r.getBuffer()
    gl_init = (time.perf_counter() - t) * 1000.0
    rd.fit_iso()
    first = rd.frame()
    second = rd.frame()
    res = {"open_s": round(open_s, 3), "idle_s": round(idle_s, 3), "gl_init_ms": round(gl_init, 1),
           "first_frame_ms": round(first, 1), "second_frame_ms": round(second, 1),
           "objects": len(doc.Objects), "mem": C.mem_mb()}
    if hd is not None:
        # When the queue emptied: nothing drawn coarse - the picture was exact when the loop went idle (open_s +
        # idle_s, as in profile fc); parts drawn coarse - HD's own end-of-pass mark. The moment this process SAW it
        # empty comes later by the 200 ms quiet window of wait_idle (smoke-hd, fix round 1: 1.252 s seen against
        # 1.051 s), which is the harness, not HD; it is kept as seen_empty_s.
        first_picture = open_s + idle_s
        fin = hd.get("hd_finished_at")
        lowered = bool((hd.get("report") or {}).get("lowered"))
        if hd["state"] not in ("done", "no-session"):   # timeout, error, or shown parts left coarse (stuck)
            refine = None
        elif not lowered:
            refine = first_picture
        elif fin is not None:
            refine = max(first_picture, fin - t0)
        else:
            refine = hd["empty_at"] - t0
        res["hd_refine_s"] = round(refine, 3) if refine is not None else None
        res["hd_refine_wait_s"] = hd["wait_s"]
        res["hd_workers"] = len(hd["worker_pids"])
        empty_at = hd.pop("empty_at")
        hd["seen_empty_s"] = round(empty_at - t0, 3) if empty_at is not None else None
        if fin is not None:                                # HD's own mark, as seconds after the openDocument call
            hd["hd_finished_at"] = round(fin - t0, 3)
        res["hd_refine"] = hd
    return doc, rd, res


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


def _hover_ms(rd, x, y):
    t = time.perf_counter()
    rd.hover(x, y)
    rd.frame(clip=False)
    return (time.perf_counter() - t) * 1000.0


def drawn_triangles(obj):
    """Triangles the object's view provider draws now: Coin's primitive count over its root node. The count follows
    the display-mode switch, so only the mode on screen counts (edges and vertices are not triangles), and with HD it
    is the mesh HD has put in, coarse or exact."""
    vp = getattr(obj, "ViewObject", None)
    node = getattr(vp, "RootNode", None) if vp is not None else None
    if node is None:
        return None
    act = coin.SoGetPrimitiveCountAction()
    act.apply(node)
    return int(act.getTriangleCount())


HEAVY_WANT = 12        # timed points on the heavy part beyond the grid's (final review I4: 1-2 grid points were all)
HEAVY_PROBES = 64      # getObjectInfo checks (not timed) spent to find them
HEAVY_PROBE_S = 45.0   # and at most this long: s1000 hd took up to 490 of the run's 600 s before this (stock baseline)


def _screen_box(rd, obj):
    """The pixel box (x0, y0, x1, y1; Coin's coordinates, origin bottom-left, as getObjectInfo and hover take them)
    of the part's drawn node on the pick region: the corners of its world box (SoGetBoundingBoxAction on the first
    path to its view provider's root node, so the transforms above it count) projected by the camera's view volume
    and clipped to the region. None when the node is not in the scene (a Link's copy) or the box is off screen."""
    vp = getattr(obj, "ViewObject", None)
    node = getattr(vp, "RootNode", None) if vp is not None else None
    if node is None:
        return None
    sa = coin.SoSearchAction()
    sa.setNode(node)
    sa.setInterest(coin.SoSearchAction.FIRST)
    sa.apply(rd.scene())
    path = sa.getPath()
    if path is None:
        return None
    w, h = rd.rm.getViewportRegion().getViewportSizePixels().getValue()
    ba = coin.SoGetBoundingBoxAction(coin.SbViewportRegion(w, h))
    ba.apply(path)
    box = ba.getBoundingBox()
    if box.isEmpty():
        return None
    vv = rd.camera().getViewVolume(float(w) / float(h))
    lo, hi = box.getMin().getValue(), box.getMax().getValue()
    xs, ys = [], []
    for x in (lo[0], hi[0]):
        for y in (lo[1], hi[1]):
            for z in (lo[2], hi[2]):
                p = vv.projectToScreen(coin.SbVec3f(x, y, z)).getValue()
                xs.append(p[0] * w)
                ys.append(p[1] * h)
    x0, x1 = max(0, int(min(xs))), min(w - 1, int(max(xs)))
    y0, y1 = max(0, int(min(ys))), min(h - 1, int(max(ys)))
    if x0 > x1 or y0 > y1:
        return None
    return x0, y0, x1, y1


def _box_points(box, k):
    x0, y0, x1, y1 = box
    return [(int(x0 + (x1 - x0) * (i + 0.5) / k), int(y0 + (y1 - y0) * (j + 0.5) / k))
            for j in range(k) for i in range(k)]


def _heavy_points(view, doc, key, box, taken):
    """Points inside the heavy part's screen box that getObjectInfo says lie on it (not timed): a 5 x 5 pass over the
    box, then a 9 x 9 one, until HEAVY_WANT points, HEAVY_PROBES checks or HEAVY_PROBE_S seconds."""
    found, probes, seen = [], 0, set(taken)
    t0 = time.perf_counter()
    for k in (5, 9):
        for pt in _box_points(box, k):
            if len(found) >= HEAVY_WANT or probes >= HEAVY_PROBES or time.perf_counter() - t0 > HEAVY_PROBE_S:
                return found, probes, round(time.perf_counter() - t0, 3)
            if pt in seen:
                continue
            seen.add(pt)
            probes += 1
            info = view.getObjectInfo(pt)
            if info and info.get("Object") and (info.get("Document") or doc.Name, info["Object"]) == key:
                found.append(pt)
    return found, probes, round(time.perf_counter() - t0, 3)


def hover(doc, rd):
    """Preselection response + highlighted frame at each point of the 16 x 9 grid over the isometric view ("all").

    "heavy" is the same timing on the heavy part: the part with the most drawn triangles (drawn_triangles) among the
    parts the grid hits. A fixed name cannot serve: VR6's ball screw lies under the top plate in this view, and
    denser grids than this one never reached it (0 of 1536 points in hybriddesign-render/phase1/out/hoverspike_vr6.json,
    0 of 200 in proof_vr6_ON.json). The grid is timed first, as the owner moves the cursor over a model he has just
    opened; what each point hit is asked afterwards (getObjectInfo, not timed).
    The grid lands on the heavy part in 1-2 points on VR6 and s1000 (final review I4), so more points are sampled on
    it: inside its projected screen box (_screen_box), checked with getObjectInfo (not timed), up to HEAVY_WANT; each
    is timed as the cursor arriving on the part (moved off to the corner first, not timed). "heavy" summarises the
    grid's points and these (its n is the number of points), "heavy_grid" the grid's alone (the definition of the
    stock baseline of 22.09); heavy_sampling says how the points were found.
    hit_parts lists every part the grid hit with its points and triangles. A grid that hits no part at all gives
    heavy None and heavy_error, which the driver records as errors.hover_heavy: the metric must not vanish."""
    pts = _grid(rd)
    times = [_hover_ms(rd, x, y) for (x, y) in pts]
    rd.hover(0, 0)
    Gui.Selection.clearPreselection()
    C.pump(3)
    view = Gui.ActiveDocument.ActiveView
    on = {}                                   # (document, object) -> indices of the grid points on it
    for i, (x, y) in enumerate(pts):
        info = view.getObjectInfo((x, y))
        if info and info.get("Object"):
            on.setdefault((info.get("Document") or doc.Name, info["Object"]), []).append(i)
    parts = []
    for (dname, name), idx in on.items():
        try:
            obj = App.getDocument(dname).getObject(name)
        except Exception:
            obj = None
        parts.append({"name": name, "document": dname, "label": getattr(obj, "Label", None),
                      "triangles": drawn_triangles(obj) if obj is not None else None, "points": len(idx)})
    parts.sort(key=lambda p: (-(p["triangles"] if p["triangles"] is not None else -1), -p["points"], p["name"]))
    res = {"all": summary(times), "points": len(times), "hit_points": sum(len(v) for v in on.values()),
           "hit_parts": parts, "heavy": None, "heavy_grid": None, "heavy_object": None, "heavy_label": None,
           "heavy_triangles": None}
    if not parts:
        res["heavy_error"] = "the %d-point hover grid hit no part: there is no heavy part to time" % len(pts)
        return res
    top = parts[0]
    key = (top["document"], top["name"])
    grid_times = [times[i] for i in on[key]]
    try:
        obj = App.getDocument(top["document"]).getObject(top["name"])
    except Exception:
        obj = None
    box = _screen_box(rd, obj) if obj is not None else None
    grid_pts = [pts[i] for i in on[key]]
    samp = {"box": list(box) if box else None,
            "grid_points_in_box": (sum(1 for (x, y) in grid_pts if box[0] <= x <= box[2] and box[1] <= y <= box[3])
                                   if box else None)}
    extra_pts, samp["probes"], samp["probe_s"] = _heavy_points(view, doc, key, box, pts) if box else ([], 0, 0.0)
    extra = []
    for (x, y) in extra_pts:
        rd.hover(0, 0)                        # the cursor arrives on the part from elsewhere, as on the grid
        Gui.Selection.clearPreselection()
        C.pump(2)
        extra.append(_hover_ms(rd, x, y))
    rd.hover(0, 0)
    Gui.Selection.clearPreselection()
    C.pump(3)
    samp["extra_points"] = len(extra)
    res["heavy"] = summary(grid_times + extra)
    res["heavy_grid"] = summary(grid_times)
    res["heavy_sampling"] = samp
    res.update(heavy_object=top["name"], heavy_label=top["label"], heavy_triangles=top["triangles"])
    return res


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


def _edit(doc, rd, setter, reps, refine_max_s=300.0):
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
    # With HD an edited part can be drawn coarse and handed to HD's mesh worker: the timed frame is HD's first
    # picture, as the owner sees it, and the worker goes on after wait_idle returns (fix round 3, vr6cur hd: after
    # every edit of BenchCut fc.log says "its shape changed while it was being refined", and at the save one part
    # was still owed). The edits' own timing stays as it is; what HD needed after the last one to bring the picture
    # to the file's quality is waited for here (not timed in "edit") and recorded, and the later actions run on it.
    after = C.hd_refinement(doc.Name, refine_max_s)
    if after is not None:
        after.pop("empty_at", None)                # clock marks of this process mean nothing in the file: dropped
        after.pop("hd_finished_at", None)
        after.pop("report", None)                  # open's hd_refine keeps HD's report per part
        res["hd_refine_after"] = after
    return res


def edit_body(doc, rd, obj_name="Pad", prop="Length", delta=0.3, reps=6):
    obj = doc.getObject(obj_name)
    v0 = getattr(obj, prop).Value
    res = _edit(doc, rd, lambda k: setattr(obj, prop, v0 + (delta if k % 2 == 0 else 0.0)), reps)
    setattr(obj, prop, v0)
    doc.recompute()
    C.wait_idle()
    return res


def edit_cut(doc, rd, base_name, reps=6, refine_max_s=300.0):
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
    # with HD, a new part may be drawn coarse and refined by HD's worker: the timed edits start after that pass
    setup_hd = C.hd_refinement(doc.Name, refine_max_s)
    res = _edit(doc, rd, lambda k: setattr(cyl, "Radius", r0 * (1.05 if k % 2 == 0 else 1.0)), reps, refine_max_s)
    res["base"] = base_name
    res["faces"] = len(base.Shape.Faces)
    res["cut_valid"] = cut.Shape.isValid()
    if setup_hd is not None:                     # clock marks of this process mean nothing in the file: dropped
        setup_hd.pop("empty_at", None)
        setup_hd.pop("hd_finished_at", None)
        res["hd_refine_setup"] = setup_hd
    return res


def fillet_holes(doc, rd, fillet_name="BenchFillet", reps=4):
    fil = doc.getObject(fillet_name)
    r0 = fil.Radius.Value
    res = _edit(doc, rd, lambda k: setattr(fil, "Radius", r0 * (1.2 if k % 2 == 0 else 1.0)), reps)
    res["valid"] = fil.Shape.isValid()
    if fil.Radius.Value != r0:                   # odd reps end on 1.2 r0: back to the file's value, as edit_body does
        fil.Radius = r0                          # (an even count already ends on r0 and costs no extra recompute)
        doc.recompute()
        C.wait_idle()
    return res


def save(doc, out_dir):
    path = os.path.join(out_dir, "saved.FCStd")
    t = time.perf_counter()
    doc.saveAs(path)
    s = time.perf_counter() - t
    return {"save_s": round(s, 3), "bytes": os.path.getsize(path)}
