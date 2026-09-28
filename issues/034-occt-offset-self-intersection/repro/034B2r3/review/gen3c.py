import math
import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/rv3/"
log = open(D + "out/gen3c.txt", "w")
def mk(name, ang, M=41):
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    def hb(x, y):
        xr, yr = ca * (x - 20) + sa * (y - 20), -sa * (x - 20) + ca * (y - 20)
        return 10. + 5. * math.exp(-(xr / 3.5) ** 2 - (yr / 9.) ** 2)
    grid = [[V(40. * i / (M - 1), 40. * j / (M - 1), hb(40. * i / (M - 1), 40. * j / (M - 1))) for j in range(M)] for i in range(M)]
    bs = Part.BSplineSurface(); bs.interpolate(grid)
    topf = bs.toShape()
    b = Part.makeBox(40, 40, 25).cut(topf.extrude(V(0, 0, 30))).Solids[0]
    if b.Volume < 0: b.reverse()
    b.exportBrep(D + "cases/" + name + ".brep")
    # fold region of d = 2 and 2.8 on the surface (max principal curvature > 1/d, convex side), scan
    for d in (2.0, 2.8):
        n = 0; pts = []
        for i in range(161):
            for j in range(161):
                u, v = i / 160., j / 160.
                try:
                    k1, k2 = bs.curvature(u, v, "Max"), bs.curvature(u, v, "Min")
                except Exception:
                    continue
                if max(-k1, -k2, k1, k2) > 1. / d:
                    p = bs.value(u, v); pts.append(p); n += 1
        xs = [p.x for p in pts]; ys = [p.y for p in pts]
        log.write("%s d=%g fold samples %d x %.2f..%.2f y %.2f..%.2f\n" % (name, d, n, min(xs or [0]), max(xs or [0]), min(ys or [0]), max(ys or [0])))
    log.write("%s valid %s faces %d\n" % (name, b.isValid(), len(b.Faces))); log.flush()
mk("bm0_a", 0.)
log.close()
