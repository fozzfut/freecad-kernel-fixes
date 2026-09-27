// down.hxx: downstream checks for a fillet result (issue 031, round 2). "Better" includes the next operations:
// every changed result must still accept what the stock result accepted.
//   thk-  : BRepOffsetAPI_MakeThickSolidByJoin, largest planar face removed, offset -t (inside), Skin, Arc join,
//           tol 1e-7, no intersection (what PartDesign Thickness does with Reversed)
//   thk+  : the same with +t (outside)
//   cut   : BRepAlgoAPI_Cut with a box (half size 1.5 r, tilted 7/11/13 deg) centred at the corner point
//   fil2  : a second fillet (0.15 r) of the pieces of the input's unfilleted edges at the corner (see fil2)
//   step  : STEP AP214 write + read back
// Each check: OK | NA (nothing to do) | FAIL (not done / exception / error code) | INV (result not valid) |
// BOP (BRepAlgoAPI_Check finds faults) | VOL (STEP volume differs by > 1e-5 relative).
#pragma once
#include <BRepAlgoAPI_Check.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
#include <BRepLProp_SLProps.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRep_Tool.hxx>
#include <BRepTools.hxx>
#include <BRepLib_FindSurface.hxx>
#include <GProp_GProps.hxx>
#include <Geom_Plane.hxx>
#include <GeomLib.hxx>
#include <Geom2d_Curve.hxx>
#include <GeomLProp_SLProps.hxx>
#include <Interface_Static.hxx>
#include <STEPControl_Reader.hxx>
#include <STEPControl_Writer.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <Standard_Failure.hxx>
#include <gp_Ax1.hxx>
#include <gp_Trsf.hxx>
#include <cmath>
#include <string>
#include <cstdio>
#include <typeinfo>
#include <vector>
#include <Extrema_ExtPC.hxx>

