import FreeCAD as App, Part
o = open("C:/dev/occt8-mig/offset-034b2/rv3/out/dumb.txt", "w")
r = Part.read("C:/dev/occt8-mig/offset-034b2/r3c/out_dumb_a2.brep")
s = Part.read("C:/dev/occt8-mig/offset-034b2/r3c/cases/dumbrod.brep")
o.write("input faces %d vol %.4f bbox %s\n" % (len(s.Faces), s.Volume, s.BoundBox))
for f in s.Faces:
    su = f.Surface
    o.write(" in  %s r=%s area=%.4f\n" % (type(su).__name__, getattr(su, "Radius", "-"), f.Area))
o.write("A2 result valid %s solids %d vol %.4f\n" % (r.isValid(), len(r.Solids), r.Volume))
for f in r.Faces:
    su = f.Surface
    rr = getattr(su, "Radius", None)
    if rr is not None and rr < 0.5:
        c = f.CenterOfMass
        o.write(" res %s r=%.4f area=%.4f com=%s inside_input=%s dist_to_input_boundary=%.4f\n" % (type(su).__name__, rr, f.Area, c, s.isInside(c, 1e-7, True), Part.Compound(s.Faces).distToShape(Part.Vertex(f.valueAt(*[(a+b)/2 for a,b in zip(f.ParameterRange[::2], f.ParameterRange[1::2])])))[0]))
o.close()
