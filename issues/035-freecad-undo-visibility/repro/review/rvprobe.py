# rvprobe.py - REVIEW of lane undo-visibility (issue 035): paths the implementer's uvprobe.py did not cover.
# Runs inside FreeCAD.exe (offscreen GUI). Writes "CASE <id> PASS|FAIL|INVALID|INFO <details>" to $UV_OUT, ends with
# "PROBE-END ...". Only Qt events posted to FreeCAD's own tree widget; no global input.
# Generic check (cycle): the action changes the visibility signature of ALL objects of ALL documents (else INVALID),
# adds exactly ONE undo step to the active document, Std_Undo restores the whole signature, Std_Redo re-applies it.
import os
import shutil
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


def result(case, verdict, details):
    stats[verdict] += 1
    log("CASE %s %s %s" % (case, verdict, details))


def want(c):
    return not ONLY or c in ONLY


def closeall():
    try:
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()
            pump(100)
    except Exception:
        pass
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    pump(50)


def newdoc(name):
    closeall()
    doc = App.newDocument(name)
    pump(100)
    return doc


def body(doc, name):
    b = doc.addObject("PartDesign::Body", name)
    b.newObject("PartDesign::AdditiveBox", name + "Box")
    return b


def ready(doc):
    for d in App.listDocuments().values():
        d.recompute()
    pump(300)
    for d in App.listDocuments().values():
        d.clearUndos()
    App.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    pump(50)


def cmd(name):
    Gui.runCommand(name, 0)
    pump(150)


def sig():
    s = []
    for d in sorted(App.listDocuments().values(), key=lambda d: d.Name):
        for o in d.Objects:
            try:
                vv = bool(o.ViewObject.Visibility) if o.ViewObject else None
            except Exception:
                vv = None
            vl = tuple(o.VisibilityList) if hasattr(o, "VisibilityList") else ()
            s.append((d.Name, o.Name, bool(o.Visibility), vv, vl))
    return s


def diff(a, b):
    return ["%s.%s:%s/%s%s->%s/%s%s" % (x[0], x[1], x[2], x[3], list(x[4]) or "", y[2], y[3], list(y[4]) or "")
            for x, y in zip(a, b) if x != y]


def cycle(case, doc, act):
    App.setActiveDocument(doc.Name)
    u0 = doc.UndoCount
    s0 = sig()
    act()
    s1 = sig()
    if s1 == s0:
        result(case, "INVALID", "action changed nothing")
        return
    u1 = doc.UndoCount
    names = list(doc.UndoNames)[: max(0, u1 - u0)]
    other = {d.Name: d.UndoCount for d in App.listDocuments().values() if d is not doc}
    cmd("Std_Undo")
    s2 = sig()
    cmd("Std_Redo")
    s3 = sig()
    ok = (u1 - u0 == 1) and s2 == s0 and s3 == s1
    result(case, "PASS" if ok else "FAIL", "steps=%d names=%s changed=%s undo_restores=%s redo_reapplies=%s other_docs_undo=%s%s"
           % (u1 - u0, names, diff(s0, s1), s2 == s0, s3 == s1, other,
              "" if s2 == s0 else " undo_left=%s" % diff(s0, s2)))


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
    m = tree.model()
    hits = m.match(m.index(0, 0), QtCore.Qt.DisplayRole, label, -1, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
    for ix in hits:
        par = ix.parent()
        if parent_label is None or (par.isValid() and par.data(QtCore.Qt.DisplayRole) == parent_label):
            return ix
    return None


def click_eye(tree, label, parent_label=None, wait=400):
    tree.expandAll()
    pump(200)
    ix = tree_item(tree, label, parent_label)
    if ix is None:
        log("  eye: no item %s under %s" % (label, parent_label))
        return
    tree.scrollTo(ix)
    pump(50)
    r = tree.visualRect(ix)
    margin = tree.style().pixelMetric(QtWidgets.QStyle.PM_FocusFrameHMargin) + 1
    pos = QtCore.QPoint(r.left() + margin + 5, r.center().y())
    vp = tree.viewport()
    gpos = vp.mapToGlobal(pos)
    for typ in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonRelease):
        ev = QtGui.QMouseEvent(typ, QtCore.QPointF(pos), QtCore.QPointF(gpos), QtCore.Qt.LeftButton,
                               QtCore.Qt.LeftButton if typ == QtCore.QEvent.MouseButtonPress else QtCore.Qt.NoButton,
                               QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(vp, ev)
        pump(30)
    pump(wait)


def space_in_tree(tree, labels):
    tree.expandAll()
    pump(200)
    sm = tree.selectionModel()
    sm.clearSelection()
    for l in labels:
        ix = tree_item(tree, l)
        if ix is not None:
            sm.select(ix, QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
    pump(100)
    tree.setFocus()
    for typ in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
        QtWidgets.QApplication.sendEvent(tree, QtGui.QKeyEvent(typ, QtCore.Qt.Key_Space, QtCore.Qt.NoModifier, " "))
    pump(150)


def select_sub(doc, obj, sub=""):
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, obj.Name, sub)
    pump(50)


def square_sketch(doc, b, name="Sketch", size=10.0):
    import Part
    sk = b.newObject("Sketcher::SketchObject", name)
    xy = [f for f in b.Origin.OriginFeatures if "XY" in f.Name or getattr(f, "Role", "") == "XY_Plane"][0]
    sk.AttachmentSupport = [(xy, "")]
    sk.MapMode = "FlatFace"
    p = [App.Vector(0, 0, 0), App.Vector(size, 0, 0), App.Vector(size, size, 0), App.Vector(0, size, 0)]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(p[i], p[(i + 1) % 4]))
    return sk


