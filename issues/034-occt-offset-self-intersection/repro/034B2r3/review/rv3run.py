# rv3run.py - Review offset-B2 r3: run the NEW class members on one run copy. Env FC_OUT (dir), RV_SET (groups).
# Per case: kernel verdict, validity, BOP check, solids, error-raising distance control (face samples at |d| from
# the source boundary), Monte-Carlo membership control (offsets), and dense section polygons of the result
# (canonical frame) for the independent shapely erosion references in cmp3.py. No offset call builds a reference.
import os, time, math, random
import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/rv3/"
OUT = os.environ["FC_OUT"]; os.makedirs(OUT, exist_ok=True)
SETS = [s for s in os.environ.get("RV_SET", "").split(",") if s]
ROT = App.Placement(V(7, -3, 11), App.Rotation(V(1, 2, 3), 37)).toMatrix()
INV = ROT.inverse()
summ = open(OUT + "/summary.txt", "a")
def want(g): return not SETS or g in SETS
def canon(sh, vn):
    c = sh.copy()
    if vn == "w": c.transformShape(INV, True)
    return c
def dumpsec(name, k, wires):
    with open("%s/%s_s%d.txt" % (OUT, name, k), "w") as f:
        for w in wires:
            for p in w.discretize(QuasiDeflection=2e-8):
                f.write("%.12f %.12f %.12f\n" % (p.x, p.y, p.z))
            f.write("END\n")
def oracle(res, sk, d, thick=False, nper=3, skip=None):
    pass; n = bad = 0; worst = 0.
    for fc in res.Faces:
        u0, u1, v0, v1 = fc.ParameterRange
        for i in range(nper):
            for j in range(nper):
                u = u0 + (u1 - u0) * (i + 0.5) / nper; v = v0 + (v1 - v0) * (j + 0.5) / nper
                p = fc.valueAt(u, v)
                if not fc.isInside(p, 1e-6, True): continue
                if skip is not None and skip.distToShape(Part.Vertex(p))[0] < 1e-7: continue  # in the opening
                dist = sk.distToShape(Part.Vertex(p))[0]; n += 1
                e = min(dist, abs(dist - abs(d))) if thick else abs(dist - abs(d))
                worst = max(worst, e)
                if e > 1e-4: bad += 1
    return n, bad, worst
def mc(res, src, d, npts=150, seed=7):
    rnd = random.Random(seed); bb = src.BoundBox; sk = Part.Compound(src.Faces); bad = n = 0
    for _ in range(npts):
        p = V(rnd.uniform(bb.XMin, bb.XMax), rnd.uniform(bb.YMin, bb.YMax), rnd.uniform(bb.ZMin, bb.ZMax))
        if not src.isInside(p, 1e-7, True): continue
        dist = sk.distToShape(Part.Vertex(p))[0]
        if abs(dist - abs(d)) < 1e-3: continue
        n += 1
        if res.isInside(p, 1e-7, True) != (dist > abs(d)): bad += 1
    return n, bad
ONLY = [x for x in os.environ.get("RV_ONLY", "").split(",") if x]
def run(name, vn, src, op, d, join=0, cap=None, secs=(), domc=True):
    if ONLY and not any(name == o for o in ONLY): return
    summ.write("START %s\n" % name); summ.flush()
    t0 = time.time(); res = None; exc = "-"
    try:
        if op == "off":
            res = src.makeOffsetShape(d, 1e-7, False, False, 0, join)
        else:
            res = src.makeThickness([cap], d, 1e-7, False, False, 0, join)
    except Exception as ex:
        exc = (str(ex).replace(" ", "_")[:50] or type(ex).__name__)
    ms = (time.time() - t0) * 1000
    summ.write("STEP %s kernel done ms=%d\n" % (name, ms)); summ.flush()
    if os.environ.get("RV_NOCHK"):
        summ.write("%-30s TIME ms=%d done=%d\n" % (name, ms, 0 if res is None else 1)); summ.flush(); return
    if res is None or res.isNull() or len(res.Faces) == 0:
        line = "%-30s ERR ms=%d exc=%s" % (name, ms, exc); summ.write(line + "\n"); summ.flush(); return
    valid = res.isValid()
    try:
        res.check(True); bop = "clean"
    except Exception as ex:
        msgs = [m for m in str(ex).splitlines() if m.strip().startswith("Error")]
        bop = "C0only" if msgs and all("GeomAbs_C0" in m for m in msgs) else "FAULTS"
    nsol = len(res.Solids)
    on, ob, ow = oracle(res, Part.Compound([f for f in src.Faces if cap is None or not f.isSame(cap)]), d, thick=(op != "off"), skip=cap)
    summ.write("STEP %s oracle done\n" % name); summ.flush()
    mn, mb = mc(res, src, d) if (domc and op == "off") else (0, 0)
    summ.write("STEP %s mc done\n" % name); summ.flush()
    c = canon(res, vn)
    for k, (kind, a) in enumerate(secs):
        if kind == "z":
            wires = c.slice(V(0, 0, 1), a)
        else:  # meridian at angle a (deg): rotate by -a about z, slice y=0, keep x>0 loops
            cc = c.copy(); cc.rotate(V(0, 0, 0), V(0, 0, 1), -a)
            wires = [w for w in cc.slice(V(0, 1, 0), 0.) if w.BoundBox.XMin > 0]
        dumpsec(name, k, wires)
    line = "%-30s RES valid=%s bop=%s nsol=%d nf=%d oracle=%d/%d/%.2g mc=%d/%d ms=%d" % (name, valid, bop, nsol, len(res.Faces), on, ob, ow, mn, mb, ms)
    summ.write(line + "\n"); summ.flush()
