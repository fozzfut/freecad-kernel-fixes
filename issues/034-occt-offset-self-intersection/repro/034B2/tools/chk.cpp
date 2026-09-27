// chk.cpp: runs the stage-A guard check (BRepCheck + ArgumentAnalyzer SelfInterMode, StopOnFirstFaulty) on a BREP
#include <BOPAlgo_ArgumentAnalyzer.hxx>
#include <BOPAlgo_CheckResult.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <TopExp_Explorer.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; BRepTools::Read(s, argv[1], b);
  printf("type=%d valid=%d\n", (int)s.ShapeType(), (int)BRepCheck_Analyzer(s).IsValid());
  for (int stop = 0; stop < 2; stop++)
  {
    BOPAlgo_ArgumentAnalyzer a; a.SetShape1(s); a.SelfInterMode() = true; a.StopOnFirstFaulty() = stop != 0; a.Perform();
    int n = 0, si = 0;
    for (NCollection_List<BOPAlgo_CheckResult>::Iterator it(a.GetCheckResult()); it.More(); it.Next()) { n++; if (it.Value().GetCheckStatus() == BOPAlgo_SelfIntersect) si++; }
    printf("stop=%d results=%d SI=%d hasfaulty=%d\n", stop, n, si, (int)a.HasFaulty());
  }
  return 0;
}
