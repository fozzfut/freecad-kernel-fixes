# rvb2.py - Review offset-B2 r1 (independent). Class members built here (Part API), each graded against an
# INDEPENDENT reference built only with primitives + Booleans (no offset call), or, where no closed-form reference
# exists, against an error-raising distance control (test side only, never geometry).
# Env: FC_OUT (output file), RV_SET (comma list of groups to run; empty = all).
import os, time, math, traceback
import FreeCAD as App, Part
V = App.Vector
out = open(os.environ["FC_OUT"], "w")
def say(*a):
    out.write(" ".join(str(x) for x in a) + "\n"); out.flush()
SETS = [s for s in os.environ.get("RV_SET", "").split(",") if s]
TOL = 1e-7

def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))

def is_vert(e, x, y):
    b = e.BoundBox
    return b.XLength < 1e-7 and b.YLength < 1e-7 and b.ZLength > 1e-3 and abs(b.XMin - x) < 1e-7 and abs(b.YMin - y) < 1e-7

def sdiff(a, b):
    try:
        return a.cut(b).Volume + b.cut(a).Volume
    except Exception as ex:
        return float("nan")

def grade(res, ref, t0):
    ms = (time.time() - t0) * 1000
    if res is None:
        return "ERR", "ms=%d" % ms
    if res.isNull() or res.Volume == 0 and len(res.Faces) == 0:
        return "ERR", "null ms=%d" % ms
    valid = res.isValid()
    try:
        res.check(True); bop = "clean"
    except Exception as ex:
        msgs = [m for m in str(ex).splitlines() if m.strip().startswith("Error")]
        bop = "C0only" if msgs and all("GeomAbs_C0" in m for m in msgs) else "FAULTS"
    nsol = len(res.Solids)
    vol = res.Volume
    info = "valid=%s bop=%s nsol=%d nf=%d vol=%.5f ms=%d" % (valid, bop, nsol, len(res.Faces), vol, ms)
    if ref is None:
        return ("OKNOREF" if valid and bop in ("clean", "C0only") else "INV"), info
    sd = sdiff(res if nsol != 1 else res.Solids[0], ref)
    rel = sd / max(ref.Volume, 1e-12)
    info += " ref=%.5f sd=%.3g rel=%.3g" % (ref.Volume, sd, rel)
    if not (valid and bop in ("clean", "C0only")):
        return "INV", info
    return ("EXACT" if rel <= 1e-6 else "WRONG"), info

def run(tag, fn, ref):
    t0 = time.time()
    res = None; exc = "-"
    try:
        res = fn()
    except Exception as ex:
        exc = str(ex).replace(" ", "_")[:60] or type(ex).__name__
    g, info = grade(res, ref, t0)
    say("%-44s %-7s %s exc=%s" % (tag, g, info, exc))
    return res

def oracle_offset(res, src, d, nper=3):
    """error-raising control only: points of the result boundary must be at |d| from the source boundary"""
    if res is None or res.isNull():
        return "-"
    sk = Part.Compound(src.Faces)
    bad = 0; n = 0; worst = 0.
    for f in res.Faces:
        u0, u1, v0, v1 = f.ParameterRange
        for i in range(nper):
            for j in range(nper):
                u = u0 + (u1 - u0) * (i + 0.5) / nper; v = v0 + (v1 - v0) * (j + 0.5) / nper
                if not f.isInside(f.valueAt(u, v), 1e-6, True):
                    continue
                p = f.valueAt(u, v)
                dist = sk.distToShape(Part.Vertex(p))[0]
                n += 1
                e = abs(dist - abs(d))
                worst = max(worst, e)
                if e > 1e-3:
                    bad += 1
    return "oracle n=%d bad=%d worst=%.3g" % (n, bad, worst)

def oracle_thick(res, src, t, nper=3):
    """control only: every result boundary point lies on the source (0) or at |t| from it"""
    if res is None or res.isNull():
        return "-"
    sk = Part.Compound(src.Faces)
    bad = 0; n = 0
    for f in res.Faces:
        u0, u1, v0, v1 = f.ParameterRange
        for i in range(nper):
            for j in range(nper):
                u = u0 + (u1 - u0) * (i + 0.5) / nper; v = v0 + (v1 - v0) * (j + 0.5) / nper
                p = f.valueAt(u, v)
                if not f.isInside(p, 1e-6, True):
                    continue
                dist = sk.distToShape(Part.Vertex(p))[0]
                n += 1
                if not (dist < 1e-3 or abs(dist - abs(t)) < 1e-3):
                    bad += 1
    return "oracleT n=%d bad=%d" % (n, bad)

