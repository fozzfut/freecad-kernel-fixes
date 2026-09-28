import math
import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/rv3/"
log = open(D + "out/gen3b.txt", "w")
e = 0.3; N = 200000
# trefoil with the seam at a valley (th = pi/3) instead of a lobe tip
tp = [V(10 * (1 + e * math.cos(3 * th)) * math.cos(th), 10 * (1 + e * math.cos(3 * th)) * math.sin(th), 0)
      for th in [math.pi / 3 + 2 * math.pi * i / 60 for i in range(60)]]
tc = Part.BSplineCurve(); tc.interpolate(tp, PeriodicFlag=True)
s = Part.Face(Part.Wire(tc.toShape())).extrude(V(0, 0, 20))
if s.Volume < 0: s.reverse()
s.exportBrep(D + "cases/trv_a.brep")
u0, u1 = tc.FirstParameter, tc.LastParameter
with open(D + "prof/trv.txt", "w") as f:
    for i in range(N):
        p = tc.value(u0 + (u1 - u0) * i / N); f.write("%.15g %.15g\n" % (p.x, p.y))
log.write("trv valid %s seam %s\n" % (s.isValid(), tc.value(u0))); log.close()
