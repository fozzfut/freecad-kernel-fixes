@echo off
call "C:\dev\toolchains\msvc-14.50\vcvars150.bat" >nul
set O=C:\dev\occt8-mig\offset-034b2\r1c\abi
dumpbin /nologo /exports C:\dev\occt8-mig\offset-034b2\r1c\final\TKOffset.dll > %O%\exp-final.txt
dumpbin /nologo /exports C:\dev\FreeCAD-occt8\FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental\bin\TKOffset.dll > %O%\exp-weekly.txt
dumpbin /nologo /imports C:\dev\occt8-mig\offset-034b2\r1c\final\TKOffset.dll > %O%\imp-final.txt
dumpbin /nologo /imports C:\dev\freecad-kernel-fixes\build\variants801\034A2r2\TKOffset.dll > %O%\imp-a2.txt
