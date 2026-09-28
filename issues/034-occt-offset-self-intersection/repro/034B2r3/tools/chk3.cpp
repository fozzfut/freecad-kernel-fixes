// chk3.cpp <result.brep> <input.brep> <|d|> : per-face distance ratio (min, max of dist/|d| over interior samples),
// BRepCheck per face / edge, BOP check statuses (test side, distance = test oracle only)
#include "memcap.hxx"
#include <BRepAlgoAPI_Check.hxx>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepCheck_Result.hxx>
#include <BRepCheck_ListOfStatus.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <IntTools_FClass2d.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <TopExp.hxx>
#include <map>
#include <BOPTools_AlgoTools.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <cstdio>
#include <cstdlib>
int main(int argc, char** argv)
{
  TopoDS_Shape r, s; BRep_Builder b;
  if (!BRepTools::Read(r, argv[1], b) || !BRepTools::Read(s, argv[2], b)) { puts("READ-FAIL"); return 1; }
  const double d = atof(argv[3]);
  TopoDS_Compound bnd; b.MakeCompound(bnd);
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next()) b.Add(bnd, e.Current());
  BRepExtrema_DistShapeShape dss; dss.LoadS2(bnd);
  int fi = 0;
  for (TopExp_Explorer e(r, TopAbs_FACE); e.More(); e.Next())
  {
    const TopoDS_Face& f = TopoDS::Face(e.Current()); ++fi;
    BRepAdaptor_Surface bas(f, false); double u0, u1, v0, v1; BRepTools::UVBounds(f, u0, u1, v0, v1);
    IntTools_FClass2d cls(f, 1e-9);
    double mn = 1e100, mx = -1e100; int n = 0; gp_Pnt worst;
    for (int i = 1; i < 8; i++) for (int j = 1; j < 8; j++)
    {
      gp_Pnt2d uv(u0 + (u1 - u0) * i / 8., v0 + (v1 - v0) * j / 8.);
      if (cls.Perform(uv) != TopAbs_IN) continue;
      gp_Pnt p = bas.Value(uv.X(), uv.Y());
      dss.LoadS1(BRepBuilderAPI_MakeVertex(p).Vertex()); dss.Perform(); if (!dss.IsDone()) continue;
      double q = dss.Value() / d; ++n; if (q < mn) { mn = q; worst = p; } if (q > mx) mx = q;
    }
    GProp_GProps g; BRepGProp::SurfaceProperties(f, g);
    TopLoc_Location L; GeomAdaptor_Surface ga(BRep_Tool::Surface(f, L));
    printf("F%d type=%d area=%.4f c=(%.3f %.3f %.3f) n=%d dist/d min=%.6f max=%.6f worst=(%.3f %.3f %.3f)\n", fi, (int)ga.GetType(), g.Mass(),
           g.CentreOfMass().X(), g.CentreOfMass().Y(), g.CentreOfMass().Z(), n, mn, mx, worst.X(), worst.Y(), worst.Z());
  }
  BRepCheck_Analyzer an(r);
  printf("BRepCheck valid=%d\n", (int)an.IsValid());
  if (!an.IsValid())
  {
    int k = 0;
    for (TopExp_Explorer e(r, TopAbs_FACE); e.More(); e.Next())
    {
      ++k; const occ::handle<BRepCheck_Result>& res = an.Result(e.Current());
      if (res.IsNull()) continue;
      for (res->InitContextIterator(); res->MoreShapeInContext(); res->NextShapeInContext())
        for (const BRepCheck_Status st : res->StatusOnShape()) if (st != BRepCheck_NoError) printf("  face %d status %d\n", k, (int)st);
    }
    for (TopExp_Explorer e(r, TopAbs_EDGE); e.More(); e.Next())
    {
      const occ::handle<BRepCheck_Result>& res = an.Result(e.Current());
      if (res.IsNull()) continue;
      for (res->InitContextIterator(); res->MoreShapeInContext(); res->NextShapeInContext())
        for (const BRepCheck_Status st : res->StatusOnShape()) if (st != BRepCheck_NoError) {
          const TopoDS_Edge& E = TopoDS::Edge(e.Current());
          gp_Pnt p = BRep_Tool::Pnt(TopExp::FirstVertex(E)), q = BRep_Tool::Pnt(TopExp::LastVertex(E));
          printf("  edge status %d (%.3f %.3f %.3f)-(%.3f %.3f %.3f) tol=%.2e sp=%d sr=%d\n", (int)st, p.X(), p.Y(), p.Z(), q.X(), q.Y(), q.Z(),
                 BRep_Tool::Tolerance(E), (int)BRep_Tool::SameParameter(E), (int)BRep_Tool::SameRange(E));
          TopTools_IndexedDataMapOfShapeListOfShape m; TopExp::MapShapesAndAncestors(r, TopAbs_EDGE, TopAbs_FACE, m);
          const int ix = m.FindIndex(E);
          if (ix > 0) for (const TopoDS_Shape& f : m(ix)) { double dmax = 0, par = 0; BOPTools_AlgoTools::ComputeTolerance(TopoDS::Face(f), E, dmax, par);
            TopLoc_Location L2; GeomAdaptor_Surface ga2(BRep_Tool::Surface(TopoDS::Face(f), L2)); printf("     face type %d dev=%.3e at %.4f\n", (int)ga2.GetType(), dmax, par); } }
    }
  }
  BRepAlgoAPI_Check ck(r);
  std::map<int, int> st; for (const BOPAlgo_CheckResult& cr : ck.Result()) st[(int)cr.GetCheckStatus()]++;
  printf("BOP:"); for (auto& kv : st) printf(" %dx%d", kv.first, kv.second); printf("\n");
  return 0;
}
