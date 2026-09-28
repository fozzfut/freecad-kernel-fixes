#!/bin/bash
# inc.sh <bn|bt> : incremental TKOffset build of C:/dev/occt-801-034-b2 (Inter3d, MakeOffset, Tool recompiled; others = stock objs of build/final)
D=$1; R=C:/dev/occt8-mig/offset-034b2/r3c/$D
DEF=""; [ "$D" = bt ] && DEF="/DOCCT034B2_TRACE"
mkdir -p $R/src && cp C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_{MakeOffset,Tool,Inter3d}.cxx $R/src/
cat > $R/b.bat <<EOB
@echo off
call "C:/dev/toolchains/msvc-14.50/vcvars150.bat" >nul
cd /d "$R"
set MP=/MP3
if "%BUILDLOCK_LOWMEM%"=="1" set MP=/MP2
cl /c /nologo %MP% /EHa /GR /std:c++17 /O2 /Ob2 /DNDEBUG /MD /fp:precise /W4 /wd26812 /wd4996 /DNOMINMAX /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_DEPRECATE /D_WIN32_WINNT=0x0601 /DHAVE_FREETYPE /DHAVE_VTK /DHAVE_RAPIDJSON /DHAVE_EIGEN $DEF /bigobj @inc.rsp /Foobj\ src\BRepOffset_MakeOffset.cxx src\BRepOffset_Tool.cxx src\BRepOffset_Inter3d.cxx > cl.log 2>&1
echo CL-EXIT=%ERRORLEVEL%
if not "%ERRORLEVEL%"=="0" exit /b 1
link /nologo /DLL /MACHINE:X64 /OUT:TKOffset.dll /IMPLIB:TKOffset.lib obj\*.obj TKOffset.res C:\dev\occt8-mig\kb1\implib\TKFillet.lib C:\dev\occt8-mig\kb1\implib\TKBRep.lib C:\dev\occt8-mig\kb1\implib\TKTopAlgo.lib C:\dev\occt8-mig\kb1\implib\TKMath.lib C:\dev\occt8-mig\kb1\implib\TKernel.lib C:\dev\occt8-mig\kb1\implib\TKGeomBase.lib C:\dev\occt8-mig\kb1\implib\TKG2d.lib C:\dev\occt8-mig\kb1\implib\TKG3d.lib C:\dev\occt8-mig\kb1\implib\TKGeomAlgo.lib C:\dev\occt8-mig\kb1\implib\TKShHealing.lib C:\dev\occt8-mig\kb1\implib\TKBO.lib C:\dev\occt8-mig\kb1\implib\TKPrim.lib C:\dev\occt8-mig\kb1\implib\TKBool.lib > link.log 2>&1
echo LINK-EXIT=%ERRORLEVEL%
if not "%ERRORLEVEL%"=="0" exit /b 1
echo BUILD-OK
EOB
bash C:/dev/tools/buildlock.sh cmd //c "$(cygpath -w $R)\b.bat"
grep -E "error|warning C" $R/cl.log | head -30
md5sum $R/TKOffset.dll
