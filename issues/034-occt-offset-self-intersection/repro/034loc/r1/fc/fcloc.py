# fcloc.py - lane R-034-loc, FreeCAD member: Part::Offset / Part::Thickness of PLACED objects (the Part-workbench
# case: getTopoShape() hands BRepOffset a shape with a TopLoc_Location = the object Placement).
# For each source kind x placement: the feature result must equal the identity-placement result moved by the
# placement (volume/area, error state). Output: FCLOC lines to FC_OUT.
import os, FreeCAD as App, Part
out = open(os.environ.get("FC_OUT", "fcloc.txt"), "w")
PL = {"id": App.Placement(),
      "p1": App.Placement(App.Vector(13.1, -7.3, 21.9), App.Rotation(App.Vector(1, 2, 3), 47)),
      "far": App.Placement(App.Vector(2.5e4, -1.3e4, 7.7e3), App.Rotation(App.Vector(0.3, -0.8, 0.52), 111))}
def mk(doc, kind):
    if kind == "sphere":
        o = doc.addObject("Part::Sphere", "S"); o.Radius = 8; return o, None
    if kind == "dome":
        o = doc.addObject("Part::Sphere", "S"); o.Radius = 10; o.Angle1 = 0; return o, "low"
    if kind == "cone":
        o = doc.addObject("Part::Cone", "C"); o.Radius1 = 10; o.Radius2 = 0; o.Height = 15; return o, "low"
    if kind == "box":
        o = doc.addObject("Part::Box", "B"); o.Length = 50; o.Width = 35; o.Height = 22; return o, "top"
for kind in ("sphere", "dome", "cone", "box"):
    for op in ("offset", "thick"):
        for pn, pl in PL.items():
            doc = App.newDocument("L")
            src, face = mk(doc, kind)
            if op == "thick" and face is None:
                App.closeDocument(doc.Name); continue
            src.Placement = pl
            doc.recompute()
            if op == "offset":
                f = doc.addObject("Part::Offset", "O"); f.Source = src; f.Value = 1.0; f.Join = "Arc"
            else:
                fs = src.Shape.Faces; loc0 = src.Shape.copy(); loc0.Placement = App.Placement()
                zs = [(ff.CenterOfMass.z, i) for i, ff in enumerate(loc0.Faces) if ff.Surface.__class__.__name__ == "Plane"]
                i = (min(zs) if face == "low" else max(zs))[1]
                f = doc.addObject("Part::Thickness", "T"); f.Faces = (src, ["Face%d" % (i + 1)]); f.Value = -1.0; f.Join = "Arc"
            doc.recompute()
            st = "|".join(f.State) if f.State else "ok"
            sh = f.Shape
            if sh.isNull() or "Invalid" in f.State or "Error" in st:
                out.write("FCLOC %s %s %s state=%s ERR\n" % (kind, op, pn, st))
            else:
                loc = sh.copy(); loc.Placement = sh.Placement  # world
                v = sh.Volume; a = sh.Area
                c = sh.BoundBox.Center; pinv = pl.inverse()
                cb = pinv.multVec(sh.Solids[0].CenterOfMass if sh.Solids else c) if sh.Solids else pinv.multVec(c)
                out.write("FCLOC %s %s %s state=%s valid=%d vol=%.6f area=%.6f cb=%.6f,%.6f,%.6f\n" % (
                    kind, op, pn, st, sh.isValid(), v, a, cb.x, cb.y, cb.z))
            out.flush()
            App.closeDocument(doc.Name)
out.write("FCLOC-DONE\n"); out.close()
