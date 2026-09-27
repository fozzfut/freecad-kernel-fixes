# bodysel.py - user-path probe for PartDesign_Body with a selection (lane vr6-body, STUMBLES bug 2).
# r2 (27.09): + link arrays / links to arrays / link groups (section C) and drop onto a body (section D, verdicts).
# Every case: new document, build the objects, select like a click (tree selection of the object),
# press PartDesign_Body through Gui.runCommand, record modal dialogs (auto-dismissed), bodies,
# BaseFeature, body Group, the body's parent container.  Verdict per case against EXPECTED
# (the fixed behaviour); on the stock module the class members must FAIL (negative control).
# Output: PROBE_OUT (text), one line per case + summary "BODYSEL pass=N fail=M".
import os, traceback
import FreeCAD as App, FreeCADGui as Gui
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


def box(d, name="Box", parent=None):
    b = d.addObject("Part::Box", name)
    if parent is not None:
        parent.addObject(b)
    return b


# each builder returns the list of objects to select (in click order)
def c_sheet(d):
    return [d.addObject("Spreadsheet::Sheet", "Spreadsheet")]


def c_varset(d):
    return [d.addObject("App::VarSet", "VarSet")]


def c_textdoc(d):
    return [d.addObject("App::TextDocument", "Notes")]


def c_part_empty(d):
    return [d.addObject("App::Part", "Part")]


def c_part_box(d):
    p = d.addObject("App::Part", "Part")
    box(d, parent=p)
    return [p]


def c_active_part_box(d):
    # Std_Part leaves its new Part active; the user selects it in the tree and presses New Body
    Gui.runCommand("Std_Part", 0)
    ui()
    p = [o for o in d.Objects if o.TypeId == "App::Part"][0]
    box(d, parent=p)
    d.recompute()
    return [p]


def c_group_box(d):
    g = d.addObject("App::DocumentObjectGroup", "Group")
    box(d, parent=g)
    return [g]


def c_origin_plane(d):
    p = d.addObject("App::Part", "Part")
    d.recompute()
    return [p.Origin.OriginFeatures[3]]  # XY_Plane of the Part's origin


def c_lcs(d):
    return [d.addObject("App::LocalCoordinateSystem", "LCS")]


def c_link_part(d):
    p = d.addObject("App::Part", "Part")
    box(d, parent=p)
    l = d.addObject("App::Link", "Link")
    l.LinkedObject = p
    return [l]


def c_mesh(d):
    import Mesh
    m = d.addObject("Mesh::Feature", "Mesh")
    m.Mesh = Mesh.createBox(10, 10, 10)
    return [m]


# ---- shape objects: stock behaviour must stay
def c_box(d):
    return [box(d)]


def c_link_box(d):
    b = box(d)
    l = d.addObject("App::Link", "Link")
    l.LinkedObject = b
    return [l]


def c_empty_feature(d):
    return [d.addObject("Part::Feature", "Empty")]


def c_two_boxes(d):
    return [box(d, "Box"), box(d, "Box001")]


def c_compound(d):
    a, b = box(d, "Box"), box(d, "Box001")
    b.Placement.Base = App.Vector(20, 0, 0)
    c = d.addObject("Part::Compound", "Compound")
    c.Links = [a, b]
    return [c]


def c_pd_datum(d):
    return [d.addObject("PartDesign::Plane", "DatumPlane")]


def c_sketch(d):
    return [d.addObject("Sketcher::SketchObject", "Sketch")]


def c_other_body_feature(d):
    b = d.addObject("PartDesign::Body", "BodyA")
    f = b.newObject("PartDesign::AdditiveBox", "AddBox")
    return [f]


def c_body(d):
    return [d.addObject("PartDesign::Body", "BodyA")]


# ---- mixed selections
def c_sheet_box(d):
    return [d.addObject("Spreadsheet::Sheet", "Spreadsheet"), box(d)]


def c_box_sheet(d):
    return [box(d), d.addObject("Spreadsheet::Sheet", "Spreadsheet")]


def c_sheet_varset(d):
    return [d.addObject("Spreadsheet::Sheet", "Spreadsheet"), d.addObject("App::VarSet", "VarSet")]


