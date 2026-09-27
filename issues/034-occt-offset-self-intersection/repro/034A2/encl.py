import os, FreeCAD as App, Part
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
say("OCC", Part.OCC_VERSION, "FC", App.Version()[:3])
for (L, W, H, r, t) in [(100, 60, 40, 5, -1), (100, 60, 40, 5, -2), (120, 80, 50, 8, -1.5), (100, 60, 40, 5, 1)]:
    b0 = Part.makeBox(L, W, H); b = b0.makeFillet(r, b0.Edges)
    top = max(b.Faces, key=lambda f: (isinstance(f.Surface, Part.Plane), f.CenterOfMass.z))
    for join in (0, 2):
        try:
            s = b.makeThickness([top], t, 1e-7, False, False, 0, join)
            v = s.isValid(); bad = []
            if not v:
                for i, f in enumerate(s.Faces, 1):
                    if not f.isValid(): bad.append("F%d:%s" % (i, type(f.Surface).__name__))
                sh = s.Shells
                bad.append("shells=%d shellsValid=%s" % (len(sh), [x.isValid() for x in sh]))
            try: s.check(True); c = "clean"
            except Exception as e: c = str(e).replace("\n", "|")[:120]
            say("box %gx%gx%g r=%g t=%g join=%d" % (L, W, H, r, t, join), "valid=%s vol=%.4f faces=%d check=%s bad=%s" % (v, s.Volume, len(s.Faces), c, " ".join(bad)[:200]))
        except Exception as e:
            say("box %gx%gx%g r=%g t=%g join=%d" % (L, W, H, r, t, join), "EXC", str(e)[:120])
say("ENCL-DONE")
