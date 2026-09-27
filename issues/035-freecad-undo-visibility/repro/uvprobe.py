# uvprobe.py - lane undo-visibility: every user way to hide/show a body/part/link -> ONE undo step (Ctrl+Z = Std_Undo
# restores, Ctrl+Y = Std_Redo hides again). Runs inside FreeCAD.exe (offscreen GUI). Writes "CASE <id> PASS|FAIL|INVALID
# <details>" lines to $UV_OUT and ends with "PROBE-END pass=.. fail=.. invalid=..". INVALID = the action itself did not
# happen (e.g. the synthetic click missed the eye icon) - never counted as PASS.
# Only Qt events posted to our own widgets (tree viewport / tree); no global input.
import os
import sys
import time
import traceback

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

OUT = os.environ["UV_OUT"]
WORK = os.environ.get("UV_WORK", os.path.dirname(OUT))
ONLY = [c for c in os.environ.get("UV_ONLY", "").split(",") if c]
PREF_OFF = os.environ.get("UV_PREF_OFF") == "1"
stats = {"PASS": 0, "FAIL": 0, "INVALID": 0}


def log(s):
    with open(OUT, "a", encoding="utf-8") as h:
        h.write(s + "\n")


def pump(ms=150):
    t = time.time() + ms / 1000.0
    app = QtWidgets.QApplication.instance()
    while time.time() < t:
        app.processEvents()
        time.sleep(0.01)


def result(case, ok, details, invalid=False):
    v = "INVALID" if invalid else ("PASS" if ok else "FAIL")
    stats[v] += 1
    log("CASE %s %s %s" % (case, v, details))


def vis(o):
    a = bool(o.Visibility)
    v = bool(o.ViewObject.Visibility)
    return a if a == v else ("MISMATCH app=%s vp=%s" % (a, v))


def newdoc(name):
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    doc = App.newDocument(name)
    pump(100)
    return doc


def body(doc, name):
    b = doc.addObject("PartDesign::Body", name)
    x = b.newObject("PartDesign::AdditiveBox", name + "Box")
    return b


def ready(doc):
    doc.recompute()
    pump(300)
    doc.clearUndos()
    Gui.Selection.clearSelection()
    pump(50)


def cmd(name):
    Gui.runCommand(name, 0)
    pump(150)


def undo():
    cmd("Std_Undo")


def redo():
    cmd("Std_Redo")


def select(doc, *objs, sub=""):
    Gui.Selection.clearSelection()
    for o in objs:
        if isinstance(o, tuple):
            Gui.Selection.addSelection(doc.Name, o[0].Name, o[1])
        else:
            Gui.Selection.addSelection(doc.Name, o.Name, sub)
    pump(50)


def states(objs):
    return [vis(o) for o in objs]


def cycle(case, doc, objs, act, before, after):
    """act() -> states == after (else INVALID), one new undo step; Std_Undo -> before; Std_Redo -> after."""
    u0 = doc.UndoCount
    act()
    s1 = states(objs)
    if s1 != after:
        result(case, False, "action did not change visibility: %s (want %s)" % (s1, after), invalid=True)
        return
    u1 = doc.UndoCount
    names = list(doc.UndoNames)[: max(0, u1 - u0)]
    undo()
    s2 = states(objs)
    redo()
    s3 = states(objs)
    ok = (u1 - u0 == 1) and s2 == before and s3 == after
    result(case, ok, "steps=%d names=%s undo->%s redo->%s" % (u1 - u0, names, s2, s3))


def tree_widget():
    mw = Gui.getMainWindow()
    for t in mw.findChildren(QtWidgets.QTreeWidget):
        if t.metaObject().className() == "Gui::TreeWidget" and t.isVisible():
            return t
    for t in mw.findChildren(QtWidgets.QTreeWidget):
        if t.metaObject().className() == "Gui::TreeWidget":
            return t
    return None


