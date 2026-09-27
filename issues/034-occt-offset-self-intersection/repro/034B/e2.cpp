// e2.cpp - issue 034 stage B experiment E2 (harness, NOT kernel code): regularized self-union of the raw offset.
//   e2 <in.brep> <op thick|offset> <t> <join arc|int> <remove largest|none|i,j,..> [grid N=4] [outdir tag]
// The stock offset returns a closed shell whose folded offset faces overlap (M1). Its regularized self-union
// (points of winding number >= 1, Zhou-Grinspun-Zorin-Jacobson 2016 "Mesh arrangements for solid geometry",
// TOG 35(4)) is the true offset: every swallowtail loop of a fold lies inside the swept band.
// 1. stock offset -> R0 (grade + oracle)
// 2. faces of R0 whose Geom_OffsetSurface folds (principal factor of the basis < 0) are divided on an N x N UV grid
//    (a single face is never intersected with itself by the General Fuse)
// 3. BOPAlgo_MakerVolume over all faces -> cells; winding numbers propagated from the outside across every split
//    face (+1 when entering the back side of a raw face)
// 4. faces between a cell with w >= 1 and one with w < 1 -> shell -> solid -> UnifySameDomain
// 5. grade + oracle against the input
#include "memcap.hxx"
#include "chk034b.hxx"
#include <BOPAlgo_MakerVolume.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRep_Builder.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <Geom_OffsetSurface.hxx>
#include <Geom_Plane.hxx>
#include <Geom_RectangularTrimmedSurface.hxx>
#include <ShapeFix_Shell.hxx>
#include <ShapeFix_Solid.hxx>
#include <ShapeUpgrade_FaceDivide.hxx>
#include <ShapeUpgrade_SplitSurface.hxx>
#include <ShapeUpgrade_UnifySameDomain.hxx>
#include <ShapeExtend.hxx>
#include <Standard_Failure.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <TopoDS_Shell.hxx>
#include <TopoDS_Solid.hxx>
#include <chrono>
#include <Standard_SStream.hxx>
#include <cstdio>
#include <cstring>
#include <deque>
#include <windows.h>
#include <psapi.h>

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

// the face's surface is an offset of a basis that folds at the offset value
static bool rawFaceFolds(const TopoDS_Face& F)
{
  TopLoc_Location L;
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(F, L);
  if (auto rt = occ::down_cast<Geom_RectangularTrimmedSurface>(S)) S = rt->BasisSurface();
  auto os = occ::down_cast<Geom_OffsetSurface>(S);
  if (os.IsNull()) return false;
  occ::handle<Geom_Surface> B = os->BasisSurface();
  const double d = os->Offset();
  double u0, u1, v0, v1;
  BRepTools::UVBounds(F, u0, u1, v0, v1);
  for (int i = 0; i <= 24; i++)
    for (int j = 0; j <= 24; j++)
    {
      double f;
      if (factor(B, u0 + (u1 - u0) * i / 24., v0 + (v1 - v0) * j / 24., d, f) && f < 0) return true;
    }
  return false;
}

class GridSplit034b : public ShapeUpgrade_SplitSurface
{
public:
  int N = 4;
  void Compute(const bool) override
  {
    const double u0 = myUSplitValues->First(), u1 = myUSplitValues->Last();
    const double v0 = myVSplitValues->First(), v1 = myVSplitValues->Last();
    occ::handle<NCollection_HSequence<double>> hu = new NCollection_HSequence<double>();
    occ::handle<NCollection_HSequence<double>> hv = new NCollection_HSequence<double>();
    for (int i = 1; i < N; i++) { hu->Append(u0 + (u1 - u0) * i / N); hv->Append(v0 + (v1 - v0) * i / N); }
    SetUSplitValues(hu);
    SetVSplitValues(hv);
    myStatus = ShapeExtend::EncodeStatus(ShapeExtend_OK);
  }
};

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

// outward normal of a face (as oriented) at an interior point; false if none found
static bool facePointNormal(const TopoDS_Face& F, gp_Pnt& p, gp_Dir& n)
{
  double u0, u1, v0, v1;
  BRepTools::UVBounds(F, u0, u1, v0, v1);
  BRepTopAdaptor_FClass2d cls(F, 1e-9);
  BRepAdaptor_Surface a(F, true);
  for (int k = 0; k < 49; k++)
  {
    // spiral of candidates from the middle
    int i = k % 7, j = k / 7;
    double fu = 0.5 + ((i % 2) ? 1 : -1) * 0.07 * ((i + 1) / 2), fv = 0.5 + ((j % 2) ? 1 : -1) * 0.07 * ((j + 1) / 2);
    double u = u0 + (u1 - u0) * fu, v = v0 + (v1 - v0) * fv;
    if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) continue;
    gp_Vec du, dv;
    a.D1(u, v, p, du, dv);
    gp_Vec nn = du.Crossed(dv);
    if (nn.Magnitude() < 1e-12) continue;
    if (F.Orientation() == TopAbs_REVERSED) nn.Reverse();
    n = gp_Dir(nn);
    return true;
  }
  return false;
}

