import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/r2/cases/"
out = open(D + "named.txt", "w")
doc = App.openDocument("C:/dev/occt8-mig/fillet-corner/files/cube_chamfer_fillet.FCStd")
objs = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull() and o.Shape.Solids]
tip = max(objs, key=lambda o: len(o.Shape.Faces))
k = tip.Shape.copy(); k.exportBrep(D + "owner031.brep")
for d in (-0.3, -1.0, 0.3):
    out.write("owner031_off%g owner031.brep offset %g arc none 0 -\n" % (d, d))
for nm in ("local", "fcworld"):
    s = Part.Shape(); s.read("C:/dev/occt8-mig/offset-034b/cases/f5829_%s.brep" % nm)
    f = min(s.Faces, key=lambda f: f.distToShape(Part.Vertex(V(48, 63, 10)))[0])
    idx = [i for i, g in enumerate(s.Faces) if g.isSame(f)][0] + 1
    for d in (-0.5, -1.0):
        out.write("5829_%s_off%g C:/dev/occt8-mig/offset-034b/cases/f5829_%s.brep offset %g arc none 0 -\n" % (nm, d, nm, d))
        out.write("5829_%s_thk%g C:/dev/occt8-mig/offset-034b/cases/f5829_%s.brep thick %g arc %d 0 -\n" % (nm, d, nm, d, idx))
out.close()
App.closeDocument(doc.Name)
