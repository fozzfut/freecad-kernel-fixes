# evalc.py: evaluate fillet results at the ridge corner. env FC_CASES = file with lines
#   <tag> <chamfer.brep> <result.brep> <r> <vertical edge idx> <miter edge idx>
# For each: validity/check, faces within 3r of the corner vertex (type, area, deviation from the exact rolling-ball
# reference), edges there (normal angles across, tolerance). FreeCADCmd.
import os, sys, math
sys.path.insert(0, "C:/dev/occt8-mig/fillet-corner/probe")
import FreeCAD as App, Part, geo, ref
V = App.Vector
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
say("VERSION", App.Version()[:4], "OCC", Part.OCC_VERSION)
for line in open(os.environ["FC_CASES"]):
    if not line.strip() or line.startswith("#"): continue
    tag, chp, resp, r, vi, mi = line.split()
    r = float(r); vi = int(vi); mi = int(mi)
    ch = Part.Shape(); ch.read(chp)
    if not os.path.exists(resp): say("==", tag, "NO RESULT"); continue
    rs = Part.Shape(); rs.read(resp)
    rg, ve = ref.ridge_from_shape(ch, vi, mi, r)
    Vp = V(*rg.V)
    far = [v for v in ve.Vertexes if (v.Point - Vp).Length > 1e-7][0]
    d = Vp - far.Point; d.normalize()
    rg.trace([d.x, d.y, d.z])
    box = App.BoundBox(Vp.x - 3 * r, Vp.y - 3 * r, Vp.z - 3 * r, Vp.x + 3 * r, Vp.y + 3 * r, Vp.z + 3 * r)
    say("==", tag, "faces", len(rs.Faces), "vol %.6f" % rs.Volume, "valid", rs.isValid(), "check", geo.check(rs), "V", "(%.4f,%.4f,%.4f)" % (Vp.x, Vp.y, Vp.z))
    ef = geo.edge_faces(rs)
    worst = 0.0
    import numpy as np
    planes = [rg.W1, rg.W2, rg.R1, rg.R2]
    def on_ridge_plane(f):
        if type(f.Surface).__name__ != "Plane": return False
        P, n = ref.outward_plane(f)
        return any(abs(abs(n.dot(q[1])) - 1) < 1e-9 and abs((P - q[0]).dot(q[1])) < 1e-7 for q in planes)
    ridgef = [on_ridge_plane(f) for f in rs.Faces]
    adj = {}
    for j, fl in ef.items():
        if len(fl) == 2:
            adj.setdefault(fl[0], set()).add(fl[1]); adj.setdefault(fl[1], set()).add(fl[0])
    for i, f in enumerate(rs.Faces):
        if not box.intersect(f.BoundBox): continue
        t = type(f.Surface).__name__
        dv = ""
        if t != "Plane" and any(ridgef[k] for k in adj.get(i, ())):
            pts, tris = f.tessellate(0.002 * r)
            P = np.array([[q.x, q.y, q.z] for q in pts])
            P = P[np.linalg.norm(P - rg.V, axis=1) < 2 * r]
            if len(P):
                dd = rg.dev(P); m = float(np.abs(dd).max()); n = len(P)
            else:
                m, n = 0.0, 0
            dv = "ridge-blend dev %.2e (n=%d within 2r)" % (m, n)
            # only faces that touch the corner region count for the corner verdict
            worst = max(worst, m)
        say("  F%d" % (i + 1), geo.fdesc(f), "area %.6f" % f.Area, "tol %.1e" % f.Tolerance, dv)
    amax_blend = 0.0
    for j, fl in ef.items():
        E = rs.Edges[j]
        if not box.intersect(E.BoundBox) or len(fl) != 2: continue
        f1, f2 = rs.Faces[fl[0]], rs.Faces[fl[1]]
        t1, t2 = type(f1.Surface).__name__, type(f2.Surface).__name__
        try: ang = geo.edge_angles(rs, j, fl, 11)
        except Exception as ex: ang = []
        kind = "blend-blend" if t1 != "Plane" and t2 != "Plane" else ("blend-face" if (t1 != "Plane") != (t2 != "Plane") else "face-face")
        say("  E%d" % (j + 1), type(E.Curve).__name__, "F%d|F%d" % (fl[0] + 1, fl[1] + 1), kind, "len %.4f" % E.Length, "tol %.1e" % E.Tolerance,
            "ang", " ".join("%.2f" % a for a in ang))
        if kind == "blend-blend" and ang: amax_blend = max(amax_blend, max(ang[1:-1]) if len(ang) > 2 else max(ang))
    say("SUMMARY", tag, "valid", rs.isValid(), "maxdev %.2e" % worst, "max_blend_blend_angle_interior %.3f" % amax_blend,
        "maxtol %.1e" % max(e.Tolerance for e in rs.Edges))
o.close()
