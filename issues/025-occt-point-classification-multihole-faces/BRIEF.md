# Defect 025 — OCCT point-in-solid / point-in-face classification is slow on faces with many holes

Self-contained brief for an independent analysis session (written 25.09.2026). The owner is a mechanical designer: FreeCAD 1.1.1 plus his HybridDesign workbench, Windows 11, a laptop with 15.4 GB RAM. This defect belongs to his speed program; earlier defects 012/018/020 are fixed the same way.

See also REFERENCE-plan-E-018.md in this folder (how the sibling defect 018 was fixed; reuse its method and tooling).

## 1. Symptom (owner, 24.09)
- **Action:** in HybridDesign, Fillet on the top face of his part **"Top"** (from his assembly VR6). The top face `Face5` has **101 edges in 94 wires**: an outer boundary plus 93 holes. The solid has 244 faces.
- **What he saw:** the preview took ~24 s. After HD-side fixes (the preview now runs in a background worker and is computed locally around each fillet instead of fusing the whole part) it takes **~8 s**. What remains is mostly OCCT time.
- **Where the ~8 s go now** (HD master 66e75e1+, regular FreeCAD, Top, r=1):

| phase | time |
|---|---|
| BRepFilletAPI_MakeFillet (101 edges) | 1.65 s |
| "differences": boxes cut to region, local generalFuse + point tests | 4.0 s |
| — cutting down to boxes | 1.25 s |
| — local generalFuse and sorting | 2.28 s |
| — HD's own work | ~0.35 s |
| meshing | 1.3 s |
| worker overhead / transfer | ~1 s |

- **Before the HD local-box change**, the full-part path took 16–27 s and showed the problem most clearly (profile below).

## 2. Evidence (read these files)
- **Owner part**, a copy (never use originals): `C:/dev/fillet-perf/parts/Top.FCStd`; also `C:/dev/fillet-local/Top.FCStd`.
- **Probes:** `C:/dev/fillet-perf/probes/{headless_phases,diff_methods,occt_phases}.py` (headless phase timings; generalFuse through FreeCAD and through raw pythonOCC `BRepAlgoAPI_BuilderAlgo`).
- **Native profile, stock:** `C:/dev/fillet-perf/prof/stock/profile.txt` (fcsample, main thread; sampling slows it ~2×):
  - 60.1 % `BRepClass3d_SClassifier::Perform`
  - 52.8 % `BRepClass3d_SolidExplorer::PointInTheFace` → 51.8 % `BRepTopAdaptor_FClass2d::Perform` → 49.9 % `BRepClass_FaceClassifier`
  - 14.7 % `BRepTools::UVBounds` (recomputed per call)
  - inside the fuse: 44.5 % `BOPAlgo_Builder::FillImagesSolids` (33.0 % `BuildSplitSolids`, 30.5 % `BOPTools_AlgoTools::ComputeState`)
- **Other measurements:**
  - generalFuse alone: 13.7–21.3 s on the full part. Raw OCCT through pythonOCC: 16.0 s. So FreeCAD's element map is NOT the cost (`logs/dm1/out.json`).
  - HD point tests (isInside etc.): 7.0–9.6 s + 3.7–5.3 s. Reusing one `BRepClass3d_SolidClassifier` per solid gives 4.3 s vs 5.3 s, so the cost is `Perform` itself, not the set-up.
- **Controller notice with the full context:** `C:/dev/cad-perf-research/_workflows/NOTICES.md`, section "24.09 ~18:30 — fillet on VR6 Top".

