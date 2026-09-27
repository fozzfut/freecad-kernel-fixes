# vselprobe.py - lane vr6-unconf, item (b): Std_ViewFitSelection on App::Link objects inside App::Part.
# Builds small documents (no file I/O), selects like a tree/3D click, presses Std_ViewFitSelection (user path) and
# compares the camera with the fit of the selection's world bounding box (Coin SoOrthographicCamera::viewBoundingBox:
# focal point = box centre, height = 2 r (or 2 r / aspect), r = half the box diagonal).
# Output: $PROBE_OUT, one line per case + 'PROBE-DONE'.
import os, sys, time, math, traceback
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector as V, Placement, Rotation
from PySide import QtCore, QtWidgets
from pivy import coin

OUT = os.environ.get("PROBE_OUT", "C:/dev/occt8-mig/vr6unconf/runs/vsel.txt")
ONLY = [s for s in os.environ.get("VSEL_ONLY", "").split(",") if s]
fh = open(OUT, "w", encoding="utf-8")
T0 = time.time()


def out(*a):
    s = " ".join(str(x) for x in a)
    fh.write(s + "\n"); fh.flush()


def ui(sec=0.0, n=3):
    end = time.time() + sec
    while True:
        for _ in range(n):
            QtWidgets.QApplication.processEvents()
        try:
            Gui.updateGui()
        except Exception:
            pass
        if time.time() >= end:
            break
        time.sleep(0.01)


def view():
    return Gui.ActiveDocument.ActiveView


def cam_state():
    c = view().getCameraNode()
    pos = V(*c.position.getValue().getValue())
    rot = c.orientation.getValue()
    d = rot.multVec(coin.SbVec3f(0, 0, -1)).getValue()
    d = V(*d)
    fd = c.focalDistance.getValue()
    h = c.height.getValue() if hasattr(c, "height") else None
    return pos, d, fd, h, pos + d * fd


def aspect():
    w, hh = view().getSize()
    return float(w) / float(hh)


def set_anim(on):
    App.ParamGet("User parameter:BaseApp/Preferences/View").SetBool("UseNavigationAnimations", bool(on))
    try:
        view().setAnimationEnabled(bool(on))
    except Exception:
        pass
    ui()


def body_box(doc, name, l, w, h):
    b = doc.addObject("PartDesign::Body", name)
    bx = doc.addObject("PartDesign::AdditiveBox", name + "Box")
    b.addObject(bx)
    bx.Length, bx.Width, bx.Height = l, w, h
    return b


def link(doc, name, target, pl, parent=None):
    ln = doc.addObject("App::Link", name)
    ln.LinkedObject = target
    ln.Placement = pl
    if parent is not None:
        parent.addObject(ln)
    return ln


def new_doc(name):
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    ui()
    doc = App.newDocument(name)
    ui()
    return doc


def world_bb(sels):
    bb = App.BoundBox()
    for o, sub in sels:
        s = Part.getShape(o, sub, needSubElement=True, transform=True)
        bb.add(s.BoundBox)
    return bb


def select(sels, plain=False):
    Gui.Selection.clearSelection()
    for o, sub in sels:
        if plain:
            Gui.Selection.addSelection(o)
        else:
            Gui.Selection.addSelection(o.Document.Name, o.Name, sub)
    ui()
    got = []
    for se in Gui.Selection.getSelectionEx("", 0):
        for sn in (se.SubElementNames or ("",)):
            got.append(f"{se.ObjectName}:{sn}")
    return got


