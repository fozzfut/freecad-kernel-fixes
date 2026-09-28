# cmpfam.py <famsec out dir> <famlist> [neg] - independent grading of the implementer's family results: the input
# section (ordered edges) is eroded in 2D by d (trimmed parallel curves; round joins at corners, noded, faces kept
# iff inside and farther than d from the section boundary); offset -> result section == erosion; thick (one cap
# removed, section plane away from it) -> result section == input minus erosion. EXACT iff sd <= 2e-6 of the area.
import sys, math
import numpy as np
from shapely.geometry import Polygon, LineString, LinearRing
from shapely.ops import unary_union, polygonize
from shapely.prepared import prep
D = sys.argv[1]; NEG = float(sys.argv[3]) if len(sys.argv) > 3 else 0.
AXK = {"0": (1, 2), "1": (0, 2), "2": (0, 1)}
def read_in(fn, k):
    loops = []; cur = []; e = []
    for ln in open(fn):
        s = ln.strip()
        if s == "EDGE":
            cur.append(np.array(e)[:, k]); e = []
        elif s == "END":
            loops.append(cur); cur = []
        else:
            e.append(list(map(float, s.split())))
    return loops
def read_res(fn, k):
    g = Polygon(); cur = []
    for ln in open(fn):
        s = ln.strip()
        if s == "END":
            if len(cur) > 2: g = g.symmetric_difference(Polygon(np.array(cur)[:, k]).buffer(0))
            cur = []
        else:
            cur.append(list(map(float, s.split())))
    return g
def erode(loops, d):
    d = d * (1 + NEG)
    region = Polygon()
    for pieces in loops:
        region = region.symmetric_difference(Polygon(np.vstack(pieces)).buffer(0))
    lines = []
    for pieces in loops:
        allp = np.vstack(pieces)
        ccw = LinearRing(allp).is_ccw
        inside_left = ccw  # outer loops: interior on the left when CCW
        # a loop that is a hole of the region: interior of the region is on its right when it is CCW
        rp = Polygon(allp).representative_point()
        if not region.contains(rp):
            inside_left = not ccw
        sgn = 1. if inside_left else -1.
        ring = []
        for i, p in enumerate(pieces):
            t = np.gradient(p, axis=0); t /= np.linalg.norm(t, axis=1)[:, None]
            n = sgn * np.c_[-t[:, 1], t[:, 0]]
            q = p + d * n
            if ring:  # round join around the corner p[0] from the previous normal to this one
                c = p[0]; a0 = math.atan2(*(np.array(ring[-1]) - c)[::-1]); a1 = math.atan2(*(q[0] - c)[::-1])
                da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                for s in np.linspace(0, 1, 65)[1:-1]:
                    ring.append(tuple(c + d * np.array([math.cos(a0 + s * da), math.sin(a0 + s * da)])))
            ring.extend(map(tuple, q))
        c = pieces[0][0]; a0 = math.atan2(*(np.array(ring[-1]) - c)[::-1]); a1 = math.atan2(*(np.array(ring[0]) - c)[::-1])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for s in np.linspace(0, 1, 65)[1:-1]:
            ring.append(tuple(c + d * np.array([math.cos(a0 + s * da), math.sin(a0 + s * da)])))
        ring.append(ring[0])
        lines.append(LineString(ring))
    noded = unary_union(lines)
    B = unary_union([LinearRing(np.vstack(p)) for p in loops]); keep = []
    pr = prep(region)
    for f in polygonize(noded):
        rp = f.representative_point()
        if pr.contains(rp) and B.distance(rp) > d: keep.append(f)
    return region, unary_union(keep)
for ln in open(sys.argv[2]):
    f = ln.split()
    if not f: continue
    name, ax, d, op = f[0], f[2], float(f[4]), f[5]
    k = list(AXK[ax])
    try:
        loops = read_in("%s/%s_in.txt" % (D, name), k); res = read_res("%s/%s_res.txt" % (D, name), k)
    except Exception as ex:
        print("%-20s NOFILE %s" % (name, ex)); continue
    region, E = erode(loops, d)
    ref = E if op == "off" else region.difference(E)
    sd = res.symmetric_difference(ref).area / ref.area
    print("%-20s %-6s A=%.9f ref=%.9f sd=%.2e" % (name, "EXACT" if sd <= 2e-6 else "WRONG", res.area, ref.area, sd))
