// down3.hxx: downstream checks for a fillet result (issue 031, round 3). Every check returns a status and its
// wall time. Status: OK (valid solid, BRepAlgoAPI_Check clean) | BOP (valid by BRepCheck, BOP check finds faults)
// | INV (BRepCheck invalid) | ERR (not done / exception / error code / no solid) | NA (nothing to do).
// BOP and INV are results returned WITHOUT an error: "silent-broken". A watchdog (dog3) records the running check,
// so a hang is reported with its name.
#pragma once
#include <BRepAlgoAPI_Check.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
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
#include <GProp_GProps.hxx>
#include <Geom_Plane.hxx>
#include <Geom2d_Curve.hxx>
#include <Interface_Static.hxx>
#include <STEPControl_Reader.hxx>
#include <STEPControl_Writer.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <Standard_Failure.hxx>
#include <Extrema_ExtPC.hxx>
#include <gp_Ax1.hxx>
#include <gp_Trsf.hxx>
#include <windows.h>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace dog3
{
// the check now running (for the watchdog)
inline char              label[1024] = {0};
inline std::atomic<long long> since{0};
inline long long now() { return (long long)GetTickCount64(); }
inline void enter(const std::string& l)
{
  strncpy(label, l.c_str(), sizeof(label) - 1);
  since = now();
}
inline void leave() { since = 0; }
} // namespace dog3

namespace down3
{
inline std::string grade(const TopoDS_Shape& s)
{
  if (s.IsNull()) return "ERR";
  int ns = 0;
  for (TopExp_Explorer ex(s, TopAbs_SOLID); ex.More(); ex.Next()) ns++;
  if (!BRepCheck_Analyzer(s).IsValid()) return "INV";
  if (ns < 1) return "ERR";
  BRepAlgoAPI_Check ck(s);
  if (!ck.IsValid()) return "BOP";
  return "OK";
}

struct Timed
{
  std::string st;
  long long   ms;
};

template <class F> inline Timed timed(const std::string& name, F f)
{
  dog3::enter(name);
  const long long t0 = dog3::now();
  std::string     st;
  try { st = f(); }
  catch (Standard_Failure const&) { st = "ERR"; }
  catch (...) { st = "ERR"; }
  const long long t1 = dog3::now();
  dog3::leave();
  return {st, t1 - t0};
}

inline int largestPlane(const TopoDS_Shape& res, TopTools_IndexedMapOfShape& fm)
{
  TopExp::MapShapes(res, TopAbs_FACE, fm);
  int    of   = 0;
  double best = -1.;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    const TopoDS_Face& f = TopoDS::Face(fm(k));
    if (BRep_Tool::Surface(f).IsNull() || !Handle(Geom_Plane)::DownCast(BRep_Tool::Surface(f))) continue;
    GProp_GProps g;
    BRepGProp::SurfaceProperties(f, g);
    if (g.Mass() > best + 1e-9) { best = g.Mass(); of = k; }
  }
  return of;
}

// PartDesign Thickness (Reversed = inside, t < 0): MakeThickSolidByJoin, Skin, Arc join, no intersection
inline std::string thick(const TopoDS_Shape& res, double t)
{
  TopTools_IndexedMapOfShape fm;
  const int                  of = largestPlane(res, fm);
  if (of <= 0) return "NA";
  NCollection_List<TopoDS_Shape> cl;
  cl.Append(fm(of));
  BRepOffsetAPI_MakeThickSolid mk;
  mk.MakeThickSolidByJoin(res, cl, t, 1.e-7, BRepOffset_Skin, false, false, GeomAbs_Arc);
  if (!mk.IsDone()) return "ERR";
  return grade(mk.Shape());
}

inline TopoDS_Shape box(const gp_Pnt& C, double h, bool tilt)
{
  TopoDS_Shape b = BRepPrimAPI_MakeBox(gp_Pnt(-h, -h, -h), 2 * h, 2 * h, 2 * h).Shape();
  gp_Trsf      a, bb, c, d;
  if (tilt)
  {
    a.SetRotation(gp_Ax1(gp::Origin(), gp::DX()), 7. * M_PI / 180.);
    bb.SetRotation(gp_Ax1(gp::Origin(), gp::DY()), 11. * M_PI / 180.);
    c.SetRotation(gp_Ax1(gp::Origin(), gp::DZ()), 13. * M_PI / 180.);
  }
  d.SetTranslation(gp_Vec(C.XYZ()));
  return BRepBuilderAPI_Transform(b, d * c * bb * a, true).Shape();
}