static bool normalAt(const TopoDS_Face& F, const gp_Pnt& p, gp_Dir& n, double& dist)
{
  TopLoc_Location L;
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(F, L);
  gp_Pnt pl = p.Transformed(L.Transformation().Inverted());
  GeomAPI_ProjectPointOnSurf pr(pl, S);
  if (!pr.NbPoints()) return false;
  double u, v;
  pr.LowerDistanceParameters(u, v);
  dist = pr.LowerDistance();
  gp_Pnt q; gp_Vec du, dv;
  S->D1(u, v, q, du, dv);
  gp_Vec nn = du.Crossed(dv);
  if (nn.Magnitude() < 1e-12) return false;
  nn.Transform(L.Transformation());
  if (F.Orientation() == TopAbs_REVERSED) nn.Reverse();
  n = gp_Dir(nn);
  return true;
}

struct SelfUnion034b
{
  TopoDS_Shape result;
  std::string  msg;
  int nCells = 0, nKept = 0, nConflict = 0, nFold = 0, nPieces = 0;
};

static SelfUnion034b selfUnion(const TopoDS_Shape& raw, int N)
{
  SelfUnion034b out;
  // 1. pieces
  std::vector<TopoDS_Face> pieces;
  for (TopExp_Explorer ex(raw, TopAbs_FACE); ex.More(); ex.Next())
  {
    TopoDS_Face F = TopoDS::Face(ex.Current());
    if (N > 1 && rawFaceFolds(F))
    {
      out.nFold++;
      occ::handle<GridSplit034b> gs = new GridSplit034b();
      gs->N = N;
      ShapeUpgrade_FaceDivide fd(F);
      fd.SetSplitSurfaceTool(gs);
      fd.Perform();
      TopoDS_Shape r = fd.Result();
      int n = 0;
      for (TopExp_Explorer e2(r, TopAbs_FACE); e2.More(); e2.Next()) { pieces.push_back(TopoDS::Face(e2.Current())); n++; }
      if (n == 0) pieces.push_back(F);
    }
    else pieces.push_back(F);
  }
  out.nPieces = (int)pieces.size();
  // 2. arrangement
  BOPAlgo_MakerVolume mv;
  NCollection_List<TopoDS_Shape> args;
  for (auto& f : pieces) args.Append(f);
  mv.SetArguments(args);
  mv.SetRunParallel(false);
  mv.SetIntersect(true);
  mv.SetAvoidInternalShapes(true);
  mv.Perform();
  if (mv.HasErrors())
  {
    Standard_SStream ss;
    mv.DumpErrors(ss);
    std::string e = ss.str();
    for (auto& c : e) if (c == 10 || c == 13 || c == ' ') c = '_';
    out.msg = "MakerVolume errors " + e.substr(0, 300);
    return out;
  }
  if (mv.HasWarnings())
  {
    Standard_SStream ss;
    mv.DumpWarnings(ss);
    std::string e = ss.str();
    for (auto& c : e) if (c == 10 || c == 13 || c == ' ') c = '_';
    out.msg += "warn:" + e.substr(0, 200) + " ";
  }
  const TopoDS_Shape& cellsC = mv.Shape();
  std::vector<TopoDS_Shape> cells;
  for (TopExp_Explorer ex(cellsC, TopAbs_SOLID); ex.More(); ex.Next()) cells.push_back(ex.Current());
  out.nCells = (int)cells.size();
  if (cells.empty()) { out.msg = "no cells"; return out; }
  // image face -> raw pieces
  NCollection_IndexedDataMap<TopoDS_Shape, NCollection_List<TopoDS_Shape>, TopTools_ShapeMapHasher> img2raw;
  for (auto& P : pieces)
  {
    const NCollection_List<TopoDS_Shape>& m = mv.Modified(P);
    if (m.IsEmpty())
    {
      if (!img2raw.Contains(P)) img2raw.Add(P, NCollection_List<TopoDS_Shape>());
      img2raw.ChangeFromKey(P).Append(P);
    }
    else
      for (NCollection_List<TopoDS_Shape>::Iterator it(m); it.More(); it.Next())
      {
        if (!img2raw.Contains(it.Value())) img2raw.Add(it.Value(), NCollection_List<TopoDS_Shape>());
        img2raw.ChangeFromKey(it.Value()).Append(P);
      }
  }
  // faces of cells: key = image face (unoriented); per occurrence the jump s = sum over raw pieces (+1: raw normal
  // points out of this cell = this cell lies on the back side)
  struct Occ { int cell; TopoDS_Face face; int s; };
  NCollection_IndexedDataMap<TopoDS_Shape, std::vector<Occ>*, TopTools_ShapeMapHasher> occ;
  std::vector<std::vector<Occ>> store;
  store.reserve(100000);
  for (int c = 0; c < (int)cells.size(); c++)
  {
    for (TopExp_Explorer ex(cells[c], TopAbs_FACE); ex.More(); ex.Next())
    {
      TopoDS_Face I = TopoDS::Face(ex.Current());
      int s = 0;
      gp_Pnt p; gp_Dir nC;
      if (!facePointNormal(I, p, nC)) { out.msg += "nopt "; }
      else if (img2raw.Contains(I))
      {
        for (NCollection_List<TopoDS_Shape>::Iterator it(img2raw.FindFromKey(I)); it.More(); it.Next())
        {
          gp_Dir nP; double dd;
          if (!normalAt(TopoDS::Face(it.Value()), p, nP, dd)) continue;
          s += (nP.Dot(nC) > 0) ? 1 : -1;
        }
      }
      else out.msg += "noraw ";
      if (!occ.Contains(I)) { store.emplace_back(); occ.Add(I, &store.back()); }
      occ.ChangeFromKey(I)->push_back({c, I, s});
    }
  }
  {
    std::map<size_t, int> h;
    for (int i = 1; i <= occ.Extent(); i++) h[occ(i)->size()]++;
    out.msg += "occ{";
    for (auto& kv : h) out.msg += std::to_string(kv.first) + ":" + std::to_string(kv.second) + ",";
    out.msg += "} ";
  }
  // 3. winding BFS
  std::vector<int> w(cells.size(), INT_MIN);
  std::deque<int> q;
  // a cell with negative volume is the unbounded outside (a reversed outer shell): w = 0
  for (int c = 0; c < (int)cells.size(); c++)
  {
    GProp_GProps g;
    BRepGProp::VolumeProperties(cells[c], g);
    if (g.Mass() < 0) { w[c] = 0; q.push_back(c); out.msg += "negcell "; }
  }
  for (int i = 1; i <= occ.Extent(); i++)
  {
    std::vector<Occ>& v = *occ(i);
    if (v.size() == 1)
    {
      int c = v[0].cell, val = 0 + v[0].s;
      if (w[c] == INT_MIN) { w[c] = val; q.push_back(c); }
      else if (w[c] != val) out.nConflict++;
    }
  }
  // adjacency
  std::vector<std::vector<std::pair<int, int>>> adj(cells.size()); // (neighbour, jump: w(this) = w(nb) + s_this)
  for (int i = 1; i <= occ.Extent(); i++)
  {
    std::vector<Occ>& v = *occ(i);
    if (v.size() == 2)
    {
      adj[v[0].cell].push_back({v[1].cell, v[0].s});
      adj[v[1].cell].push_back({v[0].cell, v[1].s});
    }
    else if (v.size() > 2) out.msg += "nonmanifold ";
  }
  while (!q.empty())
  {
    int c = q.front(); q.pop_front();
    for (auto& e : adj[c])
    {
      // w(c) = w(nb) + s_c  => w(nb) = w(c) - s_c
      int nb = e.first;
      int val = w[c] - e.second;
      if (w[nb] == INT_MIN) { w[nb] = val; q.push_back(nb); }
      else if (w[nb] != val) out.nConflict++;
    }
  }
  // 4. boundary of kept cells
  BRep_Builder bb;
  TopoDS_Shell sh;
  bb.MakeShell(sh);
  int nb = 0;
  std::string wl;
  for (int c = 0; c < (int)cells.size(); c++) { wl += std::to_string(w[c]) + ","; if (w[c] >= 1) out.nKept++; }
  out.msg += "w=[" + wl + "] ";
  for (int i = 1; i <= occ.Extent(); i++)
  {
    std::vector<Occ>& v = *occ(i);
    bool k0 = v.size() >= 1 && w[v[0].cell] >= 1;
    bool k1 = v.size() >= 2 && w[v[1].cell] >= 1;
    if (v.size() == 1 && k0) { bb.Add(sh, v[0].face); nb++; }
    else if (v.size() == 2 && k0 != k1) { bb.Add(sh, k0 ? v[0].face : v[1].face); nb++; }
  }
  if (!nb) { out.msg += "empty"; return out; }
  ShapeFix_Shell fs(sh);
  fs.FixFaceOrientation(sh, true, false);
  TopoDS_Shape shells = fs.Shape();
  TopoDS_Solid so;
  bb.MakeSolid(so);
  for (TopExp_Explorer ex(shells, TopAbs_SHELL); ex.More(); ex.Next()) bb.Add(so, ex.Current());
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

static TopoDS_Shape runOffset(const TopoDS_Shape& s, const NCollection_List<TopoDS_Shape>& cl, bool thick, double t,
                              GeomAbs_JoinType join, int& done, int& err, std::string& exc)
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
      if (done) r = mk.Shape();
    }
    else
    {
      BRepOffsetAPI_MakeOffsetShape mk;
      mk.PerformByJoin(s, t, 1.e-7, BRepOffset_Skin, false, false, join);
      done = mk.IsDone(); err = (int)mk.MakeOffset().Error();
      if (done) r = mk.Shape();
    }
  }
  catch (Standard_Failure const& e) { exc = std::string("SF:") + (e.GetMessageString() ? e.GetMessageString() : ""); for (auto& c : exc) if (c == ' ') c = '_'; }
  catch (...) { exc = "unknown"; }
  return r;
}