def c_part_and_its_box(d):
    p = d.addObject("App::Part", "Part")
    b = box(d, parent=p)
    return [p, b]


def c_sheet_two_boxes(d):
    return [d.addObject("Spreadsheet::Sheet", "Spreadsheet"), box(d, "Box"), box(d, "Box001")]


# ---- r2: link arrays (LinkBaseExtension::extensionGetLinkedObject returns the array itself)
def _array(d, target, name="Array", n=3):
    a = d.addObject("App::Link", name)
    a.LinkedObject = target
    a.ElementCount = n
    a.PlacementList = [App.Placement(App.Vector(20 * i, 0, 0), App.Rotation()) for i in range(n)]
    return a


def _link(d, target, name="Link"):
    l = d.addObject("App::Link", name)
    l.LinkedObject = target
    return l


def c_link_array(d):
    return [_array(d, box(d))]


def c_link_to_link_array(d):
    return [_link(d, _array(d, box(d)))]


def c_link_link_link_array(d):
    return [_link(d, _link(d, _array(d, box(d))), "Link001")]


def c_link_array_of_link(d):
    return [_array(d, _link(d, box(d)))]


def c_link_array_of_sheet(d):
    return [_array(d, d.addObject("Spreadsheet::Sheet", "Spreadsheet"), n=2)]


def c_link_array_of_part(d):
    p = d.addObject("App::Part", "Part")
    box(d, parent=p)
    return [_array(d, p, n=2)]


def c_linkgroup(d):
    g = d.addObject("App::LinkGroup", "LinkGroup")
    g.ElementList = [box(d)]
    return [g]


def c_link_to_linkgroup(d):
    g = d.addObject("App::LinkGroup", "LinkGroup")
    g.ElementList = [box(d)]
    return [_link(d, g)]


def c_sheet_link_array(d):
    return [d.addObject("Spreadsheet::Sheet", "Spreadsheet"), _array(d, box(d))]


EMPTY_MSG = "Bad base feature: Base feature (%s) has an empty shape."
MANY_MSG = "Bad base feature: Body may be based on no more than one feature."
MULTI_MSG = "Base feature: The selected shape consists of multiple solids."
# name, builder, expected modals (prefix match), expected bodies created by the command,
# expected BaseFeature name (None = none), in-group name (sketch), class member flag
CASES = [
    ("sheet", c_sheet, [], 1, None, "member"),
    ("varset", c_varset, [], 1, None, "member"),
    ("textdoc", c_textdoc, [], 1, None, "member"),
    ("part_empty", c_part_empty, [], 1, None, "member"),
    ("part_with_box", c_part_box, [], 1, None, "member"),
    ("active_part_with_box", c_active_part_box, [], 1, None, "member"),
    ("group_with_box", c_group_box, [], 1, None, "member"),
    ("origin_plane", c_origin_plane, [], 1, None, "member"),
    ("lcs", c_lcs, [], 1, None, "member"),
    ("link_to_part", c_link_part, [], 1, None, "member"),
    ("mesh", c_mesh, [], 1, None, "member"),
    ("sheet+box", c_sheet_box, [], 1, "Box", "member"),
    ("box+sheet", c_box_sheet, [], 1, "Box", "member"),
    ("sheet+varset", c_sheet_varset, [], 1, None, "member"),
    ("part+its_box", c_part_and_its_box, [], 1, "Box", "member"),
    ("sheet+2boxes", c_sheet_two_boxes, [MANY_MSG], 0, None, "stock"),
    ("box", c_box, [], 1, "Box", "stock"),
    ("link_to_box", c_link_box, [], 1, "Link", "stock"),
    ("empty_part_feature", c_empty_feature, [EMPTY_MSG % "Empty"], 1, None, "stock"),
    ("two_boxes", c_two_boxes, [MANY_MSG], 0, None, "stock"),
    ("compound_2_solids", c_compound, ["Base feature: The selected shape consists of multiple solids."], 1, "Compound", "stock"),
    ("pd_datum_plane", c_pd_datum, [], 1, "DatumPlane", "stock"),
    ("sketch", c_sketch, [], 1, "@Sketch", "stock"),
    ("feature_of_other_body", c_other_body_feature, ["Bad base feature: A body cannot be based on a Part Design feature."], 1, None, "stock"),
    ("body", c_body, [], 1, None, "stock"),
    # r2
    ("link_array", c_link_array, [MULTI_MSG], 1, "Array", "stock"),
    ("link_to_link_array", c_link_to_link_array, [MULTI_MSG], 1, "Link", "stock"),
    ("link>link>link_array", c_link_link_link_array, [MULTI_MSG], 1, "Link001", "stock"),
    ("link_array_of_link", c_link_array_of_link, [MULTI_MSG], 1, "Array", "stock"),
    ("link_array_of_sheet", c_link_array_of_sheet, [], 1, None, "member"),
    ("link_array_of_part", c_link_array_of_part, [], 1, None, "member"),
    ("linkgroup_with_box", c_linkgroup, [], 1, None, "member"),
    ("link_to_linkgroup", c_link_to_linkgroup, [], 1, None, "member"),
    ("sheet+link_array", c_sheet_link_array, [MULTI_MSG], 1, "Array", "member"),
]

