# pvprobe.py - lane undo-visibility-pe: a user edit of Visibility / Show In Tree in the PROPERTY EDITOR (View tab
# checkbox) and the tree's "Toggle Visibility in Tree View" -> ONE undo step (Std_Undo restores, Std_Redo repeats);
# other view properties keep stock behaviour. Runs inside FreeCAD.exe (offscreen GUI).
# Writes "CASE <id> PASS|FAIL|INVALID|INFO <details>" to $UV_OUT, ends with "PROBE-END pass=.. fail=.. invalid=..".
# INVALID = the action itself did not happen (never counted as PASS).
# User path: selection as a tree click makes it (Gui.Selection), the property editor's own row clicked with Qt mouse
# events posted to its viewport, its own checkbox editor clicked with Qt mouse events posted to the checkbox.
# No global input.
import os
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
ONLY = [c for c in os.environ.get("UV_ONLY", "").split(",") if c]
PREF_OFF = os.environ.get("UV_PREF_OFF") == "1"
stats = {"PASS": 0, "FAIL": 0, "INVALID": 0, "INFO": 0}
T, F = True, False


def log(s):
    with open(OUT, "a", encoding="utf-8") as h:
        h.write(s + "\n")


def pump(ms=150):
    t = time.time() + ms / 1000.0
    app = QtWidgets.QApplication.instance()
    while time.time() < t:
        app.processEvents()
        time.sleep(0.01)


def result(case, ok, details, invalid=False, info=False):
    v = "INFO" if info else ("INVALID" if invalid else ("PASS" if ok else "FAIL"))
    stats[v] += 1
    log("CASE %s %s %s" % (case, v, details))


def want(c):
    return not ONLY or c in ONLY


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
    b.newObject("PartDesign::AdditiveBox", name + "Box")
    return b


def ready(doc):
    doc.recompute()
    pump(300)
    doc.clearUndos()
    Gui.Selection.clearSelection()
    pump(50)


def cmd(name):
    Gui.runCommand(name, 0)
    pump(200)


def select(doc, *objs):
    Gui.Selection.clearSelection()
    for o in objs:
        Gui.Selection.addSelection(doc.Name, o.Name)
    pump(500)   # PropertyView rebuilds on a timer


