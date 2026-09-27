# mkcorpus.py: BREP inputs for the filsweep identity sweep (lane fillet-corner). FreeCADCmd; env FC_OUT = log.
import os, math, FreeCAD as App, Part, Import
V = App.Vector
D = "C:/dev/occt8-mig/fillet-corner/sweep/in/"
os.makedirs(D, exist_ok=True)
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
def put(name, sh):
    sh.exportBrep(D + name + ".brep"); say(name, sh.ShapeType, "solids", len(sh.Solids), "faces", len(sh.Faces), "valid", sh.isValid())
C = "C:/dev/occt8-mig/corpus/"
# real parts
sh = Part.Shape(); sh.read(C + "VR6-350-new-part4.step"); put("part4", Part.Compound(sh.Solids))
for fn in ("Top", "hicmos_peltier", "owner_oring"):
    d = App.openDocument(C + fn + ".FCStd")
    sols = []
    for ob in d.Objects:
        if ob.TypeId == "PartDesign::Body" and ob.Shape.Solids: sols += ob.Shape.Solids
    if not sols:
        for ob in d.Objects:
            if hasattr(ob, "Shape") and ob.Shape.Solids and not ob.InList: sols += ob.Shape.Solids
    put(fn, Part.Compound(sols)); App.closeDocument(d.Name)
# synthetic: box, L-bracket, box+boss, box with pocket, block on plate with CONVEX top chamfers, stepped block
put("box", Part.makeBox(20, 20, 20))
L = Part.makeBox(40, 10, 5).fuse(Part.makeBox(10, 10, 30)).removeSplitter(); put("lbracket", Part.Solid(L.Shells[0]))
bb = Part.makeBox(40, 40, 10).fuse(Part.makeCylinder(8, 15, V(20, 20, 10))).removeSplitter(); put("boss", Part.Solid(bb.Shells[0]))
pk = Part.makeBox(40, 40, 10).cut(Part.makeBox(20, 20, 6, V(10, 10, 4))); put("pocket", pk)
blk = Part.makeBox(30, 30, 20)
top = [e for e in blk.Edges if abs(e.BoundBox.ZMin - 20) < 1e-9 and abs(e.BoundBox.ZMax - 20) < 1e-9]
put("box_topchamfer", blk.makeChamfer(2.0, top))
st = Part.makeBox(40, 40, 5).fuse(Part.makeBox(30, 30, 10, V(5, 5, 5))).fuse(Part.makeBox(20, 20, 10, V(10, 10, 15))).removeSplitter()
st = Part.Solid(st.Shells[0])
conc = [e for e in st.Edges if type(e.Curve).__name__ == "Line" and abs(e.BoundBox.ZLength) < 1e-9 and e.BoundBox.ZMin in (5.0, 15.0)
        and 5 < e.CenterOfMass.x < 35 and 5 < e.CenterOfMass.y < 35 and not (e.BoundBox.ZMin == 5.0 and not (5.01 < e.CenterOfMass.x < 34.99 or 5.01 < e.CenterOfMass.y < 34.99))]
try:
    put("stepped_chamfer", st.makeChamfer(1.0, [e for e in conc if (e.BoundBox.ZMin == 15.0) or True][:8]))
except Exception as ex:
    say("stepped_chamfer FAIL", ex)
put("stepped", st)
o.close()