ROT = App.Placement(V(7, -3, 11), App.Rotation(V(1, 2, 3), 37)).toMatrix()
def variants(sh):
    """analytic, NURBS (BRepBuilderAPI_NurbsConvert), rotated geometry (copy, no location)"""
    yield "a", sh, (lambda r: r)
    yield "n", sh.toNurbs(), (lambda r: r)
    rs = sh.copy(); rs = rs.transformShape(ROT, True) or rs
    yield "w", rs, (lambda r: r.transformGeometry(ROT) if r is not None else None)

def rot(sh):
    c = sh.copy(); c.transformShape(ROT, True); return c

def want(g):
    return not SETS or g in SETS

# ---- rv2 helpers: polygons in the xy plane, prisms, erosions (Rossignac-Requicha; no offset call)
def prism_xy(pts, z0, z1):
    w = Part.makePolygon([V(x, y, z0) for (x, y) in pts] + [V(pts[0][0], pts[0][1], z0)])
    f = Part.Face(w)
    s = f.extrude(V(0, 0, z1 - z0))
    if s.Volume < 0:
        s.reverse()
    return s

def conv_erode(pts, t, opened=()):
    """convex CCW polygon eroded by t; sides in 'opened' (index i = side P[i]->P[i+1]) are pushed out by 0.5 (removed faces; small, so that the neighbour lines still meet beyond it)"""
    n = len(pts); L = []
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]; m = math.hypot(dx, dy); nx, ny = dy / m, -dx / m
        c = nx * p[0] + ny * p[1]
        L.append((nx, ny, c + 0.5 if i in opened else c - t))
    out = []
    for i in range(n):
        a1, b1, c1 = L[i - 1]; a2, b2, c2 = L[i]
        det = a1 * b2 - a2 * b1
        out.append(((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det))
    return out

def stadium(p, q, t, z0, z1):
    dx, dy = q[0] - p[0], q[1] - p[1]; m = math.hypot(dx, dy); nx, ny = -dy / m * t, dx / m * t
    rect = prism_xy([(p[0] + nx, p[1] + ny), (p[0] - nx, p[1] - ny), (q[0] - nx, q[1] - ny), (q[0] + nx, q[1] + ny)], z0, z1)
    return rect.fuse([Part.makeCylinder(t, z1 - z0, V(p[0], p[1], z0)), Part.makeCylinder(t, z1 - z0, V(q[0], q[1], z0))])

def poly_erode_prism(pts, t, z0, z1):
    """any simple polygon eroded by the disc t (= polygon minus the t-neighbourhood of its boundary), extruded z0..z1"""
    base = prism_xy(pts, z0, z1)
    n = len(pts)
    st = [stadium(pts[i], pts[(i + 1) % n], t, z0 - 1, z1 + 1) for i in range(n)]
    return base.cut(st[0].fuse(st[1:])).removeSplitter()

def vert_edges_at(sh, pts):
    return [e for e in sh.Edges if any(is_vert(e, x, y) for (x, y) in pts)]

def topface(s, vn):
    zax = V(0, 0, 1) if vn != "w" else App.Placement(ROT).Rotation.multVec(V(0, 0, 1))
    return max(s.Faces, key=lambda f: f.CenterOfMass.dot(zax))
H, r = 10., 1.
P = [(12., 0.), (18., 0.), (18., 10.), (30., 10.), (30., 16.), (0., 16.), (0., 10.), (12., 10.)]
conv = [(12., 0.), (18., 0.), (30., 10.), (30., 16.), (0., 16.), (0., 10.)]
s0 = prism_xy(P, 0., H)
k = s0.makeFillet(r, vert_edges_at(s0, conv))
res = k.toNurbs().makeOffsetShape(-1.5, 1e-7, join=0)
for tol in (1e-6, 1e-5, 3e-5):
    fx = res.copy(); fx.fixTolerance(tol)
    try:
        fx.check(True); say("fixTolerance(%g): clean" % tol)
    except Exception as ex:
        say("fixTolerance(%g): FAULTS" % tol)
seen = {}
for fi, f in enumerate(res.Faces):
    for e in f.Edges:
        pc = f.curveOnSurface(e)
        if not pc: continue
        a, b = e.ParameterRange; w = 0.
        for i in range(41):
            t = a + (b - a) * i / 40.
            uv = pc[0].value(t); w = max(w, (f.Surface.value(uv.x, uv.y) - e.valueAt(t)).Length)
        if w > 2 * e.Tolerance:
            bb = e.BoundBox
            say("face%d %s edge tol %.1e dev %.3e len %.4f x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f] curve %s" % (fi + 1, f.Surface.__class__.__name__, e.Tolerance, w, e.Length, bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax, e.Curve.__class__.__name__))
say("DONE")
