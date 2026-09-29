# fcdoc.py - FreeCAD document path (Part workbench features, Placement on the source object):
# Part::Thickness of a placed box-with-hole (removed face = the hole wall) and of a placed sphere with a side hole.
# Row per placement: feature state, validity, max vertex/edge tolerance, BOP-check verdict, volume.
import os, FreeCAD as App, Part
OUT = open(os.environ["RV_OUT"], "w")
V = App.Vector
PL = {"id": App.Placement(),
      "p1": App.Placement(V(13.1, -7.3, 21.9), App.Rotation(V(1, 2, 3), 47)),
      "tr": App.Placement(V(250, -40, 75), App.Rotation())}


def chk(r):
    try:
        r.check(True); return "ok"
    except Exception as e:
        s = str(e); return "BOP:%d" % s.count("Error in") if "BOP" in s else "BRep:" + s.split("\n")[0][:40]


for kind in ("boxhole", "sphx"):
    for pn, pl in PL.items():
        doc = App.newDocument("T")
        if kind == "boxhole":
            a = doc.addObject("Part::Box", "B"); a.Length = 40; a.Width = 30; a.Height = 10
            c = doc.addObject("Part::Cylinder", "C"); c.Radius = 5; c.Height = 12; c.Placement.Base = V(20, 15, -1)
        else:
            a = doc.addObject("Part::Sphere", "S"); a.Radius = 10
            c = doc.addObject("Part::Cylinder", "C"); c.Radius = 3; c.Height = 30
            c.Placement = App.Placement(V(-15, 0, 0), App.Rotation(V(0, 1, 0), 90))
        cut = doc.addObject("Part::Cut", "Cut"); cut.Base = a; cut.Tool = c
        doc.recompute()
        cut.Placement = pl  # the user moves the finished part
        doc.recompute()
        sub = [i for i, f in enumerate(cut.Shape.Faces) if f.Surface.__class__.__name__ == "Cylinder"][0]
        t = doc.addObject("Part::Thickness", "T"); t.Faces = (cut, ["Face%d" % (sub + 1)]); t.Value = -1.0; t.Join = "Arc"
        doc.recompute()
        st = "|".join(t.State) if t.State else "ok"
        sh = t.Shape
        if sh.isNull():
            OUT.write("FCDOC %s %s state=%s NULL\n" % (kind, pn, st))
        else:
            tv = max(v.Tolerance for v in sh.Vertexes); te = max(e.Tolerance for e in sh.Edges)
            OUT.write("FCDOC %s %s state=%s valid=%d vol=%.6f tolV=%.3g tolE=%.3g chk=%s srcTol=%.3g\n" % (
                kind, pn, st, sh.isValid(), sh.Volume, tv, te, chk(sh), max(v.Tolerance for v in cut.Shape.Vertexes)))
        OUT.flush()
        App.closeDocument(doc.Name)
OUT.write("FCDOC-DONE\n"); OUT.close()
