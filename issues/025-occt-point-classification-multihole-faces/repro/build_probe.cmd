@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" -vcvars_ver=14.29 >nul
if errorlevel 1 exit /b %errorlevel%
cd /d C:\dev\freecad-kernel-fixes\build\025\probe
cl /nologo /O2 /EHsc /MD /std:c++17 /I. /IC:\dev\freecad-kernel-fixes\build\occt-check\inc C:\dev\freecad-kernel-fixes\issues\025-occt-point-classification-multihole-faces\repro\probe.cpp DiagnosticFClass2d.cxx PreparedFClass2d.cxx PreparedExplorer.cxx PreparedClassifier.cxx /Fe:probe.exe /link /LIBPATH:C:\dev\freecad-kernel-fixes\build\implib TKTopAlgo.lib TKBRep.lib TKG2d.lib TKG3d.lib TKGeomBase.lib TKGeomAlgo.lib TKMath.lib TKernel.lib psapi.lib > build.log 2>&1
exit /b %errorlevel%
