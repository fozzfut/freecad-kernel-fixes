import os, FreeCAD as App, FreeCADGui as Gui
from PySide import QtCore, QtWidgets
out=[]
def watch():
    w=QtWidgets.QApplication.activeModalWidget()
    if w:
        out.append("MODAL %r: %s" % (w.windowTitle(), " / ".join(l.text() for l in w.findChildren(QtWidgets.QLabel) if l.text())))
        w.reject()
t=QtCore.QTimer(); t.timeout.connect(watch); t.start(300)
def ui():
    for _ in range(5): QtWidgets.QApplication.processEvents()
def go():
    try:
        Gui.activateWorkbench("PartDesignWorkbench"); ui()
        Gui.runCommand("Std_New",0); ui()
        d=App.ActiveDocument; gd=Gui.getDocument(d.Name)
        Gui.activateWorkbench("SpreadsheetWorkbench"); ui()
        Gui.runCommand("Spreadsheet_CreateSheet",0); ui()
        out.append("selection after CreateSheet: %s" % [o.Name for o in Gui.Selection.getSelection()])
        Gui.activateWorkbench("PartDesignWorkbench"); ui()
        Gui.runCommand("PartDesign_Body",0); ui()
        bs=[o for o in d.Objects if o.TypeId=="PartDesign::Body"]
        out.append("bodies=%d BaseFeature=%s" % (len(bs), bs[0].BaseFeature if bs else None))
        p=os.environ["PROBE_OUT"]+".FCStd"
        d.saveAs(p); ui(); out.append("after App saveAs Modified=%s" % gd.Modified)
        d.save(); ui(); out.append("after App save Modified=%s" % gd.Modified)
        Gui.runCommand("Std_Save",0); ui(); out.append("after Std_Save Modified=%s" % gd.Modified)
    except Exception:
        import traceback; out.append(traceback.format_exc())
    QtCore.QTimer.singleShot(800, fin)
def fin():
    open(os.environ["PROBE_OUT"],"w").write("\n".join(out)); os._exit(0)
QtCore.QTimer.singleShot(1000, go)
