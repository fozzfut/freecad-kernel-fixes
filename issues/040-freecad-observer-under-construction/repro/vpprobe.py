# vpprobe.py - lane vr6-asm: Python wrapper type of the view provider of every module's object types.
# Env: VP_OUT (result file), VP_OBS=1 registers a no-op Gui document observer with slotChangedObject/
# slotBeforeChangeObject (the trigger class without HD), VP_WORK (work dir for save/reopen).
# Per type: created (doc.addObject) and restored (save + close + open). Assembly also via the user command.
import os, sys, json, traceback
import FreeCAD as App, FreeCADGui as Gui
from PySide import QtCore, QtWidgets

TYPES = [
    ("App::Part", None), ("App::Link", None), ("App::DocumentObjectGroup", None), ("App::VarSet", None),
    ("App::FeaturePython", None), ("App::Origin", None),
    ("Part::Box", "PartGui"), ("Part::Feature", "PartGui"), ("Part::FeaturePython", "PartGui"),
    ("Part::Part2DObjectPython", "PartGui"),
    ("Sketcher::SketchObject", "SketcherGui"),
    ("PartDesign::Body", "PartDesignGui"), ("PartDesign::Pad", "PartDesignGui"), ("PartDesign::Plane", "PartDesignGui"),
    ("PartDesign::FeatureBase", "PartDesignGui"),
    ("Spreadsheet::Sheet", "SpreadsheetGui"),
    ("Assembly::AssemblyObject", "AssemblyGui"), ("Assembly::JointGroup", "AssemblyGui"),
    ("Mesh::Feature", "MeshGui"), ("Points::Feature", "PointsGui"),
    ("Measure::MeasurePython", "MeasureGui"), ("Measure::MeasureDistanceDetached", "MeasureGui"),
    ("TechDraw::DrawPage", "TechDrawGui"), ("TechDraw::DrawSVGTemplate", "TechDrawGui"),
    ("Fem::FemAnalysis", "FemGui"), ("Fem::ConstraintFixed", "FemGui"), ("Fem::FemMeshObject", "FemGui"),
    ("Surface::Filling", "SurfaceGui"),
]


EVENTS = {}


def _count(kind, vp, prop):
    try:
        o = vp.Object
        state = "attached" if o is not None else "unattached"
    except Exception as exc:
        state = "unreadable"
        k2 = "EXC|%s|%s|%r" % (kind, prop, exc)
        if len(EVENTS) < 100000:
            EVENTS[k2] = EVENTS.get(k2, 0) + 1
            try:
                import traceback
                EVENTS.setdefault("STACK", "".join(traceback.format_stack(limit=6)))
            except Exception:
                pass
    key = "%s|%s|%s|%s" % (kind, state, vp.TypeId if state == "attached" else "-", prop)
    EVENTS[key] = EVENTS.get(key, 0) + 1


class NoopObserver:
    def slotChangedObject(self, vp, prop):
        _count("changed", vp, prop)

    def slotBeforeChangeObject(self, vp, prop):
        _count("before", vp, prop)


def ui():
    for _ in range(3):
        QtWidgets.QApplication.processEvents()


def wrap(o):
    vo = o.ViewObject
    if vo is None:
        return None
    return {"wrapper": type(vo).__name__, "vp": vo.TypeId, "inEdit": hasattr(vo, "isInEditMode")}


def go():
    res = {"hd": "hybriddesign" in sys.modules or any(m.startswith("hybriddesign") for m in sys.modules),
           "obs": os.environ.get("VP_OBS") == "1", "created": {}, "restored": {}, "cmd": {}, "errors": []}
    try:
        if res["hd"]:
            import hybriddesign
            res["hd_file"] = hybriddesign.__file__
        if res["obs"]:
            global _obs
            _obs = NoopObserver()
            Gui.addDocumentObserver(_obs)
        for _, mod in TYPES:
            if mod:
                try:
                    __import__(mod)
                except Exception as e:
                    res["errors"].append("import %s: %r" % (mod, e))
        doc = App.newDocument("vp")
        ui()
        names = {}
        box = doc.addObject("Part::Box", "LinkTarget")
        for t, _ in TYPES:
            try:
                o = doc.addObject(t, "o_" + t.replace("::", "_"))
                if t == "App::Link":
                    o.LinkedObject = box
                names[t] = o.Name
                res["created"][t] = wrap(o)
            except Exception as e:
                res["created"][t] = "ERR %r" % e
        ui()
        path = os.path.join(os.environ["VP_WORK"], "vp.FCStd")
        doc.saveAs(path)
        App.closeDocument(doc.Name)
        ui()
        doc = App.openDocument(path)
        ui()
        for t, n in names.items():
            o = doc.getObject(n)
            res["restored"][t] = wrap(o) if o else "missing"
        App.closeDocument(doc.Name)
        ui()
        # user path: Assembly command
        try:
            Gui.activateWorkbench("AssemblyWorkbench")
        except Exception as e:
            res["errors"].append("activate Assembly: %r" % e)
        Gui.runCommand("Std_New", 0)
        ui()
        Gui.runCommand("Assembly_CreateAssembly", 0)
        ui()
        a = [o for o in App.ActiveDocument.Objects if o.TypeId == "Assembly::AssemblyObject"]
        res["cmd"]["Assembly_CreateAssembly"] = wrap(a[0]) if a else "no assembly"
        try:
            import UtilsAssembly
            res["cmd"]["activeAssembly"] = repr(UtilsAssembly.activeAssembly())
        except Exception as e:
            res["cmd"]["activeAssembly"] = "EXC %r" % e
        # Assembly_InsertLink opens its task panel (the reported symptom)
        Gui.runCommand("Assembly_InsertLink", 0)
        ui()
        dlg = Gui.Control.activeDialog()
        res["cmd"]["InsertLink_panel"] = bool(dlg)
        if dlg:
            Gui.Control.closeDialog()
            ui()
    except Exception:
        res["errors"].append(traceback.format_exc())
    res["events"] = EVENTS
    open(os.environ["VP_OUT"], "w").write(json.dumps(res, indent=1, sort_keys=True))
    os._exit(0)


QtCore.QTimer.singleShot(1500, go)
