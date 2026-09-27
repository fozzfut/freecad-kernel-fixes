# p3: timings of the plane section on the ball screw; HD_CASE = axial|perp|oblique, HD_WHAT = comma list of
# face<i> (face.section(plane)) | common (shape.common(plane)) | tess (tessellate at span/1000)
import sys, os, time
sys.path.insert(0, r"C:\dev\hd-section")
import FreeCAD as App, Part
out = open(os.environ["HD_PROBE_OUT"], "w")
def P(*a):
    s = " ".join(str(x) for x in a); out.write(s + "\n"); out.flush()
from hybriddesign.ops import section as S
P("VERSION", App.Version()[:3], Part.OCC_VERSION)
sh = Part.Shape(); sh.read(r"C:\dev\occt8-mig\corpus\ballscrew_Feature014.brep")
bb = sh.BoundBox; c = bb.Center; span = bb.DiagonalLength
obl = App.Vector(0, 0.6, 0.8); obl.normalize()
cases = {"axial": (0, 0, 1), "perp": (0, 1, 0), "oblique": (obl.x, obl.y, obl.z)}
n = cases[os.environ.get("HD_CASE", "axial")]
plane = S.cutting_plane((c.x, c.y, c.z), n, span)
for what in os.environ.get("HD_WHAT", "common").split(","):
    t = time.perf_counter()
    if what.startswith("face"):
        s = sh.Faces[int(what[4:])].section(plane); r = "edges %d" % len(s.Edges)
    elif what == "common":
        s = sh.common(plane); r = "faces %d area %.4f" % (len(s.Faces), sum(f.Area for f in s.Faces))
    elif what == "tess":
        p, tr = sh.tessellate(span / 1000.0); r = "points %d tris %d" % (len(p), len(tr))
    P("T", os.environ.get("HD_CASE"), what, "%.2fs" % (time.perf_counter() - t), r)
P("DONE")