inline std::string boolop(const TopoDS_Shape& res, const TopoDS_Shape& tool, bool fuse)
{
  if (fuse)
  {
    BRepAlgoAPI_Fuse op(res, tool);
    if (!op.IsDone() || op.HasErrors()) return "ERR";
    return grade(op.Shape());
  }
  BRepAlgoAPI_Cut op(res, tool);
  if (!op.IsDone() || op.HasErrors()) return "ERR";
  return grade(op.Shape());
}

// centre of the corner: area centre of the non-planar faces of the result within 2 r of V that are not
// cylinders/tori (the plate); V when there is none
inline gp_Pnt cornerCentre(const TopoDS_Shape& res, const gp_Pnt& V, double r)
{
  gp_XYZ s(0, 0, 0);
  double w = 0;
  for (TopExp_Explorer ex(res, TopAbs_FACE); ex.More(); ex.Next())
  {
    const TopoDS_Face&  f = TopoDS::Face(ex.Current());
    BRepAdaptor_Surface sa(f, false);
    if (sa.GetType() != GeomAbs_BSplineSurface && sa.GetType() != GeomAbs_BezierSurface) continue;
    GProp_GProps g;
    BRepGProp::SurfaceProperties(f, g);
    if (g.CentreOfMass().Distance(V) > 2 * r) continue;
    s += g.CentreOfMass().XYZ() * g.Mass();
    w += g.Mass();
  }
  return w > 0 ? gp_Pnt(s / w) : V;
}

inline double dihedral(const TopoDS_Edge& e, const TopoDS_Face& f1, const TopoDS_Face& f2)
{
  double a, b;
  BRep_Tool::Range(e, a, b);
  const double m = 0.5 * (a + b);
  gp_Dir       n[2];
  const TopoDS_Face* fs[2] = {&f1, &f2};
  for (int k = 0; k < 2; k++)
  {
    double               fa, fb;
    Handle(Geom2d_Curve) pc = BRep_Tool::CurveOnSurface(e, *fs[k], fa, fb);
    if (pc.IsNull()) return -1.;
    gp_Pnt2d            uv = pc->Value(m);
    BRepAdaptor_Surface sa(*fs[k]);
    BRepLProp_SLProps   pr(sa, uv.X(), uv.Y(), 1, 1e-9);
    if (!pr.IsNormalDefined()) return -1.;
    n[k] = pr.Normal();
    if (fs[k]->Orientation() == TopAbs_REVERSED) n[k].Reverse();
  }
  return n[0].Angle(n[1]) * 180. / M_PI;
}

// edges of the result near V: (a) pieces of the input's unfilleted edges at V ("keep"); (b) every edge with a
// vertex within 3 r of V whose faces meet at >= 10 deg in its middle
inline void nearEdges(const TopoDS_Shape& res, const std::vector<TopoDS_Edge>& keep, const gp_Pnt& V, double r,
                      std::vector<TopoDS_Edge>& onKeep, std::vector<TopoDS_Edge>& sharp)
{
  TopTools_IndexedDataMapOfShapeListOfShape ef;
  TopExp::MapShapesAndUniqueAncestors(res, TopAbs_EDGE, TopAbs_FACE, ef);
  for (int k = 1; k <= ef.Extent(); k++)
  {
    const TopoDS_Edge& e = TopoDS::Edge(ef.FindKey(k));
    if (BRep_Tool::Degenerated(e)) continue;
    TopoDS_Vertex v1, v2;
    TopExp::Vertices(e, v1, v2);
    if (v1.IsNull() || v2.IsNull()) continue;
    if (BRep_Tool::Pnt(v1).Distance(V) > 3 * r && BRep_Tool::Pnt(v2).Distance(V) > 3 * r) continue;
    BRepAdaptor_Curve c(e);
    const gp_Pnt      m = c.Value(0.5 * (c.FirstParameter() + c.LastParameter()));
    for (const TopoDS_Edge& ke : keep)
    {
      BRepAdaptor_Curve kc(ke);
      Extrema_ExtPC     ex(m, kc);
      bool              on = false;
      if (ex.IsDone())
        for (int q = 1; q <= ex.NbExt(); q++)
          if (ex.SquareDistance(q) < 1e-10) on = true;
      if (on) { onKeep.push_back(e); break; }
    }
    if (ef(k).Extent() != 2) continue;
    const TopoDS_Face& f1 = TopoDS::Face(ef(k).First());
    const TopoDS_Face& f2 = TopoDS::Face(ef(k).Last());
    if (f1.IsSame(f2) || dihedral(e, f1, f2) < 10.) continue;
    sharp.push_back(e);
  }
}

