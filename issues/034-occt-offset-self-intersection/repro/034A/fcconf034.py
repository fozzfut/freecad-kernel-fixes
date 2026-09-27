# fcconf034.py (issue 034 lane, copy of offset-study fcconf.py + status strings and more cases)
# fcconf.py (issue 034 study): confirm in FreeCAD 26.3 itself (PartDesign::Thickness / Part::Offset features, the
# owner's user path) that stock OCCT 8.0.1 BRepOffset returns broken or wrong solids WITHOUT an error.
# Per case: feature state, isValid, check(True), volume. Negative control: an unfolded offset (expect OK).
import os, time
import FreeCAD as App, Part
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
C = "C:/dev/occt8-mig/offset-study/cases/"; K = "C:/dev/occt8-mig/corpus/"
def load(fn):
    s = Part.Shape(); s.read(fn)
    if s.ShapeType != "Solid": s = max(s.Solids, key=lambda x: abs(x.Volume))
    return s
def st(ob):
    sh = ob.Shape
    err = "Invalid" in ob.State or sh.isNull()
    v = "-" if sh.isNull() else "%.4f" % sh.Volume
    if err: return "ERR state=%s msg=%s" % (",".join(ob.State), ob.getStatusString().replace(" ", "_"))
    valid = sh.isValid()
    try: sh.check(True); bop = "clean"
    except Exception as e: bop = "FAULTS"
    g = "OK" if valid and bop == "clean" else ("INV" if not valid else "BOP")
    return "%s state=%s isValid=%s check=%s vol=%s solids=%d" % (g, ",".join(ob.State) or "-", valid, bop, v, len(sh.Solids))
def pd_thick(name, fn, face, value, reversed_, join="Arc", inter=False):
    d = App.newDocument("c"); b = d.addObject("PartDesign::Body", "Body")
    base = d.addObject("Part::Feature", "Base"); base.Shape = load(fn); b.BaseFeature = base
    th = d.addObject("PartDesign::Thickness", "Thickness"); b.addObject(th)
    th.Base = (b.BaseFeature, ["Face%d" % face]); th.Value = value; th.Reversed = reversed_; th.Join = join; th.Intersection = inter
    t0 = time.time(); d.recompute(); say(name, "PD::Thickness", "value=%g reversed=%s join=%s inter=%s" % (value, reversed_, join, inter), st(th), "vol0=%.4f" % base.Shape.Volume, "%.2fs" % (time.time() - t0))
    App.closeDocument(d.Name)
def part_offset(name, fn, value, join="Arc", inter=False, selfi=False):
    d = App.newDocument("c"); base = d.addObject("Part::Feature", "Base"); base.Shape = load(fn)
    of = d.addObject("Part::Offset", "Offset"); of.Source = base; of.Value = value; of.Join = join; of.Intersection = inter; of.SelfIntersection = selfi
    t0 = time.time(); d.recompute(); say(name, "Part::Offset", "value=%g join=%s inter=%s self=%s" % (value, join, inter, selfi), st(of), "vol0=%.4f" % base.Shape.Volume, "%.2fs" % (time.time() - t0))
    App.closeDocument(d.Name)
pd_thick("lwall_nurbs_out1", C + "lwall_r05_nurbs.brep", 1, 1.0, False)
pd_thick("lwall_analytic_out1", C + "lwall_r05.brep", 1, 1.0, False)
pd_thick("vr6p4_default_in1", K + "VR6-350-new-part4.step", 3, 1.0, True)
pd_thick("c031_m2s10_sq_c15_out0.3", "C:/dev/occt8-mig/fillet-corner-r3/out/x/m2s10/case_sq_c15_r1.brep", 16, 0.3, False)
part_offset("step_nurbs_1.5", C + "step_r1_nurbs.brep", 1.5)
part_offset("step_nurbs_1.5_self", C + "step_r1_nurbs.brep", 1.5, selfi=True)
part_offset("step_analytic_1.5_int_i1", C + "step_r1.brep", 1.5, join="Intersection", inter=True)
part_offset("step_analytic_1.5_arc", C + "step_r1.brep", 1.5)
part_offset("NEGCTRL_step_nurbs_0.9", C + "step_r1_nurbs.brep", 0.9)
C2 = "C:/dev/occt8-mig/offset-034/cases/"
pd_thick("bfil_in1_KNOWN_GAP", C2 + "box_fillet_r2.brep", 9, 1.0, True)
pd_thick("bfiln_in2.5", C2 + "box_fillet_r2_nurbs.brep", 9, 2.5, True)
part_offset("NEGCTRL_bfiln_out1", C2 + "box_fillet_r2_nurbs.brep", 1.0)
part_offset("NEGCTRL_oring_out0.5", K + "owner_oring.step", 0.5)
pd_thick("NEGCTRL_oring_in1", K + "owner_oring.step", 4, 1.0, True)
say("FC-CONF-DONE")
