# gen_r2.py - export the round-2 class members (review rvb2.py geometry) as BREP + independent references
# (primitives + Booleans only) + a case list for k.sh / b2h (tag file op t join remove ref refshape)
import os, math, FreeCAD as App, Part
V = App.Vector
D = "C:/dev/occt8-mig/offset-034b2/r2/cases/"
L_ = open(D + "cases.txt", "w")
def box(x0, y0, z0, x1, y1, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
def is_vert(e, x, y):
    b = e.BoundBox
    return b.XLength < 1e-7 and b.YLength < 1e-7 and b.ZLength > 1e-3 and abs(b.XMin - x) < 1e-7 and abs(b.YMin - y) < 1e-7
ROT = App.Placement(V(7, -3, 11), App.Rotation(V(1, 2, 3), 37)).toMatrix()
def rot(sh):
    c = sh.copy(); c.transformShape(ROT, True); return c
ZR = App.Placement(ROT).Rotation.multVec(V(0, 0, 1))
def save(sh, name):
    sh.exportBrep(D + name + ".brep"); return name + ".brep"
def fidx(s, f):
    return [i for i, g in enumerate(s.Faces) if g.isSame(f)][0] + 1
def top_index(s, zax):
    fs = s.Faces; f = max(fs, key=lambda f: f.CenterOfMass.dot(zax)); return fs.index(f) + 1
def case(tag, f, op, t, join, rem, ref=None):
    rv = "0"; rs = "-"
    if ref is not None:
        rv = "%.9f" % ref.Volume; rs = save(ref, "ref_" + tag)
    L_.write("%s %s %s %g %s %s %s %s\n" % (tag, f, op, t, join, rem, rv, rs))
def lfoot_erosion(t, z0, z1):
    h = z1 - z0
    r1 = box(t, t, z0, 20 - t, 6 - t, z1); r2 = box(t, t, z0, 6 - t, 16 - t, z1)
    sq = box(6 - t, 6 - t, z0, 6, 6, z1).cut(Part.makeCylinder(t, h + 2, V(6, 6, z0 - 1)))
    return r1.fuse([r2, sq]).removeSplitter()
H = 10.
L0 = box(0, 0, 0, 20, 6, H).fuse(box(0, 0, 0, 6, 16, H)).removeSplitter()
conv = [(0, 0), (20, 0), (20, 6), (6, 16), (0, 16)]
k = L0.makeFillet(1.0, [e for e in L0.Edges if any(is_vert(e, x, y) for (x, y) in conv)])
for vn, s in (("a", k), ("n", k.toNurbs()), ("w", rot(k))):
    f = save(s, "lfoot_r1_" + vn)
    zax = ZR if vn == "w" else V(0, 0, 1)
    for d in (1.5, 2.5):
        ref = lfoot_erosion(d, d, H - d); ref = rot(ref) if vn == "w" else ref
        case("lfoot_d%g_%s_off" % (d, vn), f, "offset", -d, "arc", "none", ref)
        refT = k.cut(lfoot_erosion(d, d, H + 1)); refT = rot(refT) if vn == "w" else refT
        case("lfoot_t%g_%s_thk" % (d, vn), f, "thick", -d, "arc", str(top_index(s, zax)), refT)
    case("lfoot_t0.5_%s_thkCTL" % vn, f, "thick", -0.5, "arc", str(top_index(s, zax)), None)
f = save(L0, "lfoot_sharp")
case("lfoot_sharp_t1.5_thk", f, "thick", -1.5, "arc", str(top_index(L0, V(0, 0, 1))), L0.cut(lfoot_erosion(1.5, 1.5, H + 1)))
Lx, W = 20., 14.
for (d, r1, r2) in ((1.5, 1., 3.), (2.5, 1., 3.), (1.0, 1., 2.)):
    b = box(0, 0, 0, Lx, W, H)
    kk = b.makeFillet(r1, [e for e in b.Edges if is_vert(e, 0, 0) or is_vert(e, Lx, W)])
    kk = kk.makeFillet(r2, [e for e in kk.Edges if is_vert(e, Lx, 0) or is_vert(e, 0, W)])
    rb = box(d, d, d, Lx - d, W - d, H - d)
    if r2 > d: rb = rb.makeFillet(r2 - d, [e for e in rb.Edges if is_vert(e, Lx - d, d) or is_vert(e, d, W - d)])
    cav = box(d, d, d, Lx - d, W - d, H + 1)
    if r2 > d: cav = cav.makeFillet(r2 - d, [e for e in cav.Edges if is_vert(e, Lx - d, d) or is_vert(e, d, W - d)])
    for vn, s in (("a", kk), ("n", kk.toNurbs()), ("w", rot(kk))):
        f = save(s, "mix_r%g_%g_%s" % (r1, r2, vn))
        zax = ZR if vn == "w" else V(0, 0, 1)
        case("mix_r%g_%g_d%g_%s_off" % (r1, r2, d, vn), f, "offset", -d, "arc", "none", rot(rb) if vn == "w" else rb)
        refT = kk.cut(cav)
        case("mix_r%g_%g_t%g_%s_thk" % (r1, r2, d, vn), f, "thick", -d, "arc", str(top_index(s, zax)), rot(refT) if vn == "w" else refT)
# misc: vbox r1 d1.5 Intersection join, top+front, side
b = box(0, 0, 0, Lx, W, H)
k = b.makeFillet(1., [e for e in b.Edges if e.BoundBox.ZLength > 1e-3 and e.BoundBox.XLength < 1e-7 and e.BoundBox.YLength < 1e-7])
f = save(k, "vbox_r1_a"); d = 1.5
case("vbox_d1.5_off_INT", f, "offset", -d, "int", "none", box(d, d, d, Lx - d, W - d, H - d))
ti = top_index(k, V(0, 0, 1))
case("vbox_t1.5_thk_INT", f, "thick", -d, "int", str(ti), k.cut(box(d, d, d, Lx - d, W - d, H + 1)))
fr = min([ff for ff in k.Faces if ff.Surface.__class__.__name__ == "Plane"], key=lambda ff: ff.CenterOfMass.y)
case("vbox_t1.5_thk_TOPFRONT", f, "thick", -d, "arc", "%d,%d" % (ti, fidx(k, fr)), k.cut(box(d, -1, d, Lx - d, W - d, H + 1)))
sd = min([ff for ff in k.Faces if ff.Surface.__class__.__name__ == "Plane"], key=lambda ff: ff.CenterOfMass.x)
case("vbox_t1.5_thk_SIDE", f, "thick", -d, "arc", str(fidx(k, sd)), k.cut(box(-1, d, d, Lx - d, W - d, H - d)))
case("vbox_t1.5_thk_TOP", f, "thick", -d, "arc", str(ti), k.cut(box(d, d, d, Lx - d, W - d, H + 1)))
L_.close()
print("GEN-DONE")
