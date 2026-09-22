"""Test documents built inside FreeCAD. build(name, out_dir) -> path of a saved FCStd.

fixture:pad is small and is built into the run directory each time. fixture:holes1024 is built once into
bench/files/fixture_holes1024-<md5 of this file, 10 hex>.FCStd (tools/build_fixture.sh) and every run opens that same
file, so stock and patched runs open the identical document, as with the owner's files. Why (measured 22.09.2026):
- in the GUI every recompute of the plate meshes the top face with its 1025 wires: 75-82 s per recompute in
  FreeCAD.exe against 4-5 s in FreeCADCmd (runs/t3-gprobe/gprobe.json, runs/t3-probe/probe.json); built inside the
  timed run it took 287 of the run's 600 s (runs/t3-holes, first attempt) and left no time for the fillet edits;
- it must be built in the GUI (FreeCAD.exe, offscreen): a file saved by FreeCADCmd has no GuiDocument.xml and opens
  with every object hidden - 0 triangles drawn and a 4 s "edit" that meshes nothing (runs/t3-vprobe/vprobe.json).
If the file is missing, build() makes it (inside a GUI run too), which costs that run the build time."""
import hashlib
import json
import os

import FreeCAD as App


def build(name, out_dir):
    if name == "pad":
        return _pad(out_dir)
    if name == "holes1024":
        return _cached("holes1024", lambda d: _holes(d, 32))
    raise ValueError("unknown fixture " + name)


def cache_path(name):
    """bench/files/fixture_<name>-<key>.FCStd; the key is the md5 of this file, so any change to a fixture's code
    builds a new file and an old one is never opened by mistake."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.abspath(__file__), "rb") as f:
        key = hashlib.md5(f.read()).hexdigest()[:10]
    return os.path.join(os.path.dirname(here), "files", "fixture_%s-%s.FCStd" % (name, key))


def _cached(name, make):
    path = cache_path(name)
    if os.path.isfile(path):
        return path
    if not App.GuiUp:
        raise RuntimeError("fixture %s must be built in FreeCAD.exe (offscreen), not FreeCADCmd: without "
                           "GuiDocument.xml every object opens hidden (tools/build_fixture.sh)" % name)
    tmp = path + ".building-%d" % os.getpid()
    os.makedirs(tmp, exist_ok=True)
    built = make(tmp)
    os.replace(built, path)                     # atomic: a concurrent run sees the whole file or none
    with open(path, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    info = {"fixture": name, "file": os.path.basename(path), "freecad": ".".join(App.Version()[:3]),
            "gui": bool(App.GuiUp), "md5": md5}
    with open(path + ".json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    os.rmdir(tmp)
    return path


def _pad(out_dir):
    import Part
    import Sketcher
    d = App.newDocument("BenchPad")
    body = d.addObject("PartDesign::Body", "Body")
    sk = body.newObject("Sketcher::SketchObject", "Sketch")
    pts = [App.Vector(0, 0, 0), App.Vector(40, 0, 0), App.Vector(40, 25, 0), App.Vector(0, 25, 0)]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sk
    pad.Length = 10
    d.recompute()
    path = os.path.join(out_dir, "fixture_pad.FCStd")
    d.saveAs(path)
    App.closeDocument(d.Name)
    return path


def _holes(out_dir, n):
    """A 200 x 200 x 10 plate with n x n through holes (d 3) - the top face has n*n inner wires, the case where
    BRepCheck_Face classifies wires pairwise (spec section 8b) - as the BaseFeature of a PartDesign Body, and a
    PartDesign::Fillet R0.5 on the top edge of one hole."""
    import Part
    d = App.newDocument("BenchHoles")
    plate = Part.makeBox(200, 200, 10)
    step = 200.0 / n
    tools = [Part.makeCylinder(1.5, 30, App.Vector(step * (i + 0.5), step * (j + 0.5), -10))
             for i in range(n) for j in range(n)]
    shape = plate.cut(Part.makeCompound(tools))
    base = d.addObject("Part::Feature", "HolesPlate")
    # PartDesign_Body on a selected solid hides it (CommandBody.cpp: hideViewProvider(baseFeature)); a visible copy
    # would make open mesh the plate twice (runs/t3-holes: open_s 162 s, peak working set 7.1 GB)
    base.Visibility = False
    base.Shape = shape
    body = d.addObject("PartDesign::Body", "Body")
    body.BaseFeature = base
    d.recompute()
    # Setting Body.BaseFeature makes a PartDesign::FeatureBase inside the body; the fillet references its edges.
    fb = next(o for o in body.Group if o.TypeId == "PartDesign::FeatureBase")
    edge = None
    for k, e in enumerate(fb.Shape.Edges):
        c = e.Curve
        if c.__class__.__name__ == "Circle" and abs(c.Radius - 1.5) < 1e-6 and abs(c.Center.z - 10) < 1e-6:
            edge = "Edge%d" % (k + 1)
            break
    assert edge is not None, "no top hole edge found"
    fil = body.newObject("PartDesign::Fillet", "BenchFillet")
    fil.Base = (fb, [edge])
    fil.Radius = 0.5
    d.recompute()
    assert fil.Shape.isValid(), "fillet fixture is invalid"
    if App.GuiUp:                               # what the owner sees: the fillet result, the plate and base hidden
        shown = [o.Name for o in d.Objects if o.isDerivedFrom("Part::Feature") and o.ViewObject.Visibility]
        assert "BenchFillet" in shown and "HolesPlate" not in shown and fb.Name not in shown, "shown: %s" % shown
    top = max(fb.Shape.Faces, key=lambda f: (f.CenterOfMass.z, f.Area))
    assert len(top.Wires) == n * n + 1, "top face should have %d wires, has %d" % (n * n + 1, len(top.Wires))
    path = os.path.join(out_dir, "fixture_holes%d.FCStd" % (n * n))
    d.saveAs(path)
    App.closeDocument(d.Name)
    return path
