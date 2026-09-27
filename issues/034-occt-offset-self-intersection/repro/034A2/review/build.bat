@echo off
call "C:\dev\toolchains\msvc-14.50\vcvars150.bat" >nul
set IMP=C:\dev\occt8-mig\fillet-corner-r2\build\implib
set IMP2=C:\dev\occt8-mig\kb1\implib
set INC=@C:\dev\occt8-mig\offset-034\build\final\inc.rsp
set SRC=C:\dev\occt8-mig\offset-034a2\review
cd /d C:\dev\occt8-mig\offset-034a2\review
set CF=/nologo /EHa /std:c++17 /MD /O2 /DNDEBUG /fp:precise /D_USE_MATH_DEFINES /DNOMINMAX /wd4996
set LIBS=TKernel.lib TKMath.lib TKG2d.lib TKG3d.lib TKGeomBase.lib TKGeomAlgo.lib TKBRep.lib TKTopAlgo.lib TKFillet.lib TKOffset.lib TKBO.lib TKBool.lib TKPrim.lib TKDESTEP.lib TKXSBase.lib TKDE.lib advapi32.lib psapi.lib
for %%P in (%*) do (
  cl %CF% %INC% /I%SRC% %SRC%\%%P.cpp /Fo%%P.obj /Fe%%P.exe /link /LIBPATH:%IMP% /LIBPATH:%IMP2% %LIBS% > %%P.log 2>&1
  if errorlevel 1 (echo %%P FAILED) else (echo %%P 0)
)
