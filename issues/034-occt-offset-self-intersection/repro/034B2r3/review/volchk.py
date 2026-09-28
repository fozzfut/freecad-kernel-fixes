import FreeCAD as App, Part, MeshPart
D = "C:/dev/occt8-mig/offset-034b2/rv3/"
o = open(D + "out/volchk.txt", "w")
for n in ("rev_a", "rev_n", "tri_a", "tri_n", "obl_a", "obl_n"):
    s = Part.read(D + "cases/" + n + ".brep")
    m = MeshPart.meshFromShape(Shape=s, LinearDeflection=0.002, AngularDeflection=0.05)
    sl = s.slice(App.Vector(0, 0, 1), 5.0)
    L = sum(e.Length for w in sl for e in w.Edges)
    o.write("%s gprop=%.9f mesh=%.9f slice_len=%.9f faces=%s\n" % (n, s.Volume, m.Volume, L, [f.Surface.__class__.__name__ for f in s.Faces]))
    for f in s.Faces:
        o.write("   face area %.9f tol %.2e %s\n" % (f.Area, f.Tolerance, f.ParameterRange))
o.close()