def tree_item(tree, label, parent_label=None):
    """-> QModelIndex (no QTreeWidgetItem wrappers: shiboken reuses stale wrappers of FreeCAD's tree items)."""
    m = tree.model()
    start = m.index(0, 0)
    hits = m.match(start, QtCore.Qt.DisplayRole, label, -1, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
    for ix in hits:
        par = ix.parent()
        if parent_label is None or (par.isValid() and par.data(QtCore.Qt.DisplayRole) == parent_label):
            return ix
    return None


def expand_all(tree):
    tree.expandAll()
    pump(200)


def click_eye(tree, label, parent_label=None):
    expand_all(tree)
    ix = tree_item(tree, label, parent_label)
    if ix is None:
        log("  eye: no item %s" % label)
        return
    tree.scrollTo(ix)
    pump(50)
    r = tree.visualRect(ix)
    style = tree.style()
    margin = style.pixelMetric(QtWidgets.QStyle.PM_FocusFrameHMargin) + 1
    pos = QtCore.QPoint(r.left() + margin + 5, r.center().y())
    vp = tree.viewport()
    gpos = vp.mapToGlobal(pos)
    for typ in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonRelease):
        ev = QtGui.QMouseEvent(typ, QtCore.QPointF(pos), QtCore.QPointF(gpos), QtCore.Qt.LeftButton,
                               QtCore.Qt.LeftButton if typ == QtCore.QEvent.MouseButtonPress else QtCore.Qt.NoButton,
                               QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(vp, ev)
        pump(30)
    pump(400)   # the eye's double-click timer


def space_in_tree(tree, labels):
    expand_all(tree)
    idx = [tree_item(tree, l) for l in labels]
    sm = tree.selectionModel()
    sm.clearSelection()
    for ix in idx:
        if ix is not None:
            sm.select(ix, QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
    pump(100)
    tree.setFocus()
    for typ in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
        ev = QtGui.QKeyEvent(typ, QtCore.Qt.Key_Space, QtCore.Qt.NoModifier, " ")
        QtWidgets.QApplication.sendEvent(tree, ev)
    pump(150)


def want(c):
    return not ONLY or c in ONLY


def run():
    log("PROBE-START gui=%s pref_off=%s" % (Gui.__file__ if hasattr(Gui, "__file__") else "?", PREF_OFF))
    try:
        import hybriddesign
        log("HD %s" % hybriddesign.__file__)
    except Exception as e:
        log("HD not importable: %s" % e)
    pv = App.ParamGet("User parameter:BaseApp/Preferences/PropertyView")
    log("AutoTransactionView=%s UndoVisibility=%s" % (
        pv.GetBool("AutoTransactionView", False),
        App.ParamGet("User parameter:BaseApp/Preferences/View").GetBool("UndoVisibility", True)))
    if os.environ.get("UV_ATV") == "1":
        pv.SetBool("AutoTransactionView", True)
        log("set AutoTransactionView=True")
    if PREF_OFF:
        App.ParamGet("User parameter:BaseApp/Preferences/View").SetBool("UndoVisibility", False)
    T, F = True, False

    # C1-C3 command paths, single object
    for cid, command, before in (("C1-toggle", "Std_ToggleVisibility", T), ("C2-hidesel", "Std_HideSelection", T),
                                 ("C3-showsel", "Std_ShowSelection", F)):
        if not want(cid):
            continue
        doc = newdoc("uv")
        b = body(doc, "Body")
        ready(doc)
        if not before:
            b.ViewObject.Visibility = False
            pump(50)
            doc.clearUndos()
        select(doc, b)
        cycle(cid, doc, [b], lambda: cmd(command), [before], [not before])

    # C4-C5 multi-selection: ONE undo for the action
    for cid, command in (("C4-toggle-multi", "Std_ToggleVisibility"), ("C5-hidesel-multi", "Std_HideSelection")):
        if not want(cid):
            continue
        doc = newdoc("uv")
        b1, b2, b3 = body(doc, "B1"), body(doc, "B2"), body(doc, "B3")
        ready(doc)
        select(doc, b1, b2, b3)
        cycle(cid, doc, [b1, b2, b3], lambda: cmd(command), [T, T, T], [F, F, F])

    # C6 all-objects commands
    for cid, command, pre in (("C6a-hideall", "Std_HideObjects", T), ("C6b-showall", "Std_ShowObjects", F),
                              ("C6c-toggleall", "Std_ToggleObjects", T)):
        if not want(cid):
            continue
        doc = newdoc("uv")
        b1, b2 = body(doc, "B1"), body(doc, "B2")
        ready(doc)
        objs = [o for o in doc.Objects if o.TypeId in ("PartDesign::Body",)]
        if not pre:
            for o in doc.Objects:
                o.ViewObject.Visibility = False
            pump(50)
            doc.clearUndos()
        before = states(objs)
        cycle(cid, doc, objs, lambda: cmd(command), before, [not x for x in before])

    tree = tree_widget()
    log("TREE %s visible=%s" % (tree is not None, tree.isVisible() if tree else None))

    # C7 tree eye icon (a body at top level; a body inside an App::Part = the ElementVisible path)
    if want("C7a-eye") and tree:
        doc = newdoc("uv")
        b = body(doc, "BodyEye")
        ready(doc)
        expand_all(tree)
        it = tree_item(tree, "BodyEye")
        if it is None:
            result("C7a-eye", False, "tree item not found", invalid=True)
        else:
            cycle("C7a-eye", doc, [b], lambda: click_eye(tree, "BodyEye"), [T], [F])
    if want("C7b-eye-in-part") and tree:
        doc = newdoc("uv")
        p = doc.addObject("App::Part", "Asm")
        b = body(doc, "BodyInPart")
        p.addObject(b)
        ready(doc)
        expand_all(tree)
        it = tree_item(tree, "BodyInPart", "Asm")
        if it is None:
            result("C7b-eye-in-part", False, "tree item not found", invalid=True)
        else:
            cycle("C7b-eye-in-part", doc, [b], lambda: click_eye(tree, "BodyInPart", "Asm"), [T], [F])

    # C8 Space in the tree (TreeWidget::keyPressEvent toggles directly, no command) - single and multi
    if want("C8a-tree-space") and tree:
        doc = newdoc("uv")
        b = body(doc, "BodySp")
        ready(doc)
        expand_all(tree)
        it = tree_item(tree, "BodySp")
        cycle("C8a-tree-space", doc, [b], lambda: space_in_tree(tree, ["BodySp"]), [T], [F])
    if want("C8b-tree-space-multi") and tree:
        doc = newdoc("uv")
        b1, b2 = body(doc, "SpA"), body(doc, "SpB")
        ready(doc)
        expand_all(tree)
        its = [tree_item(tree, "SpA"), tree_item(tree, "SpB")]
        cycle("C8b-tree-space-multi", doc, [b1, b2], lambda: space_in_tree(tree, ["SpA", "SpB"]), [T, T], [F, F])

    # C9 mixed with a modeling step: Pad (hides its sketch in the SAME transaction) -> hide body -> undo -> undo
    if want("C9-modeling"):
        doc = newdoc("uv")
        b = doc.addObject("PartDesign::Body", "Body")
        import Part
        sk = b.newObject("Sketcher::SketchObject", "Sketch")
        sk.AttachmentSupport = [(doc.getObject("XY_Plane") or b.Origin.OriginFeatures[3], "")]
        sk.MapMode = "FlatFace"
        pts = [App.Vector(0, 0, 0), App.Vector(10, 0, 0), App.Vector(10, 10, 0), App.Vector(0, 10, 0)]
        for i in range(4):
            sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]))
        ready(doc)
        doc.openTransaction("Pad")
        pad = b.newObject("PartDesign::Pad", "Pad")
        pad.Profile = sk
        pad.Length = 5
        sk.ViewObject.Visibility = False
        doc.recompute()
        doc.commitTransaction()
        pump(200)
        s0 = (vis(b), vis(sk), doc.getObject("Pad") is not None)
        select(doc, b)
        cmd("Std_ToggleVisibility")
        s1 = (vis(b), vis(sk), doc.getObject("Pad") is not None)
        n1 = list(doc.UndoNames)
        undo()
        s2 = (vis(b), vis(sk), doc.getObject("Pad") is not None)
        undo()
        s3 = (vis(b), vis(sk), doc.getObject("Pad") is not None)
        redo()
        s4 = (vis(b), vis(sk), doc.getObject("Pad") is not None)
        redo()
        s5 = (vis(b), vis(sk), doc.getObject("Pad") is not None)
        ok = (s0 == (T, F, T) and s1 == (F, F, T) and s2 == (T, F, T) and s3 == (T, T, False)
              and s4 == (T, F, T) and s5 == (F, F, T) and len(n1) == 2)
        result("C9-modeling", ok, "pad=%s hide=%s undoNames=%s undo1=%s undo2=%s redo1=%s redo2=%s"
               % (s0, s1, n1, s2, s3, s4, s5))

    # C10 App::Link of a body inside an App::Part, selected through the part (sub-element path of Std_ToggleVisibility)
    if want("C10-link"):
        doc = newdoc("uv")
        b = body(doc, "Src")
        p = doc.addObject("App::Part", "Asm")
        lk = doc.addObject("App::Link", "Lnk")
        lk.LinkedObject = b
        p.addObject(lk)
        ready(doc)
        select(doc, (p, "Lnk."))
        cycle("C10-link", doc, [lk], lambda: cmd("Std_ToggleVisibility"), [T], [F])
    if want("C10b-link-hidesel"):
        doc = newdoc("uv")
        b = body(doc, "Src")
        p = doc.addObject("App::Part", "Asm")
        lk = doc.addObject("App::Link", "Lnk")
        lk.LinkedObject = b
        p.addObject(lk)
        ready(doc)
        select(doc, (p, "Lnk."))
        cycle("C10b-link-hidesel", doc, [lk], lambda: cmd("Std_HideSelection"), [T], [F])

    # C11 saved/reopened document: hidden state saved as before; the undo of a hide saved as visible; modified flag
    if want("C11-save"):
        path1 = os.path.join(WORK, "uv_hidden.FCStd")
        path2 = os.path.join(WORK, "uv_undone.FCStd")
        doc = newdoc("uv")
        b1, b2 = body(doc, "K1"), body(doc, "K2")
        ready(doc)
        gd = Gui.getDocument(doc.Name)
        doc.saveAs(os.path.join(WORK, "uv_first.FCStd"))
        modA = gd.Modified
        pump(300)
        gd.Modified = False
        mod0 = gd.Modified
        log("  C11 modified right after save=%s, forced clean=%s" % (modA, mod0))
        select(doc, b1)
        cmd("Std_HideSelection")
        mod1 = gd.Modified
        doc.saveAs(path1)
        select(doc, b2)
        cmd("Std_HideSelection")
        undo()
        doc.saveAs(path2)
        App.closeDocument(doc.Name)
        pump(100)
        d1 = App.openDocument(path1)
        pump(300)
        r1 = (vis(d1.getObject("K1")), vis(d1.getObject("K2")), d1.UndoCount)
        App.closeDocument(d1.Name)
        d2 = App.openDocument(path2)
        pump(300)
        r2 = (vis(d2.getObject("K1")), vis(d2.getObject("K2")), d2.UndoCount)
        App.closeDocument(d2.Name)
        ok = r1 == (F, T, 0) and r2 == (F, T, 0)
        result("C11-save", ok, "modified before/after hide=%s/%s reopen1=%s reopen2=%s" % (mod0, mod1, r1, r2))

    # C12 a no-op (hide an already hidden body) adds no undo step
    if want("C12-noop"):
        doc = newdoc("uv")
        b = body(doc, "Body")
        ready(doc)
        b.ViewObject.Visibility = False
        pump(50)
        doc.clearUndos()
        select(doc, b)
        cmd("Std_HideSelection")
        result("C12-noop", doc.UndoCount == 0 and vis(b) is False, "undoCount=%d vis=%s" % (doc.UndoCount, vis(b)))
    if want("C12b-noop-others"):
        doc = newdoc("uv")
        b = body(doc, "Body")
        ready(doc)
        select(doc, b)
        cmd("Std_ShowSelection")          # already shown
        n1 = doc.UndoCount
        Gui.Selection.clearSelection()
        for o in doc.Objects:
            o.ViewObject.Visibility = False
        pump(50)
        doc.clearUndos()
        cmd("Std_HideObjects")            # all hidden already
        n2 = doc.UndoCount
        result("C12b-noop-others", n1 == 0 and n2 == 0, "showsel-on-shown=%d hideall-on-hidden=%d" % (n1, n2))

    # C13 inside a tool's open transaction: the hide joins it, the tool's transaction is neither committed nor split
    if want("C13-in-tool"):
        doc = newdoc("uv")
        b1, b2 = body(doc, "T1"), body(doc, "T2")
        ready(doc)
        doc.openTransaction("Tool")
        b2.Placement = App.Placement(App.Vector(5, 0, 0), App.Rotation())
        select(doc, b1)
        cmd("Std_ToggleVisibility")
        pending = doc.HasPendingTransaction
        doc.commitTransaction()
        names = list(doc.UndoNames)
        undo()
        r = (vis(b1), b2.Placement.Base.x)
        ok = pending and names == ["Tool"] and r == (T, 0.0)
        result("C13-in-tool", ok, "pending_after_hide=%s undoNames=%s after_undo=%s" % (pending, names, r))

    log("PROBE-END pass=%d fail=%d invalid=%d" % (stats["PASS"], stats["FAIL"], stats["INVALID"]))


def main():
    try:
        run()
    except Exception:
        log("PROBE-EXC " + traceback.format_exc().replace("\n", " | "))
    finally:
        for d in list(App.listDocuments().values()):
            try:
                App.closeDocument(d.Name)
            except Exception:
                pass
        log("PROBE-EXIT")
        os._exit(0)


QtCore.QTimer.singleShot(int(os.environ.get("UV_DELAY_MS", "3000")), main)
