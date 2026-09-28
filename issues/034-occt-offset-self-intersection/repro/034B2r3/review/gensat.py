# gensat.py - Review offset-B2 r3, adversarial member: the implementer's bump t_bump_12_12 (solved by B2 at d=2.8,
# a closed lens with two miter points) plus a SATELLITE fold island: a knot-refined pole raise near one miter point,
# tuned so its apex curvature exceeds 1/d by 3 % (a tiny separate fold region between the detection samples).
# Members: satellite at ~0.16 UV from the miter (inside the certificate's miter exemption radius, estimated
# ~0.25 UV) and at ~1.2 UV (outside it, control).
import math
import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/rv3/"
o = open(D + "out/gensat.txt", "w")
src = Part.read("C:/dev/occt8-mig/offset-034b2/r3c/cases/t_bump_12_12.brep")
top = [f for f in src.Faces if type(f.Surface).__name__ == "BSplineSurface"][0]
others = [f for f in src.Faces if not f.isSame(top)]
d = 2.8
def kmax(su, u, v):
    return max(abs(su.curvature(u, v, "Max")), abs(su.curvature(u, v, "Min")))
def make(name, us, vs, excess=1.03):
    su = top.Surface.copy()
    for k in range(-4, 5):
        su.insertUKnot(us + 0.04 * k, 1, 1e-9); su.insertVKnot(vs + 0.04 * k, 1, 1e-9)
    # pole whose Greville point is nearest to (us, vs)
    uk = su.getUKnots(); um = su.getUMultiplicities(); vk = su.getVKnots(); vm = su.getVMultiplicities()
    def flat(k, m):
        r = []
        for a, b in zip(k, m): r += [a] * b
        return r
    fu, fv = flat(uk, um), flat(vk, vm); p = su.UDegree
    gu = [sum(fu[i + 1:i + 1 + p]) / p for i in range(su.NbUPoles)]
    gv = [sum(fv[j + 1:j + 1 + p]) / p for j in range(su.NbVPoles)]
    i0 = min(range(len(gu)), key=lambda i: abs(gu[i] - us)) + 1; j0 = min(range(len(gv)), key=lambda j: abs(gv[j] - vs)) + 1
    P0 = su.getPole(i0, j0)
    target = excess / d
    def apex(delta):
        s2 = su.copy(); s2.setPole(i0, j0, P0 + V(0, 0, delta))
        best = 0.
        for a in range(-10, 11):
            for b in range(-10, 11):
                best = max(best, kmax(s2, gu[i0 - 1] + 0.01 * a, gv[j0 - 1] + 0.01 * b))
        return best, s2
    lo, hi = 0., 0.5
    while apex(hi)[0] < target: hi *= 2
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if apex(mid)[0] < target: lo = mid
        else: hi = mid
    kk, s2 = apex(hi)
    # fold island around the satellite vs the main fold region
    isl = []; main = []
    for a in range(-60, 61):
        for b in range(-60, 61):
            u, v = gu[i0 - 1] + 0.005 * a, gv[j0 - 1] + 0.005 * b
            if 0 <= u <= 9 and 0 <= v <= 9 and kmax(s2, u, v) > 1. / d:
                isl.append((u, v))
    for a in range(0, 181):
        for b in range(0, 181):
            u, v = 3.5 + 2.0 * a / 180, 4.0 + 1.0 * b / 180
            if kmax(s2, u, v) > 1. / d: main.append((u, v))
    o.write("%s pole (%d,%d) greville (%.4f,%.4f) delta=%.6f apex k=%.5f (1/d=%.5f) window fold pts %d\n" % (name, i0, j0, gu[i0 - 1], gv[j0 - 1], hi, kk, 1 / d, len(isl)))
    fc = Part.Face(s2)
    sh = Part.makeShell([fc] + others); sh.sewShape()
    so = Part.Solid(Part.Shell(sh.Faces))
    if so.Volume < 0: so.reverse()
    o.write("%s solid valid %s faces %d vol %.6f (base %.6f)\n" % (name, so.isValid(), len(so.Faces), so.Volume, src.Volume))
    so.exportBrep(D + "cases/" + name + ".brep")
    with open(D + "out/" + name + "_fold.txt", "w") as f:
        for (u, v) in isl: f.write("I %.5f %.5f\n" % (u, v))
        for (u, v) in main: f.write("M %.5f %.5f\n" % (u, v))
    o.flush()
make("sat_near", 4.005 - 0.05, 4.41 - 0.15)
make("sat_near15", 4.005 - 0.05, 4.41 - 0.15, 1.15)
make("sat_near30", 4.005 - 0.05, 4.41 - 0.15, 1.30)
make("sat_far", 4.005 - 0.4, 4.41 - 1.15)
make("sat_far30", 4.005 - 0.4, 4.41 - 1.15, 1.30)
o.close()