def mouse(widget, pos, double=False):
    gpos = widget.mapToGlobal(pos)
    for typ in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonRelease):
        ev = QtGui.QMouseEvent(typ, QtCore.QPointF(pos), QtCore.QPointF(gpos), QtCore.Qt.LeftButton,
                               QtCore.Qt.LeftButton if typ == QtCore.QEvent.MouseButtonPress else QtCore.Qt.NoButton,
                               QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(widget, ev)
        pump(30)


def prop_editor(tab="View"):
    """-> (tabwidget, editor) of the visible property view; the tab named `tab` made current like a click on it."""
    mw = Gui.getMainWindow()
    name = "propertyEditorView" if tab == "View" else "propertyEditorData"
    cands = [w for w in mw.findChildren(QtWidgets.QTreeView) if w.objectName() == name]
    cands.sort(key=lambda w: not w.isVisible())
    if not cands:
        return None, None
    ed = cands[0]
    tabs = ed.parent()
    while tabs is not None and not isinstance(tabs, QtWidgets.QTabWidget):
        tabs = tabs.parent()
    if tabs is not None:
        tabs.setCurrentWidget(ed)
        pump(100)
    return tabs, ed


def find_row(ed, label):
    m = ed.model()
    hits = m.match(m.index(0, 0), QtCore.Qt.DisplayRole, label, -1, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
    return hits[0] if hits else None


def click_checkbox(case, label, tab="View"):
    """Open the editor of row `label` by clicking its value cell, then click the checkbox editor. -> note str"""
    tabs, ed = prop_editor(tab)
    if ed is None:
        return "no property editor"
    ed.expandAll()
    pump(100)
    ix = find_row(ed, label)
    if ix is None:
        return "no row %s" % label
    ix1 = ix.sibling(ix.row(), 1)
    ed.scrollTo(ix1)
    pump(50)
    r = ed.visualRect(ix1)
    mouse(ed.viewport(), r.center())
    pump(150)
    w = ed.indexWidget(ix1)
    boxes = []
    if w is not None:
        boxes = [w] if isinstance(w, QtWidgets.QCheckBox) else w.findChildren(QtWidgets.QCheckBox)
    if not boxes:
        # a click on a checkbox cell toggles it at once (delegate: editor opens, FocusIn toggles, editor closes)
        return "cell-click"
    cb = boxes[0]
    before = cb.isChecked()
    opt = QtWidgets.QStyleOptionButton()
    opt.initFrom(cb)
    ind = cb.style().subElementRect(QtWidgets.QStyle.SE_CheckBoxIndicator, opt, cb)
    mouse(cb, ind.center() if ind.isValid() and not ind.isEmpty() else QtCore.QPoint(8, cb.height() // 2))
    pump(300)
    note = "mouse"
    if cb.isChecked() == before and not _deleted(cb):
        cb.click()
        pump(300)
        note = "click()"
    return "ok:" + note


def _deleted(w):
    try:
        w.isChecked()
        return False
    except RuntimeError:
        return True


def cycle(case, doc, objs, act, before, after, getter=None):
    getter = getter or vis
    u0 = doc.UndoCount
    note = act()
    s1 = [getter(o) for o in objs]
    if s1 != after:
        result(case, False, "action did not change state: %s (want %s) note=%s" % (s1, after, note), invalid=True)
        return None
    u1 = doc.UndoCount
    names = list(doc.UndoNames)[: max(0, u1 - u0)]
    cmd("Std_Undo")
    s2 = [getter(o) for o in objs]
    cmd("Std_Redo")
    s3 = [getter(o) for o in objs]
    ok = (u1 - u0 == 1) and s2 == before and s3 == after
    result(case, ok, "steps=%d names=%s undo->%s redo->%s note=%s" % (u1 - u0, names, s2, s3, note))
    return names


def tree_widget():
    mw = Gui.getMainWindow()
    ts = [t for t in mw.findChildren(QtWidgets.QTreeWidget) if t.metaObject().className() == "Gui::TreeWidget"]
    ts.sort(key=lambda t: not t.isVisible())
    return ts[0] if ts else None


def tree_hidden(tree, label):
    """True if the tree row `label` is hidden (ShowInTree off), False if shown, None if absent."""
    pump(700)   # the tree applies ShowInTree on its status timer
    tree.expandAll()
    pump(100)
    m = tree.model()
    hits = m.match(m.index(0, 0), QtCore.Qt.DisplayRole, label, -1, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
    if not hits:
        return None
    ix = hits[0]
    return tree.isRowHidden(ix.row(), ix.parent())


def run():
    pv = App.ParamGet("User parameter:BaseApp/Preferences/PropertyView")
    vw = App.ParamGet("User parameter:BaseApp/Preferences/View")
    if PREF_OFF:
        vw.SetBool("UndoVisibility", False)
    log("PROBE-START pref_off=%s AutoTransactionView=%s AutoTransactionData=%s UndoVisibility=%s" % (
        PREF_OFF, pv.GetBool("AutoTransactionView", False), pv.GetBool("AutoTransactionData", True),
        vw.GetBool("UndoVisibility", True)))
    try:
        import hybriddesign
        log("HD %s" % hybriddesign.__file__)
    except Exception as e:
        log("HD not importable: %s" % e)

    # P1 hide one body with the View tab's Visibility checkbox
    if want("P1-hide"):
        doc = newdoc("pv")
        b = body(doc, "Body")
        ready(doc)
        select(doc, b)
        cycle("P1-hide", doc, [b], lambda: click_checkbox("P1", "Visibility"), [T], [F])

    # P2 show a hidden body
    if want("P2-show"):
        doc = newdoc("pv")
        b = body(doc, "Body")
        ready(doc)
        b.ViewObject.Visibility = False
        pump(50)
        doc.clearUndos()
        select(doc, b)
        cycle("P2-show", doc, [b], lambda: click_checkbox("P2", "Visibility"), [F], [T])

    # P3 multi-selection: three bodies in the editor, one click = ONE step
    if want("P3-multi"):
        doc = newdoc("pv")
        bs = [body(doc, n) for n in ("B1", "B2", "B3")]
        ready(doc)
        select(doc, *bs)
        cycle("P3-multi", doc, bs, lambda: click_checkbox("P3", "Visibility"), [T, T, T], [F, F, F])

    # P4 mixed multi-selection (B1 shown, B2 already hidden): one step; undo leaves B2 hidden
    if want("P4-mixed"):
        doc = newdoc("pv")
        b1, b2 = body(doc, "M1"), body(doc, "M2")
        ready(doc)
        b2.ViewObject.Visibility = False
        pump(50)
        doc.clearUndos()
        select(doc, b1, b2)
        cycle("P4-mixed", doc, [b1, b2], lambda: click_checkbox("P4", "Visibility"), [T, F], [F, F])

    # P5 a link and an App::Part (other view-provider classes)
    if want("P5-link-part"):
        doc = newdoc("pv")
        b = body(doc, "Src")
        p = doc.addObject("App::Part", "Asm")
        lk = doc.addObject("App::Link", "Lnk")
        lk.LinkedObject = b
        p.addObject(lk)
        ready(doc)
        select(doc, lk, p)
        cycle("P5-link-part", doc, [lk, p], lambda: click_checkbox("P5", "Visibility"), [T, T], [F, F])

    tree = tree_widget()
    log("TREE %s" % (tree is not None))

    # P6 Show In Tree checkbox in the property editor: hides the row in the tree; one step
    if want("P6-showintree") and tree:
        doc = newdoc("pv")
        b = body(doc, "TreeBody")
        ready(doc)
        select(doc, b)
        rows = []
        def st(o):
            rows.append(tree_hidden(tree, o.Label))   # the tree row's reaction is stock; logged, not asserted
            return bool(o.ViewObject.ShowInTree)
        cycle("P6-showintree", doc, [b], lambda: click_checkbox("P6", "Show In Tree"), [T], [F], getter=st)
        log("  P6 tree row hidden after act/undo/redo: %s" % rows)

    # P7 tree context "Toggle Visibility in Tree View" on two objects: one step
    if want("P7-tree-toggle-intree") and tree:
        doc = newdoc("pv")
        b1, b2 = body(doc, "TA"), body(doc, "TB")
        ready(doc)
        select(doc, b1, b2)
        acts = [a for a in tree.actions() + tree.findChildren(QtGui.QAction if hasattr(QtGui, "QAction") else QtWidgets.QAction)
                if a.text() == "Toggle Visibility in Tree View"]
        if not acts:
            result("P7-tree-toggle-intree", False, "action not found", invalid=True)
        else:
            def act():
                tree.expandAll()
                pump(50)
                acts[0].trigger()
                pump(200)
                return "trigger"
            st = lambda o: (bool(o.ViewObject.ShowInTree), tree_hidden(tree, o.Label))
            cycle("P7-tree-toggle-intree", doc, [b1, b2], act, [(T, F), (T, F)], [(F, T), (F, T)], getter=st)

    # P8 another view property keeps stock behaviour: Selectable (a checkbox too) and Transparency
    if want("P8-other-viewprop"):
        doc = newdoc("pv")
        b = body(doc, "Body")
        ready(doc)
        select(doc, b)
        s0 = bool(b.ViewObject.Selectable)
        note = click_checkbox("P8", "Selectable")
        s1 = bool(b.ViewObject.Selectable)
        n = doc.UndoCount
        names = list(doc.UndoNames)
        if s1 == s0:
            result("P8-other-viewprop", False, "Selectable did not change note=%s" % note, invalid=True)
        else:
            # stock (AutoTransactionView false): no step; with AutoTransactionView true: the editor's own step
            atv = pv.GetBool("AutoTransactionView", False)
            ok = (n == 0) if not atv else (n == 1)
            result("P8-other-viewprop", ok, "Selectable %s->%s steps=%d names=%s atv=%s" % (s0, s1, n, names, atv))

    # P9 inside an open transaction (a tool/task): the hide joins it, no own step, the transaction stays open
    if want("P9-in-transaction"):
        doc = newdoc("pv")
        b1, b2 = body(doc, "T1"), body(doc, "T2")
        ready(doc)
        doc.openTransaction("Tool")
        b2.Placement = App.Placement(App.Vector(5, 0, 0), App.Rotation())
        select(doc, b1)
        note = click_checkbox("P9", "Visibility")
        hid = vis(b1)
        pending = doc.HasPendingTransaction
        doc.commitTransaction()
        names = list(doc.UndoNames)
        cmd("Std_Undo")
        r = (vis(b1), b2.Placement.Base.x)
        ok = hid is F and pending and names == ["Tool"] and r == (T, 0.0)
        result("P9-in-transaction", ok, "hidden=%s pending_after=%s names=%s after_undo=%s note=%s"
               % (hid, pending, names, r, note))

    # P10 inside a real task dialog (PartDesign Pad): the hide joins the dialog's step
    if want("P10-in-task"):
        import Part
        doc = newdoc("pv")
        bd = doc.addObject("PartDesign::Body", "Body")
        other = body(doc, "Other")
        sk = bd.newObject("Sketcher::SketchObject", "Sketch")
        sk.AttachmentSupport = [(bd.Origin.OriginFeatures[3], "")]
        sk.MapMode = "FlatFace"
        pts = [App.Vector(0, 0, 0), App.Vector(10, 0, 0), App.Vector(10, 10, 0), App.Vector(0, 10, 0)]
        for i in range(4):
            sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]))
        ready(doc)
        try:
            Gui.getDocument(doc.Name).ActiveView.setActiveObject("pdbody", bd)
        except Exception:
            pass
        select(doc, sk)
        cmd("PartDesign_Pad")
        pump(800)
        dlg = Gui.Control.activeDialog()
        pend0 = doc.HasPendingTransaction
        if not dlg:
            result("P10-in-task", False, "Pad dialog did not open", invalid=True)
        else:
            select(doc, other)
            u_pre = doc.UndoCount
            note = click_checkbox("P10", "Visibility")
            hid = vis(other)
            u_in = doc.UndoCount - u_pre
            pend1 = doc.HasPendingTransaction
            # accept the dialog with its own OK button
            ok_btn = None
            for bb in Gui.getMainWindow().findChildren(QtWidgets.QDialogButtonBox):
                b_ = bb.button(QtWidgets.QDialogButtonBox.Ok)
                if b_ is not None and b_.isVisible():
                    ok_btn = b_
            if ok_btn is None:
                for bb in Gui.getMainWindow().findChildren(QtWidgets.QDialogButtonBox):
                    b_ = bb.button(QtWidgets.QDialogButtonBox.Ok)
                    if b_ is not None:
                        ok_btn = b_
            if ok_btn is not None:
                ok_btn.click()
            else:
                Gui.Control.closeDialog()
            pump(800)
            names = list(doc.UndoNames)
            ok = (hid is F and pend0 and pend1 and u_in == 0 and len(names) >= 1
                  and "Edit property Visibility" not in names)
            result("P10-in-task", ok, "pending before/after hide=%s/%s new_steps_in_task=%d hidden=%s names=%s note=%s"
                   % (pend0, pend1, u_in, hid, names, note))

    # P11 hide then modeling then undo x2: chronological steps
    if want("P11-order"):
        doc = newdoc("pv")
        b1, b2 = body(doc, "O1"), body(doc, "O2")
        ready(doc)
        select(doc, b1)
        click_checkbox("P11", "Visibility")
        doc.openTransaction("Move")
        b2.Placement = App.Placement(App.Vector(3, 0, 0), App.Rotation())
        doc.commitTransaction()
        names = list(doc.UndoNames)
        cmd("Std_Undo")
        a = (vis(b1), b2.Placement.Base.x)
        cmd("Std_Undo")
        c = (vis(b1), b2.Placement.Base.x)
        ok = len(names) == 2 and names[0] == "Move" and a == (F, 0.0) and c == (T, 0.0)
        result("P11-order", ok, "names=%s undo1=%s undo2=%s" % (names, a, c))

    log("PROBE-END pass=%d fail=%d invalid=%d info=%d" % (stats["PASS"], stats["FAIL"], stats["INVALID"], stats["INFO"]))


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
