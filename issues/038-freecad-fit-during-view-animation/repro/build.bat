@echo off
rem build.bat <gui|part> <ctl|fix>: lane vr6-unconf module build from fcD/bld144 objects + overlay sources (mkmod.py), portable MSVC 14.44
call C:\dev\toolchains\msvc-14.44\vcvars144.bat || exit /b 1
set LP=C:\dev\occt8-mig\freecad-side\libpack\LibPack-26.3.0-v3.5.5-x64-Release
set VSX=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake
set PATH=%LP%\bin;%VSX%\CMake\bin;%VSX%\Ninja;%PATH%
C:\Users\B72A~1\AppData\Local\Programs\Python\Python313\python.exe C:\dev\occt8-mig\vr6unconf\tools\mkmod.py %1 %2 C:\dev\occt8-mig\vr6unconf\build\ovl-%1-%2
echo rc_build=%ERRORLEVEL%
