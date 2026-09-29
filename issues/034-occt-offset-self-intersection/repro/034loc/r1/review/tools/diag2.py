# diag2.py - scope of the "located thick -> Unorientable face" finding (sphx) across transforms / members.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUT = open(os.environ["RV_OUT"], "w")
import FreeCAD as App, Part
os.environ["RV_OUT"] = os.environ["RV_OUT"] + ".sub"
os.environ["RV_ONLY"] = "^zzz$"
import rvloc as R
V = App.Vector
R.TR["TX"] = App.Placement(V(0, 0, 0), App.Rotation(V(1, 0, 0), 90))
R.TR["TX1"] = App.Placement(V(0, 0, 0), App.Rotation(V(1, 0, 0), 1))
R.TR["TT1"] = App.Placement(V(1, 0, 0), App.Rotation())


def chk(r):
    try:
        r.check(True); return "ok"
    except Exception as e:
        return str(e).replace("\n", "|")[:200]


def sphz():  # hole along Z removes both poles: no degenerated edge (control)
    s = Part.makeSphere(10); h = Part.makeCylinder(3, 30, V(0, 0, -15), V(0, 0, 1)); return R.solid1(s.cut(h))


def sph_blind():  # sphere with a blind radial hole from +X: poles kept, one cylinder + disk
    s = Part.makeSphere(10); h = Part.makeCylinder(3, 8, V(4, 0, 0), V(1, 0, 0)); return R.solid1(s.cut(h))


def dome_hole():  # half sphere (pole) with a vertical hole off the pole
    s = Part.makeSphere(10, V(0, 0, 0), V(0, 0, 1), 0, 90); h = Part.makeCylinder(2, 30, V(5, 0, -5), V(0, 0, 1))
    return R.solid1(s.cut(h))


def sph_face_sub():  # sphx as an OPEN shell without the cylinder face (skin offset, no thick)
    b = R.m_sphx(); fs = [f for f in b.Faces if f.Surface.__class__.__name__ == "Sphere"]
    return Part.Shell(fs)


MEM = [("sphx", R.m_sphx, "thk", "cyl"), ("sphz", sphz, "thk", "cyl"), ("sphblind", sph_blind, "thk", "cyl"),
       ("domehole", dome_hole, "thk", "bot"), ("sphxshell", sph_face_sub, "off", None), ("sphx", R.m_sphx, "off", None)]
for name, b, op, rm in MEM:
    base = b()
    for tn in ("T1", "TT", "TT1", "TZ", "TX", "TX1"):
        for var in ("none", "geo", "loc"):
            if var == "none" and tn != "T1":
                continue
            s, Tw = R.variant(base, var, R.TR[tn])
            try:
                if op == "thk":
                    i = R.face_idx(base, rm)
                    r = s.makeThickness([s.Faces[i]], -1.0, 1e-7, False, False, 0, 0)
                else:
                    r = s.makeOffsetShape(-1.0, 1e-7, join=0)
                res = "valid=%d vol=%.9g area=%.9g chk=%s" % (r.isValid(), r.Volume, r.Area, chk(r))
            except Exception as e:
                res = "ERR " + str(e)[:80]
            OUT.write("D2 %s %s %s %s %s\n" % (name, op, tn, var, res)); OUT.flush()
OUT.write("DIAG2-DONE\n"); OUT.close()
