# rvprobe.py - review vr6-body r1: class members the implementer did not test.
# User path: selection made the way a click makes it (tree (obj) / tree child (parent, "Child.") /
# 3D face (parent, "Child.Face6")), then Gui.runCommand("PartDesign_Body").  Modals recorded + dismissed.
# Section D (drag-drop onto an existing body) calls the view provider's canDropObject/dropObject, the
# functions the tree calls on a drop; it is recorded as INFO (not part of the verdict).
# Output PROBE_OUT, summary "RVPROBE pass=N fail=M".
import os, traceback
import FreeCAD as App, FreeCADGui as Gui
import Part
from PySide import QtCore, QtWidgets

out = []
modals = []


def watch():
    w = QtWidgets.QApplication.activeModalWidget()
    if w:
        txt = " / ".join(l.text() for l in w.findChildren(QtWidgets.QLabel) if l.text())
        modals.append("%s: %s" % (w.windowTitle(), txt.replace("\n", " ")))
        w.reject()


timer = QtCore.QTimer()
timer.timeout.connect(watch)
timer.start(100)


def ui():
    for _ in range(5):
        QtWidgets.QApplication.processEvents()


def box(d, name="Box", parent=None, x=0):
    b = d.addObject("Part::Box", name)
    b.Placement.Base = App.Vector(x, 0, 0)
    if parent is not None:
        parent.addObject(b)
    return b


def sheet(d):
    return d.addObject("Spreadsheet::Sheet", "Spreadsheet")


# builders return a list of selection items: obj or (obj, subname)
def c_box_face3d(d):
    b = box(d)
    return [(b, "Face6")]


def c_part_child_tree(d):
    p = d.addObject("App::Part", "Part")
    box(d, parent=p)
    return [(p, "Box.")]


def c_part_child_face3d(d):
    p = d.addObject("App::Part", "Part")
    box(d, parent=p)
    return [(p, "Box.Face6")]


def c_sheet_part_child(d):
    s = sheet(d)
    p = d.addObject("App::Part", "Part")
    box(d, parent=p)
    return [s, (p, "Box.")]


def c_link_chain(d):
    b = box(d)
    l1 = d.addObject("App::Link", "Link")
    l1.LinkedObject = b
    l2 = d.addObject("App::Link", "Link001")
    l2.LinkedObject = l1
    return [l2]


def c_link_sheet(d):
    s = sheet(d)
    l = d.addObject("App::Link", "Link")
    l.LinkedObject = s
    return [l]


def c_link_plane(d):
    p = d.addObject("App::Part", "Part")
    d.recompute()
    l = d.addObject("App::Link", "Link")
    l.LinkedObject = p.Origin.OriginFeatures[3]
    return [l]


def _array(d, name="Array"):
    b = box(d)
    a = d.addObject("App::Link", name)
    a.LinkedObject = b
    a.ElementCount = 3
    a.PlacementList = [App.Placement(App.Vector(20 * i, 0, 0), App.Rotation()) for i in range(3)]
    return a


def c_link_array(d):
    return [_array(d)]


def c_link_to_array(d):
    a = _array(d)
    l = d.addObject("App::Link", "Link")
    l.LinkedObject = a
    return [l]


def c_linkgroup(d):
    b = box(d)
    g = d.addObject("App::LinkGroup", "LinkGroup")
    g.ElementList = [b]
    return [g]


def c_points(d):
    import Points
    p = d.addObject("Points::Feature", "Points")
    p.Points = Points.Points([App.Vector(0, 0, 0), App.Vector(1, 1, 1)])
    return [p]


def c_app_fp_shape(d):
    o = d.addObject("App::FeaturePython", "PyShape")
    o.addProperty("Part::PropertyPartShape", "Shape")
    o.Shape = Part.makeBox(1, 1, 1)
    return [o]


def c_part_fp_shape(d):
    o = d.addObject("Part::FeaturePython", "PyPart")
    o.Shape = Part.makeBox(2, 2, 2)
    return [o]


def c_assembly(d):
    return [d.addObject("Assembly::AssemblyObject", "Assembly")]


def c_body_sheet(d):
    return [d.addObject("PartDesign::Body", "BodyA"), sheet(d)]


def c_sketch_sheet(d):
    return [sheet(d), d.addObject("Sketcher::SketchObject", "Sketch")]