def judge(case, sels_for_bb, extra="", settle=0.0, tol=1e-3):
    ui(settle)
    bb = world_bb(sels_for_bb)
    c = bb.Center
    r = 0.5 * bb.DiagonalLength
    pos, d, fd, h, focal = cam_state()
    asp = aspect()
    hexp = 2 * r / asp if asp < 1 else 2 * r
    err_c = (focal - c).Length
    # centre error measured across the view (along the view direction the focal point may sit anywhere)
    dv = focal - c
    across = (dv - d * dv.dot(d)).Length
    ok = across <= tol * max(r, 1) and (h is None or abs(h - hexp) <= tol * hexp)
    hs = "persp" if h is None else f"{h:.6g}"
    out(f"CASE {case} {'PASS' if ok else 'FAIL'} across={across:.4g} h={hs} hexp={hexp:.6g} "
        f"dir=({d.x:.3f},{d.y:.3f},{d.z:.3f}) centre=({c.x:.3f},{c.y:.3f},{c.z:.3f}) "
        f"focal=({focal.x:.3f},{focal.y:.3f},{focal.z:.3f}) r={r:.4g} aspect={asp:.3f} {extra}")
    return ok, h


def fit_sel():
    Gui.runCommand("Std_ViewFitSelection", 0)


def instant_right():
    view().setCameraOrientation(Rotation(V(0, 1, 0), 90).multiply(Rotation(V(0, 0, 1), 90)))  # placeholder
    ui()


def scene_rails(doc, parent_pl=Placement()):
    rail = body_box(doc, "Rail", 350, 14.4, 15)
    small = body_box(doc, "Stop", 8.2, 13.4, 13)
    asm = doc.addObject("App::Part", "Asm")
    asm.Placement = parent_pl
    ys = (-75.0, -60.6, 46.2, 60.6)
    L = [link(doc, f"L{i + 1}", rail, Placement(V(0, y, 0), Rotation()), asm) for i, y in enumerate(ys)]
    S = [link(doc, f"S{i + 1}", small, Placement(V(x, y, 1), Rotation()), asm)
         for i, (x, y) in enumerate(((-3.2, -74.5), (345, -58.9), (-3.2, 45.5), (345, 61.1)))]
    rail.Visibility = False
    small.Visibility = False
    doc.recompute(); ui()
    return asm, L, S


def start_view():
    v = view()
    v.viewIsometric(); ui()
    v.fitAll(); ui(0.1)


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def c01_part_links_tree_right():
    doc = new_doc("c01"); set_anim(False)
    asm, L, S = scene_rails(doc)
    start_view(); view().viewRight(); ui()
    fit_all_h = cam_state()[3]
    sels = [(asm, "L3."), (asm, "L4.")]
    got = select(sels)
    fit_sel()
    h = cam_state()[3]
    judge("c01_part_links_tree_right", sels, f"sel={got} fitall_h={fit_all_h:.6g} ratio={h / fit_all_h:.3f}")


@case
def c02_plain_link_objects():
    doc = new_doc("c02"); set_anim(False)
    asm, L, S = scene_rails(doc)
    start_view(); view().viewRight(); ui()
    got = select([(L[2], ""), (L[3], "")], plain=True)
    fit_sel()
    judge("c02_plain_link_objects", [(asm, "L3."), (asm, "L4.")], f"sel={got}")


@case
def c03_part_placed_rotated():
    doc = new_doc("c03"); set_anim(False)
    asm, L, S = scene_rails(doc, Placement(V(100, 200, 50), Rotation(V(0, 0, 1), 30)))
    start_view(); view().viewRight(); ui()
    sels = [(asm, "L3."), (asm, "L4.")]
    got = select(sels)
    fit_sel()
    judge("c03_part_placed_rotated", sels, f"sel={got}")


@case
def c04_nested_parts():
    doc = new_doc("c04"); set_anim(False)
    asm, L, S = scene_rails(doc, Placement(V(10, -20, 5), Rotation(V(1, 0, 0), 20)))
    outer = doc.addObject("App::Part", "Outer")
    outer.Placement = Placement(V(-300, 40, 0), Rotation(V(0, 0, 1), -45))
    outer.addObject(asm)
    doc.recompute(); ui()
    start_view(); view().viewRight(); ui()
    sels = [(outer, "Asm.L3."), (outer, "Asm.L4.")]
    got = select(sels)
    fit_sel()
    judge("c04_nested_parts", sels, f"sel={got}")


