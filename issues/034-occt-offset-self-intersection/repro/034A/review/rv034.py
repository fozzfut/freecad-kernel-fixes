# rv034.py - review of lane offset-A (issue 034 stage A), run on stock (o034s) and patched (o034p) FreeCAD 26.3.
# Owner-path cases: the 5829 model (PD Thickness), common filleted enclosures (analytic fillets), shells of the
# 5829 model with smaller thickness. Per case: state/message, isValid, BOP check (check(True)) text head, volume.
import os, time, traceback
import FreeCAD as App, Part
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
def st(ob):
    sh = ob.Shape
    if "Invalid" in ob.State or sh.isNull():
        return "ERR state=%s msg=%s" % (",".join(ob.State), ob.getStatusString().replace(" ", "_"))
    valid = sh.isValid()
    try: sh.check(True); bop = "clean"
    except Exception as e: bop = "FAULTS[" + str(e).replace("\n", "|")[:160] + "]"
    g = "OK" if valid and bop == "clean" else ("INV" if not valid else "BOP")
    return "%s isValid=%s check=%s vol=%.4f faces=%d solids=%d" % (g, valid, bop, sh.Volume, len(sh.Faces), len(sh.Solids))
def case5829(d):
    body = d.addObject("PartDesign::Body", "Body")
    w = d.addObject("PartDesign::AdditiveWedge", "Wedge")
    w.Xmin, w.X2min, w.Xmax, w.X2max = 0.0, 10.0, 96.0, 86.0
    w.Zmin, w.Z2min, w.Zmax, w.Z2max = 0.0, 10.0, 126.0, 116.0
    w.Ymin, w.Ymax = 0.0, 25.0
    body.addObject(w)
    b = d.addObject("PartDesign::AdditiveBox", "Box"); b.Length, b.Width, b.Height = 96.0, 126.0, 10.0
    b.Placement = App.Placement(App.Vector(), App.Rotation(0.0, 0.0, 90.0)); body.addObject(b); d.recompute()
    f = d.addObject("PartDesign::Fillet", "Fillet")
    f.Base = (b, ["Edge15","Edge13","Edge12","Edge11","Edge4","Edge5","Edge3","Edge2","Face4","Edge19","Edge9","Edge7"])
    f.Radius = 8.0; body.addObject(f); d.recompute()
    c = [(i, x) for i, x in enumerate(f.Shape.Faces, 1) if isinstance(x.Surface, Part.Plane) and abs(x.CenterOfMass.y + 10.0) < 1e-7]
    return body, f, "Face%d" % max(c, key=lambda t: t[1].Area)[0]
def thick5829(name, value, mode="Skin", rev=True, join="Arc"):
    d = App.newDocument("r"); body, f, face = case5829(d)
    th = d.addObject("PartDesign::Thickness", "T"); th.Base = (f, [face]); th.Value = value; th.Mode = mode
    th.Reversed = rev; th.Join = join; body.addObject(th)
    t0 = time.time(); d.recompute()
    say(name, "value=%g mode=%s rev=%s join=%s" % (value, mode, rev, join), st(th), "fillet_faces=%d %.2fs" % (len(f.Shape.Faces), time.time() - t0))
    App.closeDocument(d.Name)
def enclosure(name, L, W, H, r, value, rev=True, join="Arc"):
    d = App.newDocument("r"); body = d.addObject("PartDesign::Body", "Body")
    b = d.addObject("PartDesign::AdditiveBox", "Box"); b.Length, b.Width, b.Height = L, W, H; body.addObject(b); d.recompute()
    f = d.addObject("PartDesign::Fillet", "Fillet"); f.Base = (b, ["Edge%d" % i for i in range(1, 13)]); f.Radius = r
    body.addObject(f); d.recompute()
    top = max(enumerate(f.Shape.Faces, 1), key=lambda t: (isinstance(t[1].Surface, Part.Plane), t[1].CenterOfMass.z, t[1].Area))[0]
    th = d.addObject("PartDesign::Thickness", "T"); th.Base = (f, ["Face%d" % top]); th.Value = value; th.Reversed = rev
    th.Join = join; body.addObject(th)
    t0 = time.time(); d.recompute()
    say(name, "box=%gx%gx%g r=%g value=%g rev=%s join=%s" % (L, W, H, r, value, rev, join), st(th), "%.2fs" % (time.time() - t0))
    App.closeDocument(d.Name)
for args in [("5829_in1_default", 1.0), ("5829_rectoverso1", 1.0, "RectoVerso"), ("5829_in0.3", 0.3), ("5829_in0.5", 0.5),
             ("5829_in2", 2.0), ("5829_out1", 1.0, "Skin", False), ("5829_in1_intersection", 1.0, "Skin", True, "Intersection")]:
    try: thick5829(*args)
    except Exception: say(args[0], "PROBE-EXC", traceback.format_exc().replace("\n", "|")[:300])
for args in [("encl_r5_in2", 100, 60, 40, 5, 2), ("encl_r5_in1", 100, 60, 40, 5, 1), ("encl_r2_in3", 100, 60, 40, 2, 3),
             ("encl_r3_out1", 80, 50, 30, 3, 1, False), ("encl_r8_in1.5", 120, 80, 50, 8, 1.5)]:
    try: enclosure(*args)
    except Exception: say(args[0], "PROBE-EXC", traceback.format_exc().replace("\n", "|")[:300])
say("RV034-DONE")
