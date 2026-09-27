#!/bin/bash
# bld.sh : incremental rebuild of dev + dbg TKOffset (MakeOffset.cxx) under buildlock, then copy into v/d v/g
cd /c/dev/occt8-mig/offset-034b2
bash C:/dev/tools/buildlock.sh cmd //c "C:\dev\occt8-mig\offset-034b2\tools\bld.bat" 2>&1 | grep -E "EXIT|BLD-OK|error|warning C" | head -20
cp build/dev/TKOffset.dll v/d/ && cp build/dbg/TKOffset.dll v/g/ && cp build/trc/TKOffset.dll v/t/ && md5sum v/d/TKOffset.dll v/g/TKOffset.dll v/t/TKOffset.dll
