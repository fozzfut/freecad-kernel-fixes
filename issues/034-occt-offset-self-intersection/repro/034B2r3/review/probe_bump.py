import FreeCAD as App, Part
o = open("C:/dev/occt8-mig/offset-034b2/rv3/out/probe_bump.txt", "w")
s = Part.read("C:/dev/occt8-mig/offset-034b2/r3c/cases/t_bump_12_12.brep")
o.write("faces %d bbox %s vol %.4f\n" % (len(s.Faces), s.BoundBox, s.Volume))
for i, f in enumerate(s.Faces):
    su = f.Surface
    o.write("face %d %s range %s orient %s\n" % (i, type(su).__name__, f.ParameterRange, f.Orientation))
    if type(su).__name__ == "BSplineSurface":
        o.write("  poles %dx%d deg %d,%d uknots %s vknots %s\n" % (su.NbUPoles, su.NbVPoles, su.UDegree, su.VDegree, su.getUKnots(), su.getVKnots()))
        u0, u1, v0, v1 = f.ParameterRange
        for d in (2.8, 3.1):
            pts = []
            N = 200
            for a in range(N + 1):
                for b in range(N + 1):
                    u = u0 + (u1 - u0) * a / N; v = v0 + (v1 - v0) * b / N
                    k1 = su.curvature(u, v, "Max"); k2 = su.curvature(u, v, "Min")
                    if max(abs(k1), abs(k2)) > 1. / d: pts.append((u, v, su.value(u, v)))
            if pts:
                us = [p[0] for p in pts]; vs = [p[1] for p in pts]
                o.write("  d=%g fold n=%d u %.4f..%.4f v %.4f..%.4f\n" % (d, len(pts), min(us), max(us), min(vs), max(vs)))
                # ends along the long axis
                for key in (0, 1):
                    lo = min(pts, key=lambda p: p[key]); hi = max(pts, key=lambda p: p[key])
                    o.write("    ends axis%d: (%.4f,%.4f)->%s  (%.4f,%.4f)->%s\n" % (key, lo[0], lo[1], lo[2], hi[0], hi[1], hi[2]))
        o.write("  k at centre: %s %s\n" % (su.curvature((u0+u1)/2, (v0+v1)/2, "Max"), su.curvature((u0+u1)/2, (v0+v1)/2, "Min")))
o.close()
