# extra identity members (lane-like shapes with removed curved walls, unlocated path)
import FreeCAD as App, Part
V = App.Vector


def _s1(s):
    return s.Solids[0] if s.ShapeType != "Solid" else s


def hole():
    return _s1(Part.makeBox(40, 30, 10).cut(Part.makeCylinder(5, 12, V(20, 15, -1))))


def sphz():
    return _s1(Part.makeSphere(10).cut(Part.makeCylinder(3, 30, V(0, 0, -15), V(0, 0, 1))))


def vfil():
    b = Part.makeBox(50, 35, 22)
    return _s1(b.makeFillet(4, [e for e in b.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1]))


EXTRA = [("hole", hole, "thk", -1.0, 0, "cyl", ["T1", "TT"]), ("hole", hole, "thk", -1.0, 2, "top", ["T1"]),
         ("sphz", sphz, "thk", -1.0, 0, "cyl", ["T1"]), ("vfil", vfil, "thk", -1.2, 0, "top", ["T1"]),
         ("vfil", vfil, "off", 1.0, 2, None, ["TF"]), ("sphere", lambda: Part.makeSphere(8), "off", 1.0, 0, None, ["T1"])]
