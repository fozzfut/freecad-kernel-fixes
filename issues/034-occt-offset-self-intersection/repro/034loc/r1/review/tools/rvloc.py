# rvloc.py - Review R-034-loc r1: independent oracle (FreeCAD Part API, not the lane's C++ harness).
# Class: offset / thickness of an input carrying a TopLoc_Location == the result of its geometry-transformed twin.
# NEW members (not in the lane's loc034b/fcloc): apex-DOWN cone (MinApex branch), spindle "lemon" (torus with 2
# poles), prolate spheroid of revolution (Geom_SurfaceOfRevolution of an ellipse arc, 2 poles), capsule thick
# (removed plane under a hemisphere, analytic volume), sphere with a side hole thick (removed curved wall, poles kept),
# FreeCAD ellipsoid (non-uniform BSpline with poles), second-generation offset (Geom_OffsetSurface faces + poles),
# open single spherical face (open shell offset), rotation about the pole axis (pole maps to itself).
# Variants: none (unlocated), geo (transformed copy, geometry baked), loc (root location), nest (shell location
# inside a located solid; twin = geo by the composed matrix). Transforms: T1 moderate, TF far, TT pure translation,
# TZ rotation about Z only.
# Output lines: RV <member> <op> <T> <variant> <grade> ...   Env: RV_OUT, RV_ONLY (regex on member name).
import os, re, time, math, traceback
import FreeCAD as App, Part
OUT = open(os.environ.get("RV_OUT", "rvloc.txt"), "w")
ONLY = os.environ.get("RV_ONLY", "")
V = App.Vector

TR = {
    "T1": App.Placement(V(13.1, -7.3, 21.9), App.Rotation(V(1, 2, 3), 47)),
    "TF": App.Placement(V(3.1e4, -1.7e4, 9.3e3), App.Rotation(V(-0.4, 0.7, 0.2), 133)),
    "TT": App.Placement(V(250.0, -40.0, 75.0), App.Rotation()),
    "TZ": App.Placement(V(0, 0, 0), App.Rotation(V(0, 0, 1), 37)),
}
PB = App.Placement(V(-3.3, 5.1, 2.2), App.Rotation(V(0.2, -1, 0.5), 71))  # inner (shell) location for "nest"


def solid1(s):
    return s.Solids[0] if s.ShapeType != "Solid" else s


def m_conedn():
    return Part.makeCone(0, 10, 15)  # apex at the BOTTOM (degenerated edge at vmin)


def m_lemon():
    # circle through (0,0,-10), (6,0,0), (0,0,10): centre (-16/3,0,0), r = 34/3 -> revolved = spindle torus part
    arc = Part.Arc(V(0, 0, -10), V(6, 0, 0), V(0, 0, 10)).toShape()
    ax = Part.makeLine(V(0, 0, 10), V(0, 0, -10))
    f = Part.Face(Part.Wire([arc, ax]))
    return solid1(f.revolve(V(0, 0, 0), V(0, 0, 1), 360))


def m_spheroid():
    e = Part.Ellipse(V(0, 0, 0), 12, 7)  # centre, major, minor in XY
    e.rotate(App.Placement(V(0, 0, 0), App.Rotation(V(1, 0, 0), 90)))  # into XZ plane: major along X
    e.rotate(App.Placement(V(0, 0, 0), App.Rotation(V(0, 1, 0), 90)))  # major along Z
    a = Part.ArcOfEllipse(e, 0.0, math.pi).toShape()
    p0, p1 = a.Vertexes[0].Point, a.Vertexes[-1].Point
    ax = Part.makeLine(p1, p0)
    f = Part.Face(Part.Wire([a, ax]))
    return solid1(f.revolve(V(0, 0, 0), V(0, 0, 1), 360))


def m_capsule():
    c = Part.makeCylinder(6, 10)
    s = Part.makeSphere(6, V(0, 0, 10))
    return solid1(c.fuse(s).removeSplitter())


def m_sphx():
    s = Part.makeSphere(10)
    h = Part.makeCylinder(3, 30, V(-15, 0, 0), V(1, 0, 0))
    return solid1(s.cut(h))


def m_ellipsoid():
    s = Part.makeSphere(8)
    m = App.Matrix(); m.scale(1.0, 0.7, 1.4)
    return solid1(s.transformGeometry(m))


def m_offoff():
    return solid1(m_ellipsoid().makeOffsetShape(0.8, 1e-7, join=0))


def m_spface():
    return Part.makeSphere(10, V(0, 0, 0), V(0, 0, 1), 0, 90).Faces[0]  # dome face alone (pole + open rim)


def face_idx(sh, kind):
    fs = sh.Faces
    if kind == "top":
        return max(range(len(fs)), key=lambda i: fs[i].CenterOfMass.z if fs[i].Surface.__class__.__name__ == "Plane" else -1e9)
    if kind == "bot":
        return min(range(len(fs)), key=lambda i: fs[i].CenterOfMass.z if fs[i].Surface.__class__.__name__ == "Plane" else 1e9)
    if kind == "cyl":
        return [i for i in range(len(fs)) if fs[i].Surface.__class__.__name__ == "Cylinder"][0]
    raise ValueError(kind)


# (name, builder, op, value, join, rmface, transforms)
CASES = []
def add(n, b, op, t, j, rm, trs):
    CASES.append((n, b, op, t, j, rm, trs))

