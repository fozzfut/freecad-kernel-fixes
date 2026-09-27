variants801/viewpy - FreeCADGui.dll for FreeCAD 26.3dev weekly 019f5c5 = 028 + 033 (lane section-hang, 27.09.2026)

FreeCADGui.dll          d5b158790d789d91e4f09e4674c6cacf = fcD/src mig/viewpy-exc 3f92900 (on b593a6f = the 028 tree),
                        portable MSVC 14.44, LibPack 3.5.5, Release. Built by C:/dev/occt8-mig/sechang/fc/mkgui.py:
                        bld144's own compile lines for View3DPy.cpp / View3DViewerPy.cpp (source path, /Fo, /Fd changed)
                        and bld144's own FreeCADGui.dll link block (same objects in the same order, two swapped).
                        bld144 and the fcD/src checkout were not written.
control/FreeCADGui.dll  f4225afe95be18abdc8f23afc2cd1ced = same pipeline, sources of b593a6f unchanged. Differs from the
                        shipped 028 (680c370e) in 8 bytes only (2 PE timestamps + checksum; sechang/fc/abi/ctl-vs-dlv028-bytes.txt)
                        -> the pipeline reproduces 028; the fix build = 028 + the patch.

033: View3DInventorPy::method_varargs_ext_handler and View3DInventorViewerPy::method_{varargs,keyword}_ext_handler
set the Python error (RuntimeError, same message) and return NULL instead of 'throw Py::RuntimeError' out of a function
the interpreter calls directly. Before: e.g. view.saveImage offscreen ("Offscreen rendering failed") unwound through
CPython's C frames, the calling Python stack was lost, the -t runner / a macro never returned (HD section_gui hung).
Patch + LITERATURE: issues/033-freecad-viewpy-exception.

ABI (fcD/tools/abi.py, sechang/fc/abi): fix vs weekly and vs 028: exports 12230, missing 0, extra 0, imports +0/-0,
CRT +0/-0, unresolved 0 -> ships ALONE like 028.
Tests (C:/dev/occt8-mig/sechang/runs): probe sh_saveimg offscreen: 028 -> script stops inside saveImage, never reaches
'ALIVE' (killed at the timeout); 028+033 -> 'RuntimeError: Offscreen rendering failed' caught, ALIVE, END.
TestGuiBase offscreen (fcD/gui list): 37 run, same verdicts and messages on 028 and 028+033 (stock's own 1 FAIL + 1 ERROR).
TestPartGui offscreen 15/15 OK both. TestGuiBase windowed: not measured - both DLLs exceed the 1 GB process cap there.
HD section_gui offscreen on 028+033: 19 tests, EXIT 0.
NOT installed: delivery/pending-033-viewpy.txt has the install-all.sh / revert.bat lines (review first).
