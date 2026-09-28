# diag4.py - Review offset-B2 r4 diagnostics (test side):
#  (1) the Monte-Carlo points misclassified on tr5_w_off-2 / -3: point, distance to the source, classification by
#      the result solid, by the z-slice of the result (planar section containment) and by a tessellated mesh;
#  (2) ring a/w: mesh volumes (GProp on offset faces is unreliable), and the canonical-frame comparison of the two
#      results (the w result moved back must equal the a result: symmetric difference volume by tessellation).
import os, random
import FreeCAD as App, Part, Mesh
V = App.Vector
R = "C:/dev/occt8-mig/offset-034b2/rv4/"
OUT = os.environ["FC_OUT"]; o = open(OUT + "/diag4.txt", "w")
ROT = App.Placement(V(-5, 8, 3), App.Rotation(V(3, -1, 2), 53)).toMatrix()
def mcpts(res, src, d, npts=300, seed=11):
    rnd = random.Random(seed); bb = src.BoundBox; sk = Part.Compound(src.Faces); out = []
    for _ in range(npts):
        p = V(rnd.uniform(bb.XMin, bb.XMax), rnd.uniform(bb.YMin, bb.YMax), rnd.uniform(bb.ZMin, bb.ZMax))
        if not src.isInside(p, 1e-7, True): continue
        dist = sk.distToShape(Part.Vertex(p))[0]
        if abs(dist - abs(d)) < 1e-3: continue
        if res.isInside(p, 1e-7, True) != (dist > abs(d)): out.append((p, dist))
    return out
ROT3 = App.Placement(V(7, -3, 11), App.Rotation(V(1, 2, 3), 37)).toMatrix()
for n, d, rf, sf, rot in (("tr5_w_off-2", 2., "imp", "r4/cases/tr5_w", ROT), ("tr5_w_off-3", 3., "imp", "r4/cases/tr5_w", ROT),
                          ("bmp_w_off-2.8", 2.8, "rv3m", "rv3/cases/bmp_w", ROT3)):
    res = Part.read(R + "out/o034b2rv4-%s/%s.brep" % (rf, n)); src = Part.read("C:/dev/occt8-mig/offset-034b2/%s.brep" % sf)
    m = Mesh.Mesh(res.tessellate(0.05))
    for p, dist in mcpts(res, src, d):
        rc = res.copy(); rc.transformShape(rot.inverse(), True); pc = rot.inverse().multiply(p)
        sl = [Part.Face(w) for w in rc.slice(V(0, 0, 1), pc.z) if w.isClosed()]
        insl = any(f.isInside(pc, 1e-7, True) for f in sl)
        dres = res.distToShape(Part.Vertex(p))[0]
        o.write("%s MC point %s canon %s dist_src %.6f (d %.1f) solid_inside %s slice_inside %s mesh_inside %s dist_to_result_boundary %.6f\n" % (
            n, p, pc, dist, d, res.isInside(p, 1e-7, True), insl, m.isInside(p) if hasattr(m, "isInside") else "-", dres))
    o.flush()
for d, sub, fa_, fw_, rot in (("1.5", "imp", "ring_a", "ring_w", ROT), ("2.5", "imp", "ring_a", "ring_w", ROT), ("2.8", "rv3m", "bmp_a", "bmp_w", ROT3)):
    a = Part.read(R + "out/o034b2rv4-%s/%s_off-%s.brep" % (sub, fa_, d)); w = Part.read(R + "out/o034b2rv4-%s/%s_off-%s.brep" % (sub, fw_, d))
    wc = w.copy(); wc.transformShape(rot.inverse(), True)
    ma = Mesh.Mesh(a.tessellate(0.05)); mw = Mesh.Mesh(wc.tessellate(0.05))
    try:
        x = a.cut(wc); y = wc.cut(a); sdv = x.Volume + y.Volume
        mx = Mesh.Mesh(x.tessellate(0.05)).Volume if x.Faces else 0.; my = Mesh.Mesh(y.tessellate(0.05)).Volume if y.Faces else 0.
    except Exception as ex:
        sdv = mx = my = -1.
    o.write(fa_ + " off-%s gprop a %.6f w %.6f | mesh a %.6f w %.6f | a-w %.6f (mesh %.6f) w-a (mesh %.6f)\n" % (d, a.Volume, w.Volume, ma.Volume, mw.Volume, sdv, mx, my))
    fa = sorted(round(f.Area, 4) for f in a.Faces); fw = sorted(round(f.Area, 4) for f in wc.Faces)
    o.write("   face areas a %s\n   face areas w %s\n" % (fa, fw)); o.flush()
o.close()
