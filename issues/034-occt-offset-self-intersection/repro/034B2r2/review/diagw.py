import os, math, FreeCAD as App, Part
V = App.Vector
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
for alpha in (45., 30., 20.):
    B, H = 16., 10.
    h = (B / 2) / math.tan(math.radians(alpha / 2))
    P = [(0., 0.), (B, 0.), (B / 2, h)]
    w = Part.makePolygon([V(x, y, 0) for (x, y) in P] + [V(0, 0, 0)])
    s0 = Part.Face(w).extrude(V(0, 0, H))
    ve = [e for e in s0.Edges if e.BoundBox.ZLength > 1e-3 and e.BoundBox.XLength < 1e-7 and e.BoundBox.YLength < 1e-7]
    k = s0.makeFillet(1.0, ve); n = k.toNurbs()
    fil = [f for f in n.Faces if f.Area < 30 and f.BoundBox.ZLength > 5]
    say("alpha", alpha, "fillet nurbs:", [(f.Surface.NbUPoles, f.Surface.NbVPoles, f.Surface.UDegree, f.Surface.VDegree, len(f.Surface.getUKnots()), len(f.Surface.getVKnots()), f.Surface.isURational() or f.Surface.isVRational()) for f in fil])
    for d in (0.5, 0.9, 1.0, 1.1, 1.5):
        try:
            r = n.makeOffsetShape(-d, 1e-7, join=0); say("  n off", d, "OK", r.isValid(), "%.5f" % r.Volume)
        except Exception as ex:
            say("  n off", d, "ERR", str(ex)[:60])
    # sharp NURBS wedge (no fillet) control
    try:
        r = s0.toNurbs().makeOffsetShape(-1.5, 1e-7, join=0); say("  sharp n off 1.5 OK", "%.5f" % r.Volume)
    except Exception as ex:
        say("  sharp n off 1.5 ERR", str(ex)[:60])
say("DONE")