@case
def c05_subelement_face():
    doc = new_doc("c05"); set_anim(False)
    asm, L, S = scene_rails(doc, Placement(V(0, 0, 30), Rotation(V(0, 1, 0), 10)))
    start_view(); view().viewRight(); ui()
    sels = [(asm, "L3.RailBox.Face2"), (asm, "S2.StopBox.Face6")]
    got = select(sels)
    fit_sel()
    judge("c05_subelement_face", sels, f"sel={got}")


@case
def c06_link_to_part():
    doc = new_doc("c06"); set_anim(False)
    asm, L, S = scene_rails(doc, Placement(V(0, 0, 0), Rotation()))
    la = link(doc, "LA", asm, Placement(V(0, 400, 0), Rotation(V(0, 0, 1), 90)))
    doc.recompute(); ui()
    start_view(); view().viewRight(); ui()
    sels = [(la, "L3."), (la, "L4.")]
    got = select(sels)
    fit_sel()
    judge("c06_link_to_part", sels, f"sel={got}")


@case
def c07_link_scaled():
    doc = new_doc("c07"); set_anim(False)
    asm, L, S = scene_rails(doc)
    L[2].ScaleVector = V(2, 2, 2)
    doc.recompute(); ui()
    start_view(); view().viewRight(); ui()
    sels = [(asm, "L3."), (asm, "L4.")]
    got = select(sels)
    fit_sel()
    judge("c07_link_scaled", sels, f"sel={got}")


@case
def c08_link_array_element():
    doc = new_doc("c08"); set_anim(False)
    rail = body_box(doc, "Rail", 350, 14.4, 15)
    asm = doc.addObject("App::Part", "Asm")
    arr = doc.addObject("App::Link", "Arr")
    arr.LinkedObject = rail
    arr.ElementCount = 3
    asm.addObject(arr)
    doc.recompute(); ui()
    arr.PlacementList = [Placement(V(0, 30 * i, 0), Rotation()) for i in range(3)]
    rail.Visibility = False
    doc.recompute(); ui()
    start_view(); view().viewRight(); ui()
    sels = [(asm, "Arr.2.")]
    got = select(sels)
    fit_sel()
    judge("c08_link_array_element", sels, f"sel={got}")


@case
def c09_anim_right_then_fit():
    """What the scenario did: Right view (animated) and Fit selection right after it."""
    doc = new_doc("c09"); set_anim(True)
    asm, L, S = scene_rails(doc)
    set_anim(False); start_view(); set_anim(True)
    sels = [(asm, "L3."), (asm, "L4.")]
    got = select(sels)
    view().viewRight(); ui()
    fit_sel()
    judge("c09_anim_right_then_fit", sels, f"sel={got} anim={view().isAnimationEnabled()}", settle=1.5)


@case
def c10_anim_fit_at_rest():
    doc = new_doc("c10"); set_anim(False)
    asm, L, S = scene_rails(doc)
    start_view(); view().viewRight(); ui()
    set_anim(True)
    sels = [(asm, "L3."), (asm, "L4.")]
    got = select(sels)
    fit_sel()
    judge("c10_anim_fit_at_rest", sels, f"sel={got}", settle=1.5)


@case
def c11_anim_iso_then_fit():
    doc = new_doc("c11"); set_anim(False)
    asm, L, S = scene_rails(doc, Placement(V(50, 0, 0), Rotation(V(0, 0, 1), 15)))
    view().viewFront(); view().fitAll(); ui()
    set_anim(True)
    sels = [(asm, "S1."), (asm, "L1.")]
    got = select(sels)
    view().viewIsometric(); ui()
    fit_sel()
    judge("c11_anim_iso_then_fit", sels, f"sel={got}", settle=1.5)


@case
def c12_anim_right_then_fitall():
    """Control of the same race on Std_ViewFitAll: Right (animated) then Fit all right after it."""
    doc = new_doc("c12"); set_anim(False)
    asm, L, S = scene_rails(doc)
    start_view(); set_anim(True)
    view().viewRight(); ui()
    Gui.runCommand("Std_ViewFitAll", 0)
    ui(1.5)
    bb = doc.getObject("Asm").Shape.BoundBox if hasattr(asm, "Shape") else None
    judge("c12_anim_right_then_fitall", [(asm, "")], "")


