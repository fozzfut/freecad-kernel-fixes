# fcb2r1c.py (issue 034 lane B2 round 1, continuation): the sharp-rim class in FreeCAD 26.3 itself.
# Box 20x14x10 with only its 4 vertical edges filleted r (and one variant with vertical + top edges), made the way the
# owner does it (PartDesign Body + AdditiveBox + PD Fillet) and with Part features; PD Thickness default direction
# (inward, Reversed=True), top face removed; Part::Offset inward. Reference volumes are independent (sharp boxes).
import os, time
import FreeCAD as App, Part
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
def st(ob):
    sh = ob.Shape
    if "Invalid" in ob.State or sh.isNull():
        return "ERR state=%s msg=%s" % (",".join(ob.State), ob.getStatusString().replace(" ", "_"))
    valid = sh.isValid()
    try: sh.check(True); bop = "clean"
    except Exception: bop = "FAULTS"
    g = "OK" if valid and bop == "clean" else ("INV" if not valid else "BOP")
    return "%s isValid=%s check=%s vol=%.5f solids=%d faces=%d" % (g, valid, bop, sh.Volume, len(sh.Solids), len(sh.Faces))
def vert(e): return abs(e.BoundBox.ZMax - e.BoundBox.ZMin - 10) < 1e-6 and e.BoundBox.XLength < 1e-6 and e.BoundBox.YLength < 1e-6
def top(e): return abs(e.BoundBox.ZMin - 10) < 1e-6 and abs(e.BoundBox.ZMax - 10) < 1e-6
def pd_box(d, r, which, placement=None):
    b = d.addObject("PartDesign::Body", "Body")
    if placement: b.Placement = placement
    bx = d.addObject("PartDesign::AdditiveBox", "Box"); bx.Length, bx.Width, bx.Height = 20, 14, 10; b.addObject(bx); d.recompute()
    names = ["Edge%d" % (i + 1) for i, e in enumerate(bx.Shape.Edges) if vert(e) or (which == "vt" and top(e))]
    f = d.addObject("PartDesign::Fillet", "Fillet"); f.Base = (bx, names); f.Radius = r; b.addObject(f); d.recompute()
    return b, f
def pd_thick(name, r, which, t, ref, placement=None, rev=True):
    d = App.newDocument("c"); b, f = pd_box(d, r, which, placement)
    sh = f.Shape
    k = max((i for i, fc in enumerate(sh.Faces) if fc.Surface.__class__.__name__ == "Plane"),
            key=lambda i: sh.Faces[i].CenterOfMass.dot(b.Placement.Rotation.multVec(App.Vector(0, 0, 1))))
    th = d.addObject("PartDesign::Thickness", "Thickness"); th.Base = (f, ["Face%d" % (k + 1)]); th.Value = t; th.Reversed = rev
    b.addObject(th)
    t0 = time.time(); d.recompute()
    say(name, "PD::Thickness", "r=%g t=%g reversed=%s face=%d" % (r, t, rev, k + 1), st(th), "vol0=%.5f" % sh.Volume,
        "ref=%s" % ("-" if ref is None else "%.5f" % ref(sh.Volume)), "%.2fs" % (time.time() - t0))
    App.closeDocument(d.Name)
def part_offset(name, r, t, ref):
    d = App.newDocument("c")
    bx = d.addObject("Part::Box", "Box"); bx.Length, bx.Width, bx.Height = 20, 14, 10; d.recompute()
    f = d.addObject("Part::Fillet", "Fillet"); f.Base = bx
    f.Edges = [(i + 1, r, r) for i, e in enumerate(bx.Shape.Edges) if vert(e)]; bx.Visibility = False; d.recompute()
    of = d.addObject("Part::Offset", "Offset"); of.Source = f; of.Value = -t; of.Join = "Arc"
    t0 = time.time(); d.recompute()
    say(name, "Part::Offset", "r=%g value=%g" % (r, -t), st(of), "ref=%s" % ("-" if ref is None else "%.5f" % ref), "%.2fs" % (time.time() - t0))
    App.closeDocument(d.Name)
cav = lambda t: (lambda v0: v0 - (20 - 2 * t) * (14 - 2 * t) * (10 - t))
pl = App.Placement(App.Vector(7, -3, 11), App.Rotation(App.Vector(1, 2, 3), 30))
for t in (1.0, 1.5, 2.0):
    pd_thick("vbox_r1_pdthick_in%g" % t, 1, "v", t, cav(t))
pd_thick("vbox_r1_rot_pdthick_in1.5", 1, "v", 1.5, cav(1.5), pl)
pd_thick("vtbox_r1_pdthick_in1.5", 1, "vt", 1.5, None)
pd_thick("vbox_r2_pdthick_in3", 2, "v", 3.0, cav(3.0))
for t in (1.5, 3.0):
    part_offset("vbox_r1_off-%g" % t, 1, t, (20 - 2 * t) * (14 - 2 * t) * (10 - 2 * t))
pd_thick("NEGCTRL_vbox_r1_pdthick_in0.5", 1, "v", 0.5, None)
part_offset("NEGCTRL_vbox_r1_off-0.5", 1, 0.5, None)
say("FC-B2R1C-DONE")
