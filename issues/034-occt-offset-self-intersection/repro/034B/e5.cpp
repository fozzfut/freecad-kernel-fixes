// e5.cpp - issue 034 stage B experiment E5 (harness, NOT kernel code): E2/E4 with the winding classification of
// wind034b.hxx (General Fuse split faces + signed ray crossings) instead of MakerVolume cells.
//   e5 <in.brep> <op thick|offset> <t> <join arc> <remove largest|none|i,j,..> <src stock|union> [N=4] [outdir tag]
// src stock : raw = the stock result (closed, self-intersecting shell); faces with inverted parts cut N x N; keep w >= 1
// src union : raw = input S (group 1) + slabs/tubes/balls (group 0); keep by op (see main)
#include "memcap.hxx"
#include "chk034b.hxx"
#include "wind034b.hxx"
#include <BRepAdaptor_Surface.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffsetAPI_MakePipe.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepOffset_MakeSimpleOffset.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <GeomAPI_ProjectPointOnCurve.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <Geom2d_Curve.hxx>
#include <Geom_OffsetSurface.hxx>
#include <Geom_Plane.hxx>
#include <Geom_RectangularTrimmedSurface.hxx>
#include <ShapeExtend.hxx>
#include <ShapeUpgrade_FaceDivide.hxx>
#include <ShapeUpgrade_SplitSurface.hxx>
#include <Standard_Failure.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Vertex.hxx>
#include <TopoDS_Wire.hxx>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <map>
#include <windows.h>
#include <psapi.h>


class GridSplit034b : public ShapeUpgrade_SplitSurface
{
public:
  int NU = 4, NV = 4;
  void Compute(const bool) override
  {
    const double u0 = myUSplitValues->First(), u1 = myUSplitValues->Last();
    const double v0 = myVSplitValues->First(), v1 = myVSplitValues->Last();
    occ::handle<NCollection_HSequence<double>> hu = new NCollection_HSequence<double>();
    occ::handle<NCollection_HSequence<double>> hv = new NCollection_HSequence<double>();
    for (int i = 1; i < NU; i++) hu->Append(u0 + (u1 - u0) * i / NU);
    for (int i = 1; i < NV; i++) hv->Append(v0 + (v1 - v0) * i / NV);
    SetUSplitValues(hu);
    SetVSplitValues(hv);
    myStatus = ShapeExtend::EncodeStatus(ShapeExtend_OK);
  }
};

static void splitFace(const TopoDS_Face& F, int nu, int nv, std::vector<TopoDS_Face>& out)
{
  if (nu <= 1 && nv <= 1) { out.push_back(F); return; }
  occ::handle<GridSplit034b> gs = new GridSplit034b();
  gs->NU = nu; gs->NV = nv;
  ShapeUpgrade_FaceDivide fd(F);
  fd.SetSplitSurfaceTool(gs);
  fd.Perform();
  int n = 0;
  for (TopExp_Explorer e(fd.Result(), TopAbs_FACE); e.More(); e.Next()) { out.push_back(TopoDS::Face(e.Current())); n++; }
  if (!n) out.push_back(F);
}

static bool factor(const occ::handle<Geom_Surface>& S, double u, double v, double d, double& f)
{
  gp_Pnt P;
  gp_Vec Su, Sv, Suu, Svv, Suv;
  S->D2(u, v, P, Su, Sv, Suu, Svv, Suv);
  gp_Vec N = Su.Crossed(Sv);
  double nm = N.Magnitude();
  double E = Su.SquareMagnitude(), G = Sv.SquareMagnitude(), F = Su.Dot(Sv), den = E * G - F * F;
  if (nm < 1e-300 || den <= 0 || nm <= 1e-9 * std::sqrt(E * G)) return false;
  N.Divide(nm);
  double L = Suu.Dot(N), M = Suv.Dot(N), NN = Svv.Dot(N);
  double K = (L * NN - M * M) / den, H = (E * NN + G * L - 2 * F * M) / (2 * den);
  double disc = std::sqrt(std::max(H * H - K, 0.));
  f = std::min(1 - d * (H + disc), 1 - d * (H - disc));
  return true;
}

