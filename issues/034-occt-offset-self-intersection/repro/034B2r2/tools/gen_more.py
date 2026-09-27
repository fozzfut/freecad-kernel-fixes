# gen_more.py - extra class members for round 2 (not in the review): removed faces tangent to the vanishing set,
# sets reaching two removed faces, bottom removed, NURBS + rotated twins; references from primitives + Booleans
import FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/r2/cases/"
L_ = open(D + "more.txt", "w")
def box(x0, y0, z0, x1, y1, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
def is_vert(e, x, y):
    b = e.BoundBox
    return b.XLength < 1e-7 and b.YLength < 1e-7 and b.ZLength > 1e-3 and abs(b.XMin - x) < 1e-7 and abs(b.YMin - y) < 1e-7
ROT = App.Placement(V(7, -3, 11), App.Rotation(V(1, 2, 3), 37)).toMatrix()
def rot(sh):
    c = sh.copy(); c.transformShape(ROT, True); return c
def fidx(s, f): return [i for i, g in enumerate(s.Faces) if g.isSame(f)][0] + 1
def save(sh, name): sh.exportBrep(D + name + ".brep"); return name + ".brep"
def case(tag, f, op, t, join, rem, ref):
    rs = save(ref, "ref_" + tag) if ref is not None else "-"
    L_.write("%s %s %s %g %s %s %s %s\n" % (tag, f, op, t, join, rem, ("%.9f" % ref.Volume) if ref is not None else "0", rs))
def pick(s, key):  # face index by a key on the (un-rotated) twin
    return key(s)
H = 10.
L0 = box(0, 0, 0, 20, 6, H).fuse(box(0, 0, 0, 6, 16, H)).removeSplitter()
conv = [(0, 0), (20, 0), (20, 6), (6, 16), (0, 16)]
k = L0.makeFillet(1.0, [e for e in L0.Edges if any(is_vert(e, x, y) for (x, y) in conv)])
def cav_L(t, y0, z0, z1):
    r1 = box(t, y0, z0, 20 - t, 6 - t, z1); r2 = box(t, y0, z0, 6 - t, 16 - t, z1)
    sq = box(6 - t, 6 - t, z0, 6, 6, z1).cut(Part.makeCylinder(t, z1 - z0 + 2, V(6, 6, z0 - 1)))
    return r1.fuse([r2, sq]).removeSplitter()
planes = lambda s: [f for f in s.Faces if f.Surface.__class__.__name__ in ("Plane",) or (f.Surface.__class__.__name__ == "BSplineSurface" and f.Area > 1 and abs(f.normalAt(0.5, 0.5).z) > 0.99)]
for vn, s in (("a", k), ("n", k.toNurbs())):
    f = save(s, "lfm_r1_" + vn)
    top = max(s.Faces, key=lambda f: f.CenterOfMass.z); bot = min(s.Faces, key=lambda f: f.CenterOfMass.z)
    front = [g for g in s.Faces if abs(g.CenterOfMass.y) < 1e-6 and g.Area > 10][0]
    for t in (1.5, 2.5):
        case("lf_front_t%g_%s" % (t, vn), f, "thick", -t, "arc", str(fidx(s, front)), k.cut(cav_L(t, -1, t, H - t)))
        case("lf_bot_t%g_%s" % (t, vn), f, "thick", -t, "arc", str(fidx(s, bot)), k.cut(cav_L(t, t, -1, H - t)))
        case("lf_topfront_t%g_%s" % (t, vn), f, "thick", -t, "arc", "%d,%d" % (fidx(s, top), fidx(s, front)), k.cut(cav_L(t, -1, t, H + 1)))
kr = rot(k); f = save(kr, "lfm_r1_w")
topw = max(kr.Faces, key=lambda g: g.CenterOfMass.dot(App.Placement(ROT).Rotation.multVec(V(0, 0, 1))))
frontw = [g for g in kr.Faces if abs(g.CenterOfMass.dot(App.Placement(ROT).Rotation.multVec(V(0, 1, 0))) - V(7, -3, 11).dot(App.Placement(ROT).Rotation.multVec(V(0, 1, 0)))) < 1e-6 and g.Area > 10][0]
case("lf_topfront_t1.5_w", f, "thick", -1.5, "arc", "%d,%d" % (fidx(kr, topw), fidx(kr, frontw)), rot(k.cut(cav_L(1.5, -1, 1.5, H + 1))))
# vbox with r = 2 fillets, top + front removed, t 2.5 / 3 (d > r), and t = 2 (d = r)
Lx, W = 20., 14.
b = box(0, 0, 0, Lx, W, H)
k2 = b.makeFillet(2., [e for e in b.Edges if e.BoundBox.ZLength > 1e-3 and e.BoundBox.XLength < 1e-7 and e.BoundBox.YLength < 1e-7])
for vn, s in (("a", k2), ("n", k2.toNurbs())):
    f = save(s, "vb2_" + vn)
    top = max(s.Faces, key=lambda g: g.CenterOfMass.z)
    front = [g for g in s.Faces if abs(g.CenterOfMass.y) < 1e-6 and g.Area > 10][0]
    for t in (2.5, 3.0):
        case("vb2_topfront_t%g_%s" % (t, vn), f, "thick", -t, "arc", "%d,%d" % (fidx(s, top), fidx(s, front)), k2.cut(box(t, -1, t, Lx - t, W - t, H + 1)))
        case("vb2_front_t%g_%s" % (t, vn), f, "thick", -t, "arc", str(fidx(s, front)), k2.cut(box(t, -1, t, Lx - t, W - t, H - t)))
    # d < r control: the fillets survive (radius r - t), front + top removed
    cv = box(1, -1, 1, Lx - 1, W - 1, H + 1); cv = cv.makeFillet(1., [e for e in cv.Edges if is_vert(e, Lx - 1, W - 1) or is_vert(e, 1, W - 1)])
    case("vb2_topfront_t1_%s_CTL" % vn, f, "thick", -1.0, "arc", "%d,%d" % (fidx(s, top), fidx(s, front)), k2.cut(cv))
L_.close(); print("GEN-DONE")
