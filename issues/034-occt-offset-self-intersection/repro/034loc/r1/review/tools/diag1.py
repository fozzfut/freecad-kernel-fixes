# diag1.py - why is the located sphx thickness invalid while its geometry twin is valid?
import os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUT = open(os.environ["RV_OUT"], "w")
import FreeCAD as App, Part
os.environ["RV_OUT"] = os.environ["RV_OUT"] + ".sub"
os.environ["RV_ONLY"] = "^zzz$"
import rvloc as R  # builders only
V = App.Vector

def chk(r):
    try:
        r.check(True)
        return "check-ok"
    except Exception as e:
        return "check: " + str(e).replace("\n", " | ")[:1500]

def faces_info(r):
    out = []
    for i, f in enumerate(r.Faces):
        out.append("F%d %s valid=%d loc=%s tol=%.3g" % (i + 1, f.Surface.__class__.__name__, f.isValid(),
                   "id" if f.Placement.isIdentity() else "L", f.Tolerance))
    for i, e in enumerate(r.Edges):
        if not e.isValid():
            out.append("E%d invalid deg=%d tol=%.3g" % (i + 1, e.Degenerated if hasattr(e, 'Degenerated') else -1, e.Tolerance))
    for i, v in enumerate(r.Vertexes):
        if not v.isValid():
            out.append("V%d invalid tol=%.3g" % (i + 1, v.Tolerance))
    return " ; ".join(out)

for name, b, rm, t, j in (("sphx", R.m_sphx, "cyl", -1.0, 0), ("capsule", R.m_capsule, "bot", -1.0, 0)):
    base = b()
    for tn in ("T1",):
        for var in ("geo", "loc"):
            s, Tw = R.variant(base, var, R.TR[tn])
            i = R.face_idx(base, rm)
            r = s.makeThickness([s.Faces[i]], t, 1e-7, False, False, 0, j)
            OUT.write("D %s %s %s valid=%d\n  %s\n  %s\n" % (name, tn, var, r.isValid(), chk(r), faces_info(r)))
            # rigidly move the result back: does validity follow the location?
            rb = r.copy(); rb.Placement = Tw.inverse().multiply(rb.Placement)
            OUT.write("  moved-back valid=%d\n" % rb.isValid())
            # geometry-bake the located result: same geometry, no locations
            rg = r.transformed(App.Matrix(), True)
            OUT.write("  baked valid=%d %s\n" % (rg.isValid(), chk(rg)[:300]))
            OUT.flush()
OUT.write("DIAG-DONE\n"); OUT.close()
