# cmp4.py <run dir> [neg] - Review offset-B2 r4: grade the new members against INDEPENDENT references: 2D erosion of the
# densely sampled INPUT profile (trimmed inner parallel curves, noded, faces kept iff inside and farther than d; same
# method as review r3 cmp3.py, self-tested there against exact ellipse quadratures to 2-5e-10). Prism: section =
# A (-) d; revolution: eroded meridian section; oblique prism: eroded perpendicular section lifted along the axis.
# Verdicts: EXACT = valid + no SelfIntersect in the BOP check + 1 solid + distance/MC controls 0 bad + every section
# symmetric difference <= 2e-6 of the reference area; WRONG = a result that fails any of these (silent wrong unless
# the failure is only the stock InvalidCurveOnSurface, reported as ICS); ERR = the kernel raised.
import sys, math, re, os
import numpy as np
from shapely.geometry import Polygon, box, LineString, LinearRing
from shapely.ops import unary_union, polygonize
R = "C:/dev/occt8-mig/offset-034b2/rv4/"
RUN = sys.argv[1]; NEG = float(sys.argv[2]) if len(sys.argv) > 2 else 0.
def prof(n): return np.loadtxt(R + "prof/" + n + ".txt")
def ero_pieces(pieces, d):
    d = d * (1 + NEG); allp = np.vstack(pieces)
    if LinearRing(allp).is_ccw is False:
        pieces = [p[::-1] for p in pieces[::-1]]; allp = np.vstack(pieces)
    ring = []
    for p in pieces:
        t = np.gradient(p, axis=0); t /= np.linalg.norm(t, axis=1)[:, None]
        n = np.c_[-t[:, 1], t[:, 0]]
        ring.extend(map(tuple, p + d * n))
    ring.append(ring[0])
    noded = unary_union(LineString(ring))
    P = Polygon(allp); B = LinearRing(allp); keep = []
    for f in polygonize(noded):
        rp = f.representative_point()
        if P.contains(rp) and B.distance(rp) > d: keep.append(f)
    return unary_union(keep)
ELL = prof("ell"); ELL = np.vstack([ELL, ELL[:1]]); P_ELL = Polygon(ELL)
SX = prof("sx"); SX = np.vstack([SX, SX[:1]]); P_SX = Polygon(SX)
OQ = prof("oq"); v = np.array([2., 3., 10.]); vh = v / np.linalg.norm(v)
e1 = np.cross(vh, [0, 0, 1.]); e1 /= np.linalg.norm(e1); e2 = np.cross(vh, e1)
P3 = np.c_[OQ, np.zeros(len(OQ))]; Qp = P3 - np.outer(P3 @ vh, vh); OQP = np.c_[Qp @ e1, Qp @ e2]; OQP = np.vstack([OQP, OQP[:1]])
def obframe(vv):
    vv = np.array(vv, float); h = vv / np.linalg.norm(vv); a = np.cross(h, [0, 0, 1.]); a /= np.linalg.norm(a); b = np.cross(h, a)
    return vv, h, a, b
def perp(prof2d, fr):
    vv, h, a, b = fr; P3 = np.c_[prof2d, np.zeros(len(prof2d))]; Q = P3 - np.outer(P3 @ h, h); X = np.c_[Q @ a, Q @ b]
    return np.vstack([X, X[:1]])
def lift(poly2d, z0, fr=None):
    vv, _, ea, eb = fr if fr is not None else (v, vh, e1, e2)
    def ring(c):
        c = np.asarray(c); q = np.outer(c[:, 0], ea) + np.outer(c[:, 1], eb)
        q = q + np.outer((z0 - q[:, 2]) / vv[2], vv); return q[:, :2]
    geoms = [poly2d] if poly2d.geom_type == "Polygon" else list(poly2d.geoms)
    return unary_union([Polygon(ring(g.exterior.coords), [ring(h.coords) for h in g.interiors]) for g in geoms])
def revpieces(n, zb=0.):
    M = prof(n)  # (r1,0), top samples r1 -> r0, (r0,0)
    r1, r0 = M[0][0], M[-1][0]
    return [np.linspace([r0, zb], [r1, zb], 2001), np.linspace([r1, zb], M[1], 2001), M[1:-1], np.linspace(M[-2], [r0, zb], 2001)]
