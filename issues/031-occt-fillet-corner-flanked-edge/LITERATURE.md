# 031 — literature (vertex blends where fillets meet unblended edges)

Pass done 27.09 before the design; sources from specialist CAD/CAGD journals (count as full sources by the
owner rule of 26.09) plus the OCCT documentation. Open access marked; others read from abstract / known content.

| # | Source | Venue | Idea | Used how |
|---|--------|-------|------|----------|
| 1 | J.R. Rossignac, A.A.G. Requicha, "Constant-radius blending in solid modelling", *Computers in Mechanical Engineering* 3(1), 65–73, 1984 (no DOI; UR Research open copy) | CiME (conference-grade magazine, historical) | A constant-radius blend is the envelope of a ball rolling in contact with the faces (morphological opening). Where a ball meets an unblended edge it touches the edge line. | Reference geometry: `repro/ref.py` traces the exact ball-centre path for the owner's corner; its contact set on the two concave edges is exactly the edge pieces between the two fillet ends — the new corner boundary. It also shows the exact envelope folds (path curvature radius 0.71 < r = 1), so the pure rolling ball is not a usable target here. |
| 2 | J. Vida, R.R. Martin, T. Várady, "A survey of blending methods that use parametric surfaces", *CAD* 26(5), 341–365, 1994, doi:10.1016/0010-4485(94)90023-X (SZTAKI eprint, open) | Computer-Aided Design | Terminology: edge blends, vertex blends, setbacks; vertex blends as n-sided patches with G1 to the edge blends and G0/G1 to the faces. | Classification of the defect: an n-sided vertex blend whose boundary crosses faces with a G0 batten instead of following the edge. |
| 3 | T. Várady, A. Rockwood, "Geometric construction for setback vertex blending", *CAD* 29(6), 413–425, 1997, doi:10.1016/S0010-4485(96)00070-X (abstract) | Computer-Aided Design | Edge blends are cut back ("setback") from the vertex so the vertex blend gets room for a fair G1 patch; the setbacks are the design parameters. | The farther fillet is set back by the gap along the sharp edge, so the plate section has no inflection (analysis in README: with both ends kept, the chord leaves the range of the two end tangents, a G1 patch needs an S-section). |
| 4 | I.C. Braid, "Non-local blending of boundary models", *CAD* 29(2), 89–100, 1997, doi:10.1016/S0010-4485(96)00038-3 (abstract) | Computer-Aided Design | Blends interacting with other edges and faces of the model (ends of blends, blends running into unblended edges) — the ACIS/Romulus view: the blend boundary follows model edges where the ball meets them. | The corner border to the nearer fillet is the piece of the sharp edge (not a curve across the face). |
| 5 | T. Várady, P. Salvi, M. Vaitkus, "Genuine multi-sided parametric surface patches – A survey", *CAGD* 110, 102286, 2024, doi:10.1016/j.cagd.2024.102286 (open preprint) | Computer Aided Geometric Design | n-sided patches that interpolate positional and cross-derivative ribbons; G1 needs compatible ribbons at the corners. | Corner compatibility check of the new boundary: G1 ribbons on both fillet ends and on the wall line, G0 on the edge piece; normals agree at all six corners. We keep OCCT's GeomPlate (identity elsewhere) rather than a transfinite patch. |
| 6 | P. Salvi, T. Várady, "G2 surface interpolation over general topology curve networks", *CGF* 33(7), 2014, doi:10.1111/cgf.12483 | Computer Graphics Forum | Higher-order multi-sided interpolation. | Not applied (G2 is not what mainstream fillets give at such corners); noted as the route if a later pass replaces GeomPlate here. |
| 7 | OCCT 8.0.1 user guide, Modeling Algorithms, "Fillets and chamfers"; `ChFi3d_Builder_CnCrn.cxx` comments | documentation | Corners with more than three edges are filled with a plate (GeomPlate) built on the stripe ends and on connecting curves (line, projection or batten) across the faces. | Where the defect lives; the fix changes only the boundary choice for flanked sharp edges. |

Better-known method? A transfinite multi-sided patch (5) would give exact G1 instead of GeomPlate's
approximation (wall line up to 6.3 deg at one corner). It would replace the plate for this configuration only;
kept as a follow-up, because the plate result is already valid, BOP-clean and fold-free, and a new patch type
would add a new surface kind to the DS path.

## Round 2 (27.09, after the review): the edge piece as a G1 border, and what "downstream" depends on

Pass repeated for the two new questions (why the corner is asymmetric; why the offset refuses it). No new
journal method was needed; the existing sources answer both once the OCCT internals are read:

