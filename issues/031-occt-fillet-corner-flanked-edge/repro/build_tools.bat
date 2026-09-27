@echo off
call "C:\dev\toolchains\msvc-14.50\vcvars150.bat" >nul
set IMP=C:\dev\occt8-mig\kb1\implib
set INC=@C:\dev\occt8-mig\kb1\build150r\p001\TKFillet\inc.rsp
cd /d C:\dev\occt8-mig\fillet-corner\bin
set CF=/nologo /EHa /std:c++17 /MD /O2 /DNDEBUG /fp:precise /D_USE_MATH_DEFINES /DNOMINMAX /wd4996
cl %CF% %INC% ..\tools\filcorner.cpp /Fofilcorner.obj /Fefilcorner.exe /link /LIBPATH:%IMP% TKernel.lib TKMath.lib TKG2d.lib TKG3d.lib TKGeomBase.lib TKBRep.lib TKTopAlgo.lib TKFillet.lib > filcorner.log 2>&1
echo filcorner %ERRORLEVEL%
