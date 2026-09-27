# Reference for defect 025: how defect 018 (plan E) was fixed

Written 25.09.2026 for an independent session working on defect 025 (see BRIEF.md in this folder). 018 is the closest sibling: the same "per-query work over all wires of a multi-hole face" pattern, fixed with identity preserved. Use it as a method template. Do NOT modify its files.

## 1. Where everything is
- **The authoritative write-up** (Russian, detailed, with file:line proofs): `C:/dev/fckf-018/issues/018-occt-brepcheck-face-quadratic-wires/README.md`
- **Plan:** `C:/dev/fckf-018/docs/superpowers/plans/2026-09-22-E-brepcheck-face-018.md`, plus the addendum `2026-09-22-E-task6b-brepcheck-rest.md`
- **Ledger** (every decision, review, number): `C:/dev/fckf-018/.superpowers/sdd/2026-09-22-E-brepcheck-face-018/progress.md` and `review-t*.md`
- **OCCT source with the fix:** `C:/dev/occt-018`, branch `perf/018-brepcheck`; base tag `V7_8_1` = `bd2a789f`
- **Patches:** `…/patches/` — `SERIES.md`, 0001–0007, and `018-full.patch`
  - 0001 and 0002 are conda-forge's own patches, already in stock FreeCAD's DLL; they must be kept.
  - Apply with `git -c core.autocrlf=false apply` (plain `git apply` writes CRLF on this machine).
- **Shipped DLL:** `C:/dev/freecad-kernel-fixes/build/variants018/p018/TKTopAlgo.dll`, md5 `2444c450b94a3ffb7ff9b87b99bb01b5`. Delivered in `C:/dev/FreeCAD-perf/bin`.
- **Measurements:** `…/measurements/`
  - `baseline.md`, `control-vs-stock.md`, `determinism.md`;
  - per variant: `p018a.md`, `p018b.md`, `p018b2.md`, `p018c.md`, `p018c2.md`;
  - `classifier-copy.md`, `regression.md`, `in-freecad.md`, `abi*.md`, `linkmap*.md`, `shipped-dll.md`.
- **Tooling** (reusable for 025):
  - `repro/cpp/checkcmp.cpp` — runs BRepCheck on a corpus and dumps statuses per sub-shape; compares variants;
  - `repro/cpp/classcmp.cpp` — compares the copied classifier against the original, point by point, with far/near sets;
  - `repro/cpp/wires6b.cpp`, `bench6b.cpp`, `fcsample.cpp` (native sampling profiler);
  - `build-scripts/build-occt-check.ps1` — builds OCCT like conda-forge: v142, exceptions ON, PDB;
  - `abi-check.ps1`, `linkmap_check.py` (use `--objdir`: matching by name gives false FAILs), `gen_wireclass2d.py`, `install-into-freecad.ps1`, `check_delivery.py`;
  - `C:/dev/freecad-kernel-fixes/build/corpus018/` — corpus lists, runner `run_check.py` (1 GB cap, gates), synthetic plates, logs.

## 2. What 018 fixed
- `BRepCheck_Face` (+ Wire/Edge/Vertex/Shell) had quadratic passes on faces with N wires:
  - IntersectWires (all pairs);
  - ClassifyWires (one FClass2d per wire, then IsInside for every other wire);
  - OrientationOfWires (linear scan of a map);
  - InContext scans (explorer over the whole context);
  - and more found in the addendum: Closed2d, SelfIntersect, Wire::Orientation, Shell::Orientation/Closed.
- **Result** (control vs patched, same statuses on all 2905 corpus shapes):
  - face analyser ×23–32 on 1024-hole plates, ×87–118 on 4096;
  - fillet IsValid ×19–24 on a 1024-hole plate;
  - Part::Cut with checks ×6.3–7;
  - PartDesign fillet in FreeCAD ×4.1;
  - growth slope 1.1–1.2 instead of ~1.9.

