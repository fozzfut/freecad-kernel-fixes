"""Test documents built inside FreeCAD. build(name, out_dir) -> path of a saved FCStd."""
import os

import FreeCAD as App


def build(name, out_dir):
    if name == "pad":
        return _pad(out_dir)
    raise ValueError("unknown fixture " + name)


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
