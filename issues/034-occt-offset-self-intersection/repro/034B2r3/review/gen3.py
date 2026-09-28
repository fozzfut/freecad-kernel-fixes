# gen3.py - Review offset-B2 r3: build NEW class members (not in the lane r1c/r2/r3c nor reviews r1/r2) and dump
# dense samples of their profile curves (input geometry) for the independent references (ref3.py, shapely erosion).
import os, math
import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/rv3/"
log = open(D + "out/gen3.txt", "w")
def say(*a):
    log.write(" ".join(str(x) for x in a) + "\n"); log.flush()
ROT = App.Placement(V(7, -3, 11), App.Rotation(V(1, 2, 3), 37)).toMatrix()
def save(name, s):
    s.exportBrep(D + "cases/" + name + ".brep")
    say("case", name, "valid", s.isValid(), "faces", len(s.Faces), "vol %.9f" % s.Volume)
def dump(name, pts):
    with open(D + "prof/" + name + ".txt", "w") as f:
        for p in pts:
            f.write("%.15g %.15g\n" % p)
def variants(name, s):
    save(name + "_a", s)
    save(name + "_n", s.toNurbs())
    w = s.copy(); w.transformShape(ROT, True); save(name + "_w", w)
N = 200000
# ---- N1 revolution: annular ring rho 10..30, bottom z=0, top z = f(rho) (interpolated B-spline) with a sharp ridge
f = lambda r: 10. + 4. * math.exp(-((r - 20.) / 3.) ** 2)
pts = [V(30. - 20. * i / 40., 0, f(30. - 20. * i / 40.)) for i in range(41)]
top = Part.BSplineCurve(); top.interpolate(pts)
e_top = top.toShape()
w = Part.Wire([Part.makeLine(V(10, 0, 0), V(30, 0, 0)), Part.makeLine(V(30, 0, 0), pts[0]), e_top,
               Part.makeLine(pts[-1], V(10, 0, 0))])
rev = Part.Face(w).revolve(V(0, 0, 0), V(0, 0, 1), 360)
rev = Part.Solid(Part.Shell(rev.Faces)) if rev.ShapeType != "Solid" else rev
if rev.Volume < 0: rev.reverse()
variants("rev", rev)
u0, u1 = top.FirstParameter, top.LastParameter
prof = [(30., 0.)] + [(top.value(u0 + (u1 - u0) * i / N).x, top.value(u0 + (u1 - u0) * i / N).z) for i in range(N + 1)] + [(10., 0.)]
dump("rev", prof)
# min meridian radius of curvature
km = max(top.curvature(u0 + (u1 - u0) * i / 4000.) for i in range(4001))
say("rev meridian min radius %.6f" % (1. / km))
# ---- N3 trefoil: periodic B-spline through r(th) = 10 (1 + e cos 3 th), seam at th = 0 (a lobe tip)
e = 0.3
tp = [V(10 * (1 + e * math.cos(3 * th)) * math.cos(th), 10 * (1 + e * math.cos(3 * th)) * math.sin(th), 0)
      for th in [2 * math.pi * i / 60 for i in range(60)]]
tc = Part.BSplineCurve(); tc.interpolate(tp, PeriodicFlag=True)
tri = Part.Face(Part.Wire(tc.toShape())).extrude(V(0, 0, 20))
if tri.Volume < 0: tri.reverse()
variants("tri", tri)
u0, u1 = tc.FirstParameter, tc.LastParameter
dump("tri", [(tc.value(u0 + (u1 - u0) * i / N).x, tc.value(u0 + (u1 - u0) * i / N).y) for i in range(N)])
km = max(tc.curvature(u0 + (u1 - u0) * i / 6000.) for i in range(6000))
say("tri min radius %.6f seam at %s" % (1. / km, tc.value(u0)))
# ---- N4 oblique elliptic cylinder: ellipse a=10 b=4 in z=0 extruded along v=(2,3,10), H=10 (analytic ellipse)
el = Part.Ellipse(V(0, 0, 0), 10, 4)
ob = Part.Face(Part.Wire(el.toShape())).extrude(V(2, 3, 10))
if ob.Volume < 0: ob.reverse()
variants("obl", ob)
dump("obl", [(10 * math.cos(2 * math.pi * i / N), 4 * math.sin(2 * math.pi * i / N)) for i in range(N)])
say("obl wall surface", [type(fc.Surface).__name__ for fc in ob.Faces])
# ---- N5 rotated elongated bump on a plate (UV-oblique lens): box 40x40, top z = 10 + 5 exp(-(x'^2/2.2^2 + y'^2/9^2))
ca, sa = math.cos(math.radians(30)), math.sin(math.radians(30))
def hb(x, y):
    xr, yr = ca * (x - 20) + sa * (y - 20), -sa * (x - 20) + ca * (y - 20)
    return 10. + 5. * math.exp(-(xr / 3.5) ** 2 - (yr / 9.) ** 2)
M = 41
grid = [[V(40. * i / (M - 1), 40. * j / (M - 1), hb(40. * i / (M - 1), 40. * j / (M - 1))) for j in range(M)] for i in range(M)]
bs = Part.BSplineSurface(); bs.interpolate(grid)
topf = bs.toShape()
box = Part.makeBox(40, 40, 25)
bump = box.cut(topf.extrude(V(0, 0, 30)))
bump = bump.Solids[0]
if bump.Volume < 0: bump.reverse()
say("bump valid", bump.isValid(), "shells", len(bump.Shells))
variants("bmp", bump)
log.close()
