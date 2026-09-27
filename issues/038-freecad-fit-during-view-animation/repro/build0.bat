@echo off
rem build0.bat: D0 control - FreeCADGui.dll of fcD/bld144 with exactly the four sources the delivered 035 build swapped
rem (read-only from C:\dev\occt8-mig\undovis\src-fix, same compile lines as undovis/tools/mkgui.py)
call C:\dev\toolchains\msvc-14.44\vcvars144.bat || exit /b 1
set LP=C:\dev\occt8-mig\freecad-side\libpack\LibPack-26.3.0-v3.5.5-x64-Release
set VSX=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake
set PATH=%LP%\bin;%VSX%\CMake\bin;%VSX%\Ninja;%PATH%
set MKMOD_FLAT=C:\dev\occt8-mig\undovis\src-fix
C:\Users\B72A~1\AppData\Local\Programs\Python\Python313\python.exe C:\dev\occt8-mig\vr6unconf\tools\mkmod.py gui0 d0 C:\dev\occt8-mig\vr6unconf\build\none
echo rc_build=%ERRORLEVEL%