namespace down
{
inline bool okShape(const TopoDS_Shape& s, std::string& why)
{
  if (s.IsNull()) { why = "FAIL"; return false; }
  if (!BRepCheck_Analyzer(s).IsValid()) { why = "INV"; return false; }
  BRepAlgoAPI_Check ck(s);
  if (!ck.IsValid()) { why = "BOP"; return false; }
  int ns = 0;
  for (TopExp_Explorer ex(s, TopAbs_SOLID); ex.More(); ex.Next()) ns++;
  if (ns < 1) { why = "NOSOLID"; return false; }
  why = "OK";
  return true;
}

inline double volume(const TopoDS_Shape& s)
{
  GProp_GProps g;
  BRepGProp::VolumeProperties(s, g);
  return g.Mass();
}

inline std::string thick(const TopoDS_Shape& res, int openFace, double t)
{
  try
  {
    TopTools_IndexedMapOfShape fm;
    TopExp::MapShapes(res, TopAbs_FACE, fm);
    int of = openFace;
    if (of <= 0)
    {
      double best = -1.;
      for (int k = 1; k <= fm.Extent(); k++)
      {
        const TopoDS_Face& f = TopoDS::Face(fm(k));
        if (BRep_Tool::Surface(f).IsNull() || !Handle(Geom_Plane)::DownCast(BRep_Tool::Surface(f)))
          continue;
        GProp_GProps g;
        BRepGProp::SurfaceProperties(f, g);
        if (g.Mass() > best + 1e-9) { best = g.Mass(); of = k; }
      }
    }
    if (of <= 0) return "NA";
    NCollection_List<TopoDS_Shape> cl;
    cl.Append(fm(of));
    BRepOffsetAPI_MakeThickSolid mk;
    mk.MakeThickSolidByJoin(res, cl, t, 1.e-7, BRepOffset_Skin, false, false, GeomAbs_Arc);
    if (!mk.IsDone())
    {
      char b[32];
      sprintf(b, "FAIL%d", (int)mk.MakeOffset().Error());
      return b;
    }
    std::string why;
    okShape(mk.Shape(), why);
    return why;
  }
  catch (Standard_Failure const&) { return "FAIL-EXC"; }
  catch (...) { return "FAIL-EXC"; }
}

inline std::string cut(const TopoDS_Shape& res, const gp_Pnt& V, double r)
{
  try
  {
    const double h = 1.5 * r;
    TopoDS_Shape box = BRepPrimAPI_MakeBox(gp_Pnt(-h, -h, -h), 2 * h, 2 * h, 2 * h).Shape();
    gp_Trsf a, b, c, d;
    a.SetRotation(gp_Ax1(gp::Origin(), gp::DX()), 7. * M_PI / 180.);
    b.SetRotation(gp_Ax1(gp::Origin(), gp::DY()), 11. * M_PI / 180.);
    c.SetRotation(gp_Ax1(gp::Origin(), gp::DZ()), 13. * M_PI / 180.);
    d.SetTranslation(gp_Vec(V.XYZ()));
    box = BRepBuilderAPI_Transform(box, d * c * b * a, true).Shape();
    BRepAlgoAPI_Cut ct(res, box);
    if (!ct.IsDone() || ct.HasErrors()) return "FAIL";
    std::string why;
    okShape(ct.Shape(), why);
    return why;
  }
  catch (...) { return "FAIL-EXC"; }
}

// dihedral angle (deg) between the two faces of edge e at its middle
inline double dihedral(const TopoDS_Edge& e, const TopoDS_Face& f1, const TopoDS_Face& f2)
{
  double a, b;
  BRep_Tool::Range(e, a, b);
  const double m = 0.5 * (a + b);
  gp_Dir n[2];
  const TopoDS_Face* fs[2] = {&f1, &f2};
  for (int k = 0; k < 2; k++)
  {
    double fa, fb;
    Handle(Geom2d_Curve) pc = BRep_Tool::CurveOnSurface(e, *fs[k], fa, fb);
    if (pc.IsNull()) return -1.;
    gp_Pnt2d uv = pc->Value(m);
    BRepAdaptor_Surface sa(*fs[k]);
    BRepLProp_SLProps pr(sa, uv.X(), uv.Y(), 1, 1e-9);
    if (!pr.IsNormalDefined()) return -1.;
    n[k] = pr.Normal();
    if (fs[k]->Orientation() == TopAbs_REVERSED) n[k].Reverse();
  }
  return n[0].Angle(n[1]) * 180. / M_PI;
}

// second fillet: the pieces of the input's sharp edges at the corner vertex V that the first fillet left (edges
// "keep" of the input, e.g. the concave edges a fillet ran into), each piece near V filleted alone (0.15 r) and
// all together; result "ok_single/n all=<grade>". These edges exist in every variant's result, so the numbers
// compare across TKFillet builds.
inline std::string fil2(const TopoDS_Shape& res, const std::vector<TopoDS_Edge>& keep, const gp_Pnt& V, double r)
{
  try
  {
    std::vector<TopoDS_Edge> cand;
    TopTools_IndexedMapOfShape em;
    TopExp::MapShapes(res, TopAbs_EDGE, em);
    for (int k = 1; k <= em.Extent(); k++)
    {
      const TopoDS_Edge& e = TopoDS::Edge(em(k));
      if (BRep_Tool::Degenerated(e)) continue;
      TopoDS_Vertex v1, v2;
      TopExp::Vertices(e, v1, v2);
      if (v1.IsNull() || v2.IsNull()) continue;
      if (BRep_Tool::Pnt(v1).Distance(V) > 3 * r && BRep_Tool::Pnt(v2).Distance(V) > 3 * r) continue;
      BRepAdaptor_Curve c(e);
      const gp_Pnt m = c.Value(0.5 * (c.FirstParameter() + c.LastParameter()));
      for (const TopoDS_Edge& ke : keep)
      {
        BRepAdaptor_Curve kc(ke);
        Extrema_ExtPC ex(m, kc);
        bool on = false;
        if (ex.IsDone())
          for (int q = 1; q <= ex.NbExt(); q++)
            if (ex.SquareDistance(q) < 1e-10) on = true;
        if (on) { cand.push_back(e); break; }
      }
    }
    if (cand.empty()) return "NA";
    int ok = 0;
    int nexc = 0;
    for (const TopoDS_Edge& e : cand)
    {
      try
      {
        BRepFilletAPI_MakeFillet mf(res);
        mf.Add(0.15 * r, e);
        mf.Build();
        std::string why;
        if (mf.IsDone() && okShape(mf.Shape(), why)) ok++;
      }
      catch (Standard_Failure const&) { nexc++; }
      catch (...) { nexc += 1000; }
    }
    std::string whya = "FAIL";
    try
    {
      BRepFilletAPI_MakeFillet ma(res);
      for (const TopoDS_Edge& e : cand) ma.Add(0.15 * r, e);
      ma.Build();
      if (ma.IsDone()) okShape(ma.Shape(), whya);
    }
    catch (Standard_Failure const&) { whya = "EXC"; }
    catch (...) { whya = "EXC-NONOCC"; }
    std::string out = std::to_string(ok) + "/" + std::to_string(cand.size()) + ",all:" + whya;
    if (nexc) out += ",exc:" + std::to_string(nexc);
    return out;
  }
  catch (Standard_Failure const& e) { return std::string("FAIL-EXC(") + typeid(e).name() + ")"; }
  catch (...) { return "FAIL-EXC-NONOCC"; }
}

// fil3: every sharp edge (dihedral >= 10 deg) of the result with a vertex within 3 r of V, filleted alone (0.15 r);
// result "ok/n" (the corner's own new edges included, so n may differ between builds)
inline std::string fil3(const TopoDS_Shape& res, const gp_Pnt& V, double r)
{
  TopTools_IndexedDataMapOfShapeListOfShape ef;
  TopExp::MapShapesAndUniqueAncestors(res, TopAbs_EDGE, TopAbs_FACE, ef);
  int ok = 0, n = 0;
  for (int k = 1; k <= ef.Extent(); k++)
  {
    const TopoDS_Edge& e = TopoDS::Edge(ef.FindKey(k));
    if (BRep_Tool::Degenerated(e) || ef(k).Extent() != 2) continue;
    TopoDS_Vertex v1, v2;
    TopExp::Vertices(e, v1, v2);
    if (v1.IsNull() || v2.IsNull()) continue;
    if (BRep_Tool::Pnt(v1).Distance(V) > 3 * r && BRep_Tool::Pnt(v2).Distance(V) > 3 * r) continue;
    const TopoDS_Face& f1 = TopoDS::Face(ef(k).First());
    const TopoDS_Face& f2 = TopoDS::Face(ef(k).Last());
    if (f1.IsSame(f2) || dihedral(e, f1, f2) < 10.) continue;
    n++;
    try
    {
      BRepFilletAPI_MakeFillet mf(res);
      mf.Add(0.15 * r, e);
      mf.Build();
      std::string why;
      if (mf.IsDone() && okShape(mf.Shape(), why)) ok++;
    }
    catch (...) {}
  }
  return std::to_string(ok) + "/" + std::to_string(n);
}

inline std::string step(const TopoDS_Shape& res, const std::string& tmp)
{
  try
  {
    STEPControl_Writer w;
    if (w.Transfer(res, STEPControl_AsIs) != IFSelect_RetDone) return "FAIL-W";
    if (w.Write(tmp.c_str()) != IFSelect_RetDone) return "FAIL-W";
    STEPControl_Reader rd;
    if (rd.ReadFile(tmp.c_str()) != IFSelect_RetDone) return "FAIL-R";
    rd.TransferRoots();
    TopoDS_Shape s = rd.OneShape();
    std::remove(tmp.c_str());
    std::string why;
    if (!okShape(s, why)) return why;
    const double v0 = volume(res), v1 = volume(s);
    if (std::abs(v1 - v0) > 1e-5 * std::abs(v0))
    {
      char b[64];
      sprintf(b, "VOL(%.1e)", (v1 - v0) / v0);
      return b;
    }
    return "OK";
  }
  catch (Standard_Failure const& e) { return std::string("FAIL-EXC(") + typeid(e).name() + ":" + (e.GetMessageString() ? e.GetMessageString() : "") + ")"; }
  catch (...) { return "FAIL-EXC"; }
}

inline std::string all(const TopoDS_Shape& res, const std::vector<TopoDS_Edge>& keep, const gp_Pnt& V, double r,
                       double t, const std::string& tmp, int openFace = 0)
{
  std::string own;
  okShape(res, own);
  return "self=" + own + " thk-=" + thick(res, openFace, -t) + " thk+=" + thick(res, openFace, t)
       + " cut=" + cut(res, V, r) + " fil2=" + fil2(res, keep, V, r) + " fil3=" + fil3(res, V, r) + " step=" + step(res, tmp);
}
} // namespace down
