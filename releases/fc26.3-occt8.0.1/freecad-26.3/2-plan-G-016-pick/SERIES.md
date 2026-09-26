# Plan G task B on FreeCAD 26.3dev (weekly 2026.09.23, git 019f5c5, OCCT 8.0.1)

Apply in order with `git -c core.autocrlf=false am --keep-cr` (the sources are stored with CRLF; plain `git am`
strips the CRs and fails on AppPartGui.cpp) onto plan D's series tip `1d95905` (branch mig/freecad-side); the result is the tree of
`946127c` (branch mig/G in C:/dev/occt8-mig/fcD/src). They also apply cleanly onto plain `019f5c5`; the tested
stack is D + G.

| patch | commit | what |
|---|---|---|
| 0001-PartGui-016-G-B.patch | a3c8b97 | face/edge ray-pick acceleration: SoBrepFaceSet::generatePrimitives and the new SoBrepEdgeSet::rayPick generate only the triangles/segments the pick line/cone can reach, exactly as Coin would (new SoBrepPickAccel.{h,cpp}; PartGui.setPickAccel / pickAccelStatus; parameter Mod/Part/PickBVH) |
| 0002-PartGui.patch | 946127c | the side table and its mutex are never destroyed (no sensor detach at process exit) |

Build, checks and numbers: C:/dev/freecad-kernel-fixes/build/variants801/G/README.txt; ledger
C:/dev/occt8-mig/progress.md, section "Lane G".