static bool faceFolds(const TopoDS_Face& F, double t)
{
  TopLoc_Location L;
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(F, L);
  if (GeomAdaptor_Surface(S).GetType() == GeomAbs_Plane) return false;
  double d = F.Orientation() == TopAbs_REVERSED ? -t : t;
  double u0, u1, v0, v1;
  BRepTools::UVBounds(F, u0, u1, v0, v1);
  for (int i = 0; i <= 24; i++)
    for (int j = 0; j <= 24; j++)
    {
      double f;
      if (factor(S, u0 + (u1 - u0) * i / 24., v0 + (v1 - v0) * j / 24., d, f) && f < 0) return true;
    }
  return false;
}

static gp_Dir outNormal(const TopoDS_Face& f, const gp_Pnt2d& uv)
{
  BRepAdaptor_Surface a(f, false);
  gp_Pnt p; gp_Vec du, dv;
  a.D1(uv.X(), uv.Y(), p, du, dv);
  gp_Vec n = du.Crossed(dv);
  if (n.Magnitude() < 1e-12) return gp_Dir(0, 0, 1);
  if (f.Orientation() == TopAbs_REVERSED) n.Reverse();
  return gp_Dir(n);
}

static int edgeKind(const TopoDS_Edge& E, const TopoDS_Face& F1, const TopoDS_Face& F2)
{
  double a0, a1;
  occ::handle<Geom_Curve> C = BRep_Tool::Curve(E, a0, a1);
  if (C.IsNull()) return 0;
  double tm = 0.5 * (a0 + a1);
  double b0, b1;
  // E oriented as in F1
  TopoDS_Edge E1;
  for (TopExp_Explorer ex(F1, TopAbs_EDGE); ex.More(); ex.Next()) if (ex.Current().IsSame(E)) { E1 = TopoDS::Edge(ex.Current()); break; }
  if (E1.IsNull()) return 0;
  occ::handle<Geom2d_Curve> c1 = BRep_Tool::CurveOnSurface(E1, F1, b0, b1);
  occ::handle<Geom2d_Curve> c2 = BRep_Tool::CurveOnSurface(E, F2, b0, b1);
  if (c1.IsNull() || c2.IsNull()) return 0;
  gp_Dir n1 = outNormal(F1, c1->Value(tm)), n2 = outNormal(F2, c2->Value(tm));
  if (n1.Angle(n2) < 1e-3) return 0;
  gp_Pnt p; gp_Vec tg;
  C->D1(tm, p, tg);
  if (E1.Orientation() == TopAbs_REVERSED) tg.Reverse();
  gp_Vec inF = gp_Vec(n1).Crossed(tg); // points into F1 (material side of the loop, face on the left)
  double sgn = inF.Dot(gp_Vec(n2));
  return sgn > 0 ? -1 : 1; // n2 leaning into F1's side = concave
}

struct Element { std::string kind; TopoDS_Shape solid; };

static TopoDS_Shape orientedSolid(const TopoDS_Shape& sh)
{
  TopoDS_Shape s = sh;
  if (s.ShapeType() == TopAbs_COMPOUND) { TopExp_Explorer ex(s, TopAbs_SOLID); if (ex.More()) s = ex.Current(); }
  GProp_GProps g; BRepGProp::VolumeProperties(s, g);
  if (g.Mass() < 0) s.Reverse();
  return s;
}

static TopoDS_Shape slab(const TopoDS_Face& F, double t)
{
  BRepOffset_MakeSimpleOffset so(F, t);
  so.SetBuildSolidFlag(true);
  so.Perform();
  if (!so.IsDone()) return TopoDS_Shape();
  return orientedSolid(so.GetResultShape());
}

static TopoDS_Shape tube(const TopoDS_Edge& E, double r)
{
  double a0, a1;
  occ::handle<Geom_Curve> C = BRep_Tool::Curve(E, a0, a1);
  if (C.IsNull()) return TopoDS_Shape();
  gp_Pnt p; gp_Vec tg;
  C->D1(a0, p, tg);
  if (tg.Magnitude() < 1e-12) return TopoDS_Shape();
  gp_Circ circ(gp_Ax2(p, gp_Dir(tg)), r);
  TopoDS_Edge ce = BRepBuilderAPI_MakeEdge(circ).Edge();
  TopoDS_Wire cw = BRepBuilderAPI_MakeWire(ce).Wire();
  TopoDS_Face disk = BRepBuilderAPI_MakeFace(cw).Face();
  TopoDS_Wire spine = BRepBuilderAPI_MakeWire(TopoDS::Edge(E.Oriented(TopAbs_FORWARD))).Wire();
  BRepOffsetAPI_MakePipe mp(spine, disk);
  mp.Build();
  if (!mp.IsDone()) return TopoDS_Shape();
  return orientedSolid(mp.Shape());
}