def c_part_plane(d):
    p = d.addObject("Part::Plane", "Plane")
    return [p]


def c_other_body_sketch(d):
    b = d.addObject("PartDesign::Body", "BodyA")
    s = b.newObject("Sketcher::SketchObject", "Sketch")
    return [s]


def c_origin_axis(d):
    p = d.addObject("App::Part", "Part")
    d.recompute()
    return [p.Origin.OriginFeatures[0]]


def c_origin_obj(d):
    p = d.addObject("App::Part", "Part")
    d.recompute()
    return [p.Origin]


def c_mesh_box(d):
    import Mesh
    m = d.addObject("Mesh::Feature", "Mesh")
    m.Mesh = Mesh.createBox(10, 10, 10)
    return [m, box(d)]


def c_varset_box_face(d):
    v = d.addObject("App::VarSet", "VarSet")
    b = box(d)
    return [v, (b, "Face6")]


MULTI = "Base feature: The selected shape consists of multiple solids."
MANY = "Bad base feature: Body may be based on no more than one feature."
# name, builder, expected modal prefixes, bodies, base (None / name / @group-member), kind
CASES = [
    ("box_face3d", c_box_face3d, [], 1, "Box", "stock"),
    ("part_child_tree", c_part_child_tree, [], 1, "Box", "stock"),
    ("part_child_face3d", c_part_child_face3d, [], 1, "Box", "stock"),
    ("sheet+part_child", c_sheet_part_child, [], 1, "Box", "member"),
    ("link_chain", c_link_chain, [], 1, "Link001", "stock"),
    ("link_to_sheet", c_link_sheet, [], 1, None, "member"),
    ("link_to_origin_plane", c_link_plane, [], 1, None, "member"),
    ("link_array", c_link_array, [MULTI], 1, "Array", "stock"),
    ("link_to_link_array", c_link_to_array, [MULTI], 1, "Link", "stock"),
    ("linkgroup_with_box", c_linkgroup, [], 1, None, "member"),
    ("points", c_points, [], 1, None, "member"),
    ("app_featurepython_shape", c_app_fp_shape, [], 1, None, "member"),
    ("part_featurepython", c_part_fp_shape, [], 1, "PyPart", "stock"),
    ("assembly", c_assembly, [], 1, None, "member"),
    ("body+sheet", c_body_sheet, [], 1, None, "member"),
    ("sheet+sketch", c_sketch_sheet, [], 1, "@Sketch", "member"),
    ("part_plane_face", c_part_plane, [], 1, "Plane", "stock"),
    ("sketch_of_other_body", c_other_body_sketch,
     ["Bad base feature: Sketch already belongs to a body"], 1, None, "stock"),
    ("origin_axis", c_origin_axis, [], 1, None, "member"),
    ("origin_object", c_origin_obj, [], 1, None, "member"),
    ("mesh+box", c_mesh_box, [], 1, "Box", "member"),
    ("varset+box_face3d", c_varset_box_face, [], 1, "Box", "member"),
]


def select(items):
    Gui.Selection.clearSelection()
    for it in items:
        if isinstance(it, tuple):
            o, sub = it
            Gui.Selection.addSelection(o.Document.Name, o.Name, sub)
        else:
            Gui.Selection.addSelection(it)