def vpbb(o, sub):
    try:
        b = o.ViewObject.getBoundingBox(sub, True)
        return f"({b.XMin:.2f},{b.YMin:.2f},{b.ZMin:.2f})..({b.XMax:.2f},{b.YMax:.2f},{b.ZMax:.2f})"
    except Exception as e:
        return "ERR " + repr(e)[:120]


def fcase(name, doc, sels, tol=1e-3):
    set_anim(False)
    start_view(); view().viewRight(); ui()
    got = select(sels)
    fit_sel()
    bbs = " ".join(f"vp[{o.Name}:{s}]={vpbb(o, s)}" for o, s in sels)
    wb = world_bb(sels)
    judge(name, sels, f"sel={got} {bbs} exp=({wb.XMin:.2f},{wb.YMin:.2f},{wb.ZMin:.2f})..({wb.XMax:.2f},{wb.YMax:.2f},{wb.ZMax:.2f})", tol=tol)


PL = Placement(V(0, 0, 30), Rotation(V(0, 1, 0), 10))


@case
def f01_body_face_top():
    doc = new_doc("f01")
    rail = body_box(doc, "Rail", 350, 14.4, 15); doc.recompute(); ui()
    fcase("f01_body_face_top", doc, [(rail, "RailBox.Face2")])


@case
def f02_part_body_face():
    doc = new_doc("f02")
    rail = body_box(doc, "Rail", 350, 14.4, 15)
    asm = doc.addObject("App::Part", "Asm"); asm.addObject(rail); asm.Placement = PL
    doc.recompute(); ui()
    fcase("f02_part_body_face", doc, [(asm, "Rail.RailBox.Face2")])


@case
def f03_part_link_face_identity():
    doc = new_doc("f03")
    asm, L, S = scene_rails(doc)
    fcase("f03_part_link_face_identity", doc, [(asm, "L3.RailBox.Face2")])


@case
def f04_part_link_face_placed():
    doc = new_doc("f04")
    asm, L, S = scene_rails(doc, PL)
    fcase("f04_part_link_face_placed", doc, [(asm, "L3.RailBox.Face2")])


@case
def f05_link_face_top():
    doc = new_doc("f05")
    rail = body_box(doc, "Rail", 350, 14.4, 15)
    ln = link(doc, "L", rail, Placement(V(0, 100, 0), Rotation(V(0, 0, 1), 20)))
    rail.Visibility = False
    doc.recompute(); ui()
    fcase("f05_link_face_top", doc, [(ln, "RailBox.Face2")])


@case
def f06_part_feature_face():
    doc = new_doc("f06")
    bx = doc.addObject("Part::Box", "Bx"); bx.Length, bx.Width, bx.Height = 350, 14.4, 15
    asm = doc.addObject("App::Part", "Asm"); asm.addObject(bx); asm.Placement = PL
    doc.recompute(); ui()
    fcase("f06_part_feature_face", doc, [(asm, "Bx.Face2")])


@case
def f07_part_link_edge_vertex():
    doc = new_doc("f07")
    asm, L, S = scene_rails(doc, PL)
    fcase("f07_part_link_edge_vertex", doc, [(asm, "L3.RailBox.Edge3"), (asm, "S2.StopBox.Vertex1")])


@case
def f08_part_link_whole_placed_single():
    doc = new_doc("f08")
    asm, L, S = scene_rails(doc, PL)
    fcase("f08_part_link_whole_placed_single", doc, [(asm, "S2.")])


