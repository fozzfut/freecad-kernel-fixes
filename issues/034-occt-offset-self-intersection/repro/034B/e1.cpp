// e1.cpp - issue 034 stage B experiment E1 (harness, NOT kernel code): "remove the folding faces, offset, restore".
//   e1 <in.brep> <op thick|offset> <t> <join arc|int> <remove largest|none|i,j,..> [outdir tag]
// 1. stock offset of S -> grade + distance oracle
// 2. fold faces (smallest principal offset factor < 0 on a 30x30 grid) -> BRepAlgoAPI_Defeaturing removes them (S')
// 3. stock offset of S' (removed faces of a thick solid mapped through the defeaturing history)
// 4. thick: outward -> R' cut S ; inward -> R' common S  (S' within S outward, S within S' inward)
// 5. grade + oracle of the final result against the ORIGINAL S
#include "memcap.hxx"
#include "chk034b.hxx"
#include <BRepAlgoAPI_Common.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Defeaturing.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRep_Builder.hxx>
#include <Geom_Plane.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <Standard_Failure.hxx>
#include <chrono>
#include <cstdio>
#include <cstring>
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

// share of interior samples with factor < 0 (fold) ; -1 planar
static double foldShare(const TopoDS_Face& F, double t, double& fmin)
{
  TopLoc_Location L;
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(F, L);
  fmin = 1e30;
  if (GeomAdaptor_Surface(S).GetType() == GeomAbs_Plane) return -1;
  double d = F.Orientation() == TopAbs_REVERSED ? -t : t;
  double u0, u1, v0, v1;
  BRepTools::UVBounds(F, u0, u1, v0, v1);
  BRepTopAdaptor_FClass2d cls(F, 1e-7);
  int n = 0, neg = 0;
  for (int i = 0; i < 30; i++)
    for (int j = 0; j < 30; j++)
    {
      double u = u0 + (u1 - u0) * (i + 0.5) / 30, v = v0 + (v1 - v0) * (j + 0.5) / 30;
      if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) continue;
      double f;
      if (!factor(S, u, v, d, f)) continue;
      n++;
      if (f < 0) neg++;
      fmin = std::min(fmin, f);
    }
  return n ? double(neg) / n : 0;
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
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  NCollection_List<TopoDS_Shape> cl;
  std::vector<TopoDS_Face> rem;
  std::map<int, bool> isRem;
  std::string rs = argv[5];
  if (thick)
  {
    if (rs == "largest") { int k = largestPlane(fm); cl.Append(fm(k)); rem.push_back(TopoDS::Face(fm(k))); isRem[k] = true; }
    else if (rs != "none")
    {
      char buf[256]; strncpy(buf, rs.c_str(), 255); buf[255] = 0;
      for (char* p = strtok(buf, ","); p; p = strtok(nullptr, ",")) { int k = atoi(p); cl.Append(fm(k)); rem.push_back(TopoDS::Face(fm(k))); isRem[k] = true; }
    }
  }
  GProp_GProps g0; BRepGProp::VolumeProperties(s, g0);
  printf("IN nf=%d vol0=%.5f op=%s t=%g join=%s\n", fm.Extent(), g0.Mass(), argv[2], t, argv[4]);
  // 1. stock
  int done, err; std::string exc;
  auto t0 = std::chrono::steady_clock::now();
  TopoDS_Shape r0 = runOffset(s, cl, thick, t, join, done, err, exc);
  long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
  report("STOCK", r0, s, t, rem, done, err, exc, ms);
  // 2. fold faces
  NCollection_List<TopoDS_Shape> folds;
  std::string fl;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    if (isRem.count(k)) continue;
    double fmin;
    double sh = foldShare(TopoDS::Face(fm(k)), t, fmin);
    if (sh > 0) { folds.Append(fm(k)); char b[64]; snprintf(b, 64, "%d:%.2f:%.2f ", k, sh, fmin); fl += b; }
  }
  printf("FOLDS [%s]\n", fl.c_str());
  if (folds.IsEmpty()) return 0;
  // 3. defeature
  t0 = std::chrono::steady_clock::now();
  BRepAlgoAPI_Defeaturing df;
  df.SetShape(s);
  df.AddFacesToRemove(folds);
  df.SetRunParallel(false);
  df.Build();
  if (!df.IsDone()) { printf("DEFEATURE FAILED\n"); return 0; }
  TopoDS_Shape s1 = df.Shape();
  if (s1.ShapeType() != TopAbs_SOLID) { TopExp_Explorer ex(s1, TopAbs_SOLID); if (ex.More()) s1 = ex.Current(); }
  std::string b1; int n1;
  GProp_GProps g1; BRepGProp::VolumeProperties(s1, g1);
  printf("DEFEAT grade=%s bop=%s vol=%.5f dvol=%.5f\n", grade034b(s1, b1, n1).c_str(), b1.c_str(), g1.Mass(), g1.Mass() - g0.Mass());
  NCollection_List<TopoDS_Shape> cl1;
  for (const TopoDS_Face& f : rem)
  {
    const NCollection_List<TopoDS_Shape>& m = df.Modified(f);
    if (m.IsEmpty()) cl1.Append(f);
    else for (NCollection_List<TopoDS_Shape>::Iterator it(m); it.More(); it.Next()) cl1.Append(it.Value());
  }
  TopoDS_Shape r1 = runOffset(s1, cl1, thick, t, join, done, err, exc);
  TopoDS_Shape fin = r1;
  if (done && !r1.IsNull() && thick)
  {
    try
    {
      if (t > 0) { BRepAlgoAPI_Cut c(r1, s); fin = c.IsDone() ? c.Shape() : TopoDS_Shape(); }
      else { BRepAlgoAPI_Common c(r1, s); fin = c.IsDone() ? c.Shape() : TopoDS_Shape(); }
    }
    catch (...) { fin.Nullify(); }
    if (fin.IsNull()) done = 0;
  }
  ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
  // walls: the removed faces' images in S' too
  std::vector<TopoDS_Face> rem2 = rem;
  for (NCollection_List<TopoDS_Shape>::Iterator it(cl1); it.More(); it.Next()) rem2.push_back(TopoDS::Face(it.Value()));
  report("DEBLEND", fin, s, t, rem2, done, err, exc, ms);
  if (argc > 7)
  {
    std::string od = argv[6], tag = argv[7];
    if (!r0.IsNull()) BRepTools::Write(r0, (od + "/" + tag + "_stock.brep").c_str());
    BRepTools::Write(s1, (od + "/" + tag + "_defeat.brep").c_str());
    if (!fin.IsNull()) BRepTools::Write(fin, (od + "/" + tag + "_deblend.brep").c_str());
  }
  PROCESS_MEMORY_COUNTERS pmc; GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc));
  printf("peakMB=%.0f\n", pmc.PeakWorkingSetSize / 1048576.0);
  return 0;
}
