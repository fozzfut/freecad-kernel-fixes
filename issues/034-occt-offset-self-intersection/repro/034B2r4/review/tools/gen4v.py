# gen4v.py - Review offset-B2 r4: NEW class members (not in lane r1c..r4 nor reviews r1..r3) + dense samples of their
# INPUT profile curves for the independent 2D-erosion references (cmp4.py). Test side only (FreeCAD Part).
#   se   ellipse 10 x 4 split into TWO faces at the major tips (G1 edge through the middle of each fold band):
#        X must cross a real edge between two folding faces (fold reaching the face boundary, triple point)
#   sq   the same ellipse split 0.06 rad after the tips (the edge cuts each lens asymmetrically)
#   rs   revolution ridge (rv2 meridian) split into TWO faces of revolution at the ridge circle (closed X ring on an edge)
#   sx   3-lobe periodic B-spline extrusion (rv3 'tri' profile) with the seam 4 deg off the lobe tip (seam inside the lens,
#        asymmetric)
#   oq   the rv3 'tri' profile (seam at the lobe tip) extruded obliquely along (2, 3, 10) (oblique + seam in the lens)
import os, math
import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/rv4/"
os.makedirs(D + "cases", exist_ok=True); os.makedirs(D + "prof", exist_ok=True)
log = open(D + "out/gen4v.txt", "w")
def say(*a):
    log.write(" ".join(str(x) for x in a) + "\n"); log.flush()
ROT = App.Placement(V(-6, 4, 9), App.Rotation(V(2, -3, 1), 41)).toMatrix()
def save(name, s):
    s.exportBrep(D + "cases/" + name + ".brep")
    try:
        s.check(True); b = "clean"
    except Exception as ex:
        b = "FAULTS " + " | ".join(m.strip() for m in str(ex).splitlines() if m.strip())[:200]
    say("case", name, "valid", s.isValid(), "faces", len(s.Faces), "surf", sorted(set(type(f.Surface).__name__ for f in s.Faces)), "vol %.9f" % s.Volume, "bop", b)
def dump(name, pts):
    with open(D + "prof/" + name + ".txt", "w") as f:
        for p in pts:
            f.write("%.15g %.15g\n" % p)
def variants(name, s, nurbs=True):
    save(name + "_a", s)
    if nurbs: save(name + "_n", s.toNurbs())
    w = s.copy(); w.transformShape(ROT, True); save(name + "_w", w)
def solid(sh):
    s = sh if sh.ShapeType == "Solid" else Part.Solid(Part.Shell(sh.Faces))
    if s.Volume < 0: s.reverse()
    return s
N = 200000
# ---- se / sq: split ellipse prism
A, B, H = 10., 4., 12.
for name, t0 in (("se", 0.), ("sq", 0.06)):
    el = Part.Ellipse(V(0, 0, 0), A, B)
    e1 = Part.ArcOfEllipse(el, t0, t0 + math.pi).toShape(); e2 = Part.ArcOfEllipse(el, t0 + math.pi, t0 + 2 * math.pi).toShape()
    pr = solid(Part.Face(Part.Wire([e1, e2])).extrude(V(0, 0, H)))
    variants(name, pr)
dump("ell", [(A * math.cos(2 * math.pi * i / N), B * math.sin(2 * math.pi * i / N)) for i in range(N)])
say("ellipse tip radius %.6f" % (B * B / A))
# ---- rs: revolution, rv2 meridian 9 + 3 exp(-((r-15)/2.5)^2) on 8..24, top curve split at the ridge r = 15 (two faces)
f = lambda r: 9. + 3. * math.exp(-((r - 15.) / 2.5) ** 2)
def interp(r1, r0, n):
    pts = [V(r1 - (r1 - r0) * i / n, 0, f(r1 - (r1 - r0) * i / n)) for i in range(n + 1)]
    c = Part.BSplineCurve(); c.interpolate(pts); return c, pts
for name, rs in (("rs", 15.), ("rt", 15.4)):
    c1, p1 = interp(24., rs, 30); c2, p2 = interp(rs, 8., 24)
    w = Part.Wire([Part.makeLine(V(8, 0, 0), V(24, 0, 0)), Part.makeLine(V(24, 0, 0), p1[0]), c1.toShape(), c2.toShape(),
                   Part.makeLine(p2[-1], V(8, 0, 0))])
    rev = solid(Part.Face(w).revolve(V(0, 0, 0), V(0, 0, 1), 360))
    variants(name, rev)
    prof = [(24., 0.)]
    for c in (c1, c2):
        u0, u1 = c.FirstParameter, c.LastParameter
        prof += [(c.value(u0 + (u1 - u0) * i / N).x, c.value(u0 + (u1 - u0) * i / N).z) for i in range(N + 1)]
    prof += [(8., 0.)]
    dump(name, prof)
    km = max(max(c.curvature(c.FirstParameter + (c.LastParameter - c.FirstParameter) * i / 4000.) for i in range(4001)) for c in (c1, c2))
    say(name, "meridian min radius %.6f" % (1. / km), "faces of revolution", len([x for x in rev.Faces if 'Revolution' in type(x.Surface).__name__]))
# ---- sx: rv3 tri profile (e = 0.3, 3 lobes) with the interpolation (seam) starting 4 deg after the lobe tip
e = 0.3
def triprof(th0, n=60):
    return [V(10 * (1 + e * math.cos(3 * th)) * math.cos(th), 10 * (1 + e * math.cos(3 * th)) * math.sin(th), 0)
            for th in [th0 + 2 * math.pi * i / n for i in range(n)]]
tc = Part.BSplineCurve(); tc.interpolate(triprof(math.radians(4.)), PeriodicFlag=True)
sx = solid(Part.Face(Part.Wire(tc.toShape())).extrude(V(0, 0, 20)))
variants("sx", sx)
u0, u1 = tc.FirstParameter, tc.LastParameter
dump("sx", [(tc.value(u0 + (u1 - u0) * i / N).x, tc.value(u0 + (u1 - u0) * i / N).y) for i in range(N)])
km = max(tc.curvature(u0 + (u1 - u0) * i / 6000.) for i in range(6000))
say("sx min radius %.6f seam at %s" % (1. / km, tc.value(u0)))
# ---- oq: rv3 tri profile (seam at the lobe tip) extruded along (2, 3, 10)
tq = Part.BSplineCurve(); tq.interpolate(triprof(0.), PeriodicFlag=True)
oq = solid(Part.Face(Part.Wire(tq.toShape())).extrude(V(2, 3, 10)))
variants("oq", oq)
u0, u1 = tq.FirstParameter, tq.LastParameter
dump("oq", [(tq.value(u0 + (u1 - u0) * i / N).x, tq.value(u0 + (u1 - u0) * i / N).y) for i in range(N)])
say("oq wall surface", [type(x.Surface).__name__ for x in oq.Faces])
log.close()
