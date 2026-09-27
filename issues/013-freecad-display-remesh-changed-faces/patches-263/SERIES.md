# Plan D (013 + 014 + F-DLV1) on FreeCAD 26.3dev / OCCT 8.0.1

Base: FreeCAD weekly 2026.09.23, git `019f5c5`. The series is the branch `mig/freecad-side` of `C:/dev/fc-263-src`
(`git format-patch 019f5c5..1d95905`). Apply in order with `git am` or `git apply --index`. Applied to `019f5c5`, it
gives the tree of `1d95905` byte for byte (checked 26.09: `git diff --cached 1d95905` is empty).

| # | commit | what |
|---|---|---|
| 0001 | 3f0d9bb | 014: preference `Mod/Part/MeshControlSurfaceDeflection`, default true (= stock) |
| 0002 | c16ab21 | 013: `DisplayMeshReuse` registry in `setupCoinGeometry` (re-mesh only changed faces) |
| 0003 | fbdb28b | F-DLV1 part 1: kept faces and their edges get `Modified` (after the lock check), as `BRepTools::Clean` gives them |
| 0004 | aa23614 | F-DLV1 part 2: `afterMeshing()`, where kept faces get `BRepTools::Update` + `Modified`, as BRepMesh does for faces it re-meshes |
| 0005 | 1d95905 | OCCT 8.0.1: the header `BRep_ListIteratorOfListOfCurveRepresentation.hxx` was removed, so it is dropped |

Only files under `src/Mod/Part/Gui` change: `PartGui.pyd` changes, and `Part.pyd` is built from unmodified source.

Build: portable MSVC 14.44 (cl 19.44.35229), LibPack 3.5.5, Release, no PCH, Ninja -j4. The outputs are in
`C:/dev/freecad-kernel-fixes/build/variants801/D/`. Identity against stock 26.3 was checked on the patched tree,
and the evidence is in `C:/dev/occt8-mig/fcD/` (ledger: `C:/dev/occt8-mig/progress.md`, lane "plan D on 26.3").
