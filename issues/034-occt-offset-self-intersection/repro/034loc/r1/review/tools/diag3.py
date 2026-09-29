# diag3.py - wire/edge dump of the Unorientable spherical faces (sphx thick, TT pure translation) vs the twin,
# plus the BOP-check control: is "BOPAlgo SelfIntersect" on located results a checker artifact?
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUT = open(os.environ["RV_OUT"], "w")
import FreeCAD as App, Part
os.environ["RV_OUT"] = os.environ["RV_OUT"] + ".sub"
os.environ["RV_ONLY"] = "^zzz$"
import rvloc as R
V = App.Vector


def chk(r):
    try:
        r.check(True); return "ok"
    except Exception as e:
        return str(e).replace("\n", "|")[:160]


def dumpface(f, Tw):
    lines = []
    inv = Tw.inverse()
    for wi, w in enumerate(f.Wires):
        lines.append("  wire%d closed=%d nE=%d outer=%d" % (wi, w.isClosed(), len(w.Edges), w.isSame(f.OuterWire)))
        for e in w.Edges:
            try:
                c2, a, b = f.curveOnSurface(e)
                p0 = c2.value(a); p1 = c2.value(b)
                uv = "uv(%.4f,%.4f)->(%.4f,%.4f)" % (p0.x, p0.y, p1.x, p1.y)
            except Exception as ex:
                uv = "uv-ERR"
            deg = e.isDegenerated() if hasattr(e, "isDegenerated") else e.Degenerated
            q0 = inv.multVec(e.Vertexes[0].Point); q1 = inv.multVec(e.Vertexes[-1].Point)
            lines.append("    E deg=%d or=%s %s P(%.4f,%.4f,%.4f)->(%.4f,%.4f,%.4f) tol=%.2g locE=%s" % (
                deg, e.Orientation[0], uv, q0.x, q0.y, q0.z, q1.x, q1.y, q1.z, e.Tolerance,
                "id" if e.Placement.isIdentity() else "L"))
    return "\n".join(lines)


base = R.m_sphx()
for tn in ("TT",):
    for var in ("geo", "loc"):
        s, Tw = R.variant(base, var, R.TR[tn])
        i = R.face_idx(base, "cyl")
        r = s.makeThickness([s.Faces[i]], -1.0, 1e-7, False, False, 0, 0)
        OUT.write("== sphx thk %s %s valid=%d\n" % (tn, var, r.isValid()))
        for k, f in enumerate(r.Faces):
            OUT.write(" F%d %s valid=%d or=%s\n%s\n" % (k + 1, f.Surface.__class__.__name__, f.isValid(), f.Orientation, dumpface(f, Tw)))
OUT.write("== input faces sphx (unlocated)\n")
for k, f in enumerate(base.Faces):
    OUT.write(" F%d %s\n%s\n" % (k + 1, f.Surface.__class__.__name__, dumpface(f, App.Placement())))
# BOP-check control: plain located solids (no offset) and baked located results
for nm, sh in (("box", Part.makeBox(10, 10, 10)), ("sphere", Part.makeSphere(8)), ("sphz", None)):
    if sh is None:
        s0 = Part.makeSphere(10); sh = R.solid1(s0.cut(Part.makeCylinder(3, 30, V(0, 0, -15), V(0, 0, 1))))
    for tn in ("TT", "T1"):
        l = sh.copy(); l.Placement = R.TR[tn]
        OUT.write("CTRL located %s %s input chk=%s\n" % (nm, tn, chk(l)))
    if nm == "sphz":
        for tn in ("TT",):
            s, Tw = R.variant(sh, "loc", R.TR[tn])
            r = s.makeThickness([s.Faces[R.face_idx(sh, "cyl")]], -1.0, 1e-7, False, False, 0, 0)
            rb = r.transformed(App.Matrix(), True)
            OUT.write("CTRL sphz thk %s loc chk=%s | baked chk=%s | nV=%d nE=%d vs twin nV/nE follow\n" % (tn, chk(r), chk(rb), len(r.Vertexes), len(r.Edges)))
            sg, _ = R.variant(sh, "geo", R.TR[tn])
            rg = sg.makeThickness([sg.Faces[R.face_idx(sh, "cyl")]], -1.0, 1e-7, False, False, 0, 0)
            OUT.write("CTRL sphz thk %s geo chk=%s nV=%d nE=%d\n" % (tn, chk(rg), len(rg.Vertexes), len(rg.Edges)))
            for v in r.Vertexes:
                OUT.write("   locV tol=%.3g P=%s\n" % (v.Tolerance, R.TR[tn].inverse().multVec(v.Point)))
            for v in rg.Vertexes:
                OUT.write("   geoV tol=%.3g P=%s\n" % (v.Tolerance, R.TR[tn].inverse().multVec(v.Point)))
OUT.write("DIAG3-DONE\n"); OUT.close()
