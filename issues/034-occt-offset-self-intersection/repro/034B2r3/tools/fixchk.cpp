// fixchk.cpp <shells.brep> : edge tolerances raised to the measured pcurve deviations, solid made, then BRepCheck +
// BOP check (test side; mimics the end steps of the offset)
#include "memcap.hxx"
#include <BOPTools_AlgoTools.hxx>
#include <BRepAlgoAPI_Check.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepLib.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Solid.hxx>
#include <map>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape r; BRep_Builder b; if (!BRepTools::Read(r, argv[1], b)) return 1;
  TopTools_IndexedDataMapOfShapeListOfShape m; TopExp::MapShapesAndAncestors(r, TopAbs_EDGE, TopAbs_FACE, m);
  double worst = 0;
  for (int i = 1; i <= m.Extent(); i++)
  {
    const TopoDS_Edge& E = TopoDS::Edge(m.FindKey(i)); double mx = 0;
    for (const TopoDS_Shape& f : m(i)) { double d = 0, p = 0; if (BOPTools_AlgoTools::ComputeTolerance(TopoDS::Face(f), E, d, p)) mx = std::max(mx, d); }
    if (mx > BRep_Tool::Tolerance(E)) b.UpdateEdge(E, mx * 1.000001 + 1e-10);
    worst = std::max(worst, mx);
  }
  BRepLib::UpdateTolerances(r);
  TopoDS_Solid so; b.MakeSolid(so);
  for (TopExp_Explorer e(r, TopAbs_SHELL); e.More(); e.Next()) b.Add(so, e.Current());
  printf("worst dev %.3e valid=%d\n", worst, (int)BRepCheck_Analyzer(so).IsValid());
  BRepAlgoAPI_Check ck(so); std::map<int, int> st; for (const BOPAlgo_CheckResult& cr : ck.Result()) st[(int)cr.GetCheckStatus()]++;
  printf("BOP:"); for (auto& kv : st) printf(" %dx%d", kv.first, kv.second); printf("\n");
  if (argc > 2) BRepTools::Write(so, argv[2]);
  return 0;
}