def accept_task():
    dlg = Gui.Control.activeTaskDialog()
    if dlg is None:
        return False
    dlg.accept()
    pump(600)
    return not Gui.Control.activeDialog()


def run():
    log("PROBE-START")
    try:
        import hybriddesign
        log("HD %s" % hybriddesign.__file__)
    except Exception as e:
        log("HD not importable: %s" % e)
    log("UndoVisibility=%s AutoTransactionView=%s" % (
        App.ParamGet("User parameter:BaseApp/Preferences/View").GetBool("UndoVisibility", True),
        App.ParamGet("User parameter:BaseApp/Preferences/PropertyView").GetBool("AutoTransactionView", False)))
    tree = tree_widget()
    log("TREE %s" % (tree is not None))

    # R1 real PartDesign_Pad through the GUI command + OK, then hide the body with the eye; Ctrl+Z twice
    if want("R1-pad-gui"):
        doc = newdoc("rv")
        b = doc.addObject("PartDesign::Body", "PadBody")
        sk = square_sketch(doc, b)
        ready(doc)
        select_sub(doc, sk)
        cmd("PartDesign_Pad")
        pump(800)
        acc = accept_task()
        pad = [o for o in doc.Objects if o.TypeId == "PartDesign::Pad"]
        n0 = list(doc.UndoNames)
        st0 = (bool(b.Visibility), bool(sk.Visibility), len(pad))
        click_eye(tree, "PadBody")
        st1 = (bool(b.Visibility), bool(sk.Visibility), len([o for o in doc.Objects if o.TypeId == "PartDesign::Pad"]))
        n1 = list(doc.UndoNames)
        cmd("Std_Undo")
        st2 = (bool(b.Visibility), bool(sk.Visibility), len([o for o in doc.Objects if o.TypeId == "PartDesign::Pad"]))
        cmd("Std_Undo")
        st3 = (bool(b.Visibility), bool(sk.Visibility), len([o for o in doc.Objects if o.TypeId == "PartDesign::Pad"]))
        cmd("Std_Redo")
        cmd("Std_Redo")
        st4 = (bool(b.Visibility), bool(sk.Visibility), len([o for o in doc.Objects if o.TypeId == "PartDesign::Pad"]))
        ok = (acc and st0 == (T, F, 1) and st1 == (F, F, 1) and len(n1) == len(n0) + 1
              and st2 == (T, F, 1) and st3 == (T, T, 0) and st4 == (F, F, 1))
        result("R1-pad-gui", "PASS" if ok else "FAIL",
               "accepted=%s after_pad=%s names=%s after_eye=%s names=%s undo1=%s undo2=%s redo2=%s"
               % (acc, st0, n0, st1, n1, st2, st3, st4))

    # R2 hide another body with the eye while a sketch is open in edit mode, then close the sketch
    if want("R2-sketch-edit"):
        doc = newdoc("rv")
        b = doc.addObject("PartDesign::Body", "EdBody")
        sk = square_sketch(doc, b, "EdSketch")
        other = body(doc, "OtherBody")
        ready(doc)
        Gui.getDocument(doc.Name).setEdit(sk.Name)
        pump(800)
        inedit = Gui.getDocument(doc.Name).getInEdit() is not None
        pend0 = doc.HasPendingTransaction
        click_eye(tree, "OtherBody")
        hid = not other.Visibility
        pend1 = doc.HasPendingTransaction
        n_in = list(doc.UndoNames)
        Gui.getDocument(doc.Name).resetEdit()
        pump(600)
        pend2 = doc.HasPendingTransaction
        n_after = list(doc.UndoNames)
        # chronological (LIFO): Ctrl+Z walks back the steps made after the hide first, then the hide itself
        k = n_after.index("Hide") + 1 if "Hide" in n_after else 0
        for _ in range(k):
            cmd("Std_Undo")
        v_undo = bool(other.Visibility)
        cmd("Std_Redo")
        v_redo = bool(other.Visibility)
        ok = inedit and hid and not pend2 and k >= 1 and v_undo and not v_redo
        result("R2-sketch-edit", "PASS" if ok else "FAIL",
               "inedit=%s pending before/after eye/after close=%s/%s/%s names_in_edit=%s names_after=%s undos=%d undo->vis=%s redo->vis=%s"
               % (inedit, pend0, pend1, pend2, n_in, n_after, k, v_undo, v_redo))

    # R3 datum plane and sketch inside a body: eye, Space
    if tree and (want("R3a-datum-eye") or want("R3b-datum-space") or want("R3c-sketch-space")):
        for cid, how, lab in (("R3a-datum-eye", "eye", "DatumP"), ("R3b-datum-space", "space", "DatumP"),
                              ("R3c-sketch-space", "space", "DSketch")):
            if not want(cid):
                continue
            doc = newdoc("rv")
            b = body(doc, "DBody")
            dp = b.newObject("PartDesign::Plane", "DatumP")
            sk = square_sketch(doc, b, "DSketch")
            ready(doc)
            if how == "eye":
                cycle(cid, doc, lambda: click_eye(tree, lab))
            else:
                cycle(cid, doc, lambda: space_in_tree(tree, [lab]))

    # R4 link array: one element hidden (ElementVisible API of the link)
    if tree and (want("R4a-linkarray-eye") or want("R4b-linkarray-hidesel")):
        for cid in ("R4a-linkarray-eye", "R4b-linkarray-hidesel"):
            if not want(cid):
                continue
            doc = newdoc("rv")
            b = body(doc, "ArrSrc")
            lk = doc.addObject("App::Link", "Arr")
            lk.LinkedObject = b
            lk.ShowElement = True
            lk.ElementCount = 3
            ready(doc)
            b.ViewObject.Visibility = False
            pump(50)
            doc.clearUndos()
            els = [o for o in lk.ElementList]
            log("  %s elements %s" % (cid, [(e.Name, e.Label) for e in els]))
            if len(els) < 2:
                result(cid, "INVALID", "no link elements")
                continue
            e1 = els[1]
            if cid.endswith("eye"):
                cycle(cid, doc, lambda: click_eye(tree, e1.Label, lk.Label))
            else:
                select_sub(doc, lk, e1.Name + ".")
                cycle(cid, doc, lambda: cmd("Std_HideSelection"))

    # R5 STEP-import structure made by HybridDesign itself: two equal solids in an App::Part -> imports.convert
    # (dedup: one Body + one App::Link twin). Hide the link (eye), the body (eye), the body through the link (HideSel).
    if tree and any(want(c) for c in ("R5a-dedup-link-eye", "R5b-dedup-body-eye", "R5c-dedup-sub-hidesel",
                                      "R5d-dedup-toggle-multi")):
        try:
            import Part
            from hybriddesign.ops import imports, dedup
            have = True
        except Exception as e:
            have = False
            result("R5", "INVALID", "HD import ops not available: %s" % e)
        for cid in ("R5a-dedup-link-eye", "R5b-dedup-body-eye", "R5c-dedup-sub-hidesel", "R5d-dedup-toggle-multi"):
            if not have or not want(cid):
                continue
            doc = newdoc("rv")
            part = doc.addObject("App::Part", "Imported")
            f1 = doc.addObject("Part::Feature", "Nut1")
            f1.Shape = Part.makeCylinder(4, 3)
            f2 = doc.addObject("Part::Feature", "Nut2")
            f2.Shape = Part.makeCylinder(4, 3)
            f2.Placement = App.Placement(App.Vector(20, 0, 0), App.Rotation(App.Vector(0, 0, 1), 30))
            part.addObject(f1)
            part.addObject(f2)
            doc.recompute()
            was = dedup.enabled()
            dedup.set_enabled(True)
            try:
                rep = imports.convert(doc, [part, f1, f2])
            finally:
                dedup.set_enabled(was)
            ready(doc)
            links = [o for o in doc.Objects if o.TypeId == "App::Link"]
            bodies = [o for o in doc.Objects if o.TypeId == "PartDesign::Body"]
            log("  %s convert linked=%s links=%s bodies=%s" % (
                cid, getattr(rep, "linked", None), [(l.Name, l.Label) for l in links], [(x.Name, x.Label) for x in bodies]))
            if not links or not bodies:
                result(cid, "INVALID", "no dedup link made")
                continue
            lk, bd = links[0], bodies[0]
            lpar = lk.getParentGeoFeatureGroup()
            bpar = bd.getParentGeoFeatureGroup()
            if cid == "R5a-dedup-link-eye":
                cycle(cid, doc, lambda: click_eye(tree, lk.Label, lpar.Label if lpar else None))
            elif cid == "R5b-dedup-body-eye":
                cycle(cid, doc, lambda: click_eye(tree, bd.Label, bpar.Label if bpar else None))
            elif cid == "R5c-dedup-sub-hidesel":
                top = lpar
                while top is not None and top.getParentGeoFeatureGroup() is not None:
                    top = top.getParentGeoFeatureGroup()
                if top is None:
                    select_sub(doc, lk, "")
                else:
                    path = []
                    o = lk
                    while o is not None and o is not top:
                        path.insert(0, o.Name)
                        o = o.getParentGeoFeatureGroup()
                    select_sub(doc, top, ".".join(path) + ".")
                cycle(cid, doc, lambda: cmd("Std_HideSelection"))
            else:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(doc.Name, lk.Name, "")
                Gui.Selection.addSelection(doc.Name, bd.Name, "")
                pump(50)
                cycle(cid, doc, lambda: cmd("Std_ToggleVisibility"))

    # R6 Assembly workbench document (owner's O-ring assembly, a copy): eye and Toggle on a component
    if tree and (want("R6a-asm-eye") or want("R6b-asm-toggle") or want("R6c-asm-hideall")):
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oring_copy.FCStd")
        for cid in ("R6a-asm-eye", "R6b-asm-toggle", "R6c-asm-hideall"):
            if not want(cid):
                continue
            closeall()
            dst = os.path.join(WORK, "oring_%s.FCStd" % cid)
            shutil.copy2(src, dst)
            doc = App.openDocument(dst)
            pump(500)
            ready(doc)
            asm = [o for o in doc.Objects if o.TypeId == "Assembly::AssemblyObject"]
            if not asm:
                result(cid, "INVALID", "no assembly in %s" % [o.TypeId for o in doc.Objects][:10])
                continue
            asm = asm[0]
            comps = [o for o in asm.Group if o.TypeId in ("App::Link", "PartDesign::Body", "App::Part", "Part::Feature")
                     and o.Visibility]
            log("  %s assembly %s comps=%s" % (cid, asm.Label, [(c.Name, c.TypeId, c.Label) for c in comps]))
            if not comps:
                result(cid, "INVALID", "no visible component")
                continue
            c = comps[0]
            if cid == "R6a-asm-eye":
                cycle(cid, doc, lambda: click_eye(tree, c.Label, asm.Label))
            elif cid == "R6b-asm-toggle":
                select_sub(doc, asm, c.Name + ".")
                cycle(cid, doc, lambda: cmd("Std_ToggleVisibility"))
            else:
                cycle(cid, doc, lambda: cmd("Std_HideObjects"))

    # R7 two documents: a link in A to a body of B
    if tree and (want("R7a-xdoc-link-eye") or want("R7b-xdoc-child-eye") or want("R7c-xdoc-sub-hidesel")):
        for cid in ("R7a-xdoc-link-eye", "R7b-xdoc-child-eye", "R7c-xdoc-sub-hidesel"):
            if not want(cid):
                continue
            closeall()
            db = App.newDocument("rvB")
            bb = body(db, "BBody")
            bpart = db.addObject("App::Part", "BPart")
            bpart.addObject(bb)
            db.recompute()
            db.saveAs(os.path.join(WORK, "rvB_%s.FCStd" % cid.replace("-", "_")))
            da = App.newDocument("rvA")
            da.saveAs(os.path.join(WORK, "rvA_%s.FCStd" % cid.replace("-", "_")))
            lk = da.addObject("App::Link", "XLink")
            lk.LinkedObject = bpart if cid == "R7b-xdoc-child-eye" else bb
            ready(da)
            if cid == "R7a-xdoc-link-eye":
                cycle(cid, da, lambda: click_eye(tree, lk.Label))
            elif cid == "R7b-xdoc-child-eye":
                # the body shown under the link in A's tree; B's own tree item has the same label -> parent filter
                s0 = sig()
                click_eye(tree, bb.Label, lk.Label)
                s1 = sig()
                info = "changed=%s A.undo=%s B.undo=%s A.names=%s B.names=%s" % (
                    diff(s0, s1), da.UndoCount, db.UndoCount, list(da.UndoNames), list(db.UndoNames))
                App.setActiveDocument(da.Name)
                cmd("Std_Undo")
                sA = sig()
                App.setActiveDocument(db.Name)
                cmd("Std_Undo")
                sB = sig()
                result(cid, "INFO", info + " undoInA_restores=%s undoInB_restores=%s" % (sA == s0, sB == s0))
            else:
                select_sub(da, lk, "")
                cycle(cid, da, lambda: cmd("Std_HideSelection"))

    # R8 programmatic visibility changes stay out of the undo list (identity with stock)
    if want("R8-programmatic"):
        doc = newdoc("rv")
        b1, b2, b3 = body(doc, "P1"), body(doc, "P2"), body(doc, "P3")
        ready(doc)
        b1.Visibility = False
        b2.ViewObject.hide()
        select_sub(doc, b3)
        Gui.Selection.setVisible(False)
        pump(100)
        n = doc.UndoCount
        hidden = (b1.Visibility, b2.Visibility, b3.Visibility)
        result("R8-programmatic", "PASS" if n == 0 and hidden == (F, F, F) else "FAIL",
               "undoCount=%d vis=%s" % (n, hidden))

    # R9 a face picked in the 3D view, then Hide Selection
    if want("R9-face-hidesel"):
        doc = newdoc("rv")
        b = body(doc, "FBody")
        ready(doc)
        select_sub(doc, b, "FBodyBox.Face1")
        log("  R9 selection %s" % [(s.ObjectName, s.SubElementNames) for s in Gui.Selection.getSelectionEx("", 0)])
        cycle("R9-face-hidesel", doc, lambda: cmd("Std_HideSelection"))

    # R10 a hide + its undo leaves no feature touched (no recompute needed), names of every path
    if want("R10-untouched") and tree:
        doc = newdoc("rv")
        b = doc.addObject("PartDesign::Body", "UBody")
        sk = square_sketch(doc, b, "USketch")
        doc.openTransaction("Pad")
        pad = b.newObject("PartDesign::Pad", "UPad")
        pad.Profile = sk
        pad.Length = 3
        doc.recompute()
        doc.commitTransaction()
        pump(200)
        click_eye(tree, "UBody")
        t1 = [o.Name for o in doc.Objects if "Touched" in o.State]
        cmd("Std_Undo")
        t2 = [o.Name for o in doc.Objects if "Touched" in o.State]
        names = list(doc.UndoNames)
        result("R10-untouched", "PASS" if not t1 and not t2 and bool(b.Visibility) and names == ["Pad"] else "FAIL",
               "touched after hide=%s after undo=%s vis=%s undoNames=%s" % (t1, t2, bool(b.Visibility), names))

    # R11 toggle on a feature selected in the 3D view (PartDesign toggles the whole body)
    if want("R11-feature-toggle"):
        doc = newdoc("rv")
        b = body(doc, "TBody")
        ready(doc)
        select_sub(doc, b, "TBodyBox.")
        cycle("R11-feature-toggle", doc, lambda: cmd("Std_ToggleVisibility"))

    # R12 two quick clicks on the eye: two steps, undo walks them back one by one (informational + checked)
    if want("R12-eye-twice") and tree:
        doc = newdoc("rv")
        b = body(doc, "QBody")
        ready(doc)
        click_eye(tree, "QBody", wait=50)
        click_eye(tree, "QBody", wait=400)
        v = bool(b.Visibility)
        names = list(doc.UndoNames)
        cmd("Std_Undo")
        v1 = bool(b.Visibility)
        cmd("Std_Undo")
        v2 = bool(b.Visibility)
        ok = v and names == ["Show", "Hide"] and v1 is False and v2 is True
        result("R12-eye-twice", "PASS" if ok else "FAIL", "vis=%s names=%s undo1=%s undo2=%s" % (v, names, v1, v2))

    log("PROBE-END pass=%d fail=%d invalid=%d info=%d" % (stats["PASS"], stats["FAIL"], stats["INVALID"], stats["INFO"]))


def main():
    try:
        run()
    except Exception:
        log("PROBE-EXC " + traceback.format_exc().replace("\n", " | "))
    finally:
        try:
            closeall()
        except Exception:
            pass
        log("PROBE-EXIT")
        os._exit(0)


QtCore.QTimer.singleShot(int(os.environ.get("UV_DELAY_MS", "3000")), main)
