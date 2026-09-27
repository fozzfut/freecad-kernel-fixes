# 027 - OCCT: plane section of a long helical B-spline face takes minutes (worse on OCCT 8.0.1)

Found 26.09.2026 by the HybridDesign lane "section-cap" (C:/dev/occt8-mig/progress.md). Status: OPEN, not patched.
HybridDesign no longer depends on it (quick cap from the closed display mesh, branch fix/section-cap).

## Symptom
HybridDesign's section mode caps every crossed part with `Shape.common(plane_face)`. On the VR6 ball screw
(SFU1605, corpus C:/dev/occt8-mig/corpus/ballscrew_Feature014.brep: 1 solid, 172 faces, valid) a plane through
the axis never got a cap: the boolean outlasts the 20 s budget of the cap process by 5-7 times.

## Numbers (one run each, FreeCADCmd, plane z = 35 through the axis, normal (0,0,1); runs in C:/dev/occt8-mig/hd-section/runs)
| step | FreeCAD 26.3 / OCCT 8.0.1 (delivery run copy dlv2) | FreeCAD-perf 1.1.1 / OCCT 7.8.1 |
|---|---|---|
| `shape.common(plane)` (result 1 face, area 4880.572 on both) | 135.7 s (p1-w.txt) | 99.0 s (p3-o-ax-common.txt) |
| `Faces[149].section(plane)`, B-spline 2 x 241 poles, deg 1x2, 29 edges | 23.4 s (p2-w.txt) | 7.8 s (p3-o-ax-149.txt) |
| `Faces[150].section(plane)`, same kind | 21.7 s | 7.2 s |
| `Faces[153].section(plane)`, B-spline 4 x 1305 poles, deg 3x2, 653 V-knots, 117 edges | 276.0 s (p2-w.txt) | 202.9 s (p3-o-ax-153.txt) |
| every other face (cylinders, planes) | 0.002-0.08 s each | - |

- Old defect, worse on OCCT 8: 1.4x (face 153, common) to 3x (faces 149/150) slower than 7.8.1.
- Superlinear in the face length (inference from one experiment, p4-w.txt): the UNTRIMMED surface of face 153 cut
  into 117 pieces of 4 knot spans each is sectioned in 4.95 s in total, the same 117 edges; in 30 pieces 7.45 s;
  in 8 pieces 20.7 s. The trimmed face in one piece: 276 s. So the cost grows much faster than the surface size.
- Not the cause: tolerances (face tol 1e-7, edges <= 0.007), validity (isValid True), shells (it is one solid).

## Repro
`repro/section_timing.py` (FreeCADCmd; env HD_PROBE_OUT = output file, HD_CASE = axial|perp|oblique,
HD_WHAT = comma list of face<i> | common | tess). Example: HD_CASE=axial HD_WHAT=face149 -> about 8 s on 7.8.1, 23 s on 8.0.1.
It imports hybriddesign.ops.section only for `cutting_plane` (a square face of 3 x the bbox diagonal around the bbox centre).

## Where to look (not investigated)
BRepAlgoAPI_Section -> IntTools_FaceFace -> IntPatch_ImpPrmIntersection (plane x parametric surface), walking
(IntWalk_PWalking) and the approximation of the walking lines. The sampling/start-point search over a long surface
of 1305 poles is the suspect for the superlinear part; the OCCT 8 slowdown needs a profile (VTune/ETW) of face 149.

## Status 26.09 (lane k027): PATCHED, results identical to stock; not installed (review)
Evidence: C:/dev/occt8-mig/k027/REPORT.txt. Branch perf/801-027 (worktree C:/dev/occt-801-027), patches in
`patches-801/`, DLLs in `C:/dev/freecad-kernel-fixes/build/variants801/027/` (TKBO.dll + TKGeomBase.dll, together).

Where the time went (native samples, k027/runs/prof-weekly-*.txt): NOT the walk (IntPatch/IntWalk 3 % of face 153).
- `IntTools_FaceFace::ComputeTolReached3d` -> `FindMaxDistance`: ~250 point projections per section curve, each an
  `Extrema_GenExtPS` over the whole face grid (face 149: 90 %, face 153: 50 %). Curves x face size = the superlinear term.
- `BOPAlgo_PaveFiller::PutPavesOnCurve` -> `IntTools_Context::IsVertexOnLine`: every EF vertex projected on every
  1001-pole section curve (face 153: 39 %, whole-screw common: 26 %).
- The "3x slower on OCCT 8" was machine load: paired rerun face 149: 7.10 s (7.8.1, Perf) vs 6.9-7.5 s (8.0.1);
  the three code paths are the same algorithms in 7.8.1 and 8.0.1.

Fix (3 exact changes): pole-box rejection in IsVertexOnLine; parallel deviations with one projector per worker;
GenExtPS edge evaluations deferred and sorted by V span. One paired FreeCAD run (26.3): face 153 axial section
213.97 -> 46.26 s, faces 149/150 11.9 -> 1.6 s, `shape.common(plane)` axial (HD exact cap) 90.63 -> 44.21 s,
oblique section 37.84 -> 32.14 s; every result md5 identical.
Left: the GenExtPS whole-grid search per projection stays (its extrema set is the stock result; pruning would change
tolerances) - the HD exact cap is still > 20 s, the quick cap stays; IntWalk TestArretPassage (12 % of the common).