add("conedn", m_conedn, "off", 1.0, 2, None, ["T1", "TT"])
add("conedn", m_conedn, "off", 1.0, 0, None, ["T1"])
add("conedn", m_conedn, "off", -0.5, 2, None, ["T1"])
add("conedn", m_conedn, "thk", -1.0, 2, "top", ["T1", "TF"])
add("conedn", m_conedn, "thk", -1.0, 0, "top", ["T1"])
add("lemon", m_lemon, "off", 1.0, 0, None, ["T1", "TF"])
add("lemon", m_lemon, "off", -0.5, 2, None, ["T1"])
add("spheroid", m_spheroid, "off", 1.0, 0, None, ["T1", "TF", "TZ"])
add("spheroid", m_spheroid, "off", -1.0, 2, None, ["T1"])
add("capsule", m_capsule, "thk", -1.0, 0, "bot", ["T1", "TF", "TT"])
add("capsule", m_capsule, "thk", -1.0, 2, "bot", ["T1"])
add("capsule", m_capsule, "off", 1.0, 0, None, ["T1"])
add("sphx", m_sphx, "thk", -1.0, 0, "cyl", ["T1", "TF"])
add("sphx", m_sphx, "off", 1.0, 2, None, ["T1"])
add("ellipsoid", m_ellipsoid, "off", 1.0, 0, None, ["T1", "TZ"])
add("ellipsoid", m_ellipsoid, "off", -0.8, 2, None, ["T1"])
add("offoff", m_offoff, "off", 0.5, 0, None, ["T1"])
add("spface", m_spface, "off", 1.0, 0, None, ["T1", "TF"])
add("spface", m_spface, "off", -1.0, 2, None, ["T1"])


def variant(base, var, T):
    if var == "none":
        return base.copy(), App.Placement()
    if var == "geo":
        return base.transformed(T.toMatrix(), True), T  # copy=True: geometry baked, no location
    if var == "loc":
        s = base.copy(); s.Placement = T; return s, T
    if var == "nest":
        comp = T.multiply(PB.inverse())  # T = comp * PB
        if base.ShapeType == "Face":
            f = base.copy(); f.Placement = PB
            s = Part.Shell([f])
        else:
            sh = base.Shells[0].copy(); sh.Placement = PB
            s = Part.Solid(sh)
        s.Placement = comp
        return s, T
    if var == "geon":  # geometry twin of nest with the composed matrix
        comp = T.multiply(PB.inverse())
        return base.transformed(comp.multiply(PB).toMatrix(), True), T
    raise ValueError(var)


def locinfo(s):
    root = not s.Placement.isIdentity()
    sub = any(not x.Placement.isIdentity() for x in (s.Shells if s.ShapeType == "Solid" else []))
    return "%d%d" % (root, sub)


def fmt(x):
    return "%.10g" % x


def run(base, name, op, t, j, rm, tn, var):
    T = TR[tn]
    s, Tw = variant(base, var, T)
    t0 = time.perf_counter()
    try:
        if op == "off":
            r = s.makeOffsetShape(t, 1e-7, inter=False, self_inter=False, offsetMode=0, join=j, fill=False)
        else:
            i = face_idx(base, rm)
            r = s.makeThickness([s.Faces[i]], t, 1e-7, False, False, 0, j)
        ms = (time.perf_counter() - t0) * 1e3
        if r.isNull():
            return "ERR null ms=%.1f" % ms
        v = r.Volume if r.Solids else 0.0
        a = r.Area
        c = r.Solids[0].CenterOfMass if r.Solids else r.Faces[0].CenterOfMass if r.Faces else V()
        bb = r.BoundBox
        # world -> local frame of the base (undo the transform) so every variant is comparable to "none" too
        cl = Tw.inverse().multVec(c)
        return "OK valid=%d ns=%d nf=%d vol=%s area=%s c=%s,%s,%s cl=%s,%s,%s diag=%s ms=%.1f" % (
            r.isValid(), len(r.Solids), len(r.Faces), fmt(v), fmt(a), fmt(c.x), fmt(c.y), fmt(c.z),
            fmt(cl.x), fmt(cl.y), fmt(cl.z), fmt(bb.DiagonalLength), ms)
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1e3
        msg = re.sub(r"\s+", "_", str(e))[:80] or e.__class__.__name__
        return "ERR %s ms=%.1f" % (msg, ms)


for (n, b, op, t, j, rm, trs) in CASES:
    if ONLY and not re.search(ONLY, n):
        continue
    try:
        base = b()
    except Exception:
        OUT.write("RV %s BUILD-FAILED %s\n" % (n, traceback.format_exc().splitlines()[-1])); OUT.flush(); continue
    kinds = ",".join(sorted(set(f.Surface.__class__.__name__ for f in base.Faces)))
    for tn in trs:
        for var in ("none", "geo", "loc", "nest", "geon"):
            s_info = ""
            if var in ("loc", "nest"):
                s_info = " li=" + locinfo(variant(base, var, TR[tn])[0])
            res = run(base, n, op, t, j, rm, tn, var)
            OUT.write("RV %s %s%g j%d %s %s%s %s kinds=%s\n" % (n, op, t, j, tn, var, s_info, res, kinds))
            OUT.flush()
OUT.write("RV-DONE\n"); OUT.close()
