# Lane vr6-save probe: after every successful save of a document into its OWN file the Gui document is not
# modified, whoever started the save; a save into ANOTHER file (saveCopy), a recovery snapshot and a failed save
# keep the flag. Offscreen GUI run, output to VS_OUT. One line per case: PASS/FAIL name expected actual.
import os, stat, traceback
import FreeCAD as App, FreeCADGui as Gui
from PySide import QtCore, QtWidgets

OUT = os.environ["VS_OUT"]
WORK = os.environ["VS_WORK"]
lines = []
modals = []


def watch():
    w = QtWidgets.QApplication.activeModalWidget()
    if w:
        modals.append("%r: %s" % (w.windowTitle(), " / ".join(l.text() for l in w.findChildren(QtWidgets.QLabel) if l.text())))
        w.reject()


tm = QtCore.QTimer()
tm.timeout.connect(watch)
tm.start(200)


def ui():
    for _ in range(5):
        QtWidgets.QApplication.processEvents()


res = []


def check(name, expected, actual, extra=""):
    ok = expected == actual
    res.append(ok)
    lines.append("%s %s expected=%s actual=%s %s" % ("PASS" if ok else "FAIL", name, expected, actual, extra))


def path(n):
    return os.path.join(WORK, n)


def change(doc):
    b = doc.getObject("Box")
    b.Length = b.Length.Value + 1.0
    doc.recompute()
    ui()


def go():
    try:
        Gui.runCommand("Std_New", 0); ui()
        a = App.ActiveDocument; ga = Gui.getDocument(a.Name)
        a.addObject("Part::Box", "Box"); a.recompute(); ui()
        check("C0 new doc with a box is modified", True, ga.Modified)

        a.saveAs(path("a.FCStd")); ui()
        check("C1 App saveAs", False, ga.Modified)

        change(a)
        check("C1b change after save marks modified", True, ga.Modified)
        a.save(); ui()
        check("C2 App save", False, ga.Modified)

        change(a)
        if hasattr(App, "saveDocument"):
            App.saveDocument(a.Name); ui()
            check("C3 FreeCAD.saveDocument", False, ga.Modified)
        else:  # not in this build's module table: the same App::Document::save() through getDocument
            App.getDocument(a.Name).save(); ui()
            check("C3 App.getDocument(name).save()", False, ga.Modified)

        change(a)
        a.saveCopy(path("copy.FCStd")); ui()
        check("C4 saveCopy keeps modified", True, ga.Modified, "copy_written=%s" % os.path.isfile(path("copy.FCStd")))
        check("C4b FileName unchanged by saveCopy", path("a.FCStd").replace("\\", "/").lower(),
              a.FileName.replace("\\", "/").lower())

        r = App.writeRecoverySnapshotToTransientDir(a)
        ui()
        check("C5 recovery snapshot keeps modified", True, ga.Modified, "written=%s" % r)

        a.save(); ui()
        a.getObject("Box").ViewObject.LineWidth = 3.0; ui()
        check("C6a view-only change marks modified", True, ga.Modified)
        a.save(); ui()
        check("C6 App save after a view-only change", False, ga.Modified)

        change(a)
        os.chmod(path("a.FCStd"), stat.S_IREAD)
        err = ""
        try:
            a.save()
        except Exception as e:
            err = type(e).__name__
        finally:
            os.chmod(path("a.FCStd"), stat.S_IREAD | stat.S_IWRITE)
        ui()
        check("C7 failed save (read-only file) keeps modified", True, ga.Modified, "error=%s" % err)

        a.saveAs(path("noext")); ui()
        check("C8 App saveAs without extension", False, ga.Modified, "FileName=%s" % os.path.basename(a.FileName))

        change(a)
        a.saveAs(a.FileName); ui()
        check("C9 App saveAs to its own file", False, ga.Modified)

        change(a)
        Gui.runCommand("Std_New", 0); ui()
        b = App.ActiveDocument; gb = Gui.getDocument(b.Name)
        b.addObject("Part::Box", "Box"); b.recompute(); ui()
        b.saveAs(path("b.FCStd")); ui()
        check("C10 saving doc B leaves doc A modified", True, ga.Modified)
        check("C10b doc B saved", False, gb.Modified)

        change(b)
        Gui.doCommand("App.getDocument('%s').save()" % b.Name); ui()
        check("C11 macro-style save through Gui.doCommand", False, gb.Modified)

        change(b)
        Gui.getDocument(b.Name).save(); ui()
        check("C12 Gui Document.save (Std_Save path)", False, gb.Modified)

        change(b)
        Gui.Selection.clearSelection()
        Gui.getDocument(b.Name).ActiveView  # b is active
        Gui.runCommand("Std_Save", 0); ui()
        check("C13 Std_Save", False, gb.Modified)

        # the user-visible symptom: close after a script save asks "Save changes?"
        change(b)
        b.save(); ui()
        n0 = len(modals)
        Gui.runCommand("Std_CloseActiveWindow", 0); ui()
        check("C14 close after App save asks nothing", 0, len(modals) - n0, "modals=%s" % modals[n0:])
    except Exception:
        lines.append("EXC " + traceback.format_exc())
        res.append(False)
    QtCore.QTimer.singleShot(500, fin)


def fin():
    lines.append("VS: pass=%d/%d" % (sum(res), len(res)))
    open(OUT, "w").write("\n".join(lines) + "\n")
    os._exit(0)


QtCore.QTimer.singleShot(1000, go)
