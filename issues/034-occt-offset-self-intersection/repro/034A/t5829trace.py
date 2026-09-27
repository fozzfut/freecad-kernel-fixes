# t5829trace.py: FreeCAD's own 5829 thickness test geometry, recomputed with the TKOffset of this run copy; prints the
# feature verdict and (trace build) the G034 lines go to stderr -> stdout.log. Also exports the fillet in world coords.
import FreeCAD as App, Part
from PartDesignTests import TestThickness as TT
for name in ("testCase5829ThicknessOnRotatedFillet", "testCase5829RectoVersoThicknessOnRotatedFillet"):
    t = TT.TestThickness(name); t.setUp()
    body, fillet = t._create_case_5829()
    fs = fillet.Shape
    fs.exportBrep("C:/dev/occt8-mig/offset-034/cases/f5829_world.brep")
    op = t._find_case_5829_opening_face_name(fs)
    th = t.Doc.addObject("PartDesign::Thickness", "Thickness"); th.Base = (fillet, [op]); th.Value = 1.0
    if "Recto" in name: th.Mode = "RectoVerso"
    else: th.Reversed = True
    body.addObject(th); t.Doc.recompute()
    sh = th.Shape
    msg = "OK" if th.isValid() else th.getStatusString()
    ok = (not sh.isNull()) and sh.isValid()
    bop = "-"
    if not sh.isNull():
        try: sh.check(True); bop = "clean"
        except Exception as e: bop = "FAULTS:" + str(e)[:300].replace("\n", " | ")
    print("T5829", name, "opening", op, "feature", msg, "shapeValid", ok, "vol", (None if sh.isNull() else sh.Volume), "check", bop, flush=True)
    if not sh.isNull():
        import os
        sh.exportBrep("C:/dev/occt8-mig/offset-034/cases/thk5829_%s_%s.brep" % ("rv" if "Recto" in name else "rev", os.path.basename(App.getHomePath().rstrip("/\\"))))
    t.tearDown()
