import FreeCAD as App, Part
D = "C:/dev/occt8-mig/offset-034b2/rv3/"
o = open(D + "out/faults.txt", "w")
def chk(tag, s):
    try:
        s.check(True); o.write("%s clean\n" % tag)
    except Exception as ex:
        msgs = [m.strip() for m in str(ex).splitlines() if m.strip()]
        o.write("%s FAULTS %d: %s\n" % (tag, len(msgs), " | ".join(msgs[:6])))
    o.flush()
for n in ("rev_a", "tri_a", "tri_n", "obl_a", "bmp_a"):
    s = Part.read(D + "cases/" + n + ".brep"); chk("input " + n, s)
s = Part.read(D + "cases/tri_a.brep"); r = s.makeOffsetShape(-1.5, 1e-7, False, False, 0, 0); chk("tri_a off-1.5", r)
s = Part.read(D + "cases/obl_a.brep"); r = s.makeOffsetShape(-1.0, 1e-7, False, False, 0, 0); chk("obl_a off-1", r)
o.close()
