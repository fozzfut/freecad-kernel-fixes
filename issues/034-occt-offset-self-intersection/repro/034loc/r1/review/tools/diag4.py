# diag4.py - tolerance twin check: max vertex/edge/face tolerance and BOP check of located results vs twins,
# on members of the lane (box/cyl/hole/vfil/dome/sphere) and the review's (capsule/sphz/sphx/spheroid).
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
        s = str(e)
        return "BOP:%d" % s.count("Error in") if "BOP" in s else "BRep:" + s.replace("\n", "|")[:60]


def tols(r):
    tv = max([v.Tolerance for v in r.Vertexes] or [0]); te = max([e.Tolerance for e in r.Edges] or [0])
    tf = max([f.Tolerance for f in r.Faces] or [0])
    return "tolV=%.3g tolE=%.3g tolF=%.3g" % (tv, te, tf)


def box():
    return Part.makeBox(50, 35, 22)


def cyl():
    return Part.makeCylinder(10, 20)


def hole():
    return R.solid1(Part.makeBox(40, 30, 10).cut(Part.makeCylinder(5, 12, V(20, 15, -1))))


def vfil():
    b = Part.makeBox(50, 35, 22)
    return R.solid1(b.makeFillet(4, [e for e in b.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1]))


def dome():
    return Part.makeSphere(10, V(0, 0, 0), V(0, 0, 1), 0, 90)


def sphz():
    return R.solid1(Part.makeSphere(10).cut(Part.makeCylinder(3, 30, V(0, 0, -15), V(0, 0, 1))))


MEM = [("box", box, "thk", "top", -1.2), ("box", box, "off", None, 2.0), ("cyl", cyl, "thk", "top", -1.0),
       ("hole", hole, "thk", "top", -1.0), ("hole", hole, "thk", "cyl", -1.0), ("vfil", vfil, "thk", "top", -1.2),
       ("dome", dome, "thk", "bot", -1.0), ("sphere", lambda: Part.makeSphere(8), "off", None, 1.0),
       ("capsule", R.m_capsule, "thk", "bot", -1.0), ("sphz", sphz, "thk", "cyl", -1.0),
       ("sphx", R.m_sphx, "thk", "cyl", -1.0), ("spheroid", R.m_spheroid, "off", None, 1.0)]
for name, b, op, rm, t in MEM:
    base = b()
    for tn in ("T1", "TT"):
        for var in ("geo", "loc"):
            s, Tw = R.variant(base, var, R.TR[tn])
            try:
                if op == "thk":
                    r = s.makeThickness([s.Faces[R.face_idx(base, rm)]], t, 1e-7, False, False, 0, 0)
                else:
                    r = s.makeOffsetShape(t, 1e-7, join=0)
                res = "valid=%d vol=%.9g %s chk=%s" % (r.isValid(), r.Volume, tols(r), chk(r))
            except Exception as e:
                res = "ERR " + str(e)[:60]
            OUT.write("D4 %s %s%g rm=%s %s %s %s\n" % (name, op, t, rm, tn, var, res)); OUT.flush()
OUT.write("DIAG4-DONE\n"); OUT.close()
