# cmp3.py <run dir> [negshift] - Review offset-B2 r3: grade the new members against INDEPENDENT references:
# 2D Minkowski erosion (shapely buffer(-d) of the densely sampled INPUT profile; the eroded solid of an extrusion
# is (A - d) x [d, H - d], of a solid of revolution the revolution of the eroded meridian section, of an oblique
# cylinder the eroded perpendicular section lifted along the axis - Rossignac-Requicha 1986, product/rotation
# symmetry of the distance function). EXACT = kernel result valid + BOP clean + 1 solid + distance controls 0 bad +
# every section symmetric difference <= 2e-6 of the reference area.
import sys, math, re, os
import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
R = "C:/dev/occt8-mig/offset-034b2/rv3/"
RUN = sys.argv[1]; NEG = float(sys.argv[2]) if len(sys.argv) > 2 else 0.
def prof(n):
    return np.loadtxt(R + "prof/" + n + ".txt")
QS = 16
P_REV = Polygon(prof("rev")); P_TRI = Polygon(prof("tri")); P_TRV = Polygon(prof("trv"))
el = prof("obl"); v = np.array([2., 3., 10.]); vh = v / np.linalg.norm(v)
e1 = np.cross(vh, [0, 0, 1.]); e1 /= np.linalg.norm(e1); e2 = np.cross(vh, e1)
P3 = np.c_[el, np.zeros(len(el))]; Q = P3 - np.outer(P3 @ vh, vh)
P_OBLP = Polygon(np.c_[Q @ e1, Q @ e2])
def lift(poly2d, z0):
    def ring(c):
        c = np.asarray(c); q = np.outer(c[:, 0], e1) + np.outer(c[:, 1], e2)
        q = q + np.outer((z0 - q[:, 2]) / v[2], v); return q[:, :2]
    geoms = [poly2d] if poly2d.geom_type == "Polygon" else list(poly2d.geoms)
    return unary_union([Polygon(ring(g.exterior.coords), [ring(h.coords) for h in g.interiors]) for g in geoms])
from shapely.geometry import LineString, Point, LinearRing
from shapely.ops import polygonize
def ero_pieces(pieces, d):
    """exact-to-sampling erosion of the closed region bounded by the smooth pieces (CCW, each piece ends where the
    next begins) by d: trimmed inner parallel curves (points p - d n, normals by central differences), noded,
    polygonized; a face is kept iff it lies in the region and its interior point is farther than d from the
    boundary (test-side classification of whole faces)."""
    d = d * (1 + NEG); allp = np.vstack(pieces)
    if LinearRing(allp).is_ccw is False:
        pieces = [p[::-1] for p in pieces[::-1]]; allp = np.vstack(pieces)
    lines = []
    for p in pieces:
        t = np.gradient(p, axis=0); t /= np.linalg.norm(t, axis=1)[:, None]
        n = np.c_[-t[:, 1], t[:, 0]]  # left normal = inward for CCW
        lines.append(p + d * n)
    ring = []
    for q in lines: ring.extend(map(tuple, q))
    ring.append(ring[0])
    noded = unary_union(LineString(ring))
    P = Polygon(allp); B = LinearRing(allp); keep = []
    for f in polygonize(noded):
        rp = f.representative_point()
        if P.contains(rp) and B.distance(rp) > d: keep.append(f)
    return unary_union(keep)
REV = prof("rev")
REV_PIECES = [np.linspace([10., 0.], [30., 0.], 2001), np.linspace([30., 0.], REV[1], 2001), REV[1:-1], np.linspace(REV[-2], [10., 0.], 2001)]
TRI = prof("tri"); TRI = np.vstack([TRI, TRI[:1]])
OBLP = np.array(P_OBLP.exterior.coords)
TRV = prof("trv"); TRV = np.vstack([TRV, TRV[:1]])
def ero(P, d):
    if P is P_REV: return ero_pieces(REV_PIECES, d)
    if P is P_TRI: return ero_pieces([TRI], d)
    if P is P_OBLP: return ero_pieces([OBLP], d)
    if P is P_TRV: return ero_pieces([TRV], d)
    return ero_pieces(P, d)
