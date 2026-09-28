# famsec.py - Review offset-B2 r3: independent section dumps for the implementer's family results (D0 runs).
# For every listed case: slice the INPUT solid and the RESULT solid by the same plane (mid of the eroded range),
# dump the input section edge by edge (ordered, oriented) and the result section as loops. cmpfam.py erodes the
# input section in 2D (trimmed parallel curves with round corner joins) and compares.
import os
import FreeCAD as App, Part
V = App.Vector
R = "C:/dev/occt8-mig/offset-034b2/rv3/"
LST = os.environ["FAM_LIST"]; RES = os.environ["FAM_RES"]; OUT = os.environ["FC_OUT"]
os.makedirs(OUT, exist_ok=True)
AX = {"0": V(1, 0, 0), "1": V(0, 1, 0), "2": V(0, 0, 1)}
log = open(OUT + "/famsec.txt", "w")
def edges_in_order(w):
    es = w.OrderedEdges
    out = []; last = None
    for e in es:
        p = [e.valueAt(x) for x in []]
        pts = e.discretize(QuasiDeflection=2e-8)
        if last is not None and (pts[0] - last).Length > (pts[-1] - last).Length:
            pts = pts[::-1]
        if last is None and len(es) > 1:
            nxt = es[1]
            a, b = nxt.Vertexes[0].Point, nxt.Vertexes[-1].Point
            if min((pts[0] - a).Length, (pts[0] - b).Length) < min((pts[-1] - a).Length, (pts[-1] - b).Length):
                pts = pts[::-1]
        out.append(pts); last = pts[-1]
    return out
for ln in open(LST):
    f = ln.split()
    if not f or f[0].startswith("#"): continue
    name, inp, ax, pos = f[0], f[1], f[2], float(f[3])
    try:
        src = Part.read(inp); res = Part.read(RES + "/" + name + ".brep")
    except Exception as ex:
        log.write("%s NORES %s\n" % (name, ex)); continue
    n = AX[ax]
    ws = src.slice(n, pos); wr = res.slice(n, pos)
    with open("%s/%s_in.txt" % (OUT, name), "w") as fo:
        for w in ws:
            for pts in edges_in_order(w):
                for p in pts: fo.write("%.12f %.12f %.12f\n" % (p.x, p.y, p.z))
                fo.write("EDGE\n")
            fo.write("END\n")
    with open("%s/%s_res.txt" % (OUT, name), "w") as fo:
        for w in wr:
            for p in w.discretize(QuasiDeflection=2e-8): fo.write("%.12f %.12f %.12f\n" % (p.x, p.y, p.z))
            fo.write("END\n")
    log.write("%s OK in_wires=%d res_wires=%d valid=%s\n" % (name, len(ws), len(wr), res.isValid()))
    log.flush()
log.close()
