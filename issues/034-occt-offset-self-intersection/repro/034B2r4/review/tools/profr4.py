# profr4.py - Review offset-B2 r4: dense INPUT profile samples of the implementer's r4 members (rebuilt from the
# formulas of r4/tools/gen4r.py; each rebuild is checked against the implementer's case file by volume) for the
# independent erosion references of cmp4.py. Test side only.
import math
import FreeCAD as App, Part
V = App.Vector
R = "C:/dev/occt8-mig/offset-034b2/rv4/"; C4 = "C:/dev/occt8-mig/offset-034b2/r4/cases/"
log = open(R + "out/profr4.txt", "w")
N = 200000
def dump(name, pts):
    with open(R + "prof/" + name + ".txt", "w") as f:
        for p in pts: f.write("%.15g %.15g\n" % p)
def samp(c, xy=True):
    u0, u1 = c.FirstParameter, c.LastParameter
    out = []
    for i in range(N + (0 if c.isPeriodic() else 1)):
        p = c.value(u0 + (u1 - u0) * i / N); out.append((p.x, p.y) if xy else (p.x, p.z))
    return out
def solid(sh):
    s = sh if sh.ShapeType == "Solid" else Part.Solid(Part.Shell(sh.Faces))
    if s.Volume < 0: s.reverse()
    return s
def chk(name, s):
    ref = Part.read(C4 + name + "_a.brep")
    log.write("%s rebuilt vol %.9f case vol %.9f diff %.2e\n" % (name, s.Volume, ref.Volume, abs(s.Volume - ref.Volume))); log.flush()
def revmer(name, f, r0, r1, n):
    pts = [V(r1 - (r1 - r0) * i / n, 0, f(r1 - (r1 - r0) * i / n)) for i in range(n + 1)]
    top = Part.BSplineCurve(); top.interpolate(pts)
    w = Part.Wire([Part.makeLine(V(r0, 0, 0), V(r1, 0, 0)), Part.makeLine(V(r1, 0, 0), pts[0]), top.toShape(), Part.makeLine(pts[-1], V(r0, 0, 0))])
    chk(name, solid(Part.Face(w).revolve(V(0, 0, 0), V(0, 0, 1), 360)))
    dump(name, [(r1, 0.)] + samp(top, False) + [(r0, 0.)])
revmer("rv2", lambda r: 9. + 3. * math.exp(-((r - 15.) / 2.5) ** 2), 8., 24., 48)
revmer("rv3", lambda r: 9. + 3. * math.exp(-((r - 14.) / 2.2) ** 2) + 2.5 * math.exp(-((r - 22.) / 2.) ** 2), 8., 28., 60)
e = 0.18
tp = [V(10 * (1 + e * math.cos(5 * th)) * math.cos(th), 10 * (1 + e * math.cos(5 * th)) * math.sin(th), 0) for th in [2 * math.pi * i / 80 for i in range(80)]]
tc = Part.BSplineCurve(); tc.interpolate(tp, PeriodicFlag=True)
chk("tr5", solid(Part.Face(Part.Wire(tc.toShape())).extrude(V(0, 0, 16)))); dump("tr5", samp(tc))
wp = [V(11 * math.cos(t) * (1 + 0.08 * math.cos(4 * t)), 6 * math.sin(t) * (1 + 0.08 * math.cos(4 * t)), 0) for t in [2 * math.pi * i / 64 for i in range(64)]]
wc = Part.BSplineCurve(); wc.interpolate(wp, PeriodicFlag=True)
chk("ob2", solid(Part.Face(Part.Wire(wc.toShape())).extrude(V(-3, 1, 8)))); dump("ob2", samp(wc))
el = Part.Ellipse(V(0, 0, 0), 9, 3.5)
chk("ob3", solid(Part.Face(Part.Wire(el.toShape())).extrude(V(4, -1, 10))))
dump("ob3", [(9 * math.cos(2 * math.pi * i / N), 3.5 * math.sin(2 * math.pi * i / N)) for i in range(N)])
log.close()
