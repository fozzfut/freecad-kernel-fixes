# Issue 034, lane B2, round 3 (continuation after the 28.09 ~09:20 session restart)

Branch `perf/801-034b2` in `C:/dev/occt-801-034-b2`: commit `0476266c61` on r2 `bdef38f1` (on A2 r2 `7192f9ea`);
the WIP chain of this round is kept as `backup/801-034b2-r3-wip` (`bbdd25f5`, same tree `e7e7ef36`).

## Class
Free-form faces whose offset folds on a PART of the face (a principal factor 1 - d k < 0 on a region inside the face
or across it): elliptic / B-spline profile walls (fold bands, X a line), B-spline ridges and bumps (closed lenses with
two miter points), NURBS forms, location and baked placements, offsets and thick solids (inward).

## Root causes (A2 / r2, file BRepOffset_MakeOffset.cxx of 7192f9ea)
1. Nothing trims a partial fold: the offset face of a partially folding face is built untrimmed
   (BRepOffset_Offset + MakeLoops trim only at intersections with neighbours).
2. Stage A guard misses folds: `faceMayFold034` samples 16 (extrusions) or 2/span points; `resultIsBroken034`'s BOP
   self-interference compares DIFFERENT faces only, `resultTooClose034` samples 4x4 per face. Measured silent wrong on
   the DELIVERED f5fcd5a0: bump d2.8/3.1, bump2016 d1.6/2.2 (valid + BOP clean, oracle MIX), w18 d3 (INVALID returned),
   dumbbell_rod thick -1 Int (A2 probe set: a 0.2 tube kept in a 0.8 rod, MC 1 bad).
3. Stock pass cannot be reused for the lens: split faces need the planar substitution, analysis and caps built on
   the split input (the WIP split after BuildFaceComp and refused planar-substituted neighbours).

## Fix (see LIT-r3c.txt for sources / own derivations)
- stock-first two passes with a complete state snapshot (OffsetState034c); split-first lens pass; skin; history remap;
- X traced (divided difference), refined until both preimage interpolants give the same offset within 1e-9 size;
- certificate of the pieces (interval bounds, miter regions only unresolved); stage A certified; fold seeds;
- folded-point check of every result (fold parameter inside an image face = proven wrong -> error / lens pass);
- exact corners for prolonged rim sections (GeomAPI_IntCS) instead of the estimated reach.

## Evidence (all light, <= 150 s, <= 60 MB per process)
- `fam_r3.txt` / `runs/fam-c4.txt` (57 members, exact references `ref/ellref.py`, `ref/profref.py`, cross-section
  area `tools/xa.cpp`); `runs/pdthk-*.txt` (PartDesign Thickness path); identity `runs/{class,corp,rv116,b33,rvx}-*`,
  `runs/fam3-*`, `runs/cases-*`, `runs/more-*`; cost `runs/pairs-c4.txt`; FreeCAD suites in fcD/runs/b2r3-*.