static void report(const char* tag, const TopoDS_Shape& r, const TopoDS_Shape& S, double t, const std::vector<TopoDS_Face>& rem,
                   int done, int err, const std::string& exc, long long ms)
{
  std::string bop; int ns = 0;
  std::string gr = exc != "-" ? "EXC" : (done && !r.IsNull() ? grade034b(r, bop, ns) : "ERR");
  double vol = 0; int nf = 0;
  Oracle034b o;
  if (!r.IsNull() && done)
  {
    GProp_GProps g; BRepGProp::VolumeProperties(r, g); vol = g.Mass();
    for (TopExp_Explorer e(r, TopAbs_FACE); e.More(); e.Next()) nf++;
    o = distOracle034b(r, S, t, rem, 1e-4, std::max(1e-4, 2e-3 * std::abs(t)));
  }
  printf("%s done=%d err=%d exc=%s ms=%lld grade=%s bop=%s nsol=%d nf=%d vol=%.5f oracle S=%d OFF=%d WALL=%d MIX=%d offDev=%.2e mixWorst=%.3g mix=[%s]\n",
         tag, done, err, exc.c_str(), ms, gr.c_str(), bop.empty() ? "-" : bop.c_str(), ns, nf, vol, o.nS, o.nOff, o.nWall, o.nMix, o.offDev, o.mixWorst, o.mixList.c_str());
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
  const GeomAbs_JoinType join = !strcmp(argv[4], "int") ? GeomAbs_Intersection : GeomAbs_Arc;
  const int N = argc > 6 ? atoi(argv[6]) : 4;
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  NCollection_List<TopoDS_Shape> cl;
  std::vector<TopoDS_Face> rem;
  std::string rs = argv[5];
  if (thick)
  {
    if (rs == "largest") { int k = largestPlane(fm); cl.Append(fm(k)); rem.push_back(TopoDS::Face(fm(k))); }
    else if (rs != "none")
    {
      char buf[256]; strncpy(buf, rs.c_str(), 255); buf[255] = 0;
      for (char* p = strtok(buf, ","); p; p = strtok(nullptr, ",")) { int k = atoi(p); cl.Append(fm(k)); rem.push_back(TopoDS::Face(fm(k))); }
    }
  }
  GProp_GProps g0; BRepGProp::VolumeProperties(s, g0);
  printf("IN nf=%d vol0=%.5f op=%s t=%g join=%s N=%d\n", fm.Extent(), g0.Mass(), argv[2], t, argv[4], N);
  int done, err; std::string exc;
  auto t0 = std::chrono::steady_clock::now();
  TopoDS_Shape r0 = runOffset(s, cl, thick, t, join, done, err, exc);
  long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
  report("STOCK", r0, s, t, rem, done, err, exc, ms);
  if (r0.IsNull() || !done) return 0;
  t0 = std::chrono::steady_clock::now();
  SelfUnion034b su;
  try { su = selfUnion(r0, N); }
  catch (Standard_Failure const& e) { su.msg += std::string("EXC:") + (e.GetMessageString() ? e.GetMessageString() : ""); }
  ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
  printf("SU fold=%d pieces=%d cells=%d kept=%d conflicts=%d msg=%s\n", su.nFold, su.nPieces, su.nCells, su.nKept, su.nConflict, su.msg.c_str());
  report("UNION", su.result, s, t, rem, !su.result.IsNull(), 0, "-", ms);
  if (argc > 8 && !su.result.IsNull())
  {
    std::string od = argv[7], tag = argv[8];
    BRepTools::Write(r0, (od + "/" + tag + "_stock.brep").c_str());
    BRepTools::Write(su.result, (od + "/" + tag + "_union.brep").c_str());
  }
  PROCESS_MEMORY_COUNTERS pmc; GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc));
  printf("peakMB=%.0f\n", pmc.PeakWorkingSetSize / 1048576.0);
  return 0;
}
