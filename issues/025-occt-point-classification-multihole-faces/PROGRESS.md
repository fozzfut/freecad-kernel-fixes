# 025: execution ledger

2026-09-25, Codex. Research status: DONE_WITH_CONCERNS; production fix NOT complete.

## Owner decision (latest, overrides initial prioritization)
Latest owner direction: first perform a deep primary-literature review and inspect OCCT 8 before selecting an implementation. Seek a mathematically stronger, cheaper common-kernel mechanism. Removing duplicate passes is neither mandatory nor a substitute for changing the algorithm. The earlier winding prototype is a feasibility experiment, not the selected solution. No rendering-only preview, HD-only workaround or accuracy reduction.

## Scope of modifications
Only issue 025 and build/025 research artifacts, plus this session's coordination notice. No edits to installed FreeCAD, 018, paused 022, deployed DLLs or unrelated worktree changes. No commits or deployment.

## Verified findings
- Existing intersectors and FClass2d objects already have a per-face lifetime; not everything is rebuilt per query.
- Native diagnostic on Top Face5: 94 valid polygon classifiers; no bad-wire fallback. 0/512 random queries entered exact fallback; 473/505 boundary-focused queries entered it because the polygon answer was ambiguous.
- Thus the alternative must cheaply handle points near curves, not just accelerate random points away from them.
- Stock explorer reuse and private prepared-adjacency C++ prototype are retained as fallback comparisons. Native diagnostic/prepared results: 17,653 queries, zero observed mismatches, peak working set 19,779,584 bytes. This is not corpus-wide production identity certification.

## Algorithm replacement prototype
repro/bezier_winding_boundary.py evaluates winding via positive-weight rational Bezier control hulls and homotopy-preserving chord substitution; no curve/ray intersection solve on its own path. A BVH over closed wires rejects unrelated contours. Distance bounds from control-point capsules handle ON separately. At the exact tolerance threshold the prototype still defers to stock.

- Top: 256 random and 606 boundary-focused points, zero mismatches; the second prototype needed no stock fallback on these two sets.
- Five planar faces: 3,191 distinct query entries, each compared in two new modes; zero mismatches. These samples are not real BOP traces.
- Extra tolerance/curve regression: 1,959 query entries, zero mismatches; 210 of them used stock fallback at the tolerance threshold. Includes ordinary and rational cubic Bezier curves.
- Negative controls detected missing holes (93 Top hole-center disagreements) and flattening curved boundaries (74/77 disagreements on cubic/rational cubic fixtures).
- Early timings improve large perforated faces but regress small boundary-heavy cases in Python. No claim of universal speedup or end-to-end FreeCAD acceleration.

## Next engineering gate
First compare the current upstream 8.0.1 mechanism and compatibility against 7.8.1, then obtain a short real BOP query trace. Evaluate prepared curved point location (Hemmer et al.), local rational-curve predicates (Spainhour et al.; Bao et al.), certified numeric filters, and conditional signed BOP relations (BOOLE). Do not continue the existing prototype by inertia. Preserve tolerance/exception/message behavior; production delivery still requires regression, mutants, threading and ABI checks. A migration to OCCT 8 requires a compatible FreeCAD rebuild, not a DLL swap.

Details, measurements, sources and limitations: MECHANISM-RESEARCH.md.
## Literature and upstream review — 25.09.2026

LITERATURE-REVIEW.md annotates 27 publications, distinguishes full-text evidence from abstracts, and maps article algorithms to the missing OCCT work. No reviewed single paper supplies a complete drop-in replacement. Prepared curved point location changes dependence on boundary count; ON certification remains an independent requirement. OCCT already groups connected faces before classification, so new BOP work must demonstrate additional signed relations between those blocks.

OCCT8-REVIEW.md records official release/PR/source evidence. 8.0.1 is stable; the inspected FClass2d still has the per-wire polygon loop and exact fallback. Many-hole BRepCheck improvements address the sibling validation problem. Release-note timing claims cannot be copied without checking final merged revisions.

Research only this step: no native builds/tests, no deployed changes, no commits.