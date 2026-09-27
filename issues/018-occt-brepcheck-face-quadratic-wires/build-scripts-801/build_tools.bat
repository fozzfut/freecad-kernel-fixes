@echo off
rem Native 018 tools against OCCT 8.0.1 headers and implibs from the weekly DLL exports, MSVC 14.50 (as the DLLs).
rem checkcmp801.exe : BRepCheck_Analyzer status dump / phases / fillet / cut / gen / probe / step2brep
rem classcmp801.exe : BRepCheck_WireClass2d of the 018 tree (compiled in) vs weekly TKTopAlgo BRepTopAdaptor_FClass2d
call "C:\dev\toolchains\msvc-14.50\vcvars150.bat" >nul
set IMP=C:\dev\occt8-mig\kb1\implib
set WB=C:\dev\FreeCAD-occt8\FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental\bin
set OUT=C:\dev\occt8-mig\k018\bin-tools
set T=C:\dev\occt8-mig\k018\tools
set SRC=C:\dev\occt-801-018\src\ModelingAlgorithms\TKTopAlgo\BRepCheck
if not exist %OUT% mkdir %OUT%
cd /d %OUT%
for %%L in (TKernel TKMath TKG2d TKG3d TKGeomBase TKBRep TKGeomAlgo TKTopAlgo TKPrim TKBO TKBool TKFillet TKShHealing TKDESTEP TKXSBase TKDE) do (
  if not exist "%IMP%\%%L.lib" (
    python C:\dev\occt8-mig\kb1\tools\mkdef.py "%WB%\%%L.dll" "%IMP%\%%L.def" > nul || (echo MKDEF-FAIL %%L & exit /b 1)
    lib /nologo /machine:x64 /def:"%IMP%\%%L.def" /out:"%IMP%\%%L.lib" > nul || (echo LIB-FAIL %%L & exit /b 1)
  )
)
set INC=@C:\dev\occt8-mig\k018\build\control\TKTopAlgo\inc.rsp
set CF=/nologo /EHa /GR /std:c++17 /MD /O2 /Ob2 /DNDEBUG /fp:precise /D_USE_MATH_DEFINES /DNOMINMAX /wd4996
set LIBS=TKernel.lib TKMath.lib TKG2d.lib TKG3d.lib TKGeomBase.lib TKBRep.lib TKGeomAlgo.lib TKTopAlgo.lib TKPrim.lib TKBO.lib TKBool.lib TKFillet.lib TKShHealing.lib TKDESTEP.lib TKXSBase.lib TKDE.lib psapi.lib
cl %CF% %INC% %T%\checkcmp801.cpp /Focheckcmp801.obj /Fecheckcmp801.exe /link /LIBPATH:%IMP% %LIBS% > checkcmp801.log 2>&1
echo checkcmp801 %ERRORLEVEL%
cl %CF% /I"%SRC%" %INC% %T%\classcmp801.cpp "%SRC%\BRepCheck_WireClass2d.cxx" /Foclasscmp801\ /Feclasscmp801.exe /link /LIBPATH:%IMP% %LIBS% > classcmp801.log 2>&1
echo classcmp801 %ERRORLEVEL%
echo TOOLS-DONE