TR5 = prof("tr5") if os.path.exists(R + "prof/tr5.txt") else None
OBF = {"ob2": obframe([-3., 1., 8.]), "ob3": obframe([4., -1., 10.]), "obl": obframe([2., 3., 10.])}
OBZ = {"ob2": (4., 3.6), "ob3": (5., 4.5), "obl": (5., 3.5)}
CACHE = {}
def ero(key, pieces, d):
    k = (key, d, NEG)
    if k not in CACHE: CACHE[k] = ero_pieces(pieces, d)
    return CACHE[k]
def ref(case, k):
    m = re.match(r"(\w+?)_(\w)_(off|thktop|thkbot)-([\d.]+)", case); fam, op, d = m.group(1), m.group(3), float(m.group(4))
    if fam in ("se", "sq"):
        return (ero("ell", [ELL], d) if op == "off" else P_ELL.difference(ero("ell", [ELL], d))), (0, 1)
    if fam == "sx":
        return (ero("sx", [SX], d) if op == "off" else P_SX.difference(ero("sx", [SX], d))), (0, 1)
    if fam == "oq":
        z0 = (5., 4.5)[k]; return lift(ero("oq", [OQP], d), z0), (0, 1)
    if fam in ("tri", "tq"):
        T = prof(fam); T = np.vstack([T, T[:1]]); PT = Polygon(T)
        return (ero(fam, [T], d) if op == "off" else PT.difference(ero(fam, [T], d))), (0, 1)
    if fam == "tr5":
        T = np.vstack([TR5, TR5[:1]]); PT = Polygon(T)
        return (ero("tr5", [T], d) if op == "off" else PT.difference(ero("tr5", [T], d))), (0, 1)
    if fam in OBF:
        return lift(ero(fam, [perp(prof(fam), OBF[fam])], d), OBZ[fam][k], OBF[fam]), (0, 1)
    if fam in ("ring", "bmp", "sat"): return None, None
    if fam in ("rs", "rt", "rv2", "rv3", "rev", "rk", "r3r"):
        PR = Polygon(np.vstack(revpieces(fam)))
        if op == "off": return ero(fam, revpieces(fam), d), (0, 2)
        E = ero(fam + "ext", revpieces(fam, -50.), d).intersection(box(-1e3, 0, 1e3, 1e3)); return PR.difference(E), (0, 2)
def respoly(fn, ax):
    rings = []; cur = []
    for ln in open(fn):
        if ln.startswith("END"):
            if len(cur) > 2: rings.append(Polygon(cur).buffer(0))
            cur = []
        else:
            x = list(map(float, ln.split())); cur.append((x[ax[0]], x[ax[1]]))
    g = Polygon()
    for r in rings: g = g.symmetric_difference(r)
    return g
for ln in open(RUN + "/summary.txt"):
    f = ln.split()
    if not f: continue
    case = f[0]
    if case == "START":
        print("%-30s HANG   %s" % (f[1], " ".join(f[2:])[:100])); continue
    if f[1] == "ERR":
        print("%-30s ERR    %s" % (case, " ".join(f[2:]))); continue
    kv = dict(x.split("=", 1) for x in f[2:] if "=" in x)
    on, ob = kv["oracle"].split("/")[:2]; mn, mb = kv["mc"].split("/")
    si = "SelfIntersect" in kv["bop"]
    ok = kv["valid"] == "True" and not si and kv["nsol"] == "1" and ob == "0" and mb == "0"
    secs = sorted(x for x in os.listdir(RUN) if x.startswith(case + "_s"))
    worst = 0.; det = []
    base = case.replace("_ctl", "").replace("_int", "")
    for x in secs:
        kk = int(x[len(case) + 2:-4]); rp, ax = ref(base, kk)
        if rp is None: continue
        g = respoly(RUN + "/" + x, ax)
        sd = g.symmetric_difference(rp).area / rp.area; worst = max(worst, sd)
        det.append("s%d:A=%.6f/%.6f sd=%.1e" % (kk, g.area, rp.area, sd))
    verdict = "EXACT" if ok and det and worst <= 2e-6 else ("ORACLE" if ok and not det else "WRONG")
    if verdict == "EXACT" and kv["bop"] not in ("clean",) and not si:
        verdict = "EXACT*"  # geometry exact; BOP reports only stock ICS / C0 kinds
    print("%-30s %-6s %s | %s" % (case, verdict, " ".join(det), " ".join(f[2:])))
