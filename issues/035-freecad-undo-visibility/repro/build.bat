@echo off
rem build.bat <ctl|fix> <srcdir>: FreeCADGui.dll of fcD/bld144 with four sources swapped (mkgui.py), portable MSVC 14.44
call C:\dev\toolchains\msvc-14.44\vcvars144.bat || exit /b 1
set LP=C:\dev\occt8-mig\freecad-side\libpack\LibPack-26.3.0-v3.5.5-x64-Release
set VSX=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake
set PATH=%LP%\bin;%VSX%\CMake\bin;%VSX%\Ninja;%PATH%
C:\Users\B72A~1\AppData\Local\Programs\Python\Python313\python.exe C:\dev\occt8-mig\undovis\tools\mkgui.py %1 %2
echo rc_build=%ERRORLEVEL%