inline std::string fillet(const TopoDS_Shape& res, const std::vector<TopoDS_Edge>& es, double rr)
{
  BRepFilletAPI_MakeFillet mf(res);
  for (const TopoDS_Edge& e : es) mf.Add(rr, e);
  mf.Build();
  if (!mf.IsDone()) return "ERR";
  return grade(mf.Shape());
}

inline std::string step(const TopoDS_Shape& res, const std::string& tmp)
{
  STEPControl_Writer w;
  if (w.Transfer(res, STEPControl_AsIs) != IFSelect_RetDone) return "ERR";
  if (w.Write(tmp.c_str()) != IFSelect_RetDone) return "ERR";
  STEPControl_Reader rd;
  if (rd.ReadFile(tmp.c_str()) != IFSelect_RetDone) return "ERR";
  rd.TransferRoots();
  TopoDS_Shape s = rd.OneShape();
  std::remove(tmp.c_str());
  std::string g = grade(s);
  if (g != "OK") return g;
  GProp_GProps g0, g1;
  BRepGProp::VolumeProperties(res, g0);
  BRepGProp::VolumeProperties(s, g1);
  if (std::abs(g1.Mass() - g0.Mass()) > 1e-5 * std::abs(g0.Mass())) return "INV"; // silently different solid
  return "OK";
}

// all checks; output "name=STATUS:ms ..." (fil2/fil3: one entry per edge, "f2a.<k>" etc.)
inline std::string all(const std::string& key, const TopoDS_Shape& res, const std::vector<TopoDS_Edge>& keep,
                       const gp_Pnt& V, double r, const std::string& tmp, bool whole = true)
{
  std::string out;
  auto add = [&](const std::string& n, const Timed& t) {
    char b[64];
    sprintf(b, ":%lld", t.ms);
    out += " " + n + "=" + t.st + b;
  };
  const double ts[4] = {-0.3, -0.1, 0.1, 0.3};
  const char*  tn[4] = {"thk-0.3", "thk-0.1", "thk+0.1", "thk+0.3"};
  for (int k = 0; k < 4 && whole; k++)
    add(tn[k], timed(key + " " + tn[k], [&] { return thick(res, ts[k] * r); }));
  if (V.X() > 1e8) // whole-body checks only
  {
    if (whole) add("step", timed(key + " step", [&] { return step(res, tmp); }));
    return out;
  }
  const gp_Pnt P = cornerCentre(res, V, r);
  add("cutT", timed(key + " cutT", [&] { return boolop(res, box(V, 1.5 * r, true), false); }));
  add("cut06", timed(key + " cut06", [&] { return boolop(res, box(P, 0.6 * r, false), false); }));
  add("cut15", timed(key + " cut15", [&] { return boolop(res, box(P, 1.5 * r, false), false); }));
  add("fuse06", timed(key + " fuse06", [&] { return boolop(res, box(P, 0.6 * r, false), true); }));
  std::vector<TopoDS_Edge> onKeep, sharp;
  nearEdges(res, keep, V, r, onKeep, sharp);
  // fil2: each piece of the input's unfilleted edges alone (0.15 r and 0.3 r), then all of them (0.15 r)
  for (size_t k = 0; k < onKeep.size(); k++)
  {
    add("f2s" + std::to_string(k), timed(key + " f2s", [&] { return fillet(res, {onKeep[k]}, 0.15 * r); }));
    add("f2m" + std::to_string(k), timed(key + " f2m", [&] { return fillet(res, {onKeep[k]}, 0.2 * r); }));
    add("f2b" + std::to_string(k), timed(key + " f2b", [&] { return fillet(res, {onKeep[k]}, 0.3 * r); }));
  }
  if (!onKeep.empty())
    add("f2all", timed(key + " f2all", [&] { return fillet(res, onKeep, 0.15 * r); }));
  // fil3: every sharp edge near the corner alone (0.15 r), then all together (0.15 r)
  for (size_t k = 0; k < sharp.size(); k++)
    add("f3s" + std::to_string(k), timed(key + " f3s", [&] { return fillet(res, {sharp[k]}, 0.15 * r); }));
  if (!sharp.empty())
    add("f3all", timed(key + " f3all", [&] { return fillet(res, sharp, 0.15 * r); }));
  if (whole) add("step", timed(key + " step", [&] { return step(res, tmp); }));
  return out;
}
} // namespace down3
