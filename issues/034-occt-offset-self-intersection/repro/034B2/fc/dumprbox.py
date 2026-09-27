# dumprbox.py: the FreeCAD-built rounded box (Part::Box 20x14x10 + Part::Fillet r=1 on all edges) and the boss, as BREP
import os
import FreeCAD as App, Part
o = open(os.environ["FC_OUT"], "w")
d = App.newDocument("c")
b = d.addObject("Part::Box", "Box"); b.Length, b.Width, b.Height = 20, 14, 10; d.recompute()
f = d.addObject("Part::Fillet", "Fillet"); f.Base = b; f.Edges = [(i + 1, 1, 1) for i in range(len(b.Shape.Edges))]; d.recompute()
s = f.Shape
o.write("type=%s loc=%s placement=%s faces=%d\n" % (s.ShapeType, s.Placement, f.Placement, len(s.Faces)))
s.exportBrep("C:/dev/occt8-mig/offset-034b2/cases/fc_rbox_r1.brep")
s2 = s.copy(); s2.Placement = App.Placement()
o.write("DONE\n")