@case
def f09_curved_face_in_part():
    doc = new_doc("f09")
    cy = doc.addObject("Part::Cylinder", "Cy"); cy.Radius, cy.Height = 10, 80
    asm = doc.addObject("App::Part", "Asm"); asm.addObject(cy)
    asm.Placement = Placement(V(40, -30, 5), Rotation(V(1, 1, 0), 35))
    big = doc.addObject("Part::Box", "Big"); big.Length, big.Width, big.Height = 400, 300, 50
    doc.recompute(); ui()
    # Face2 = the top disk (curved boundary). The viewer's box of a transformed node is Coin's SbXfBox3f rule: the node's LOCAL axis-aligned box, transformed,
    # then projected to world axes (looser than the exact world box for a rotated curved face - stock for every
    # object). Expected = that rule applied to the face's own box; 2 % for mesh vs exact.
    set_anim(False)
    start_view(); view().viewRight(); ui()
    sels = [(asm, "Cy.Face2")]
    got = select(sels)
    fit_sel()
    lb = cy.Shape.Faces[1].BoundBox
    pl = asm.Placement.multiply(cy.Placement)
    wb = App.BoundBox()
    for x in (lb.XMin, lb.XMax):
        for y in (lb.YMin, lb.YMax):
            for z in (lb.ZMin, lb.ZMax):
                wb.add(pl.multVec(V(x, y, z)))
    global world_bb
    saved = world_bb
    world_bb = lambda _s: wb
    try:
        judge("f09_curved_face_in_part", sels, f"sel={got} vp={vpbb(asm, 'Cy.Face2')} xfbox=({wb.XMin:.2f},{wb.YMin:.2f},{wb.ZMin:.2f})..({wb.XMax:.2f},{wb.YMax:.2f},{wb.ZMax:.2f})", tol=2e-2)
    finally:
        world_bb = saved


@case
def f10_two_faces_same_object():
    doc = new_doc("f10")
    asm, L, S = scene_rails(doc, PL)
    fcase("f10_two_faces_same_object", doc, [(asm, "L3.RailBox.Face1"), (asm, "L3.RailBox.Face3")])


@case
def f11_link_array_element_face():
    doc = new_doc("f11")
    rail = body_box(doc, "Rail", 350, 14.4, 15)
    asm = doc.addObject("App::Part", "Asm")
    arr = doc.addObject("App::Link", "Arr"); arr.LinkedObject = rail; arr.ElementCount = 3
    asm.addObject(arr); asm.Placement = PL
    doc.recompute(); ui()
    arr.PlacementList = [Placement(V(0, 30 * i, 0), Rotation(V(0, 0, 1), 5 * i)) for i in range(3)]
    rail.Visibility = False
    doc.recompute(); ui()
    fcase("f11_link_array_element_face", doc, [(asm, "Arr.2.RailBox.Face2")])


@case
def f12_single_vertex_keeps_zoom():
    """A lone vertex has no extent: the fit must centre it and keep the zoom (no zero-height camera)."""
    doc = new_doc("f12")
    asm, L, S = scene_rails(doc, PL)
    set_anim(False)
    start_view(); view().viewRight(); ui()
    h0 = cam_state()[3]
    sels = [(asm, "S2.StopBox.Vertex1")]
    got = select(sels)
    fit_sel(); ui()
    pos, d, fd, h, focal = cam_state()
    p = Part.getShape(asm, "S2.StopBox.Vertex1", needSubElement=True, transform=True).Vertexes[0].Point
    dv = focal - p
    across = (dv - d * dv.dot(d)).Length
    ok = across <= 1e-3 * h0 and h is not None and abs(h - h0) <= 1e-6 * h0
    out(f"CASE f12_single_vertex_keeps_zoom {'PASS' if ok else 'FAIL'} across={across:.4g} h={h} h_before={h0} "
        f"vertex=({p.x:.3f},{p.y:.3f},{p.z:.3f}) vp={vpbb(asm, 'S2.StopBox.Vertex1')} sel={got}")


@case
def f13_edge_only():
    doc = new_doc("f13")
    asm, L, S = scene_rails(doc, PL)
    fcase("f13_edge_only", doc, [(asm, "S2.StopBox.Edge1")])