def ref(case, k):
    m = re.match(r"(\w+?)_(\w)_(off|thktop|thkbot)-([\d.]+)", case); fam, op, d = m.group(1), m.group(3), float(m.group(4))
    if fam == "rev":
        if op == "off": return ero(P_REV, d), (0, 2)
        ext = [np.linspace([10., -50.], [30., -50.], 2001), np.linspace([30., -50.], REV[1], 2001), REV[1:-1], np.linspace(REV[-2], [10., -50.], 2001)]
        E = ero(ext, d).intersection(box(-1e3, 0, 1e3, 1e3)); return P_REV.difference(E), (0, 2)
    if fam == "tri":
        return (ero(P_TRI, d) if op == "off" else P_TRI.difference(ero(P_TRI, d))), (0, 1)
    if fam == "trv":
        return ero(P_TRV, d), (0, 1)
    if fam == "obl":
        z0 = (5., 3.5)[k]; return lift(ero(P_OBLP, d), z0), (0, 1)
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
if len(sys.argv) > 3 and sys.argv[3] == "selftest":
    # ellipse a=10 b=4 eroded by 2 and 3 vs the exact quadrature values of the lane (ellref.py): pipeline accuracy
    t = np.linspace(0, 2 * math.pi, 200001); E = np.c_[10 * np.cos(t), 4 * np.sin(t)]
    for d, ex in ((2, 46.188743045), (3, 16.799413087), (1, 82.779073606)):
        a = ero_pieces([E], d).area
        print("selftest ellipse d=%g mine=%.9f lane-exact=%.9f rel=%.2e" % (d, a, ex, abs(a - ex) / ex))
    for nm, P in (("rev", P_REV), ("tri", P_TRI), ("oblp", P_OBLP)):
        for d in (2., 3.):
            a1 = ero(P, d).area; a2 = P.buffer(-d, quad_segs=QS).area
            print("selftest %s d=%g mine=%.9f shapely-buffer=%.9f rel=%.2e" % (nm, d, a1, a2, abs(a1 - a2) / a1))
    sys.exit()
for ln in open(RUN + "/summary.txt"):
    f = ln.split(); case = f[0]
    if case == "STEP": continue
    if case == "START":
        if not any(l.split()[0] == f[1] for l in open(RUN + "/summary.txt") if l.split()[0] != "START"): print("%-30s HANG   (no verdict: killed at the run cap)" % f[1])
        continue
    if f[1] == "ERR":
        print("%-30s ERR    %s" % (case, " ".join(f[2:]))); continue
    kv = dict(x.split("=", 1) for x in f[2:])
    on, ob = kv["oracle"].split("/")[:2]; mn, mb = kv["mc"].split("/")
    ok = kv["valid"] == "True" and kv["bop"] in ("clean", "C0only") and kv["nsol"] == "1" and ob == "0" and mb == "0"
    secs = sorted(x for x in os.listdir(RUN) if x.startswith(case + "_s"))
    worst = 0.; det = []
    if case.startswith("bmp") or not secs:
        verdict = ("ORACLE" if ok else "WRONG")
    else:
        for x in secs:
            k = int(x[len(case) + 2:-4]); rp, ax = ref(case.replace("_ctl", "").replace("_int", ""), k)
            g = respoly(RUN + "/" + x, ax)
            sd = g.symmetric_difference(rp).area / rp.area; worst = max(worst, sd)
            det.append("s%d:A=%.6f/%.6f sd=%.1e" % (k, g.area, rp.area, sd))
        verdict = "EXACT" if ok and worst <= 2e-6 else "WRONG"
    print("%-30s %-6s %s | %s" % (case, verdict, " ".join(det), " ".join(f[2:])))
