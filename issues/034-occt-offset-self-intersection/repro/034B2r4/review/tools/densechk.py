# densechk.py - Review offset-B2 r4 (test side, error-raising controls only): for result files listed in DC_LIST
# ("<result.brep> <source.brep> <d>"), (1) dense distance control: 25 x 25 samples per face inside the trimmed face,
# |dist(p, source boundary) - |d|| <= 1e-4; (2) usability: fuse / common / cut with a box through the middle of the
# result, validity of each, and the volume identity V(A u B) + V(A n B) = V(A) + V(B), V(A - B) = V(A) - V(A n B);
# (3) the BOP check messages of the result as the user sees them in Check geometry.
import os
import FreeCAD as App, Part
V = App.Vector
OUT = os.environ["FC_OUT"]; os.makedirs(OUT, exist_ok=True)
o = open(OUT + "/dense.txt", "a")
for ln in open(os.environ["DC_LIST"]):
    f = ln.split()
    if not f or f[0].startswith("#"): continue
    rf, sf, d = f[0], f[1], abs(float(f[2]))
    if not os.path.exists(rf):
        o.write("%s MISSING\n" % os.path.basename(rf)); o.flush(); continue
    res = Part.read(rf); src = Part.read(sf); sk = Part.Compound(src.Faces)
    n = bad = 0; worst = 0.; near = 0
    for fc in res.Faces:
        u0, u1, v0, v1 = fc.ParameterRange
        for i in range(25):
            for j in range(25):
                p = fc.valueAt(u0 + (u1 - u0) * (i + 0.5) / 25, v0 + (v1 - v0) * (j + 0.5) / 25)
                if not fc.isInside(p, 1e-6, True): continue
                dist = sk.distToShape(Part.Vertex(p))[0]; n += 1
                e = abs(dist - d); worst = max(worst, e)
                if e > 1e-4: bad += 1
                if dist < d - 1e-6: near += 1
    try:
        res.check(True); msg = "clean"
    except Exception as ex:
        msg = " | ".join(sorted(set(m.strip() for m in str(ex).splitlines() if m.strip().startswith("Error"))))
    bb = res.BoundBox
    b = Part.makeBox(bb.XLength * 0.6, bb.YLength * 1.2, bb.ZLength * 1.2, V(bb.Center.x, bb.YMin - 0.1 * bb.YLength, bb.ZMin - 0.1 * bb.ZLength))
    try:
        fu = res.fuse(b); co = res.common(b); cu = res.cut(b)
        va, vb, vf, vc, vk = res.Volume, b.Volume, fu.Volume, co.Volume, cu.Volume
        e1 = abs(vf + vc - va - vb) / va; e2 = abs(vk - (va - vc)) / va
        boo = "fuse_valid=%s common_valid=%s cut_valid=%s id1=%.1e id2=%.1e" % (fu.isValid(), co.isValid(), cu.isValid(), e1, e2)
    except Exception as ex:
        boo = "BOOL-EXC %s" % str(ex)[:60]
    o.write("%-28s dense=%d/%d/%.2g closer_than_d=%d | %s | bop: %s\n" % (os.path.basename(rf)[:-5], n, bad, worst, near, boo, msg[:200]))
    o.flush()
o.close()