static int largestPlane(const TopTools_IndexedMapOfShape& fm)
{
  int best = 0; double ba = -1;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    TopLoc_Location L;
    if (BRep_Tool::Surface(TopoDS::Face(fm(k)), L)->DynamicType() != STANDARD_TYPE(Geom_Plane)) continue;
    GProp_GProps g; BRepGProp::SurfaceProperties(fm(k), g);
    if (g.Mass() > ba) { ba = g.Mass(); best = k; }
  }
  return best;
}

struct RawGen034b
{
  int          type = 0; // 0 none, 1 face, 2 edge, 3 vertex
  TopoDS_Shape gen;
};
static double g_t = 0; // signed offset of the run

static bool invertedAt(const TopoDS_Face& RF, const RawGen034b& g, double u, double v)
{
  TopLoc_Location L;
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(RF, L);
  occ::handle<Geom_Surface> B = S;
  if (auto rt = occ::down_cast<Geom_RectangularTrimmedSurface>(B)) B = rt->BasisSurface();
  if (auto os = occ::down_cast<Geom_OffsetSurface>(B))
  {
    double f;
    return factor(os->BasisSurface(), u, v, os->Offset(), f) && f < 0;
  }
  if (g.type == 0 || g.type == 3) return false;
  if (GeomAdaptor_Surface(B).GetType() == GeomAbs_Plane && g.type == 1) return false;
  gp_Pnt P; gp_Vec du, dv;
  S->D1(u, v, P, du, dv);
  gp_Vec n = du.Crossed(dv);
  if (n.Magnitude() < 1e-12) return true; // singular point of the raw surface: treat as fold
  n.Transform(L.Transformation());
  P.Transform(L.Transformation());
  if (RF.Orientation() == TopAbs_REVERSED) n.Reverse();
  if (g.type == 2)
  {
    double a0, a1;
    TopLoc_Location EL;
    occ::handle<Geom_Curve> C = BRep_Tool::Curve(TopoDS::Edge(g.gen), EL, a0, a1);
    if (C.IsNull()) return false;
    gp_Pnt Pl = P.Transformed(EL.Transformation().Inverted());
    GeomAPI_ProjectPointOnCurve pc(Pl, C, a0, a1);
    if (!pc.NbPoints()) return false;
    gp_Pnt c = pc.NearestPoint().Transformed(EL.Transformation());
    return n.Dot(gp_Vec(c, P)) < 0;
  }
  // face generator, surface not an offset surface: compare with the generator normal at the projection
  const TopoDS_Face& GF = TopoDS::Face(g.gen);
  TopLoc_Location GL;
  occ::handle<Geom_Surface> GS = BRep_Tool::Surface(GF, GL);
  GeomAPI_ProjectPointOnSurf pr(P.Transformed(GL.Transformation().Inverted()), GS);
  if (!pr.NbPoints()) return false;
  double gu, gv;
  pr.LowerDistanceParameters(gu, gv);
  gp_Pnt q; gp_Vec gu1, gv1;
  GS->D1(gu, gv, q, gu1, gv1);
  gp_Vec N = gu1.Crossed(gv1);
  N.Transform(GL.Transformation());
  if (GF.Orientation() == TopAbs_REVERSED) N.Reverse();
  return n.Dot(N) * (g_t > 0 ? 1 : -1) < 0;
}

