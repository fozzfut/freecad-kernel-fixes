Review R-034-loc r1 (independent, adversarial) - 29.09.2026
Subject: perf/801-034loc fbe511b2de (= perf/801-034int b45eb1e40d + 1 commit), staged TKOffset db26a52d.
Run copies (lane's, unchanged): fcD/rc/loc2r2 (delivery + r1 TKOffset db26a52d), fcD/rc/loc2dlv (delivery, TKOffset
c2732f46), fcD/rc/weekly (stock TKOffset 67f22d0d, bisect only). All other bin/lib DLLs of loc2dlv/loc2r2 == delivery.
Every FreeCADCmd via fcD/tools/fcrun.sh (fcslot, timeout 600, fresh cfg copies, runguard 1 GB); peak <= 90 MB.

VERDICT: NOT ACCEPTED, class closed: no.

1. CODE REVIEW (both hunks correct, keep them):
 - CheckInputData/checkSinglePoint: sampled point + D1U/D1V moved to the located frame only when L is not identity;
   the degenerated points come from BRep_Tool::Pnt (located) -> same frame. Correct; rigid-invariant check.
 - BRepOffset_Offset::Init: MinApex/MaxApex are TheSurf points; TheSurf is local when !IsTransformed (cone/analytic
   kept with location L) and already located when IsTransformed (BSpline/revolution/extrusion/offset copied +
   transformed) -> the transform after both branches under (!L.IsIdentity() && !IsTransformed) is exactly right.
 - Unlocated inputs: both new transforms are skipped (L identity) -> code path unchanged (confirmed by runs, 3.).

2. D0: TKOffset built by me from C:/dev/occt-801-034loc at fbe511b2de (same path, build_tk.py, MSVC 19.50, /MP2,
   buildlock, 0 warnings in cl.log) = d0/TKOffset.dll 310edcfa: differs from staged db26a52d in 4 bytes only
   (PE TimeDateStamp @273-274 + debug-directory timestamp in .rdata @1439621-1439622). Staged DLL == reviewed source.

3. IDENTITY (unlocated inputs, tools/rvid.py, order-independent fingerprint: volume, counts, sorted per face/edge/
   vertex type/area/length/CoM/point/tolerance/orientation): 57 cases (40 results + 17 errors, 12 member kinds incl.
   hole/vfil/sphere/capsule/spheroid/cone apex) r1 == delivered in 2 runs each; each DLL == itself run to run.
   NEG (one vertex tolerance x1.5 on every 'none' row): 18/18 caught. NOTE: raw BREP text md5 is NOT a usable identity
   on this stack - entity order and regularity-record face order change run to run on EVERY DLL (brep/ dumps).

4. INDEPENDENT ORACLE (tools/rvloc.py, FreeCAD Part API, not the lane's C++ harness), NEW members: apex-DOWN cone
   (MinApex branch), lemon (spindle-torus revolve, 2 poles), prolate spheroid (Geom_SurfaceOfRevolution, 2 poles),
   capsule thick (analytic volume 536.165 = pi*512/3 exact), sphere with side hole thick (removed curved wall, poles
   kept), open single spherical face, rotation about the pole axis (TZ), pure translation (TT); variants none / geo
   (BRepBuilderAPI_Transform copy) / loc (root) / nest (shell location inside a located solid) / geon.
   Twin rule (tools/twin.py, loc==geo, nest==geon): delivered 20 EQ / 36 DIFF -> r1 51 EQ / 5 DIFF. NEG caught.
   r1 fixes (== twin): sphere/dome/spheroid/capsule/spface located offset + thick, conedn located == twin errors.
   REMAINING DIFF (r1): sphx thick located (T1, TF, loc + nest) -> OK but INVALID (Unorientable) while the twin is
   valid (delivered: ERR); lemon nest -> invalid body vs twin ERR (frame-sensitive member, twin itself fails).

5. FINDING F1 (CRITICAL, class member, stock - NOT fixed by r1): located REMOVED CURVED FACE (cork) -> result
   tolerances ~ size of the placement displacement. tools/diag4.py (Part API) and tools/fcdoc.py (FreeCAD document):
   box 40x30x10 with a through hole r5, thickness -1 removing the HOLE WALL (cylinder):
     geo twin: tolV 2e-7, BOP check ok; located T1: tolV=tolE=20.6, BOP check 176 errors; located TT (250,-40,75):
     tolV=tolE=277, 392 errors; valid=1, same volume -> SILENT. Same on delivered c2732f46 and stock weekly 67f22d0d.
   sphere r10 with a Z hole (no poles), same op: twin 1.1e-6, located 27.9 / 277. Plane corks (hole thick removing
   the top) are clean -> the curved/periodic cork is the trigger (blown edges = the cork SEAM edges in the result,
   diag3). FreeCAD user path (fcdoc.py): Part::Cut(Box, placed Cylinder) + Part::Thickness(hole face), Up-to-date,
   valid=1, tolV 26.3 even at identity Cut placement (the tool Placement already locates the hole face), 35.6 at p1,
   295 at (250,-40,75); AND the SOURCE Cut shape's vertex tolerance becomes the same (26.3/35.6/295): the algorithm
   raises tolerances on vertices it shares with the input -> the user's source object is corrupted too.
   With r1 this defect also reaches pole faces: sphx thick (sphere + side hole, remove hole wall) located ->
   Unorientable faces + tol 34.6/277 (delivered: ERR 'command not done'). FreeCAD row 'sphx tr': delivered
   Touched|Invalid -> r1 Up-to-date with an invalid body (silent in the tree).
6. STOCK FINDINGS outside the class (for other lanes): conedn (apex-down cone) thickness -1 Arc removing the top
   plane gives valid=1 vol=2e+100 (unbounded solid) on UNLOCATED input, all DLLs -> silent wrong geometry
   (R-034-frame/apex lane); lemon offset -0.5 Intersection -> Access violation on all DLLs; conedn/lemon/sphx offset
   frame sensitivity (geo != none) as the lane reported (R-034-frame).
7. LITERATURE: frame bug, no new algorithm; Jackson 1995 SPM (local tolerances must cover only the geometric gap -
   a tolerance ~ placement distance is a frame error) already cited by lane cav. No web search (budget).

Files: tools/ (rvloc.py rvid.py diag1-4.py diag4mem.py fcdoc.py dumpc.py twin.py), runs/, d0/ (build.bat,
cl/link logs, TKOffset.dll 310edcfa), brep/.
