// wind034b.hxx - issue 034 stage B: regularized union of a set of closed (possibly self-intersecting) oriented face
// sets by generalized winding numbers (Jacobson-Kavan-Sorkine-Hornung 2013 TOG; Zhou-Grinspun-Zorin-Jacobson 2016
// TOG "Mesh arrangements for solid geometry"): split every raw face against all others (General Fuse, OCCT
// BOPAlgo_Builder), measure the winding number of each group (0 = offset elements, 1 = input solid S) just in front
// of and just behind every split face by signed ray crossings, keep the split faces where the chosen predicate
// changes, sew them. Purely topological/orientation based: no distance field.
#pragma once
#include <BOPAlgo_Builder.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepBndLib.hxx>
#include <BRepMesh_IncrementalMesh.hxx>
#include <BRepTools.hxx>
#include <BRepTopAdaptor_FClass2d.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <Bnd_Box.hxx>
#include <IntCurvesFace_ShapeIntersector.hxx>
#include <Poly_Triangulation.hxx>
#include <ShapeFix_Shell.hxx>
#include <ShapeFix_Solid.hxx>
#include <ShapeUpgrade_UnifySameDomain.hxx>
#include <Standard_SStream.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Shell.hxx>
#include <TopoDS_Solid.hxx>
#include <functional>
#include <string>
#include <vector>

struct OrientedHasher034b
{
  size_t operator()(const TopoDS_Shape& s) const noexcept
  {
    return std::hash<const void*>()(s.TShape().get()) ^ (size_t)s.Orientation() * 0x9e3779b9u;
  }
  bool operator()(const TopoDS_Shape& a, const TopoDS_Shape& b) const noexcept { return a.IsEqual(b); }
};

struct RawFace034b
{
  TopoDS_Face f;
  int         group; // 0 elements, 1 input solid
};

// interior point and normal (as oriented) of a face; false if none
static bool interiorPoint034b(const TopoDS_Face& F, gp_Pnt& p, gp_Vec& n)
{
  double u0, u1, v0, v1;
  BRepTools::UVBounds(F, u0, u1, v0, v1);
  BRepTopAdaptor_FClass2d cls(F, 1e-9);
  BRepAdaptor_Surface a(F, true);
  for (int lev = 0; lev < 2; lev++)
  {
    const int M = lev == 0 ? 9 : 31;
    for (int k = 0; k < M * M; k++)
    {
      int i = k % M, j = k / M;
      // from the middle outwards
      int ii = (i % 2) ? (M / 2 + (i + 1) / 2) : (M / 2 - i / 2);
      int jj = (j % 2) ? (M / 2 + (j + 1) / 2) : (M / 2 - j / 2);
      double u = u0 + (u1 - u0) * (ii + 0.5) / M, v = v0 + (v1 - v0) * (jj + 0.5) / M;
      if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) continue;
      gp_Vec du, dv;
      a.D1(u, v, p, du, dv);
      n = du.Crossed(dv);
      if (n.Magnitude() < 1e-14) continue;
      n.Normalize();
      if (F.Orientation() == TopAbs_REVERSED) n.Reverse();
      return true;
    }
  }
  // sliver: centroid of a mesh triangle
  BRepMesh_IncrementalMesh mesh(F, 1e-3, false, 0.5);
  TopLoc_Location L;
  occ::handle<Poly_Triangulation> T = BRep_Tool::Triangulation(F, L);
  if (T.IsNull() || T->NbTriangles() == 0) return false;
  int n1, n2, n3;
  T->Triangle(1).Get(n1, n2, n3);
  if (!T->HasUVNodes()) return false;
  gp_Pnt2d uv((T->UVNode(n1).XY() + T->UVNode(n2).XY() + T->UVNode(n3).XY()) / 3.);
  gp_Vec du, dv;
  a.D1(uv.X(), uv.Y(), p, du, dv);
  n = du.Crossed(dv);
  if (n.Magnitude() < 1e-14) return false;
  n.Normalize();
  if (F.Orientation() == TopAbs_REVERSED) n.Reverse();
  return true;
}

class Winding034b
{
public:
  Winding034b(const std::vector<RawFace034b>& raw, double tol)
  {
    BRep_Builder bb;
    bb.MakeCompound(myAll);
    for (const auto& r : raw)
    {
      bb.Add(myAll, r.f);
      if (!myGroup.IsBound(r.f)) myGroup.Bind(r.f, r.group);
    }
    myIsec.Load(myAll, tol);
    myDirs[0] = gp_Dir(0.5773, 0.5774, 0.5773);
    myDirs[1] = gp_Dir(-0.3181, 0.8342, 0.4503);
    myDirs[2] = gp_Dir(0.7071, -0.2240, 0.6708);
    myDirs[3] = gp_Dir(-0.6019, -0.4415, 0.6653);
    myDirs[4] = gp_Dir(0.1232, -0.9031, -0.4113);
  }