only = os.environ.get("BODYSEL_ONLY")


def run_case(name, build, exp_modals, exp_bodies, exp_base, kind):
    d = App.newDocument("C_" + name.replace("+", "_"))
    Gui.activateView("Gui::View3DInventor", True)
    ui()
    sel = build(d)
    d.recompute()
    ui()
    before = set(o.Name for o in d.Objects if o.TypeId == "PartDesign::Body")
    Gui.Selection.clearSelection()
    for o in sel:
        Gui.Selection.addSelection(o)
    selnames = [o.Name for o in Gui.Selection.getSelection()]
    del modals[:]
    Gui.runCommand("PartDesign_Body", 0)
    ui()
    if Gui.Control.activeDialog():
        Gui.Control.closeDialog()
        ui()
    got_modals = list(modals)
    bodies = [o for o in d.Objects if o.TypeId == "PartDesign::Body" and o.Name not in before]
    base = bodies[0].BaseFeature.Name if bodies and bodies[0].BaseFeature else None
    group = [o.Name for o in bodies[0].Group] if bodies else []
    parent = bodies[0].getParentGeoFeatureGroup() if bodies else None
    d.recompute()
    bad = [o.Name for o in d.Objects if "Invalid" in o.State or "Error" in o.State]
    ok = len(bodies) == exp_bodies and len(got_modals) == len(exp_modals) and all(
        g.startswith(e) for g, e in zip(got_modals, exp_modals))
    if exp_base and exp_base.startswith("@"):
        ok = ok and base is None and exp_base[1:] in group
    else:
        ok = ok and base == exp_base
    ok = ok and not bad
    out.append("%s %-22s [%s] sel=%s bodies=%d base=%s group=%s parent=%s invalid=%s modals=%s" % (
        "PASS" if ok else "FAIL", name, kind, selnames, len(bodies), base, group,
        parent.Name if parent else None, bad, got_modals))
    App.closeDocument(d.Name)
    ui()
    return ok


# ---- r2 section D: drop onto an existing empty body through the view provider (the tree calls
# canDropObject/dropObject on a drop). Expected: (canDrop, BaseFeature name, name that must be in Group)
def d_box(d):
    return box(d)


def d_link_box(d):
    return _link(d, box(d))


def d_link_array(d):
    return _array(d, box(d))


def d_link_to_link_array(d):
    return _link(d, _array(d, box(d)))


def d_group(d):
    g = d.addObject("App::DocumentObjectGroup", "Group")
    box(d, parent=g)
    return g


def d_part(d):
    p = d.addObject("App::Part", "Part")
    box(d, parent=p)
    return p


def d_linkgroup(d):
    return c_linkgroup(d)[0]


def d_link_part(d):
    return c_link_part(d)[0]


def d_link_array_of_part(d):
    return c_link_array_of_part(d)[0]


def d_sheet(d):
    return d.addObject("Spreadsheet::Sheet", "Spreadsheet")


