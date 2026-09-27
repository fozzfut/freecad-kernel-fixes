# qual.py: corner quality of fillet/chamfer results, stock vs patched (lane fillet-corner, issue 031).
# env FC_PAIRS = file with lines "<key>\t<stock.brep>\t<patched.brep>", FC_OUT = log.
# Per result: validity, BRepCheck/BOP check, max edge tolerance, the corner faces (BSpline = GeomPlate patches) and,
# along every edge of such a face: max normal angle to a neighbouring BLEND face (G1 target 0) and to a PLANE
# (crease; > 90 deg = the patch folds over), plus min face area (slivers).
import os, sys, math
sys.path.insert(0, "C:/dev/occt8-mig/fillet-corner/probe")
import FreeCAD as App, Part, geo
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
say("VERSION", App.Version()[:4], "OCC", Part.OCC_VERSION)

def metrics(path):
    s = Part.Shape(); s.read(path)
    ef = geo.edge_faces(s)
    plates = [i for i, f in enumerate(s.Faces) if type(f.Surface).__name__ == "BSplineSurface"]
    g1 = 0.0; crease = 0.0; fold = 0
    for j, fl in ef.items():
        if len(fl) != 2 or not (fl[0] in plates or fl[1] in plates): continue
        other = fl[1] if fl[0] in plates else fl[0]
        try: ang = geo.edge_angles(s, j, fl, 11)
        except Exception: continue
        inner = ang[1:-1]
        if type(s.Faces[other].Surface).__name__ == "Plane":
            crease = max(crease, max(inner))
            fold += sum(1 for a in inner if a > 90.0)
        else:
            g1 = max(g1, max(inner))
    ck = geo.check(s)
    return dict(valid=s.isValid(), check="OK" if ck == "OK" else "FAIL", maxtol=max(e.Tolerance for e in s.Edges),
                plates=len(plates), g1=g1, crease=crease, fold=fold,
                minarea=min(f.Area for f in s.Faces), vol=s.Volume)

def fmt(m):
    return "valid=%d check=%s maxtol=%.1e plates=%d g1max=%.2f crease=%.1f folds=%d minarea=%.2e" % (
        m["valid"], m["check"], m["maxtol"], m["plates"], m["g1"], m["crease"], m["fold"], m["minarea"])

tot = {"better": 0, "worse": 0, "same": 0}
for line in open(os.environ["FC_PAIRS"]):
    if not line.strip(): continue
    key, a, b = line.rstrip("\n").split("\t")
    ma, mb = metrics(a), metrics(b)
    # verdict: validity/check first, then folds, then G1 break, then tolerance
    def score(m): return (m["valid"] and m["check"] == "OK", -m["fold"], -round(m["g1"], 1), -m["maxtol"])
    v = "same"
    if score(mb) > score(ma): v = "better"
    elif score(mb) < score(ma): v = "worse"
    tot[v] += 1
    say("CASE", key)
    say("   stock  ", fmt(ma), "vol %.6f" % ma["vol"])
    say("   p031   ", fmt(mb), "vol %.6f" % mb["vol"], "->", v.upper())
say("TOTAL", tot)
o.close()