  // winding numbers per group at q; false if no clean ray
  bool At(const gp_Pnt& q, int& w0, int& w1)
  {
    for (int k = 0; k < 5; k++)
    {
      myIsec.Perform(gp_Lin(q, myDirs[k]), 0., 1.e100);
      if (!myIsec.IsDone()) continue;
      bool clean = true;
      int a = 0, b = 0;
      for (int i = 1; i <= myIsec.NbPnt() && clean; i++)
      {
        if (myIsec.State(i) != TopAbs_IN || myIsec.Transition(i) == IntCurveSurface_Tangent) { clean = false; break; }
        if (myIsec.WParameter(i) < 1e-12) { clean = false; break; }
        const TopoDS_Face& F = myIsec.Face(i);
        BRepAdaptor_Surface s(F, false);
        gp_Pnt p; gp_Vec du, dv;
        s.D1(myIsec.UParameter(i), myIsec.VParameter(i), p, du, dv);
        gp_Vec n = du.Crossed(dv);
        if (n.Magnitude() < 1e-14) { clean = false; break; }
        n.Normalize();
        if (F.Orientation() == TopAbs_REVERSED) n.Reverse();
        const double c = n.Dot(gp_Vec(myDirs[k]));
        if (std::abs(c) < 1e-4) { clean = false; break; }
        const int s1 = c > 0 ? 1 : -1;
        const int* g = myGroup.Seek(F);
        if (g && *g == 1) b += s1; else a += s1;
      }
      if (!clean) { myDirty++; continue; }
      w0 = a; w1 = b;
      return true;
    }
    myFail++;
    return false;
  }
  int myDirty = 0, myFail = 0;

private:
  TopoDS_Compound                                                        myAll;
  NCollection_DataMap<TopoDS_Shape, int, OrientedHasher034b> myGroup;
  IntCurvesFace_ShapeIntersector                                         myIsec;
  gp_Dir                                                                 myDirs[5];
};

struct WindResult034b
{
  TopoDS_Shape result;
  std::string  msg;
  int nSplit = 0, nKept = 0, nNoPt = 0, nNoRay = 0;
};

// keep(w0, w1) -> true if the point belongs to the result
static WindResult034b windUnion034b(const std::vector<RawFace034b>& raw, const std::function<bool(int, int)>& keep,
                                    double fuzzy = 0.)
{
  WindResult034b out;
  BOPAlgo_Builder gf;
  NCollection_List<TopoDS_Shape> args;
  for (const auto& r : raw) args.Append(r.f);
  gf.SetArguments(args);
  gf.SetRunParallel(false);
  gf.SetNonDestructive(true);
  if (fuzzy > 0) gf.SetFuzzyValue(fuzzy);
  gf.Perform();
  if (gf.HasErrors())
  {
    Standard_SStream ss; gf.DumpErrors(ss); std::string e = ss.str();
    for (auto& c : e) if (c == 10 || c == 13 || c == ' ') c = '_';
    out.msg = "GF-errors " + e.substr(0, 200);
    return out;
  }
  if (gf.HasWarnings())
  {
    Standard_SStream ss; gf.DumpWarnings(ss); std::string e = ss.str();
    for (auto& c : e) if (c == 10 || c == 13 || c == ' ') c = '_';
    out.msg += "warn:" + e.substr(0, 120) + " ";
  }
  // split faces (unique TShapes)
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> splits;
  for (TopExp_Explorer ex(gf.Shape(), TopAbs_FACE); ex.More(); ex.Next()) splits.Add(ex.Current());
  out.nSplit = splits.Extent();
  Bnd_Box bx;
  BRepBndLib::Add(gf.Shape(), bx);
  const double diag = bx.IsVoid() ? 1. : std::sqrt(bx.SquareExtent());
  double maxTol = 0;
  for (TopExp_Explorer ex(gf.Shape(), TopAbs_EDGE); ex.More(); ex.Next()) maxTol = std::max(maxTol, BRep_Tool::Tolerance(TopoDS::Edge(ex.Current())));
  const double eps = std::max(20. * maxTol, 1e-6 * diag);
  Winding034b W(raw, 1e-7);
  BRep_Builder bb;
  TopoDS_Shell sh;
  bb.MakeShell(sh);
  for (int i = 1; i <= splits.Extent(); i++)
  {
    TopoDS_Face F = TopoDS::Face(splits(i));
    gp_Pnt p; gp_Vec n;
    if (!interiorPoint034b(F, p, n)) { out.nNoPt++; continue; }
    int a0, a1, b0, b1;
    if (!W.At(p.Translated(n * eps), a0, a1) || !W.At(p.Translated(n * -eps), b0, b1)) { out.nNoRay++; continue; }
    const bool kf = keep(a0, a1), kb = keep(b0, b1);
    if (kf == kb) continue;
    // result normal must point from kept to not kept: the face normal n points to the front
    bb.Add(sh, kb ? F : TopoDS::Face(F.Reversed()));
    out.nKept++;
  }
  out.msg += "eps=" + std::to_string(eps) + " dirty=" + std::to_string(W.myDirty) + " ";
  if (!out.nKept) { out.msg += "empty"; return out; }
  ShapeFix_Shell fs(sh);
  fs.FixFaceOrientation(sh, true, false);
  TopoDS_Solid so;
  bb.MakeSolid(so);
  for (TopExp_Explorer ex(fs.Shape(), TopAbs_SHELL); ex.More(); ex.Next()) bb.Add(so, ex.Current());
  ShapeFix_Solid fso(so);
  fso.Perform();
  TopoDS_Shape res = fso.Solid();
  try
  {
    ShapeUpgrade_UnifySameDomain us(res, true, true, false);
    us.Build();
    if (!us.Shape().IsNull()) res = us.Shape();
  }
  catch (...) { out.msg += "unify-exc "; }
  out.result = res;
  return out;
}