static double invertedShare(const TopoDS_Face& F, const RawGen034b& g, int n)
{
  double u0, u1, v0, v1;
  BRepTools::UVBounds(F, u0, u1, v0, v1);
  BRepTopAdaptor_FClass2d cls(F, 1e-9);
  int in = 0, inv = 0;
  for (int i = 0; i <= n; i++)
    for (int j = 0; j <= n; j++)
    {
      double u = u0 + (u1 - u0) * (0.02 + 0.96 * i / n), v = v0 + (v1 - v0) * (0.02 + 0.96 * j / n);
      TopAbs_State st = cls.Perform(gp_Pnt2d(u, v));
      if (st == TopAbs_OUT) continue;
      in++;
      if (invertedAt(F, g, u, v)) inv++;
    }
  return in ? double(inv) / in : -1;
}

static void collectGens(BRepOffset_MakeOffset& mo, const TopoDS_Shape& s,
                        NCollection_IndexedDataMap<TopoDS_Shape, RawGen034b, TopTools_ShapeMapHasher>* gens)
{
  if (!gens) return;
  const TopAbs_ShapeEnum ty[3] = {TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX};
  for (int k = 0; k < 3; k++)
  {
    TopTools_IndexedMapOfShape m;
    TopExp::MapShapes(s, ty[k], m);
    for (int i = 1; i <= m.Extent(); i++)
    {
      const NCollection_List<TopoDS_Shape>& L = mo.Generated(m(i));
      for (NCollection_List<TopoDS_Shape>::Iterator it(L); it.More(); it.Next())
      {
        if (it.Value().ShapeType() != TopAbs_FACE || gens->Contains(it.Value())) continue;
        RawGen034b g;
        g.type = k + 1;
        g.gen = m(i);
        gens->Add(it.Value(), g);
      }
    }
  }
}

static TopoDS_Shape runOffset(const TopoDS_Shape& s, const NCollection_List<TopoDS_Shape>& cl, bool thick, double t,
                              GeomAbs_JoinType join, int& done, int& err, std::string& exc,
                              NCollection_IndexedDataMap<TopoDS_Shape, RawGen034b, TopTools_ShapeMapHasher>* gens = nullptr)
{
  TopoDS_Shape r;
  done = 0; err = -1; exc = "-";
  try
  {
    if (thick)
    {
      BRepOffsetAPI_MakeThickSolid mk;
      mk.MakeThickSolidByJoin(s, cl, t, 1.e-7, BRepOffset_Skin, false, false, join);
      done = mk.IsDone(); err = (int)mk.MakeOffset().Error();
      if (done) { r = mk.Shape(); collectGens(const_cast<BRepOffset_MakeOffset&>(mk.MakeOffset()), s, gens); }
    }
    else
    {
      BRepOffsetAPI_MakeOffsetShape mk;
      mk.PerformByJoin(s, t, 1.e-7, BRepOffset_Skin, false, false, join);
      done = mk.IsDone(); err = (int)mk.MakeOffset().Error();
      if (done) { r = mk.Shape(); collectGens(const_cast<BRepOffset_MakeOffset&>(mk.MakeOffset()), s, gens); }
    }
  }
  catch (Standard_Failure const& e) { exc = std::string("SF:") + (e.GetMessageString() ? e.GetMessageString() : ""); for (auto& c : exc) if (c == ' ') c = '_'; }
  catch (...) { exc = "unknown"; }
  return r;
}

static void report(const char* tag, const TopoDS_Shape& r, const TopoDS_Shape& S, double t, const std::vector<TopoDS_Face>& rem, long long ms)
{
  std::string bop; int ns = 0;
  std::string gr = r.IsNull() ? "ERR" : grade034b(r, bop, ns);
  double vol = 0; int nf = 0;
  Oracle034b o;
  if (!r.IsNull())
  {
    GProp_GProps g; BRepGProp::VolumeProperties(r, g); vol = g.Mass();
    for (TopExp_Explorer e(r, TopAbs_FACE); e.More(); e.Next()) nf++;
    o = distOracle034b(r, S, t, rem, 1e-4, std::max(1e-4, 2e-3 * std::abs(t)));
  }
  printf("%s ms=%lld grade=%s bop=%s nsol=%d nf=%d vol=%.5f oracle S=%d OFF=%d WALL=%d MIX=%d offDev=%.2e mixWorst=%.3g mix=[%s]\n",
         tag, ms, gr.c_str(), bop.empty() ? "-" : bop.c_str(), ns, nf, vol, o.nS, o.nOff, o.nWall, o.nMix, o.offDev, o.mixWorst, o.mixList.c_str());
  fflush(stdout);
}


