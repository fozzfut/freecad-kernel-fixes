# rvprobe.py - independent REVIEW of lane undo-visibility-pe: class members beyond pvprobe.py P1-P11 (helpers copied
# from pvprobe.py). Context menus are driven with key events posted to the menu widget.
# Runs inside FreeCAD.exe (offscreen GUI).
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


def undo_names(doc):
    return list(doc.UndoNames)


def show_hidden_via_menu(tab="Data"):
    """Toggle the property editor's 'Show Hidden' like a user: context menu on a row, the action chosen with
    key events posted to the menu. -> dict with the action's previous state or an error."""
    tabs, ed = prop_editor(tab)
    if ed is None:
        return {"err": "no editor"}
    m = ed.model()
    ix = m.index(0, 0)
    r = ed.visualRect(ix)
    state = {}

    def pick():
        menu = QtWidgets.QApplication.activePopupWidget()
        if menu is None:
            state["err"] = "no popup"
            return
        acts = [a for a in menu.actions() if a.text().replace("&", "") == "Show Hidden"]
        if not acts:
            state["err"] = "no action in %s" % [a.text() for a in menu.actions()]
            menu.close()
            return
        state["was"] = acts[0].isChecked()
        menu.setActiveAction(acts[0])
        for typ in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
            QtWidgets.QApplication.sendEvent(menu, QtGui.QKeyEvent(typ, QtCore.Qt.Key_Return, QtCore.Qt.NoModifier))
    QtCore.QTimer.singleShot(400, pick)
    pos = r.center() if r.isValid() else QtCore.QPoint(10, 10)
    ev = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, pos, ed.viewport().mapToGlobal(pos))
    QtWidgets.QApplication.sendEvent(ed.viewport(), ev)
    pump(800)
    return state


def pad_body(doc, name):
    """Body with a closed sketch (for a Pad)."""
    import Part
    bd = doc.addObject("PartDesign::Body", name)
    sk = bd.newObject("Sketcher::SketchObject", name + "Sk")
    sk.AttachmentSupport = [(bd.Origin.OriginFeatures[3], "")]
    sk.MapMode = "FlatFace"
    pts = [App.Vector(0, 0, 0), App.Vector(10, 0, 0), App.Vector(10, 10, 0), App.Vector(0, 10, 0)]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]))
    return bd, sk


