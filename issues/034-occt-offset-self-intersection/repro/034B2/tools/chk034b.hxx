// chk034b.hxx - issue 034 stage B test oracle (NOT kernel code).
// grade(): BRepCheck + BOP check + solids.
// distOracle(): samples a 5x5 interior grid on every face of the result and measures the distance to the input
// solid S (BRepExtrema). A face is "S" (lies on the input, max < tolOn), "OFF" (every sample at |t| within tolOff),
// "WALL" (thick only: every sample on the surface of a removed face) or "MIX" (anything else = wrong geometry for a
// plain offset / an offset face of a thick solid). For a valid closed solid whose boundary is on the exact offset
// surface (and walls/input faces), the result is the exact offset.
#pragma once
#include <BRepAlgoAPI_Check.hxx>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRepTopAdaptor_FClass2d.hxx>
#include <BRep_Tool.hxx>
#include <BRep_Builder.hxx>
#include <TopoDS_Compound.hxx>
#include <GeomAPI_ProjectPointOnSurf.hxx>
#include <GProp_GProps.hxx>
#include <Geom_Surface.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Vertex.hxx>
#include <cmath>
#include <map>
#include <string>
#include <vector>

static std::string grade034b(const TopoDS_Shape& s, std::string& bop, int& nsol)
{
  bop.clear();
  nsol = 0;
  if (s.IsNull()) return "ERR";
  for (TopExp_Explorer ex(s, TopAbs_SOLID); ex.More(); ex.Next()) nsol++;
  const bool valid = BRepCheck_Analyzer(s).IsValid();
  BRepAlgoAPI_Check ck(s);
  std::map<int, int> st;
  for (const BOPAlgo_CheckResult& cr : ck.Result()) st[(int)cr.GetCheckStatus()]++;
  for (auto& kv : st) bop += std::to_string(kv.first) + "x" + std::to_string(kv.second) + ",";
  if (bop.empty()) bop = "-";
  if (!valid) return "INV";
  if (nsol < 1) return "NOSOLID";
  if (!ck.IsValid()) return "BOP";
  return "OK";
}

struct Oracle034b
{
  int nS = 0, nOff = 0, nWall = 0, nMix = 0;
  double offDev = 0;    // max |dist - |t|| over OFF faces
  double mixWorst = 0;  // worst |dist - |t|| over MIX faces (min(dist, |dist-|t||) sense)
  std::string mixList;
};

static Oracle034b distOracle034b(const TopoDS_Shape& res, const TopoDS_Shape& S, double t,
                                 const std::vector<TopoDS_Face>& removed, double tolOn, double tolOff)
{
  Oracle034b o;
  const double at = std::abs(t);
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(res, TopAbs_FACE, fm);
  BRepExtrema_DistShapeShape dss;
  // distance to the BOUNDARY of S (a solid gives 0 for points inside it)
  TopoDS_Compound shellS;
  {
    BRep_Builder cb;
    cb.MakeCompound(shellS);
    // thick solids: the inner/outer offset is measured against the faces that are offset (removed faces excluded)
    for (TopExp_Explorer ex(S, TopAbs_FACE); ex.More(); ex.Next())
    {
      bool isRem = false;
      for (const TopoDS_Face& rf : removed) if (rf.IsSame(ex.Current())) isRem = true;
      if (!isRem) cb.Add(shellS, ex.Current());
    }
  }
  dss.LoadS2(shellS);
  for (int i = 1; i <= fm.Extent(); i++)
  {
    const TopoDS_Face& F = TopoDS::Face(fm(i));
    TopLoc_Location L;
    occ::handle<Geom_Surface> Sf = BRep_Tool::Surface(F, L);
    double u0, u1, v0, v1;
    BRepTools::UVBounds(F, u0, u1, v0, v1);
    BRepTopAdaptor_FClass2d cls(F, 1e-7);
    std::vector<double> ds;
    std::vector<gp_Pnt> ps;
    for (int a = 0; a < 7 && ds.size() < 25; a++)
      for (int b = 0; b < 7 && ds.size() < 25; b++)
      {
        double u = u0 + (u1 - u0) * (a + 0.5) / 7, v = v0 + (v1 - v0) * (b + 0.5) / 7;
        if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) continue;
        gp_Pnt p = Sf->Value(u, v).Transformed(L.Transformation());
        dss.LoadS1(BRepBuilderAPI_MakeVertex(p).Vertex());
        dss.Perform();
        if (!dss.IsDone()) continue;
        ds.push_back(dss.Value());
        ps.push_back(p);
      }
    if (ds.empty()) continue;
    double mx = 0, dev = 0;
    for (double d : ds) { mx = std::max(mx, d); dev = std::max(dev, std::abs(d - at)); }
    if (mx < tolOn) { o.nS++; continue; }
    if (dev < tolOff) { o.nOff++; o.offDev = std::max(o.offDev, dev); continue; }
    bool wall = false;
    for (const TopoDS_Face& rf : removed)
    {
      occ::handle<Geom_Surface> rs = BRep_Tool::Surface(rf);
      bool all = true;
      for (const gp_Pnt& p : ps)
      {
        GeomAPI_ProjectPointOnSurf pr(p, rs);
        if (!pr.NbPoints() || pr.LowerDistance() > tolOff) { all = false; break; }
      }
      if (all) { wall = true; break; }
    }
    if (wall) { o.nWall++; continue; }
    o.nMix++;
    double w = 0;
    for (double d : ds) w = std::max(w, std::min(d, std::abs(d - at)));
    o.mixWorst = std::max(o.mixWorst, w);
    char buf[96];
    snprintf(buf, sizeof(buf), "%d(%.3g..%.3g) ", i, *std::min_element(ds.begin(), ds.end()), mx);
    o.mixList += buf;
  }
  return o;
}