@case
def c13_anim_right_then_fitall_offcentre():
    """Fit all right after an animated Right view, the orbit centre being elsewhere (after a fit on a small part)."""
    doc = new_doc("c13"); set_anim(False)
    asm, L, S = scene_rails(doc)
    start_view()
    select([(asm, "S1.")]); fit_sel(); ui(); Gui.Selection.clearSelection(); ui()
    set_anim(True)
    view().viewRight(); ui()
    Gui.runCommand("Std_ViewFitAll", 0)
    ui(1.5)
    pos, d, fd, h, focal = cam_state()
    set_anim(False); view().viewRight(); view().fitAll(); ui(0.2)
    pos2, d2, fd2, h2, focal2 = cam_state()
    dv = focal - focal2
    across = (dv - d2 * dv.dot(d2)).Length
    ok = across <= 1e-3 * h2 and abs(h - h2) <= 1e-3 * h2 and (d - d2).Length < 1e-4
    out(f"CASE c13_anim_right_then_fitall_offcentre {'PASS' if ok else 'FAIL'} across={across:.4g} h={h:.6g} h_ref={h2:.6g} dir=({d.x:.3f},{d.y:.3f},{d.z:.3f})")


@case
def c14_macro_viewtop_fitall():
    """Macro style: v.viewTop(); v.fitAll() with animations on (Python API, no event processing between)."""
    doc = new_doc("c14"); set_anim(False)
    asm, L, S = scene_rails(doc)
    start_view()
    select([(asm, "S4.")]); fit_sel(); ui(); Gui.Selection.clearSelection(); ui()
    set_anim(True)
    v = view(); v.viewTop(); v.fitAll(); ui(1.5)
    pos, d, fd, h, focal = cam_state()
    set_anim(False); v.viewTop(); v.fitAll(); ui(0.2)
    pos2, d2, fd2, h2, focal2 = cam_state()
    dv = focal - focal2
    across = (dv - d2 * dv.dot(d2)).Length
    ok = across <= 1e-3 * h2 and abs(h - h2) <= 1e-3 * h2 and (d - d2).Length < 1e-4
    out(f"CASE c14_macro_viewtop_fitall {'PASS' if ok else 'FAIL'} across={across:.4g} h={h:.6g} h_ref={h2:.6g} dir=({d.x:.3f},{d.y:.3f},{d.z:.3f}) ref=({d2.x:.3f},{d2.y:.3f},{d2.z:.3f})")


@case
def c15_perspective_anim_right_then_fit():
    doc = new_doc("c15"); set_anim(False)
    asm, L, S = scene_rails(doc)
    view().setCameraType("Perspective"); ui()
    start_view(); set_anim(True)
    sels = [(asm, "L3."), (asm, "L4.")]
    got = select(sels)
    view().viewRight(); ui()
    fit_sel()
    judge("c15_perspective_anim_right_then_fit", sels, f"sel={got}", settle=1.5)


@case
def c16_anim_face_fit_after_front():
    doc = new_doc("c16"); set_anim(False)
    asm, L, S = scene_rails(doc, PL)
    start_view(); set_anim(True)
    sels = [(asm, "S3.StopBox.Face6")]
    got = select(sels)
    view().viewFront(); ui()
    fit_sel()
    judge("c16_anim_face_fit_after_front", sels, f"sel={got}", settle=1.5)


def main():
    try:
        out("START", App.Version()[:4], "pid", os.getpid())
        import FreeCADGui
        for fn in CASES:
            if ONLY and not any(fn.__name__.startswith(o) for o in ONLY):
                continue
            try:
                fn()
            except Exception:
                out(f"CASE {fn.__name__} ERROR", traceback.format_exc().replace("\n", " | ")[-900:])
        out("PROBE-DONE", f"{time.time() - T0:.1f}s")
    finally:
        fh.close()
        for d in list(App.listDocuments().values()):
            App.closeDocument(d.Name)
        QtCore.QTimer.singleShot(200, lambda: Gui.getMainWindow().close())
        QtCore.QTimer.singleShot(15000, lambda: os._exit(4))


QtCore.QTimer.singleShot(60000 * 3, lambda: (out("HARD TIMEOUT"), fh.close(), os._exit(3)))
QtCore.QTimer.singleShot(1500, main)
