import os, FreeCAD as App, Part
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
def chk(s):
    try: s.check(True); c = "clean"
    except Exception as e: c = "FAULTS"
    return "valid=%s check=%s vol=%.4f shells=%d faces=%d" % (s.isValid(), c, s.Volume, len(s.Shells), len(s.Faces))
b0 = Part.makeBox(100, 60, 40)
top = lambda s: max(s.Faces, key=lambda f: (isinstance(f.Surface, Part.Plane), f.CenterOfMass.z))
# (a) fillet only edges that do not touch the top face, then shell
e8 = [e for e in b0.Edges if not (abs(e.BoundBox.ZMin - 40) < 1e-9 and abs(e.BoundBox.ZMax - 40) < 1e-9)]
fa = b0.makeFillet(5, e8)
for t in (-1, -2):
    try: say("a_fillet8_then_shell t=%g" % t, chk(fa.makeThickness([top(fa)], t, 1e-7, False, False, 0, 0)))
    except Exception as e: say("a_fillet8_then_shell t=%g EXC %s" % (t, e))
# (b) shell first, then fillet the outer 8 edges
for t in (-1, -2):
    try:
        s = b0.makeThickness([top(b0)], t, 1e-7, False, False, 0, 0)
        outer = [e for e in s.Edges if (e.BoundBox.XMin < 1e-9 or e.BoundBox.XMax > 100 - 1e-9 or e.BoundBox.YMin < 1e-9 or e.BoundBox.YMax > 60 - 1e-9 or e.BoundBox.ZMax < 1e-9) and not abs(e.BoundBox.ZMin - 40) < 1e-9 and e.BoundBox.ZMin < 1e-9 or (e.BoundBox.ZMin < 1e-9 and e.BoundBox.ZMax > 40 - 1e-9 and (e.BoundBox.XMin < 1e-9 or e.BoundBox.XMax > 100 - 1e-9) and (e.BoundBox.YMin < 1e-9 or e.BoundBox.YMax > 60 - 1e-9))]
        f = s.makeFillet(5, outer)
        say("b_shell_then_fillet t=%g edges=%d" % (t, len(outer)), chk(f))
    except Exception as e: say("b_shell_then_fillet t=%g EXC %s" % (t, e))
say("WA-DONE")