## 3. Reading of the cause (hypothesis, to be verified in source)
- Point-in-solid classification casts a ray and, for each face hit, classifies the hit point against the face's 2D boundary: `BRepTopAdaptor_FClass2d` / `BRepClass_FaceClassifier` over ALL wires and edges. It also recomputes `BRepTools::UVBounds` every time.
- With W inner wires, each query is O(W·edges). With many queries (BOP solid-image building, HD's fragment tests) the total is quadratic-looking.
- Nothing is cached per face between queries.
- This is a sibling of **defect 018** (BRepCheck_Face, quadratic in wires), which was fixed with a per-face wire-box index plus a classifier copy with a proven "far outside" shortcut.

## 4. Source locations (OCCT V7_8_1; read-only reference tree `C:/dev/freecad-kernel-fixes/occt`)
- `src/BRepClass3d/BRepClass3d_SClassifier.cxx` — Perform (ray loop over faces)
- `src/BRepClass3d/BRepClass3d_SolidExplorer.cxx` — PointInTheFace, FindAPointInTheFace, and the per-face classifier creation
- `src/BRepClass3d/BRepClass3d_BndBoxTree.*` — existing box tree (check what it covers)
- `src/BRepTopAdaptor/BRepTopAdaptor_FClass2d.cxx` — the face 2D classifier (polygonisation of all wires plus a point-in-polygon test)
- `src/BRepClass/BRepClass_FaceClassifier*`, `src/BRepTools/BRepTools.cxx` — UVBounds
- `src/BOPTools/BOPTools_AlgoTools.cxx` — ComputeState (the callers in BOP)

## 5. Prior art in this program (reuse the method)
- **Defect 018 / plan E** (done):
  - worktrees `C:/dev/fckf-018` and `C:/dev/occt-018`;
  - plan `C:/dev/fckf-018/docs/superpowers/plans/2026-09-22-E-brepcheck-face-018.md`;
  - ledger `.superpowers/sdd/2026-09-22-E-brepcheck-face-018/progress.md`;
  - the classifier copy `BRepCheck_WireClass2d` with an `IsFarOutside`/NearBox shortcut and its proof, plus the verification build comparing old and new on every call.
  - Result: face check ×23–118 on 1024–4096-hole plates, with statuses identical to stock on 2905 shapes.
- **Defect 012 / plan B:** a wire-box prefilter in BRepMesh (identity by construction; strict mesh identity on the corpus).
- **Corpus and tooling:** `C:/dev/freecad-kernel-fixes/build/corpus018/`, the `checkcmp`/`classcmp` harnesses, and the synthetic multi-hole plates (face_grid_1024/4096, bop_plate_1024, prism_plate_4096).

## 6. What a fix must satisfy (owner rules, non-negotiable)
- **Identical results to stock.** Every classification answer (IN/OUT/ON), every BOP result and every status must be identical, proven by construction AND by evidence:
  - a verification build that runs the old and new code on every call and counts mismatches (must be 0);
  - the whole corpus;
  - negative controls (mutants that must be caught).
- **Cheaper computation, not removed checks.** Never slower anywhere (a quick paired sanity check; no long timing campaigns).
- **No public class layout change in OCCT headers** (ABI: FreeCAD links the stock headers). Caches live in side tables inside .cxx files or in existing private members only if the layout is unchanged; check with an ABI/layout probe.
- **Thread safety:** BOP runs in parallel (OSD_Parallel). Any per-face cache must be safe or per-thread.
- **Deliverable:**
  - the patched DLL(s) (likely TKTopAlgo for BRepClass3d/BRepTopAdaptor, TKBO if BOPTools changes), built like conda-forge FreeCAD 1.1.1's OCCT: v142, OCCT exceptions ON;
  - a patch series against V7_8_1;
  - a README with the measurements.
- **Stacking:** TKTopAlgo already carries defect 018; stack on it: `C:/dev/freecad-kernel-fixes/build/variants018/p018/TKTopAlgo.dll`, series in `C:/dev/fckf-018/.../SERIES.md`.

## 7. Suggested approach (for the analyst to verify or replace)
1. **Reproduce** natively (C++ harness, no FreeCAD): classify points against Top's solid and a synthetic N-hole plate for N = 64/256/1024. Plot time against N; expect a slope ≈ 2.
2. **Locate the per-query O(W) work** in PointInTheFace, FClass2d and UVBounds, and what could be cached per face for the lifetime of a SolidExplorer / SolidClassifier.
3. **Candidate fixes:**
   - per-face cached UV bounds;
   - a per-face wire-box index so the 2D classifier only tests wires whose box can contain the point, with a proven far-outside shortcut as in 018;
   - reuse of one FClass2d per face across queries instead of rebuilding it.
4. **Prove identity** as in plan E, then measure: the N-hole slope, Top's fillet preview "differences" phase, and generalFuse on Top.

## 8. Machine rules if you run anything on this machine
- Read `C:/dev/cad-perf-research/_workflows/AGENT-RULES.md`.
- ≤ 1 GB per test process. Gates: free RAM ≥ 1.0 GB and commit ≥ 4 GB.
- Compiles via `C:/dev/tools/buildlock.sh` only.
- FreeCAD via `C:/dev/tools/fcslot.sh` with -u/-s config copies and a 600 s cap. Never run FreeCAD from `C:/dev/fc-test/stock`.
- Never write to `C:/Program Files`. Never kill processes you did not start.
- Plan K (defect 022) is paused and also touches TKTopAlgo/TKBO: do not touch `C:/dev/fckf-022` or `C:/dev/occt-022`.
- Coordinate through `C:/dev/cad-perf-research/_workflows/NOTICES.md`.
