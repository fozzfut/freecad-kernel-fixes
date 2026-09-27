// e4.cpp - issue 034 stage B experiment E4 (harness, NOT kernel code): offset as a union of elements classified by
// the winding number (degree) of the element boundaries.
//   e4 <in.brep> <op thick|offset> <t> <join arc> <remove largest|none|i,j,..> [split N=4] [outdir tag]
// S (+) B_|t| = S u slabs(faces) u tubes(convex edges) u balls(vertices)   (Rossignac-Requicha 1986)
// A folding slab is a self-intersecting closed surface; its degree is still well defined, so every element enters
// the General Fuse as a set of faces (MakerVolume), every cell gets the sum of element windings (propagated across
// split faces, Zhou et al. 2016), and the union is { sum >= 1 }. Folding offset faces and tubes are cut into N
// pieces first (a face is never intersected with itself).
// thick outward: {elements >= 1} minus S ; thick inward: S minus {elements >= 1} (elements go inward, tubes on
// concave edges) ; removed faces get no slab, their edges no tube.
#include "memcap.hxx"
#include "chk034b.hxx"
#include <BOPAlgo_MakerVolume.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffsetAPI_MakePipe.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepOffset_MakeSimpleOffset.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRep_Builder.hxx>
#include <GC_MakeCircle.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <Geom_Circle.hxx>
#include <Geom_Plane.hxx>
#include <Geom2d_Curve.hxx>
#include <ShapeFix_Shell.hxx>
#include <ShapeFix_Solid.hxx>
#include <ShapeUpgrade_FaceDivide.hxx>
#include <ShapeUpgrade_SplitSurface.hxx>
#include <ShapeUpgrade_UnifySameDomain.hxx>
#include <ShapeExtend.hxx>
#include <Standard_Failure.hxx>
#include <Standard_SStream.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Shell.hxx>
#include <TopoDS_Solid.hxx>
#include <TopoDS_Wire.hxx>
#include <chrono>
#include <climits>
#include <array>
#include <cstdio>
#include <cstring>
#include <deque>
#include <windows.h>
#include <psapi.h>

static std::string g_log;

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

// +1 convex, -1 concave, 0 tangent (angle below 1e-3 rad) at the middle of E between F1 (as oriented in the solid) and F2
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

struct UnionResult { TopoDS_Shape result; std::string msg; int nCells = 0, nKept = 0, nConflict = 0, nFaces = 0; };