def tree_action(tree, text):
    kls = QtGui.QAction if hasattr(QtGui, "QAction") else QtWidgets.QAction
    return [a for a in tree.actions() + tree.findChildren(kls) if a.text() == text]


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

    # R1 PartDesign features: showing the hidden non-tip feature in the View tab makes PartDesign hide the tip
    #    feature -> ONE step must restore BOTH; redo repeats both.
    if want("R1-pd-exclusive"):
        doc = newdoc("rv")
        b = doc.addObject("PartDesign::Body", "Body")
        f1 = b.newObject("PartDesign::AdditiveBox", "Box")
        f2 = b.newObject("PartDesign::AdditiveCylinder", "Cyl")
        ready(doc)
        st0 = [vis(f1), vis(f2)]
        select(doc, f1)
        u0 = doc.UndoCount
        note = click_checkbox("R1", "Visibility")
        st1 = [vis(f1), vis(f2)]
        n = doc.UndoCount - u0
        names = undo_names(doc)[:n]
        cmd("Std_Undo")
        st2 = [vis(f1), vis(f2)]
        cmd("Std_Redo")
        st3 = [vis(f1), vis(f2)]
        ok = st1 != st0 and n == 1 and st2 == st0 and st3 == st1
        result("R1-pd-exclusive", ok, "before=%s after=%s steps=%d names=%s undo->%s redo->%s note=%s"
               % (st0, st1, n, names, st2, st3, note), invalid=(st1 == st0))

    # R2 two edits in a row (hide, then show again) = two steps, undone one by one
    if want("R2-two-edits"):
        doc = newdoc("rv")
        b = body(doc, "Body")
        ready(doc)
        select(doc, b)
        click_checkbox("R2a", "Visibility")
        a = vis(b)
        select(doc, b)
        click_checkbox("R2b", "Visibility")
        c = vis(b)
        names = undo_names(doc)
        cmd("Std_Undo")
        u1 = vis(b)
        cmd("Std_Undo")
        u2 = vis(b)
        ok = (a, c) == (F, T) and len(names) == 2 and (u1, u2) == (F, T)
        result("R2-two-edits", ok, "states=%s names=%s undo1=%s undo2=%s" % ((a, c), names, u1, u2),
               invalid=((a, c) != (F, T)))

    # R3 the owner's scenario via the property editor: Pad (own transaction), hide the body in the View tab,
    #    Ctrl+Z -> body visible AND the Pad still there; second Ctrl+Z removes the Pad
    if want("R3-owner-pad"):
        doc = newdoc("rv")
        bd, sk = pad_body(doc, "Body")
        ready(doc)
        doc.openTransaction("Make Pad")
        pad = bd.newObject("PartDesign::Pad", "Pad")
        pad.Profile = sk
        pad.Length = 5
        doc.recompute()
        doc.commitTransaction()
        pump(200)
        select(doc, bd)
        note = click_checkbox("R3", "Visibility")
        hid = vis(bd)
        names = undo_names(doc)
        cmd("Std_Undo")
        a = (vis(bd), doc.getObject("Pad") is not None)
        cmd("Std_Undo")
        c = (vis(bd), doc.getObject("Pad") is not None)
        ok = hid is F and a == (T, T) and c[1] is False
        result("R3-owner-pad", ok, "hidden=%s names=%s undo1(vis,pad)=%s undo2=%s note=%s" % (hid, names, a, c, note),
               invalid=(hid is not F))

    # R4 App::Part with children: hiding the Part is one step; children keep their own Visibility
    if want("R4-part-children"):
        doc = newdoc("rv")
        p = doc.addObject("App::Part", "Part")
        c1 = body(doc, "C1")
        c2 = body(doc, "C2")
        p.addObject(c1)
        p.addObject(c2)
        ready(doc)
        select(doc, p)
        g = lambda o: (vis(o), vis(c1), vis(c2))
        cycle("R4-part-children", doc, [p], lambda: click_checkbox("R4", "Visibility"), [(T, T, T)], [(F, T, T)],
              getter=g)

    # R5 Show In Tree on a multi-selection (two bodies) = one step
    if want("R5-showintree-multi"):
        doc = newdoc("rv")
        b1, b2 = body(doc, "S1"), body(doc, "S2")
        ready(doc)
        select(doc, b1, b2)
        g = lambda o: bool(o.ViewObject.ShowInTree)
        cycle("R5-showintree-multi", doc, [b1, b2], lambda: click_checkbox("R5", "Show In Tree"), [T, T], [F, F],
              getter=g)

    tree = tree_widget()

    # R6 tree 'Toggle Visibility in Tree View' inside an open transaction: joins it, no own step
    if want("R6-tree-toggle-in-tx") and tree:
        doc = newdoc("rv")
        b1, b2 = body(doc, "X1"), body(doc, "X2")
        ready(doc)
        select(doc, b1)
        tree.expandAll()
        pump(50)
        acts = tree_action(tree, "Toggle Visibility in Tree View")
        doc.openTransaction("Tool")
        b2.Placement = App.Placement(App.Vector(5, 0, 0), App.Rotation())
        acts[0].trigger()
        pump(200)
        s = bool(b1.ViewObject.ShowInTree)
        pend = doc.HasPendingTransaction
        doc.commitTransaction()
        names = undo_names(doc)
        cmd("Std_Undo")
        r = (bool(b1.ViewObject.ShowInTree), b2.Placement.Base.x)
        ok = s is F and pend and names == ["Tool"] and r == (T, 0.0)
        result("R6-tree-toggle-in-tx", ok, "sit=%s pending=%s names=%s after_undo=%s" % (s, pend, names, r),
               invalid=(s is not F))

    # R7 Data tab, a non-visibility bool (Body 'Allow Compound'): the editor's stock handling (identity line)
    if want("R7-data-bool-identity"):
        doc = newdoc("rv")
        b = body(doc, "Body")
        ready(doc)
        select(doc, b)
        a0 = bool(b.AllowCompound)
        note = click_checkbox("R7", "Allow Compound", tab="Data")
        pump(300)
        a1 = bool(b.AllowCompound)
        names = undo_names(doc)
        cmd("Std_Undo")
        a2 = bool(b.AllowCompound)
        result("R7-data-bool-identity", True, "AllowCompound %s->%s names=%s undo->%s note=%s"
               % (a0, a1, names, a2, note), info=True)

    # R8 sketch edit mode: a View-tab hide of another body behaves like Std_ToggleVisibility (035) in the same mode
    if want("R8-sketch-edit"):
        doc = newdoc("rv")
        bd, sk = pad_body(doc, "Body")
        o1, o2 = body(doc, "E1"), body(doc, "E2")
        ready(doc)
        Gui.getDocument(doc.Name).setEdit(sk.Name)
        pump(800)
        indlg = Gui.Control.activeDialog()
        u0 = doc.UndoCount
        select(doc, o1)
        note = click_checkbox("R8", "Visibility")
        pe = (vis(o1), doc.UndoCount - u0, undo_names(doc)[:doc.UndoCount - u0], doc.HasPendingTransaction)
        u1 = doc.UndoCount
        select(doc, o2)
        cmd("Std_ToggleVisibility")
        tg = (vis(o2), doc.UndoCount - u1, undo_names(doc)[:doc.UndoCount - u1], doc.HasPendingTransaction)
        Gui.getDocument(doc.Name).resetEdit()
        pump(500)
        consistent = pe[0] is F and tg[0] is F and pe[1] == tg[1] and pe[3] == tg[3]
        result("R8-sketch-edit", consistent, "dialog=%s pe(vis,steps,names,pend)=%s toggle=%s after_close=%s note=%s"
               % (bool(indlg), pe, tg, undo_names(doc), note))

    # R9 touched document: a Length edit not recomputed, then a View-tab hide -> INFO identity line
    if want("R9-touched"):
        doc = newdoc("rv")
        b = body(doc, "Body")
        ready(doc)
        b.Group[0].Length = 7
        t0 = sorted(o.Name for o in doc.Objects if "Touched" in o.State)
        select(doc, b)
        click_checkbox("R9", "Visibility")
        t1 = sorted(o.Name for o in doc.Objects if "Touched" in o.State)
        names = undo_names(doc)
        cmd("Std_Undo")
        t2 = sorted(o.Name for o in doc.Objects if "Touched" in o.State)
        result("R9-touched", True, "touched before=%s after_hide=%s names=%s after_undo=%s vis=%s len=%s"
               % (t0, t1, names, t2, vis(b), b.Group[0].Length.Value), info=True)

    # R10 save after a View-tab hide, reopen: saved hidden, no undo history; Modified flags as INFO
    if want("R10-save-reopen"):
        doc = newdoc("rvsave")
        b = body(doc, "Body")
        ready(doc)
        gd = Gui.getDocument(doc.Name)
        m0 = gd.Modified
        select(doc, b)
        click_checkbox("R10", "Visibility")
        m1 = gd.Modified
        path = os.path.join(os.environ["UV_WORK"], "rvsave.FCStd")
        doc.saveAs(path)
        App.closeDocument(doc.Name)
        pump(200)
        d2 = App.openDocument(path)
        pump(500)
        b2 = d2.getObject("Body")
        ok = vis(b2) is F and d2.UndoCount == 0
        result("R10-save-reopen", ok, "modified before/after hide=%s/%s reopened vis=%s undo=%d"
               % (m0, m1, vis(b2), d2.UndoCount))

    # R11 Data tab: the object's own (hidden) Visibility property, shown with the editor's context menu
    #     'Show Hidden' (menu driven with key events) -> a user edit there is one step as well
    if want("R11-data-visibility"):
        doc = newdoc("rv")
        b = body(doc, "Body")
        ready(doc)
        select(doc, b)
        st = show_hidden_via_menu("Data")
        pump(600)
        select(doc, b)
        tabs, ed = prop_editor("Data")
        ed.expandAll()
        pump(100)
        has = find_row(ed, "Visibility") is not None
        if not has:
            result("R11-data-visibility", False, "no Visibility row in the Data tab (menu %s)" % st, invalid=True)
        else:
            cycle("R11-data-visibility", doc, [b], lambda: click_checkbox("R11", "Visibility", tab="Data"), [T], [F])
            log("  R11 menu=%s" % st)
        st2 = show_hidden_via_menu("Data")
        log("  R11 menu restore=%s" % st2)

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
