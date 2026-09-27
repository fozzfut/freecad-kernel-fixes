@echo off
rem build_d0.bat: round 2 D0 - FreeCADGui.dll of fcD/bld144 with the five 035-PE sources (3eccec5) from a same-length path
call C:\dev\toolchains\msvc-14.44\vcvars144.bat || exit /b 1
set LP=C:\dev\occt8-mig\freecad-side\libpack\LibPack-26.3.0-v3.5.5-x64-Release
set VSX=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake
set PATH=%LP%\bin;%VSX%\CMake\bin;%VSX%\Ninja;%PATH%
C:\Users\B72A~1\AppData\Local\Programs\Python\Python313\python.exe C:\dev\occt8-mig\vr6unconf\tools\mkmod.py gui2d0 d0 C:\dev\occt8-mig\vr6unconf\d
echo rc_build=%ERRORLEVEL%