| # | Source | Idea | Used how |
|---|--------|------|----------|
| 1 (again) | Rossignac–Requicha 1984 | Where the ball touches an unblended edge it pivots on it: along the contact set the envelope's tangent plane turns about the edge from one face's plane to the other's. | The edge piece becomes a G1 border whose tangent plane turns about the edge from the far face (the set-back fillet's wall) to the near face (the face the nearer fillet rolls on) — built as a ruled "pivot" surface through the edge (`PivotBorder`). |
| 5 (again) | Várady–Salvi–Vaitkus 2024 (and Gregory-type patches, see there) | Multi-sided G1 patches need cross-derivative data on every side and compatible data at the corners (vertex compatibility). | Round 1 mixed G0 (edge piece) and G1 sides; at a G0/G1 corner the G1 data is free. Now every side carries G1 data and the data agree at all six corners (both tangent planes are the face planes there). |
| 8 | OCCT 8.0.1 `GeomPlate_BuildPlateSurface::Intersect` (source) | At a point shared by curve constraints i < j the plate drops the point of curve i ("the point on curve i is removed; the point on curve j is preserved"); non-compatible G1/G1 pairs lose a zone on both. | Root cause of the asymmetry: the loop order decided which side kept the wall line's G1 end point (review: 15.7 deg at one end only). With compatible G1 data everywhere the dropped point is replaced by an identical one, so the result no longer depends on the order: owner's corner now mirror-symmetric (creases 0.90→42.18 deg on both sides, wall lines ≤ 2.88 deg on both). |
| 9 | OCCT 8.0.1 `BRepOffset_MakeOffset::MakeOffsetShape` (source) | Edges are classified tangent / sharp with TolAngle = 4·asin(Tol/(|t|/2)), Tol = the shape's MAX vertex tolerance. | Explains issue 5829: with round-1 edge pieces at 12–17 deg and Tol 3.4e-2 the threshold at t = 1 was 15.6 deg — a contradictory tangent/sharp triple at the wall vertex. It also explains the thickness "lottery" of whole bodies: a corner that lowers the max tolerance changes the threshold for every edge of the body (verified: raising one far vertex tolerance of the new result back to stock's value reproduces stock's thickness outcome exactly, runs/tolmatch.txt). |

Better-known method? For the plate itself, still the transfinite multi-sided patch (5); not needed for the
downstream problem, which came from the G0 side and the order dependence, not from GeomPlate's accuracy. A G1
approximation criterion for GeomPlate_MakeApprox (GeomPlate_PlateG1Criterion) was tried for these corners: better
tolerance on the owner's part (6.1e-4) but the 5829 corner then fails the BOP check (vertex self-interference) —
rejected.

## Round 3 (27.09): why a smooth corner breaks the next Thickness, and whether a construction can avoid it

| # | Source | Venue | Idea | Used how |
|---|--------|-------|------|----------|
| 10 | T. Maekawa, "An overview of offset curves and surfaces", *Computer-Aided Design* 31(3), 165–173, 1999, doi:10.1016/S0010-4485(99)00013-5 (abstract / known content) | Computer-Aided Design (specialist, full source) | An offset at distance d self-intersects locally wherever d exceeds the radius of curvature on the concave side. | Explains the new silent Thickness results: the new corner's concave ridge has radius 0.047 r (measured, tools curvk), thickness +0.1 r / +0.3 r self-intersects exactly there (thkdiag: BOP SelfIntersect centred on the ridge). |
| 11 | J.-K. Seong, G. Elber, M.-S. Kim, "Trimming local and global self-intersections in offset curves/surfaces using distance maps", *Computer-Aided Design* 38(3), 183–193, 2006, doi:10.1016/j.cad.2005.09.002 (abstract / known content) | Computer-Aided Design | Robust offsetting must detect and trim local self-intersections. | BRepOffset does not; that is why it returns a BOP-faulty solid instead of an error. The fix belongs to BRepOffset (out of this lane); recorded as the route that would make a smooth corner safe downstream. |
| 1, 3 (again) | Rossignac–Requicha 1984; Várady–Rockwood 1997 | — | The exact rolling-ball envelope folds at this corner (probe/ref.py: centre-path radius 0.71 < r); setbacks are free design parameters of a vertex blend. | The ridge is intrinsic to any G1 corner faithful to the ball; only a much larger setback (a flatter corner that deviates from the ball) could raise its radius — not tried, it changes the blend's shape beyond "the same fillet, better built". |

Better-known method? For the edge piece: the split where the crease reaches the tangency angle (reviewer's proposal)
works for the regularity flags. For the downstream offset: offset-trimming (11) — an OCCT BRepOffset change, not a
TKFillet one.
