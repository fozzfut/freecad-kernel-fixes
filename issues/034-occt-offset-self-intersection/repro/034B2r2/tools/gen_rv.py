import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/r2/cases/"
L_ = open(D + "rvx2.txt", "w")
def box(x0, y0, z0, x1, y1, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
ROT = App.Placement(V(7, -3, 11), App.Rotation(V(1, 2, 3), 37)).toMatrix()
def rot(sh):
    c = sh.copy(); c.transformShape(ROT, True); return c
def fidx(s, f): return [i for i, g in enumerate(s.Faces) if g.isSame(f)][0] + 1
ZR = App.Placement(ROT).Rotation.multVec(V(0, 0, 1))
L, W, H = 20., 14., 10.
b = box(0, 0, 0, L, W, H)
ev = [e for e in b.Edges if e.BoundBox.ZLength > 1e-3 and e.BoundBox.XLength < 1e-7 and e.BoundBox.YLength < 1e-7]
k = b.makeFillet(0.6, 0.9, ev)
k.exportBrep(D + "var_a.brep"); rot(k).exportBrep(D + "var_w.brep")
for d in (1.2, 2.0, 0.75):
    for vn in ("a", "w"):
        L_.write("var_d%g_%s var_%s.brep offset %g arc none 0 -\n" % (d, vn, vn, -d))
def barrel(R, rr, z0, z1):
    h = z1 - z0; cs = [(R, 7.), (20. - R, 7.), (10., R), (10., 14. - R)]; s = None
    for (cx, cy) in cs:
        c = Part.makeCylinder(R - rr, h, V(cx, cy, z0)); s = c if s is None else s.common(c)
    return s.removeSplitter()
b0 = barrel(30., 0., 0., H)
ve = [e for e in b0.Edges if e.BoundBox.ZLength > H - 1e-6 and e.BoundBox.XLength < 1e-6 and e.BoundBox.YLength < 1e-6]
for r in (1.0, 2.0):
    kk = b0.makeFillet(r, ve)
    for vn, s in (("a", kk), ("w", rot(kk))):
        nm = "barrel_r%g_%s" % (r, vn); s.exportBrep(D + nm + ".brep")
        zax = ZR if vn == "w" else V(0, 0, 1)
        top = max(s.Faces, key=lambda f: f.CenterOfMass.dot(zax))
        for d in (1.5 * r, 3.0 * r):
            if d >= 5: continue
            refT = kk.cut(barrel(30., d, d, H + 1)); refT = rot(refT) if vn == "w" else refT
            refT.exportBrep(D + "ref_%s_t%g.brep" % (nm, d))
            L_.write("%s_t%g %s.brep thick %g arc %d %.9f ref_%s_t%g.brep\n" % (nm, d, nm, -d, fidx(s, top), refT.Volume, nm, d))
L_.close()
