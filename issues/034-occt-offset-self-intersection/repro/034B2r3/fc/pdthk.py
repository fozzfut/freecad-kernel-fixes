# pdthk.py - issue 034 B2 r3: the PartDesign path (Body with a base feature + PD Thickness) on partial-fold members.
# Output: FC_OUT. Each line: name, state, validity, volume, area of the inner cross-section face (test side).
import os, FreeCAD as App, Part
out = open(os.environ.get("FC_OUT", "pdthk.txt"), "w")
C = "C:/dev/occt8-mig/offset-034b2/r3c/cases/"
cases = [  # name, brep, face index (1-based, the removed face), thickness value, reversed (inward), plane axis, pos, ref
    ("ell_t2_in", "ell_a0.brep", 2, 2.0, True, 2, 6.0, 46.188743045),
    ("ell_t3_in", "ell_a0.brep", 2, 3.0, True, 2, 5.0, 16.799413087),
    ("wave_t3_in", "wave_a0.brep", 3, 3.0, True, 1, 3.0, 227.224281836),
    ("ridge_t5_in", "t_ridge_12_12.brep", 4, 5.0, True, 0, 5.0, 123.066108212),
    ("ell_t1_in_ctl", "ell_a0.brep", 2, 1.0, True, 2, 7.0, 82.779073606),
    ("wave_t3_out", "wave_a0.brep", 3, 3.0, False, 1, -3.0, 0.0),
]
for name, f, fi, t, inward, ax, pos, ref in cases:
    doc = App.newDocument(name)
    try:
        sh = Part.Shape(); sh.read(C + f)
        base = doc.addObject("Part::Feature", "Base"); base.Shape = sh
        body = doc.addObject("PartDesign::Body", "Body"); body.BaseFeature = base
        doc.recompute()
        th = body.newObject("PartDesign::Thickness", "Thickness")
        th.Base = (body.BaseFeature, ["Face%d" % fi])
        th.Value = t; th.Reversed = inward; th.Mode = 0; th.Join = 0
        doc.recompute()
        s = th.Shape
        st = "OK" if th.isValid() and not s.isNull() else "ERR:" + ",".join(th.getStatusString() if hasattr(th, "getStatusString") else [])
        area = 0.0
        if st == "OK":
            for fc in s.Faces:
                bb = fc.BoundBox
                lo = (bb.XMin, bb.YMin, bb.ZMin)[ax]; hi = (bb.XMax, bb.YMax, bb.ZMax)[ax]
                if fc.Surface.__class__.__name__ == "Plane" and abs(lo - pos) < 1e-5 and abs(hi - pos) < 1e-5:
                    area += fc.Area
        rel = abs(area - ref) / ref if ref > 0 and area > 0 else -1
        out.write("%s %s valid=%s vol=%.6f area=%.10f ref=%.9f rel=%.2e\n" % (name, st, s.isValid() if not s.isNull() else False,
                  s.Volume if not s.isNull() else 0, area, ref, rel))
    except Exception as e:
        out.write("%s EXC %s\n" % (name, str(e).replace("\n", " ")))
    out.flush()
    App.closeDocument(name)
out.write("PDTHK-DONE\n")
out.close()