## 3. The method (copy this for 025)
1. **Baseline and D0.**
   - Build a CONTROL DLL from unmodified V7_8_1 + conda patches with the same toolchain.
   - Prove control == stock on the whole corpus (statuses identical, same exports, same linker) before touching code. Only then do patched-vs-control comparisons mean anything.
2. **Same calls, same order; skip only what is proven.** The patched code performs the same checks in the same order and skips a call only when its answer is PROVEN without it. Wherever a precondition is not met, fall back to the original code.
   - Proofs are written as comments in the code with file:line references to the stock logic.
3. **Beware the naive box trap** (README §"Почему наивные боксы не годятся"). The stock answer is defined by the classifier's CODE, not by geometry:
   - `BRepTopAdaptor_FClass2d` starts its box at (0,0) (`BRepTopAdaptor_FClass2d.cxx:111-112`);
   - failed discretisation (`TabOrien(1) = -1`) and degenerate `CSLib_Class2d` (N = 0) behave specially;
   - points within the polygon tolerance go to the full classifier;
   - stock stops at the FIRST intersecting pair and catches exceptions.
   A box prefilter must reproduce exactly these semantics, or fall back.
4. **Classifier copy.**
   - 018 generated `BRepCheck_WireClass2d` as a byte-faithful copy of `BRepTopAdaptor_FClass2d` (script `gen_wireclass2d.py`), with only prescribed diffs: header lines, `recordPolygon` hooks, and a proven `IsFarOutside`/NearBox shortcut.
   - inf/NaN points always get the full `Perform`; only `Perform(P, false)` may use the shortcut.
   - The copy lets you cache per-wire data without changing the public class layout (ABI).
5. **Verification build.** A build variant runs BOTH the old and the new path on every call and counts mismatches. It must be 0 across the whole corpus, at par 0 and par 1 (parallel mode).
6. **Negative controls.** Build mutants (e.g. grid radius one cell too small, a dropped condition, skipping touching boxes) and show the corpus or a synthetic face catches each one. Record the mutants that cannot be caught and why.
7. **ABI.** No public header class layout change; check with the layout probe/abi-check (all exports present, no unresolved imports). Linkmap with `--objdir` shows every differing symbol is our own code.
8. **Determinism.** Run stock against stock first. Shapes whose outcome varies between stock runs (for example the huge assemblies that run out of memory) are excluded explicitly, with the reason recorded.
9. **FreeCAD level.**
   - Install the DLL into a run COPY (never Program Files, never C:/dev/fc-test/stock itself).
   - Run FreeCAD's test suites (Part, PartDesign, …) and the HybridDesign suites on stock and patched; compare runner decisions and console messages. Identity includes messages.
   - Time one owner action (fillet on a 1024-hole plate).
10. **Delivery.** `SERIES.md` plus `018-full.patch`; a patch gate (patch non-empty, equals the build input, the series applied to V7_8_1 equals HEAD); install/revert tested on a copy; README with numbers and a not-measured list.

## 4. Lessons / pitfalls from 018
- MSBuild logs are UTF-16: convert them before grepping for warnings.
- `CMakeCache` shows `BUILD_RELEASE_DISABLE_EXCEPTIONS:UNINITIALIZED=OFF`. That is fine: verify there is no `No_Exception` in the vcxproj and that the probe throws `Standard_OutOfRange`.
- Linkmap matching by symbol name gave 21 false FAILs (destructors, RTTI, strings). Compare object bytes and relocations instead (`--objdir`).
- Timing on this laptop is noisy (VS Code and other agents). Use min-of-N and interleaved series; the owner has now said to skip long before/after series.
- Keep every test process ≤ 1 GB (the job-object cap in the harness).
- 018 lives in TKTopAlgo. 025 will likely also touch TKTopAlgo (BRepClass3d, BRepTopAdaptor): **stack 025 on the 018 series**, and prove identity against a control that already contains 018.
