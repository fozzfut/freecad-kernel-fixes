# dumpc.py - dump the result BREP of conedn offset +1 Arc (unlocated) and input location report
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ["RV_OUT"]
import FreeCAD as App, Part
os.environ["RV_OUT"] = OUT + ".sub"; os.environ["RV_ONLY"] = "^zzz$"
import rvloc as R
base = R.m_conedn()
rep = []
for sub in ("Faces", "Edges", "Vertexes", "Shells"):
    for i, x in enumerate(getattr(base, sub)):
        if not x.Placement.isIdentity():
            rep.append("%s%d located %s" % (sub, i, x.Placement))
open(OUT + ".inputloc", "w").write("\n".join(rep) + "\nroot=%s\n" % base.Placement)
for k in range(2):
    r = base.copy().makeOffsetShape(1.0, 1e-7, join=0)
    open(OUT + ".%d.brep" % k, "w").write(r.exportBrepToString())