def run_case(name, build, exp_modals, exp_bodies, exp_base, kind):
    d = App.newDocument("R_" + name.replace("+", "_"))
    Gui.activateView("Gui::View3DInventor", True)
    ui()
    try:
        items = build(d)
    except Exception as e:
        out.append("SKIP %-24s build failed: %s" % (name, e))
        App.closeDocument(d.Name)
        return None
    d.recompute()
    ui()
    before = set(o.Name for o in d.Objects if o.TypeId == "PartDesign::Body")
    select(items)
    selx = [(s.ObjectName, s.SubElementNames) for s in Gui.Selection.getSelectionEx("", 0)]
    selr = [o.Name for o in Gui.Selection.getSelection()]
    del modals[:]
    Gui.runCommand("PartDesign_Body", 0)
    ui()
    if Gui.Control.activeDialog():
        Gui.Control.closeDialog()
        ui()
    got = list(modals)
    bodies = [o for o in d.Objects if o.TypeId == "PartDesign::Body" and o.Name not in before]
    base = bodies[0].BaseFeature.Name if bodies and bodies[0].BaseFeature else None
    group = [o.Name for o in bodies[0].Group] if bodies else []
    d.recompute()
    bad = [o.Name for o in d.Objects if "Invalid" in o.State or "Error" in o.State]
    vol = None
    if bodies:
        try:
            vol = round(bodies[0].Shape.Volume, 3) if not bodies[0].Shape.isNull() else 0
        except Exception:
            vol = "err"
    ok = len(bodies) == exp_bodies and len(got) == len(exp_modals) and all(
        g.startswith(e) for g, e in zip(got, exp_modals))
    if exp_base and exp_base.startswith("@"):
        ok = ok and base is None and exp_base[1:] in group
    else:
        ok = ok and base == exp_base
    ok = ok and not bad
    out.append("%s %-24s [%s] sel=%s resolved=%s bodies=%d base=%s group=%s vol=%s invalid=%s modals=%s" % (
        "PASS" if ok else "FAIL", name, kind, selx, selr, len(bodies), base, group, vol, bad, got))
    App.closeDocument(d.Name)
    ui()
    return ok


# ---- D: drag-drop onto an existing empty body (INFO only)
def d_group(d):
    g = d.addObject("App::DocumentObjectGroup", "Group")
    box(d, parent=g)
    return g


def d_part(d):
    p = d.addObject("App::Part", "Part")
    box(d, parent=p)
    return p


def d_sheet(d):
    return sheet(d)


def d_link_array(d):
    return _array(d)


def drop_case(name, build):
    d = App.newDocument("D_" + name)
    Gui.activateView("Gui::View3DInventor", True)
    ui()
    obj = build(d)
    body = d.addObject("PartDesign::Body", "Body")
    d.recompute()
    ui()
    vp = body.ViewObject
    del modals[:]
    try:
        can = vp.canDropObject(obj)
    except Exception as e:
        can = "exc %s" % e
    if can is True:
        try:
            vp.dropObject(obj)
        except Exception as e:
            out.append("  drop exc %s" % e)
    ui()
    d.recompute()
    bad = [o.Name for o in d.Objects if "Invalid" in o.State or "Error" in o.State]
    base = body.BaseFeature.Name if body.BaseFeature else None
    out.append("INFO drop %-12s canDrop=%s base=%s invalid=%s modals=%s" % (name, can, base, bad, list(modals)))
    App.closeDocument(d.Name)
    ui()


def go():
    npass = nfail = nskip = 0
    try:
        Gui.activateWorkbench("PartDesignWorkbench")
        import PartDesignGui  # noqa: F401
        out.append("workbench active: %s" % Gui.activeWorkbench().name())
        try:
            import AssemblyApp  # noqa: F401
        except Exception as e:
            out.append("AssemblyApp import: %s" % e)
        ui()
        only = os.environ.get("RV_ONLY")
        for c in CASES:
            if only and c[0] not in only.split(","):
                continue
            try:
                r = run_case(*c)
                if r is None:
                    nskip += 1
                elif r:
                    npass += 1
                else:
                    nfail += 1
            except Exception:
                nfail += 1
                out.append("FAIL %s EXC %s" % (c[0], traceback.format_exc().replace("\n", " | ")))
                for n in list(App.listDocuments()):
                    try:
                        App.closeDocument(n)
                    except Exception:
                        pass
        for n, b in (("group", d_group), ("part", d_part), ("sheet", d_sheet), ("link_array", d_link_array)):
            try:
                drop_case(n, b)
            except Exception:
                out.append("INFO drop %s EXC %s" % (n, traceback.format_exc().replace("\n", " | ")))
    except Exception:
        out.append(traceback.format_exc())
        nfail += 1
    import PartDesignGui
    out.append("module %s" % PartDesignGui.__file__)
    try:
        import hybriddesign
        out.append("hybriddesign %s" % hybriddesign.__file__)
    except Exception as e:
        out.append("hybriddesign not loaded: %s" % e)
    out.append("RVPROBE pass=%d fail=%d skip=%d" % (npass, nfail, nskip))
    QtCore.QTimer.singleShot(300, fin)


def fin():
    open(os.environ["PROBE_OUT"], "w", encoding="utf-8").write("\n".join(out) + "\n")
    os._exit(0)


QtCore.QTimer.singleShot(1000, go)
