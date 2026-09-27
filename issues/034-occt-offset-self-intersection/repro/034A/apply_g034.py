"""apply_g034.py <MakeOffset.cxx>: inserts the issue-034 guard helpers (g034.txt) and includes. Idempotence: refuses twice."""
import os
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8", newline="").read()
if "Issue 034 guard" in s:
    sys.exit("already applied")
g = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "g034.txt"), encoding="utf-8").read()
anchor = "} // namespace\n\n//=======================================================================\n// static methods"
assert s.count(anchor) == 1, "anchor"
s = s.replace(anchor, "} // namespace\n" + g + "\n//=======================================================================\n// static methods")
inc = "#include <BOPAlgo_MakerVolume.hxx>\n"
assert s.count(inc) == 1
s = s.replace(inc, "#include <BOPAlgo_ArgumentAnalyzer.hxx>\n#include <BOPAlgo_CheckResult.hxx>\n" + inc
              + "#include <Bnd_Box.hxx>\n#include <BRepAdaptor_Surface.hxx>\n#include <BRepBndLib.hxx>\n"
              "#include <BRepExtrema_DistShapeShape.hxx>\n#include <Geom_BSplineSurface.hxx>\n"
              "#include <Standard_ErrorHandler.hxx>\n#include <algorithm>\n#include <cmath>\n", 1)
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