def load(n): return Part.read(D + "cases/" + n + ".brep")
def capface(s, vn, which):
    c = canon(s, vn)
    idx = min(range(len(c.Faces)), key=lambda i: c.Faces[i].CenterOfMass.z) if which == "bot" else \
          max(range(len(c.Faces)), key=lambda i: c.Faces[i].CenterOfMass.z)
    return s.Faces[idx]
VN = ("a", "n", "w")
if want("rev"):
    for vn in VN:
        s = load("rev_" + vn)
        for d in (2.0, 2.8):
            run("rev_%s_off-%g" % (vn, d), vn, s, "off", -d, secs=(("m", 0.), ("m", 73.)))
        run("rev_%s_thkbot-2" % vn, vn, s, "thk", -2.0, cap=capface(s, vn, "bot"), secs=(("m", 0.), ("m", 211.)))
    s = load("rev_a")
    run("rev_a_off-0.8_ctl", "a", s, "off", -0.8, secs=(("m", 0.),))
    run("rev_a_off-2_int", "a", s, "off", -2.0, join=2, secs=(("m", 0.),))
if want("tri"):
    for vn in VN:
        s = load("tri_" + vn)
        for d in (3.0, 4.0):
            run("tri_%s_off-%g" % (vn, d), vn, s, "off", -d, secs=(("z", 10.), ("z", 5.)))
        run("tri_%s_thktop-3" % vn, vn, s, "thk", -3.0, cap=capface(s, vn, "top"), secs=(("z", 10.),))
    s = load("tri_a")
    run("tri_a_off-1.5_ctl", "a", s, "off", -1.5, secs=(("z", 10.),))
    run("tri_a_off-3_int", "a", s, "off", -3.0, join=2, secs=(("z", 10.),))
if want("trv"):
    s = load("trv_a")
    for d in (3.0, 4.0):
        run("trv_a_off-%g" % d, "a", s, "off", -d, secs=(("z", 10.),))
if want("obl"):
    for vn in VN:
        s = load("obl_" + vn)
        for d in (2.0, 3.0):
            run("obl_%s_off-%g" % (vn, d), vn, s, "off", -d, secs=(("z", 5.), ("z", 3.5)))
    s = load("obl_a")
    run("obl_a_off-1_ctl", "a", s, "off", -1.0, secs=(("z", 5.),))
    run("obl_a_off-2_int", "a", s, "off", -2.0, join=2, secs=(("z", 5.),))
if want("bm0"):
    s = load("bm0_a")
    for d in (2.0, 2.8):
        run("bm0_a_off-%g" % d, "a", s, "off", -d)
if want("bmp"):
    for vn in VN:
        s = load("bmp_" + vn)
        for d in (2.0, 2.8):
            run("bmp_%s_off-%g" % (vn, d), vn, s, "off", -d)
    s = load("bmp_a")
    run("bmp_a_off-1_ctl", "a", s, "off", -1.0)
if want("sat"):
    import numpy as np
    for nm in ("t_bump_12_12", "sat_near", "sat_near15", "sat_near30", "sat_far", "sat_far30"):
        if ONLY and not any(o.startswith(nm) for o in ONLY): continue
        s = Part.read(("C:/dev/occt8-mig/offset-034b2/r3c/cases/" if nm.startswith("t_") else D + "cases/") + nm + ".brep")
        name = nm + "_off-2.8"
        summ.write("START %s\n" % name); summ.flush()
        t0 = time.time(); res = None; exc = "-"
        try:
            res = s.makeOffsetShape(-2.8, 1e-7, False, False, 0, 0)
        except Exception as ex:
            exc = (str(ex).replace(" ", "_")[:50] or type(ex).__name__)
        ms = (time.time() - t0) * 1000
        top = [f for f in s.Faces if type(f.Surface).__name__ == "BSplineSurface"][0]
        su = top.Surface
        isl = np.loadtxt(D + "out/%s_island.txt" % nm, ndmin=2) if os.path.exists(D + "out/%s_island.txt" % nm) else np.zeros((0, 2))
        kk = max([max(abs(su.curvature(u, v, "Max")), abs(su.curvature(u, v, "Min"))) for (u, v) in isl] or [0])
        if res is None or res.isNull() or len(res.Faces) == 0:
            summ.write("%-30s ERR ms=%d exc=%s island=%d kmax=%.4f\n" % (name, ms, exc, len(isl), kk)); summ.flush(); continue
        res.exportBrep(OUT + "/" + name + ".brep")
        valid = res.isValid()
        on, ob, ow = oracle(res, Part.Compound(s.Faces), -2.8)
        rc = Part.Compound(res.Faces); sc = Part.Compound(s.Faces)
        kept = 0; worst = 0.; n = 0
        sgn = -1. if top.Orientation == "Reversed" else 1.
        for (u, v) in isl:
            p = su.value(u, v); nn = su.normal(u, v) * sgn  # outward normal of the face in the solid
            q = p - nn * 2.8
            dr = rc.distToShape(Part.Vertex(q))[0]; ds = sc.distToShape(Part.Vertex(q))[0]
            n += 1; worst = max(worst, 2.8 - ds)
            if dr < 1e-5 and ds < 2.8 - 1e-7: kept += 1
        summ.write("%-30s RES valid=%s nf=%d oracle=%d/%d/%.2g island=%d kmax=%.4f kept_folded=%d deficit_max=%.3g ms=%d\n" % (name, valid, len(res.Faces), on, ob, ow, n, kk, kept, worst, ms))
        summ.flush()
summ.close()
