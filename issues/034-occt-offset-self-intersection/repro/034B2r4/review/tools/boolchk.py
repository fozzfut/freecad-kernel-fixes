# boolchk.py - Review offset-B2 r4: are the lens-pass results whose faces the BOP check flags (SelfIntersect) usable in
# the next modelling step? Booleans with (i) a small box far from any lens, (ii) a box through the lens region, (iii)
# a cylinder drilled through the lens region; validity, BOP check of the boolean result, volume identities by mesh
# volumes (GProp is unreliable on these offset faces). Also: which faces are flagged (surface types).
import os
import FreeCAD as App, Part, Mesh
V = App.Vector
R = "C:/dev/occt8-mig/offset-034b2/rv4/"
o = open(os.environ["FC_OUT"] + "/boolchk.txt", "a")
def mv(s): return Mesh.Mesh(s.tessellate(0.05)).Volume if s.Faces else 0.
def chk(s):
    try:
        s.check(True); return "clean"
    except Exception as ex:
        return ",".join(sorted(set(m.split("BOPAlgo")[-1].strip() for m in str(ex).splitlines() if "BOPAlgo" in m)))
CASES = [("imp/ring_a_off-1.5", [("corner", Part.makeBox(4, 4, 30, V(-1, -1, -5))), ("ring", Part.makeBox(4, 40, 30, V(29, 0, -5))),
                                 ("drill", Part.makeCylinder(1.5, 40, V(31, 20, -5)))]),
         ("rv3m/bmp_a_off-2.8", [("corner", Part.makeBox(4, 4, 30, V(-1, -1, -5))), ("lens", Part.makeBox(3, 40, 30, V(19, 0, -5))),
                                 ("drill", Part.makeCylinder(1.2, 40, V(20, 20, -5)))]),
         ("imp/rv2_w_off-2.5", [])]
for n, tools in CASES:
    r = Part.read(R + "out/o034b2rv4-%s.brep" % n)
    bb = r.BoundBox
    flagged = []
    for i, f in enumerate(r.Faces):
        if "SelfIntersect" in chk(f):
            flagged.append("Face%d:%s" % (i + 1, type(f.Surface).__name__ + ("(" + type(f.Surface.BasisSurface).__name__ + ")" if hasattr(f.Surface, "BasisSurface") else "")))
    o.write("%s bb %s flagged %s\n" % (n, [round(x, 2) for x in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)], flagged)); o.flush()
    va = mv(r)
    for tn, t in tools:
        try:
            cu = r.cut(t); co = r.common(t)
            vk, vc, vt = mv(cu), mv(co), mv(t)
            o.write("  %-7s cut valid=%s bop=%s | common valid=%s bop=%s | V(cut)+V(common)-V(A) = %.3g (rel %.1e)\n" % (
                tn, cu.isValid(), chk(cu), co.isValid(), chk(co), vk + vc - va, (vk + vc - va) / va))
        except Exception as ex:
            o.write("  %-7s EXC %s\n" % (tn, str(ex)[:80]))
        o.flush()
o.close()
