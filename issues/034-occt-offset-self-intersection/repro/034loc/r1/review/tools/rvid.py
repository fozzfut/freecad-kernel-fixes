# rvid.py - identity of UNLOCATED inputs (none + geometry twins) r1 vs delivered: md5 of the result BREP text.
import os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUT = open(os.environ["RV_OUT"], "w")
import FreeCAD as App, Part
os.environ["RV_OUT"] = os.environ["RV_OUT"] + ".sub"
os.environ["RV_ONLY"] = "^zzz$"
import rvloc as R
import diag4mem as D
V = App.Vector
MEM = list(R.CASES) + D.EXTRA
DUMP = os.environ.get("RV_DUMP", "")
NEG = os.environ.get("RV_NEG", "") == "1"
if DUMP:
    os.makedirs(DUMP, exist_ok=True)
CONT = ("C0", "G1", "C1", "G2", "C2", "C3", "CN")


def norm(txt):
    # regularity records "4 <cont> f1 l1 f2 l2": the face pair order follows map/hash order (memory addresses) -
    # not geometry; sort the pair so only real differences remain
    out = []
    for ln in txt.splitlines():
        t = ln.split()
        if len(t) == 6 and t[0] == "4" and t[1] in CONT:
            a, b = (t[2], t[3]), (t[4], t[5])
            if b < a:
                a, b = b, a
            ln = " ".join(["4", t[1], a[0], a[1], b[0], b[1]])
        out.append(ln)
    return chr(10).join(out)
def g(x):
    return "%.10g" % x


def pv(p):
    return ",".join(g(c) for c in (p.x, p.y, p.z))


def fp(r):
    # order-independent fingerprint of the result: the BREP entity order follows hash/address order and changes
    # from run to run on every DLL; geometry, tolerances and topology counts do not
    fs = sorted("%s|%s|%s|%s|%s" % (f.Surface.__class__.__name__, g(f.Area), pv(f.CenterOfMass), g(f.Tolerance), f.Orientation) for f in r.Faces)
    es = sorted("%s|%s|%s|%d" % (g(e.Length), pv(e.CenterOfMass) if e.Length > 0 else "-", g(e.Tolerance), int(e.Length == 0)) for e in r.Edges)
    vs = sorted("%s|%s" % (pv(v.Point), g(v.Tolerance)) for v in r.Vertexes)
    return "V%s|%d|%d|%d|%d#" % (g(r.Volume), len(r.Solids), len(r.Shells), len(r.Wires), len(r.Faces)) + ";".join(fs + es + vs)


for (n, b, op, t, j, rm, trs) in MEM:
    try:
        base = b()
    except Exception as e:
        OUT.write("ID %s BUILD-FAILED\n" % n); continue
    if n in ("lemon",) and op == "off" and t < 0:
        continue  # access violation on every DLL (stock crash), keep the identity run clean
    for tn in trs:
        for var in ("none", "geo"):
            if var == "none" and tn != trs[0]:
                continue
            s, Tw = R.variant(base, var, R.TR[tn])
            try:
                if op == "off":
                    r = s.makeOffsetShape(t, 1e-7, inter=False, self_inter=False, offsetMode=0, join=j, fill=False)
                else:
                    r = s.makeThickness([s.Faces[R.face_idx(base, rm)]], t, 1e-7, False, False, 0, j)
                if NEG and var == "none":
                    r = r.copy(); vx = r.Vertexes[0]; vx.Tolerance = vx.Tolerance * 1.5  # NEG: one tolerance changed
                h = hashlib.md5(fp(r).encode()).hexdigest()[:12]
                if DUMP:
                    txt = norm(r.exportBrepToString())
                    open(os.path.join(DUMP, "%s_%s%g_j%d_%s_%s.brep" % (n, op, t, j, tn, var)), "w").write(txt)
                res = "md5=%s valid=%d" % (h, r.isValid())
            except Exception as e:
                res = "ERR " + str(e).replace(" ", "_")[:60]
            OUT.write("ID %s %s%g j%d %s %s %s\n" % (n, op, t, j, tn, var, res)); OUT.flush()
OUT.write("ID-DONE\n"); OUT.close()
