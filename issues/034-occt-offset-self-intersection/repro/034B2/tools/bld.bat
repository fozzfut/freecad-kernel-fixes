@echo off
set SRC=C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_Inter3d.cxx
call C:/dev/occt8-mig/offset-034b2/build/dev/inc.bat %SRC% || exit /b 1
call C:/dev/occt8-mig/offset-034b2/build/dbg/inc.bat %SRC% || exit /b 1
call C:/dev/occt8-mig/offset-034b2/build/trc/inc.bat %SRC% || exit /b 1
echo BLD-OK
