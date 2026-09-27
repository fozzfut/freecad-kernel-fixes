# owner.py: the owner's document (copy) rebuilt headless; env FC_TKFILLET = full path of a TKFillet.dll to load
# BEFORE Part (the loader then reuses it for every later "TKFillet.dll"), FC_TAG = name for outputs, FC_OUT = log.
# Recomputes the whole Body (touch every feature), reports the HD fillet and the corner, exports the BREP and saves
# the rebuilt document under out/owner_<tag>.FCStd.
import os, sys, ctypes
pre = os.environ.get("FC_TKFILLET")
if pre:
    ctypes.WinDLL(pre)
sys.path.insert(0, "C:/dev/occt8-mig/fillet-corner/probe")
import FreeCAD as App, Part, geo
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
k = ctypes.WinDLL("kernel32"); buf = ctypes.create_unicode_buffer(512)
k.GetModuleHandleW.restype = ctypes.c_void_p
h = k.GetModuleHandleW("TKFillet.dll"); k.GetModuleFileNameW(ctypes.c_void_p(h), buf, 512)
HD = "C:/dev/occt8-mig/fillet-corner/home-w/Mod/HybridDesign"
if HD not in sys.path: sys.path.insert(0, HD)
import hybriddesign.ops.fillet_feature  # the document's HD fillet proxy (restore blocks imports it has not seen)
say("VERSION", App.Version()[:4], "OCC", Part.OCC_VERSION, "TKFillet", buf.value)
TAG = os.environ.get("FC_TAG", "x")
d = App.openDocument("C:/dev/occt8-mig/fillet-corner/files/cube_chamfer_fillet.FCStd")
f = d.getObject("Fillet")
say("FILLET proxy", type(f.Proxy).__name__ if f.Proxy else None, "HDKind", getattr(f, "HDKind", None))
for ob in d.getObject("Body").Group:
    ob.touch()
d.recompute()
for n in ("Pad", "Pocket", "Chamfer", "Fillet"):
    ob = d.getObject(n)
    say("STATE", n, ob.State, "faces", len(ob.Shape.Faces), "vol %.6f" % ob.Shape.Volume, "valid", ob.Shape.isValid())
sh = f.Shape
if sh.ShapeType == "Compound" and len(sh.Solids) == 1: sh = sh.Solids[0]
sh.exportBrep("C:/dev/occt8-mig/fillet-corner/out/owner_%s.brep" % TAG)
FB = App.BoundBox(27.5, 27.7, 1.5, 32, 32.3, 5.5)
geo.report(sh, say, "FILLET-" + TAG, focus_box=FB)
d.saveAs("C:/dev/occt8-mig/fillet-corner/out/owner_%s.FCStd" % TAG)
say("SAVED")
o.close()