// elements: closed solids (possibly self-intersecting) with outward orientation; sign +1 counts, sExcl marks the cells
// inside S for thick results. mode: 0 union (w>=1), 1 union minus S (w_el>=1 && w_S==0), 2 S minus union
static UnionResult unionByWinding(const std::vector<Element>& els, const TopoDS_Shape& S, int mode, int N)
{
  UnionResult out;
  // pieces: every face of every element; folding faces (offset surfaces / pipes) cut into pieces
  struct Piece { TopoDS_Face f; int el; }; // el = index into els, -1 = S
  std::vector<Piece> pieces;
  for (int e = -1; e < (int)els.size(); e++)
  {
    const TopoDS_Shape& so = e < 0 ? S : els[e].solid;
    for (TopExp_Explorer ex(so, TopAbs_FACE); ex.More(); ex.Next())
    {
      TopoDS_Face F = TopoDS::Face(ex.Current());
      std::vector<TopoDS_Face> sub;
      BRepAdaptor_Surface a(F, false);
      bool cut = false;
      if (e >= 0 && (a.GetType() == GeomAbs_OffsetSurface || a.GetType() == GeomAbs_BSplineSurface || a.GetType() == GeomAbs_SurfaceOfRevolution || a.GetType() == GeomAbs_Torus || a.GetType() == GeomAbs_OtherSurface))
        cut = els[e].kind == "slabfold" || els[e].kind == "tube";
      if (cut) splitFace(F, els[e].kind == "tube" ? 1 : N, N, sub);
      else sub.push_back(F);
      for (auto& f : sub) pieces.push_back({f, e});
    }
  }
  out.nFaces = (int)pieces.size();
  BOPAlgo_MakerVolume mv;
  NCollection_List<TopoDS_Shape> args;
  for (auto& p : pieces) args.Append(p.f);
  mv.SetArguments(args);
  mv.SetRunParallel(false);
  mv.SetIntersect(true);
  mv.SetAvoidInternalShapes(true);
  mv.Perform();
  if (mv.HasErrors())
  {
    Standard_SStream ss; mv.DumpErrors(ss); std::string e = ss.str();
    for (auto& c : e) if (c == 10 || c == 13 || c == ' ') c = '_';
    out.msg = "MV-errors " + e.substr(0, 200);
    return out;
  }
  if (mv.HasWarnings())
  {
    Standard_SStream ss; mv.DumpWarnings(ss); std::string e = ss.str();
    for (auto& c : e) if (c == 10 || c == 13 || c == ' ') c = '_';
    out.msg += "warn:" + e.substr(0, 160) + " ";
  }
  std::vector<TopoDS_Shape> cells;
  for (TopExp_Explorer ex(mv.Shape(), TopAbs_SOLID); ex.More(); ex.Next()) cells.push_back(ex.Current());
  out.nCells = (int)cells.size();
  if (cells.empty()) { out.msg += "no-cells"; return out; }
  // image -> raw pieces
  NCollection_IndexedDataMap<TopoDS_Shape, std::vector<int>, TopTools_ShapeMapHasher> img2raw;
  for (int i = 0; i < (int)pieces.size(); i++)
  {
    const NCollection_List<TopoDS_Shape>& m = mv.Modified(pieces[i].f);
    if (m.IsEmpty())
    {
      if (!img2raw.Contains(pieces[i].f)) img2raw.Add(pieces[i].f, std::vector<int>());
      img2raw.ChangeFromKey(pieces[i].f).push_back(i);
    }
    else
      for (NCollection_List<TopoDS_Shape>::Iterator it(m); it.More(); it.Next())
      {
        if (!img2raw.Contains(it.Value())) img2raw.Add(it.Value(), std::vector<int>());
        img2raw.ChangeFromKey(it.Value()).push_back(i);
      }
  }
  // occurrences: per cell and face, jump vector (element count, S count)
  struct Occ { int cell; TopoDS_Face face; int sEl; int sS; };
  NCollection_IndexedDataMap<TopoDS_Shape, int, TopTools_ShapeMapHasher> occIdx;
  std::vector<std::vector<Occ>> occs;
  int nopt = 0, noraw = 0;
  for (int c = 0; c < (int)cells.size(); c++)
    for (TopExp_Explorer ex(cells[c], TopAbs_FACE); ex.More(); ex.Next())
    {
      TopoDS_Face I = TopoDS::Face(ex.Current());
      int sEl = 0, sS = 0;
      // interior point + normal of I as oriented in the cell
      double u0, u1, v0, v1;
      BRepTools::UVBounds(I, u0, u1, v0, v1);
      BRepTopAdaptor_FClass2d cls(I, 1e-9);
      BRepAdaptor_Surface aI(I, true);
      gp_Pnt p; gp_Vec nC; bool okp = false;
      for (int k = 0; k < 81 && !okp; k++)
      {
        int i = k % 9, j = k / 9;
        double fu = 0.5 + ((i % 2) ? 1 : -1) * 0.05 * ((i + 1) / 2), fv = 0.5 + ((j % 2) ? 1 : -1) * 0.05 * ((j + 1) / 2);
        double u = u0 + (u1 - u0) * fu, v = v0 + (v1 - v0) * fv;
        if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) continue;
        gp_Vec du, dv; aI.D1(u, v, p, du, dv); nC = du.Crossed(dv);
        if (nC.Magnitude() < 1e-14) continue;
        if (I.Orientation() == TopAbs_REVERSED) nC.Reverse();
        okp = true;
      }
      if (!okp) nopt++;
      else if (!img2raw.Contains(I)) noraw++;
      else
        for (int ri : img2raw.FindFromKey(I))
        {
          const TopoDS_Face& P = pieces[ri].f;
          TopLoc_Location L;
          occ::handle<Geom_Surface> Sf = BRep_Tool::Surface(P, L);
          GeomAPI_ProjectPointOnSurf pr(p.Transformed(L.Transformation().Inverted()), Sf);
          if (!pr.NbPoints()) continue;
          double u, v; pr.LowerDistanceParameters(u, v);
          gp_Pnt q; gp_Vec du, dv; Sf->D1(u, v, q, du, dv);
          gp_Vec nP = du.Crossed(dv); nP.Transform(L.Transformation());
          if (P.Orientation() == TopAbs_REVERSED) nP.Reverse();
          int s = nP.Dot(nC) > 0 ? 1 : -1; // raw normal points out of this cell -> cell on the back (inside) side
          if (pieces[ri].el < 0) sS += s; else sEl += s;
        }
      if (!occIdx.Contains(I)) { occIdx.Add(I, (int)occs.size()); occs.emplace_back(); }
      occs[occIdx.FindFromKey(I)].push_back({c, I, sEl, sS});
    }
  if (nopt || noraw) out.msg += "nopt=" + std::to_string(nopt) + " noraw=" + std::to_string(noraw) + " ";
  std::vector<int> wE(cells.size(), INT_MIN), wS(cells.size(), INT_MIN);
  std::deque<int> q;
  for (int c = 0; c < (int)cells.size(); c++)
  {
    GProp_GProps g; BRepGProp::VolumeProperties(cells[c], g);
    if (g.Mass() < 0) { wE[c] = 0; wS[c] = 0; q.push_back(c); out.msg += "negcell "; }
  }
  std::vector<std::vector<std::array<int, 3>>> adj(cells.size());
  std::map<size_t, int> hist;
  for (auto& v : occs)
  {
    hist[v.size()]++;
    if (v.size() == 1)
    {
      int c = v[0].cell;
      if (wE[c] == INT_MIN) { wE[c] = v[0].sEl; wS[c] = v[0].sS; q.push_back(c); }
      else if (wE[c] != v[0].sEl || wS[c] != v[0].sS) out.nConflict++;
    }
    else if (v.size() == 2)
    {
      adj[v[0].cell].push_back({v[1].cell, v[0].sEl, v[0].sS});
      adj[v[1].cell].push_back({v[0].cell, v[1].sEl, v[1].sS});
    }
  }
  out.msg += "occ{";
  for (auto& kv : hist) out.msg += std::to_string(kv.first) + ":" + std::to_string(kv.second) + ",";
  out.msg += "} ";
  while (!q.empty())
  {
    int c = q.front(); q.pop_front();
    for (auto& e : adj[c])
    {
      int nb = e[0];
      int ve = wE[c] - e[1], vs = wS[c] - e[2];
      if (wE[nb] == INT_MIN) { wE[nb] = ve; wS[nb] = vs; q.push_back(nb); }
      else if (wE[nb] != ve || wS[nb] != vs) out.nConflict++;
    }
  }
  auto kept = [&](int c) -> bool {
    if (wE[c] == INT_MIN) return false;
    if (mode == 0) return wE[c] >= 1 || wS[c] >= 1;
    if (mode == 1) return wE[c] >= 1 && wS[c] <= 0;
    if (mode == 3) return wE[c] >= 1 && wS[c] >= 1;
    return wS[c] >= 1 && wE[c] <= 0;
  };
  std::string wl;
  int nUnset = 0;
  for (int c = 0; c < (int)cells.size(); c++)
  {
    if (wE[c] == INT_MIN) nUnset++;
    if (kept(c)) out.nKept++;
  }
  out.msg += "unset=" + std::to_string(nUnset) + " ";
  BRep_Builder bb;
  TopoDS_Shell sh;
  bb.MakeShell(sh);
  int nb = 0;
  for (auto& v : occs)
  {
    bool k0 = kept(v[0].cell);
    bool k1 = v.size() >= 2 && kept(v[1].cell);
    if (v.size() == 1 && k0) { bb.Add(sh, v[0].face); nb++; }
    else if (v.size() == 2 && k0 != k1) { bb.Add(sh, k0 ? v[0].face : v[1].face); nb++; }
  }
  if (!nb) { out.msg += "empty"; return out; }
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
  if (argc < 6) { printf("usage\n"); return 2; }
  TopoDS_Shape s;
  BRep_Builder bb;
  if (!BRepTools::Read(s, argv[1], bb) || s.IsNull()) { printf("READ-FAIL\n"); return 3; }
  if (s.ShapeType() != TopAbs_SOLID) { TopExp_Explorer ex(s, TopAbs_SOLID); if (ex.More()) s = ex.Current(); }
  const bool thick = !strcmp(argv[2], "thick");
  const double t = atof(argv[3]);
  const int N = argc > 6 ? atoi(argv[6]) : 4;
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  std::vector<TopoDS_Face> rem;
  std::map<int, bool> isRem;
  std::string rs = argv[5];
  if (thick)
  {
    if (rs == "largest") { int k = largestPlane(fm); rem.push_back(TopoDS::Face(fm(k))); isRem[k] = true; }
    else if (rs != "none")
    {
      char buf[256]; strncpy(buf, rs.c_str(), 255); buf[255] = 0;
      for (char* p = strtok(buf, ","); p; p = strtok(nullptr, ",")) { int k = atoi(p); rem.push_back(TopoDS::Face(fm(k))); isRem[k] = true; }
    }
  }
  GProp_GProps g0; BRepGProp::VolumeProperties(s, g0);
  printf("IN nf=%d vol0=%.5f op=%s t=%g N=%d\n", fm.Extent(), g0.Mass(), argv[2], t, N);
  auto t0 = std::chrono::steady_clock::now();
  // elements
  std::vector<Element> els;
  int nSlab = 0, nFold = 0, nTube = 0, nBall = 0, nFail = 0;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    if (isRem.count(k)) continue;
    const TopoDS_Face& F = TopoDS::Face(fm(k));
    TopoDS_Shape sl;
    try { sl = slab(F, t); } catch (...) {}
    if (sl.IsNull()) { nFail++; g_log += "slabfail" + std::to_string(k) + " "; continue; }
    bool fo = faceFolds(F, t);
    els.push_back({fo ? "slabfold" : "slab", sl});
    nSlab++; if (fo) nFold++;
  }
  TopTools_IndexedDataMapOfShapeListOfShape ef;
  TopExp::MapShapesAndAncestors(s, TopAbs_EDGE, TopAbs_FACE, ef);
  TopTools_IndexedMapOfShape remEdges, remVerts, ballVerts;
  for (auto& f : rem) { TopExp::MapShapes(f, TopAbs_EDGE, remEdges); TopExp::MapShapes(f, TopAbs_VERTEX, remVerts); }
  const int want = t > 0 ? 1 : -1; // outward: tubes on convex edges; inward: on concave edges
  for (int i = 1; i <= ef.Extent(); i++)
  {
    const TopoDS_Edge& E = TopoDS::Edge(ef.FindKey(i));
    if (BRep_Tool::Degenerated(E) || remEdges.Contains(E)) continue;
    const TopTools_ListOfShape& L = ef(i);
    if (L.Extent() != 2) continue;
    // faces as oriented in the solid
    TopoDS_Face F1 = TopoDS::Face(L.First()), F2 = TopoDS::Face(L.Last());
    int kind = edgeKind(E, F1, F2);
    if (kind != want) continue;
    TopoDS_Shape tb;
    try { tb = tube(E, std::abs(t)); } catch (...) {}
    if (tb.IsNull()) { nFail++; g_log += "tubefail "; continue; }
    els.push_back({"tube", tb});
    nTube++;
    TopoDS_Vertex v1, v2; TopExp::Vertices(E, v1, v2);
    ballVerts.Add(v1); ballVerts.Add(v2);
  }
  for (int i = 1; i <= ballVerts.Extent(); i++)
  {
    const TopoDS_Vertex& V = TopoDS::Vertex(ballVerts(i));
    if (remVerts.Contains(V)) continue;
    BRepPrimAPI_MakeSphere ms(BRep_Tool::Pnt(V), std::abs(t));
    els.push_back({"ball", orientedSolid(ms.Shape())});
    nBall++;
  }
  printf("ELEMENTS slabs=%d fold=%d tubes=%d balls=%d fail=%d %s\n", nSlab, nFold, nTube, nBall, nFail, g_log.c_str());
  fflush(stdout);
  int mode = !thick ? (t > 0 ? 0 : 2) : (t > 0 ? 1 : 3);
  UnionResult ur;
  try { ur = unionByWinding(els, s, mode, N); }
  catch (Standard_Failure const& e) { ur.msg += std::string("EXC:") + (e.GetMessageString() ? e.GetMessageString() : ""); }
  catch (...) { ur.msg += "EXC"; }
  long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
  printf("WU faces=%d cells=%d kept=%d conflicts=%d msg=%s\n", ur.nFaces, ur.nCells, ur.nKept, ur.nConflict, ur.msg.c_str());
  // for an inward plain offset the kept set is S minus elements: fine; thick inward: S minus elements (the wall)
  report("UNION", ur.result, s, t, rem, ms);
  if (argc > 8 && !ur.result.IsNull())
  {
    std::string od = argv[7], tag = argv[8];
    BRepTools::Write(ur.result, (od + "/" + tag + "_e4.brep").c_str());
  }
  PROCESS_MEMORY_COUNTERS pmc; GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc));
  printf("peakMB=%.0f\n", pmc.PeakWorkingSetSize / 1048576.0);
  return 0;
}