int main(int argc, char** argv)
{
  if (argc < 7) { printf("usage\n"); return 2; }
  TopoDS_Shape s;
  BRep_Builder bb;
  if (!BRepTools::Read(s, argv[1], bb) || s.IsNull()) { printf("READ-FAIL\n"); return 3; }
  if (s.ShapeType() != TopAbs_SOLID) { TopExp_Explorer ex(s, TopAbs_SOLID); if (ex.More()) s = ex.Current(); }
  const bool thick = !strcmp(argv[2], "thick");
  const double t = atof(argv[3]);
  const GeomAbs_JoinType join = !strcmp(argv[4], "int") ? GeomAbs_Intersection : GeomAbs_Arc;
  const std::string src = argv[6];
  const int N = argc > 7 ? atoi(argv[7]) : 4;
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  std::vector<TopoDS_Face> rem;
  std::map<int, bool> isRem;
  NCollection_List<TopoDS_Shape> cl;
  std::string rs = argv[5];
  if (thick)
  {
    if (rs == "largest") { int k = largestPlane(fm); rem.push_back(TopoDS::Face(fm(k))); isRem[k] = true; cl.Append(fm(k)); }
    else if (rs != "none")
    {
      char buf[256]; strncpy(buf, rs.c_str(), 255); buf[255] = 0;
      for (char* p = strtok(buf, ","); p; p = strtok(nullptr, ",")) { int k = atoi(p); rem.push_back(TopoDS::Face(fm(k))); isRem[k] = true; cl.Append(fm(k)); }
    }
  }
  GProp_GProps g0; BRepGProp::VolumeProperties(s, g0);
  printf("IN nf=%d vol0=%.5f op=%s t=%g src=%s N=%d\n", fm.Extent(), g0.Mass(), argv[2], t, src.c_str(), N);
  g_t = t;
  auto t0 = std::chrono::steady_clock::now();
  std::vector<RawFace034b> raw;
  std::function<bool(int, int)> keep;
  if (src == "stock")
  {
    int done, err; std::string exc;
    NCollection_IndexedDataMap<TopoDS_Shape, RawGen034b, TopTools_ShapeMapHasher> gens;
    TopoDS_Shape r0 = runOffset(s, cl, thick, t, join, done, err, exc, &gens);
    long long ms0 = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
    report("STOCK", done ? r0 : TopoDS_Shape(), s, t, rem, ms0);
    if (r0.IsNull() || !done) { printf("NO-RAW done=%d err=%d exc=%s\n", done, err, exc.c_str()); return 0; }
    int nFold = 0;
    for (TopExp_Explorer ex(r0, TopAbs_FACE); ex.More(); ex.Next())
    {
      TopoDS_Face F = TopoDS::Face(ex.Current());
      RawGen034b g;
      if (gens.Contains(F)) g = gens.FindFromKey(F);
      double sh = invertedShare(F, g, 16);
      std::vector<TopoDS_Face> sub;
      if (sh > 0 && N > 1) { nFold++; splitFace(F, N, N, sub); }
      else sub.push_back(F);
      for (auto& f : sub) raw.push_back({f, 0});
    }
    printf("RAW faces=%d foldFaces=%d\n", (int)raw.size(), nFold);
    keep = [](int w0, int) { return w0 >= 1; };
  }
  else
  {
    int nSlab = 0, nFold = 0, nTube = 0, nBall = 0, nFail = 0;
    std::vector<Element> els;
    for (int k = 1; k <= fm.Extent(); k++)
    {
      if (isRem.count(k)) continue;
      const TopoDS_Face& F = TopoDS::Face(fm(k));
      TopoDS_Shape sl;
      try { sl = slab(F, t); } catch (...) {}
      if (sl.IsNull()) { nFail++; continue; }
      bool fo = faceFolds(F, t);
      els.push_back({fo ? "slabfold" : "slab", sl});
      nSlab++; if (fo) nFold++;
    }
    TopTools_IndexedDataMapOfShapeListOfShape ef;
    TopExp::MapShapesAndAncestors(s, TopAbs_EDGE, TopAbs_FACE, ef);
    TopTools_IndexedMapOfShape remEdges, remVerts, ballVerts;
    for (auto& f : rem) { TopExp::MapShapes(f, TopAbs_EDGE, remEdges); TopExp::MapShapes(f, TopAbs_VERTEX, remVerts); }
    const int want = t > 0 ? 1 : -1;
    for (int i = 1; i <= ef.Extent(); i++)
    {
      const TopoDS_Edge& E = TopoDS::Edge(ef.FindKey(i));
      if (BRep_Tool::Degenerated(E) || remEdges.Contains(E)) continue;
      const TopTools_ListOfShape& L = ef(i);
      if (L.Extent() != 2) continue;
      TopoDS_Face F1 = TopoDS::Face(L.First()), F2 = TopoDS::Face(L.Last());
      if (edgeKind(E, F1, F2) != want) continue;
      TopoDS_Shape tb;
      try { tb = tube(E, std::abs(t)); } catch (...) {}
      if (tb.IsNull()) { nFail++; continue; }
      els.push_back({"tube", tb});
      nTube++;
      TopoDS_Vertex v1, v2; TopExp::Vertices(E, v1, v2);
      ballVerts.Add(v1); ballVerts.Add(v2);
    }
    for (int i = 1; i <= ballVerts.Extent(); i++)
    {
      const TopoDS_Vertex& V = TopoDS::Vertex(ballVerts(i));
      if (remVerts.Contains(V)) continue;
      BRepPrimAPI_MakeSphere msp(BRep_Tool::Pnt(V), std::abs(t));
      els.push_back({"ball", orientedSolid(msp.Shape())});
      nBall++;
    }
    for (auto& e : els)
      for (TopExp_Explorer ex(e.solid, TopAbs_FACE); ex.More(); ex.Next())
      {
        TopoDS_Face F = TopoDS::Face(ex.Current());
        std::vector<TopoDS_Face> sub;
        BRepAdaptor_Surface a(F, false);
        bool cut = (e.kind == "slabfold" && (a.GetType() == GeomAbs_OffsetSurface || a.GetType() == GeomAbs_BSplineSurface || a.GetType() == GeomAbs_OtherSurface))
                   || (e.kind == "tube" && a.GetType() != GeomAbs_Plane);
        if (cut && N > 1) splitFace(F, N, N, sub); else sub.push_back(F);
        for (auto& f : sub) raw.push_back({f, 0});
      }
    for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next()) raw.push_back({TopoDS::Face(ex.Current()), 1});
    printf("ELEMENTS slabs=%d fold=%d tubes=%d balls=%d fail=%d raw=%d\n", nSlab, nFold, nTube, nBall, nFail, (int)raw.size());
    if (!thick && t > 0) keep = [](int w0, int w1) { return w0 >= 1 || w1 >= 1; };
    else if (!thick) keep = [](int w0, int w1) { return w1 >= 1 && w0 <= 0; };
    else if (t > 0) keep = [](int w0, int w1) { return w0 >= 1 && w1 <= 0; };
    else keep = [](int w0, int w1) { return w0 >= 1 && w1 >= 1; };
  }
  fflush(stdout);
  WindResult034b wr;
  const char* fz = getenv("FUZZY");
  try { wr = windUnion034b(raw, keep, fz ? atof(fz) : 0.); }
  catch (Standard_Failure const& e) { wr.msg += std::string("EXC:") + (e.GetMessageString() ? e.GetMessageString() : ""); }
  catch (...) { wr.msg += "EXC"; }
  long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
  printf("WIND split=%d kept=%d nopt=%d noray=%d msg=%s\n", wr.nSplit, wr.nKept, wr.nNoPt, wr.nNoRay, wr.msg.c_str());
  report("RESULT", wr.result, s, t, rem, ms);
  if (argc > 9 && !wr.result.IsNull())
  {
    std::string od = argv[8], tag = argv[9];
    BRepTools::Write(wr.result, (od + "/" + tag + "_e5" + src + ".brep").c_str());
  }
  PROCESS_MEMORY_COUNTERS pmc; GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc));
  printf("peakMB=%.0f\n", pmc.PeakWorkingSetSize / 1048576.0);
  return 0;
}
