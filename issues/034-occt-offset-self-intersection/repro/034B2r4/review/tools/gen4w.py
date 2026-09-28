# gen4w.py - Review offset-B2 r4, second batch of NEW members inside the sub-classes round 4 claims solved:
#   rk   revolution, SKEWED ridge (left width 1.6, right width 3.2, height 3) on r 8..24: closed X ring, lens not symmetric
#   r3r  revolution with THREE ridges (r 12, 17.5, 23; widths 1.8 / 2.2 / 1.5): several closed lenses on one face
#   tq   4-lobe periodic B-spline extrusion with UNEQUAL lobes (e_k = 0.30, 0.18, 0.25, 0.12), seam at the sharpest tip
import os, math
import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/rv4/"
log = open(D + "out/gen4w.txt", "w")
def say(*a):
    log.write(" ".join(str(x) for x in a) + "\n"); log.flush()
ROT = App.Placement(V(-6, 4, 9), App.Rotation(V(2, -3, 1), 41)).toMatrix()
N = 200000
def save(name, s):
    s.exportBrep(D + "cases/" + name + ".brep")
    say("case", name, "valid", s.isValid(), "faces", len(s.Faces), "vol %.9f" % s.Volume)
def variants(name, s):
    save(name + "_a", s); save(name + "_n", s.toNurbs())
    w = s.copy(); w.transformShape(ROT, True); save(name + "_w", w)
def solid(sh):
    s = sh if sh.ShapeType == "Solid" else Part.Solid(Part.Shell(sh.Faces))
    if s.Volume < 0: s.reverse()
    return s
def dump(name, pts):
    with open(D + "prof/" + name + ".txt", "w") as f:
        for p in pts: f.write("%.15g %.15g\n" % p)
def rev(name, f, r0, r1, n):
    pts = [V(r1 - (r1 - r0) * i / n, 0, f(r1 - (r1 - r0) * i / n)) for i in range(n + 1)]
    top = Part.BSplineCurve(); top.interpolate(pts)
    w = Part.Wire([Part.makeLine(V(r0, 0, 0), V(r1, 0, 0)), Part.makeLine(V(r1, 0, 0), pts[0]), top.toShape(), Part.makeLine(pts[-1], V(r0, 0, 0))])
    variants(name, solid(Part.Face(w).revolve(V(0, 0, 0), V(0, 0, 1), 360)))
    u0, u1 = top.FirstParameter, top.LastParameter
    dump(name, [(r1, 0.)] + [(top.value(u0 + (u1 - u0) * i / N).x, top.value(u0 + (u1 - u0) * i / N).z) for i in range(N + 1)] + [(r0, 0.)])
    km = max(top.curvature(u0 + (u1 - u0) * i / 6000.) for i in range(6001))
    say(name, "meridian min radius %.6f" % (1. / km))
def skew(r):
    w = 1.6 if r < 15. else 3.2
    return 9. + 3. * math.exp(-((r - 15.) / w) ** 2)
rev("rk", skew, 8., 24., 64)
rev("r3r", lambda r: 9. + 2.6 * math.exp(-((r - 12.) / 1.8) ** 2) + 3. * math.exp(-((r - 17.5) / 2.2) ** 2) + 2.2 * math.exp(-((r - 23.) / 1.5) ** 2), 8., 27., 76)
E = (0.30, 0.18, 0.25, 0.12)
def rq(th):
    k = int(((th % (2 * math.pi)) + math.pi / 4) // (math.pi / 2)) % 4  # lobe index by nearest tip (tips at k pi/2)
    return 10. * (1 + sum(E[j] * math.exp(-((math.atan2(math.sin(th - j * math.pi / 2), math.cos(th - j * math.pi / 2))) / 0.35) ** 2) for j in range(4)))
tp = [V(rq(th) * math.cos(th), rq(th) * math.sin(th), 0) for th in [2 * math.pi * i / 96 for i in range(96)]]
tc = Part.BSplineCurve(); tc.interpolate(tp, PeriodicFlag=True)
variants("tq", solid(Part.Face(Part.Wire(tc.toShape())).extrude(V(0, 0, 18))))
u0, u1 = tc.FirstParameter, tc.LastParameter
dump("tq", [(tc.value(u0 + (u1 - u0) * i / N).x, tc.value(u0 + (u1 - u0) * i / N).y) for i in range(N)])
ks = [tc.curvature(u0 + (u1 - u0) * i / 8000.) for i in range(8000)]
say("tq min radius %.6f" % (1. / max(ks)), "radius at the lobe tips", ["%.3f" % (1. / tc.curvature(tc.parameter(V(rq(j * math.pi / 2) * math.cos(j * math.pi / 2), rq(j * math.pi / 2) * math.sin(j * math.pi / 2), 0)))) for j in range(4)])
log.close()
