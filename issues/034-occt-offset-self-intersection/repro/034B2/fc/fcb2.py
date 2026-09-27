# fcb2.py (issue 034 lane B2): the class in FreeCAD 26.3 itself - offsets / thickness of solids whose blends vanish
# (blend radius < offset). Features built by FreeCAD (Part::Box, Part::Fillet, Part::Cylinder, Part::Fuse), then
# Part::Offset and PartDesign::Thickness (the owner's path). Per case: state, isValid, check(True), volume and the
# independent reference volume (sharp inner box / cavity). NEGCTRL rows: offsets below the radius (not in the class).
import os, time
import FreeCAD as App, Part
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
def st(ob):
    sh = ob.Shape
    err = "Invalid" in ob.State or sh.isNull()
    v = "-" if sh.isNull() else "%.5f" % sh.Volume
    if err: return "ERR state=%s msg=%s" % (",".join(ob.State), ob.getStatusString().replace(" ", "_"))
    valid = sh.isValid()
    try: sh.check(True); bop = "clean"
    except Exception: bop = "FAULTS"
    g = "OK" if valid and bop == "clean" else ("INV" if not valid else "BOP")
    return "%s isValid=%s check=%s vol=%s solids=%d faces=%d" % (g, valid, bop, v, len(sh.Solids), len(sh.Faces))
def rbox(d, r, placement=None):
    b = d.addObject("Part::Box", "Box"); b.Length, b.Width, b.Height = 20, 14, 10
    if placement: b.Placement = placement
    d.recompute()
    f = d.addObject("Part::Fillet", "Fillet"); f.Base = b
    f.Edges = [(i + 1, r, r) for i in range(len(b.Shape.Edges))]
    b.Visibility = False; d.recompute(); return f
def boss(d, r):
    p = d.addObject("Part::Box", "Plate"); p.Length, p.Width, p.Height = 30, 30, 5
    c = d.addObject("Part::Cylinder", "Cyl"); c.Radius, c.Height = 6, 6; c.Placement = App.Placement(App.Vector(15, 15, 5), App.Rotation())
    u = d.addObject("Part::MultiFuse", "Fuse"); u.Shapes = [p, c]; u.Refine = True; d.recompute()
    f = d.addObject("Part::Fillet", "Fillet"); f.Base = u
    es = [i + 1 for i, e in enumerate(u.Shape.Edges) if abs(e.CenterOfMass.z - 5) < 1e-6 and abs((e.CenterOfMass - App.Vector(15, 15, 5)).Length - 6) < 1e-4
          or (hasattr(e.Curve, "Radius") and abs(e.Curve.Radius - 6) < 1e-6 and abs(e.BoundBox.ZMin - 5) < 1e-6 and abs(e.BoundBox.ZMax - 5) < 1e-6)]
    f.Edges = [(i, r, r) for i in es]; d.recompute(); return f
def part_offset(name, mk, value, ref=None, join="Arc"):
    d = App.newDocument("c"); src = mk(d)
    of = d.addObject("Part::Offset", "Offset"); of.Source = src; of.Value = value; of.Join = join
    t0 = time.time(); d.recompute()
    say(name, "Part::Offset", "value=%g join=%s" % (value, join), st(of), "ref=%s" % ("-" if ref is None else "%.5f" % ref), "%.2fs" % (time.time() - t0))
    App.closeDocument(d.Name)
def pd_thick(name, mk, zface, value, reversed_, ref=None, join="Arc"):
    d = App.newDocument("c"); src = mk(d)
    b = d.addObject("PartDesign::Body", "Body"); b.BaseFeature = src; d.recompute()
    faces = src.Shape.Faces
    k = min(range(len(faces)), key=lambda i: abs(faces[i].CenterOfMass.z - zface) + (0 if faces[i].Surface.__class__.__name__ == "Plane" else 1e6) - faces[i].Area * 1e-9)
    th = d.addObject("PartDesign::Thickness", "Thickness"); b.addObject(th)
    th.Base = (b.BaseFeature, ["Face%d" % (k + 1)]); th.Value = value; th.Reversed = reversed_; th.Join = join
    t0 = time.time(); d.recompute()
    say(name, "PD::Thickness", "face=%d value=%g reversed=%s join=%s" % (k + 1, value, reversed_, join), st(th), "vol0=%.5f" % src.Shape.Volume,
        "ref=%s" % ("-" if ref is None else "%.5f" % ref), "%.2fs" % (time.time() - t0))
    App.closeDocument(d.Name)
V0 = None
# rounded box r=1: inward offset past the fillet radius -> sharp inner box (20-2t)(14-2t)(10-2t)
for t in (1.5, 2.5):
    part_offset("rbox_r1_off-%g" % t, lambda d: rbox(d, 1), -t, ref=(20 - 2 * t) * (14 - 2 * t) * (10 - 2 * t))
part_offset("rbox_r1_off-1_eq_radius", lambda d: rbox(d, 1), -1.0, ref=18 * 12 * 8)
pl = App.Placement(App.Vector(7, -3, 11), App.Rotation(App.Vector(1, 2, 3), 30))
part_offset("rbox_r1_rot_off-1.5", lambda d: rbox(d, 1, pl), -1.5, ref=17 * 11 * 7)
# PD Thickness of the rounded box, top face removed, inward 1.5 / 2 > r: shell with a sharp cavity
def rbox_vol(r):
    d = App.newDocument("v"); v = rbox(d, r).Shape.Volume; App.closeDocument(d.Name); return v
V1 = rbox_vol(1)
for t in (1.5, 2.0):
    pd_thick("rbox_r1_pdthick_in%g" % t, lambda d: rbox(d, 1), 10, t, True, ref=V1 - (20 - 2 * t) * (14 - 2 * t) * (10 - t))
# boss with a concave root fillet r=1: outward offset past the radius (torus ring vanishes)
part_offset("boss_r1_off+1.5", lambda d: boss(d, 1), 1.5)
part_offset("boss_r1_off+1.5_int", lambda d: boss(d, 1), 1.5, join="Intersection")
# negative controls (not in the class: offset below the radius)
part_offset("NEGCTRL_rbox_r1_off-0.5", lambda d: rbox(d, 1), -0.5)
pd_thick("NEGCTRL_rbox_r2_pdthick_out1", lambda d: rbox(d, 2), 10, 1.0, False)
part_offset("NEGCTRL_boss_r2_off+1", lambda d: boss(d, 2), 1.0)
say("FC-B2-DONE")