def d_empty_feature(d):
    return d.addObject("Part::Feature", "Empty")


def d_varset(d):
    return d.addObject("App::VarSet", "VarSet")


def d_sketch(d):
    return d.addObject("Sketcher::SketchObject", "Sketch")


def d_pd_datum(d):
    return d.addObject("PartDesign::Plane", "DatumPlane")


def d_mesh(d):
    return c_mesh(d)[0]


DROPS = [
    ("box", d_box, (True, "Box", None), "stock"),
    ("link_to_box", d_link_box, (True, "Link", None), "stock"),
    ("link_array", d_link_array, (True, "Array", None), "stock"),
    ("link_to_link_array", d_link_to_link_array, (True, "Link", None), "stock"),
    ("sheet", d_sheet, (False, None, None), "stock"),
    ("empty_part_feature", d_empty_feature, (False, None, None), "stock"),
    ("varset", d_varset, (True, None, "VarSet"), "stock"),
    ("sketch", d_sketch, (True, None, "Sketch"), "stock"),
    ("pd_datum_plane", d_pd_datum, (True, None, "DatumPlane"), "stock"),
    ("mesh", d_mesh, (False, None, None), "stock"),
    ("group_with_box", d_group, (False, None, None), "member"),
    ("part_with_box", d_part, (False, None, None), "member"),
    ("linkgroup_with_box", d_linkgroup, (False, None, None), "member"),
    ("link_to_part", d_link_part, (False, None, None), "member"),
    ("link_array_of_part", d_link_array_of_part, (False, None, None), "member"),
]


def drop_case(name, build, exp, kind):
    d = App.newDocument("D_" + name)
    Gui.activateView("Gui::View3DInventor", True)
    ui()
    obj = build(d)
    body = d.addObject("PartDesign::Body", "Body")
    d.recompute()
    ui()
    vp = body.ViewObject
    del modals[:]
    can = vp.canDropObject(obj)
    if can is True:
        vp.dropObject(obj)
    ui()
    d.recompute()
    bad = [o.Name for o in d.Objects if "Invalid" in o.State or "Error" in o.State]
    base = body.BaseFeature.Name if body.BaseFeature else None
    group = [o.Name for o in body.Group]
    ok = can == exp[0] and base == exp[1] and (exp[2] is None or exp[2] in group) and not bad and not modals
    out.append("%s drop:%-20s [%s] canDrop=%s base=%s group=%s invalid=%s modals=%s" % (
        "PASS" if ok else "FAIL", name, kind, can, base, group, bad, list(modals)))
    App.closeDocument(d.Name)
    ui()
    return ok


def go():
    npass = nfail = 0
    try:
        try:
            Gui.activateWorkbench(os.environ.get("BODYSEL_WB", "PartDesignWorkbench"))
        except Exception as e:
            out.append("workbench: %s" % e)
        import PartDesignGui  # noqa: F401  (registers PartDesign_Body when the workbench is trimmed)
        out.append("workbench active: %s" % Gui.activeWorkbench().name())
        ui()
        for c in CASES:
            if only and c[0] not in only.split(","):
                continue
            try:
                if run_case(*c):
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
        for c in DROPS:
            if only and ("drop:" + c[0]) not in only.split(","):
                continue
            try:
                if drop_case(*c):
                    npass += 1
                else:
                    nfail += 1
            except Exception:
                nfail += 1
                out.append("FAIL drop:%s EXC %s" % (c[0], traceback.format_exc().replace(chr(10), " | ")))
                for n in list(App.listDocuments()):
                    try:
                        App.closeDocument(n)
                    except Exception:
                        pass
    except Exception:
        out.append(traceback.format_exc())
        nfail += 1
    import PartDesignGui
    out.append("module %s" % PartDesignGui.__file__)
    out.append("BODYSEL pass=%d fail=%d" % (npass, nfail))
    QtCore.QTimer.singleShot(300, fin)


def fin():
    open(os.environ["PROBE_OUT"], "w", encoding="utf-8").write("\n".join(out) + "\n")
    os._exit(0)


QtCore.QTimer.singleShot(1000, go)
