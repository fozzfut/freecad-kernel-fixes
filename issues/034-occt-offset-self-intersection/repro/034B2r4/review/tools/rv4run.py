# rv4run.py - Review offset-B2 r4: run class members listed in RV_LIST (one or more names via RV_ONLY) on one run copy.
# Per case: kernel verdict, validity, BOP check WITH fault kinds (SelfIntersect vs InvalidCurveOnSurface vs C0),
# solids, error-raising distance control on face samples (test side), Monte-Carlo membership control, dense
# section polygons in the canonical frame for the independent erosion references in cmp4.py.
# No offset call builds a reference.
import os, time, math, random
import FreeCAD as App, Part
V = App.Vector
R = "C:/dev/occt8-mig/offset-034b2/rv4/"
OUT = os.environ["FC_OUT"]; os.makedirs(OUT, exist_ok=True)
ONLY = [x for x in os.environ.get("RV_ONLY", "").split(",") if x]
ROTS = {"rv4": App.Placement(V(-6, 4, 9), App.Rotation(V(2, -3, 1), 41)).toMatrix(),
        "rv3": App.Placement(V(7, -3, 11), App.Rotation(V(1, 2, 3), 37)).toMatrix(),
        "r4": App.Placement(V(-5, 8, 3), App.Rotation(V(3, -1, 2), 53)).toMatrix()}
summ = open(OUT + "/summary.txt", "a")
def canon(sh, vn, src):
    c = sh.copy()
    if vn == "w": c.transformShape(ROTS[src].inverse(), True)
    return c
def dumpsec(name, k, wires):
    with open("%s/%s_s%d.txt" % (OUT, name, k), "w") as f:
        for w in wires:
            for p in w.discretize(QuasiDeflection=2e-8):
                f.write("%.12f %.12f %.12f\n" % (p.x, p.y, p.z))
            f.write("END\n")
def oracle(res, sk, d, thick=False, nper=4, skip=None):
    n = bad = 0; worst = 0.
    for fc in res.Faces:
        u0, u1, v0, v1 = fc.ParameterRange
        for i in range(nper):
            for j in range(nper):
                u = u0 + (u1 - u0) * (i + 0.5) / nper; v = v0 + (v1 - v0) * (j + 0.5) / nper
                p = fc.valueAt(u, v)
                if not fc.isInside(p, 1e-6, True): continue
                if skip is not None and skip.distToShape(Part.Vertex(p))[0] < 1e-7: continue
                dist = sk.distToShape(Part.Vertex(p))[0]; n += 1
                e = min(dist, abs(dist - abs(d))) if thick else abs(dist - abs(d))
                worst = max(worst, e)
                if e > 1e-4: bad += 1
    return n, bad, worst
def mc(res, src, d, npts=300, seed=11):
    rnd = random.Random(seed); bb = src.BoundBox; sk = Part.Compound(src.Faces); bad = n = 0
    for _ in range(npts):
        p = V(rnd.uniform(bb.XMin, bb.XMax), rnd.uniform(bb.YMin, bb.YMax), rnd.uniform(bb.ZMin, bb.ZMax))
        if not src.isInside(p, 1e-7, True): continue
        dist = sk.distToShape(Part.Vertex(p))[0]
        if abs(dist - abs(d)) < 1e-3: continue
        n += 1
        if res.isInside(p, 1e-7, True) != (dist > abs(d)): bad += 1
    return n, bad
def bopkinds(res):
    try:
        res.check(True); return "clean"
    except Exception as ex:
        msgs = [m.strip() for m in str(ex).splitlines() if m.strip().startswith("Error")]
        kinds = sorted(set(m.split("BOPAlgo")[-1].strip().replace(" ", "") for m in msgs))
        return ",".join(kinds) or "FAULTS?"
def capface(s, vn, src, which):
    c = canon(s, vn, src)
    key = lambda i: c.Faces[i].CenterOfMass.z
    return s.Faces[min(range(len(c.Faces)), key=key) if which == "bot" else max(range(len(c.Faces)), key=key)]
def run(name, path, vn, src, op, d, join, capsel, secs):
    summ.write("START %s\n" % name); summ.flush()
    s = Part.read(path)
    cap = capface(s, vn, src, capsel) if op != "off" else None
    t0 = time.time(); res = None; exc = "-"
    try:
        if op == "off":
            res = s.makeOffsetShape(d, 1e-7, False, False, 0, join)
        else:
            res = s.makeThickness([cap], d, 1e-7, False, False, 0, join)
    except Exception as ex:
        exc = (str(ex).replace(" ", "_")[:50] or type(ex).__name__)
    ms = (time.time() - t0) * 1000
    summ.write("STEP %s kernel done ms=%d\n" % (name, ms)); summ.flush()
    if res is None or res.isNull() or len(res.Faces) == 0:
        summ.write("%-30s ERR ms=%d exc=%s\n" % (name, ms, exc)); summ.flush(); return
    res.exportBrep(OUT + "/" + name + ".brep")
    valid = res.isValid(); bop = bopkinds(res); nsol = len(res.Solids)
    on, ob, ow = oracle(res, Part.Compound([f for f in s.Faces if cap is None or not f.isSame(cap)]), d, thick=(op != "off"), skip=cap)
    summ.write("STEP %s oracle done\n" % name); summ.flush()
    mn, mb = mc(res, s, d) if op == "off" else (0, 0)
    c = canon(res, vn, src)
    for k, (kind, a) in enumerate(secs):
        if kind == "z":
            wires = c.slice(V(0, 0, 1), a)
        else:
            cc = c.copy(); cc.rotate(V(0, 0, 0), V(0, 0, 1), -a)
            wires = [w for w in cc.slice(V(0, 1, 0), 0.) if w.BoundBox.XMin > 0]
        dumpsec(name, k, wires)
    summ.write("%-30s RES valid=%s bop=%s nsol=%d nf=%d vol=%.9f oracle=%d/%d/%.2g mc=%d/%d ms=%d\n" % (
        name, valid, bop, nsol, len(res.Faces), res.Volume, on, ob, ow, mn, mb, ms))
    summ.flush()
for ln in open(os.environ["RV_LIST"]):
    f = ln.split()
    if not f or f[0].startswith("#"): continue
    name, path, vn, src, op, d, join, capsel = f[:8]
    if ONLY and name not in ONLY: continue
    secs = []
    for x in f[8:]:
        kind, a = x.split(":"); secs.append((kind, float(a)))
    run(name, path, vn, src, op, float(d), int(join), capsel, secs)
summ.close()
