// offstudy.cpp - issue 034 study harness (OCCT 8.0.1 BRepOffset local self-intersection).
//   offstudy gen <dir>                       : writes the synthetic cases (BREP) into <dir>
//   offstudy run <in.brep|.step> <op> <t> <join> <inter> <self> <remove> [out.brep]
//     op     thick | offset          (BRepOffsetAPI_MakeThickSolid::MakeThickSolidByJoin / MakeOffsetShape::PerformByJoin)
//     join   arc | int               (GeomAbs_Arc / GeomAbs_Intersection), mode always BRepOffset_Skin, tol 1e-7
//     inter  0|1  (Intersection flag), self 0|1 (SelfInter flag)
//     remove largest | none | <face index list 1-based, comma separated>
//   Prints one RES line: done flag, Error() code, exception, build ms, grade of the result
//   (OK | BOP = BRepCheck-valid but BRepAlgoAPI_Check faults | INV = BRepCheck invalid | ERR | EXC),
//   BOP fault statuses, volume, and the FOLD PREDICTOR: for every offset (non-removed) input face, the sign of the
//   offset-surface Jacobian J = ((P+dN)_u x (P+dN)_v).N / |P_u x P_v| on an interior UV grid; J < 0 means the
//   face's own offset folds (offset distance beyond the focal distance: Maekawa 1999 / Farouki 1986).
#include <BRepAlgoAPI_Check.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_NurbsConvert.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRepBndLib.hxx>
#include <Bnd_Box.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepTools.hxx>
#include <BRepTopAdaptor_FClass2d.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <Geom_Curve.hxx>
#include <Geom_Plane.hxx>
#include <Geom_Surface.hxx>
#include <STEPControl_Reader.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <windows.h>
#include <psapi.h>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>

static TopoDS_Shape readAny(const char* p)
{
  std::string s(p);
  TopoDS_Shape r;
  if (s.size() > 5 && (s.substr(s.size() - 5) == ".step" || s.substr(s.size() - 4) == ".stp"))
  {
    STEPControl_Reader rd;
    if (rd.ReadFile(p) != IFSelect_RetDone) return r;
    rd.TransferRoots();
    r = rd.OneShape();
  }
  else
  {
    BRep_Builder bb;
    BRepTools::Read(r, p, bb);
  }
  if (r.IsNull() || r.ShapeType() == TopAbs_SOLID) return r;
  // largest solid
  double best = -1;
  TopoDS_Shape bs;
  for (TopExp_Explorer ex(r, TopAbs_SOLID); ex.More(); ex.Next())
  {
    GProp_GProps g;
    BRepGProp::VolumeProperties(ex.Current(), g);
    if (std::abs(g.Mass()) > best) { best = std::abs(g.Mass()); bs = ex.Current(); }
  }
  return bs.IsNull() ? r : bs;
}

static std::string grade(const TopoDS_Shape& s, std::string& bop)
{
  if (s.IsNull()) return "ERR";
  int ns = 0;
  for (TopExp_Explorer ex(s, TopAbs_SOLID); ex.More(); ex.Next()) ns++;
  const bool valid = BRepCheck_Analyzer(s).IsValid();
  BRepAlgoAPI_Check ck(s);
  std::map<int, int> st;
  for (const BOPAlgo_CheckResult& cr : ck.Result()) st[(int)cr.GetCheckStatus()]++;
  for (auto& kv : st) bop += std::to_string(kv.first) + "x" + std::to_string(kv.second) + ",";
  if (bop.empty()) bop = "-";
  if (!valid) return "INV";
  if (ns < 1) return "NOSOLID";
  if (!ck.IsValid()) return "BOP";
  return "OK";
}

// fold predictor for one face and signed offset t along the solid's outward normal
static void foldFace(const TopoDS_Face& f, double t, double& minJ, int& nNeg, int& nTot)
{
  minJ = 1e30; nNeg = 0; nTot = 0;
  TopLoc_Location L;
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(f, L);
  if (S.IsNull()) return;
  const double d = (f.Orientation() == TopAbs_REVERSED) ? -t : t;
  double u0, u1, v0, v1;
  BRepTools::UVBounds(f, u0, u1, v0, v1);
  BRepTopAdaptor_FClass2d cls(f, 1e-9);
  const int n = 24;
  const double hu = (u1 - u0) * 1e-4, hv = (v1 - v0) * 1e-4;
  auto Q = [&](double u, double v, gp_Pnt& P, gp_Vec& N) -> bool {
    gp_Vec du, dv;
    S->D1(u, v, P, du, dv);
    N = du.Crossed(dv);
    if (N.Magnitude() < 1e-14) return false;
    N.Normalize();
    return true;
  };
  for (int i = 1; i < n; i++)
    for (int j = 1; j < n; j++)
    {
      const double u = u0 + (u1 - u0) * i / n, v = v0 + (v1 - v0) * j / n;
      if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) continue;
      gp_Pnt P, Pa, Pb, Pc, Pd; gp_Vec N, Na, Nb, Nc, Nd;
      if (!Q(u, v, P, N) || !Q(u + hu, v, Pa, Na) || !Q(u - hu, v, Pb, Nb) || !Q(u, v + hv, Pc, Nc)
          || !Q(u, v - hv, Pd, Nd)) continue;
      const gp_Vec Pu = gp_Vec(Pb, Pa), Pv = gp_Vec(Pd, Pc);
      const gp_Vec Qu = Pu + (Na - Nb) * d, Qv = Pv + (Nc - Nd) * d;
      const double a = Pu.Crossed(Pv).Magnitude();
      if (a < 1e-300) continue;
      const double J = Qu.Crossed(Qv).Dot(N) / a;
      nTot++;
      if (J < 0) nNeg++;
      if (J < minJ) minJ = J;
    }
}

static int largestPlane(const TopTools_IndexedMapOfShape& fm)
{
  int of = 0; double best = -1.;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    const TopoDS_Face& f = TopoDS::Face(fm(k));
    if (BRep_Tool::Surface(f).IsNull() || occ::handle<Geom_Plane>::DownCast(BRep_Tool::Surface(f)).IsNull()) continue;
    GProp_GProps g;
    BRepGProp::SurfaceProperties(f, g);
    if (g.Mass() > best + 1e-9) { best = g.Mass(); of = k; }
  }
  return of;
}

static void save(const TopoDS_Shape& s, const std::string& dir, const char* name)
{
  std::string p = dir + "/" + name + ".brep";
  BRepTools::Write(s, p.c_str());
  GProp_GProps g;
  BRepGProp::VolumeProperties(s, g);
  printf("GEN %s faces=%d vol=%.6f valid=%d\n", name, [&] { int k = 0; for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next()) k++; return k; }(),
         g.Mass(), (int)BRepCheck_Analyzer(s).IsValid());
}

static TopoDS_Edge findEdge(const TopoDS_Shape& s, const gp_Pnt& mid)
{
  TopoDS_Edge best; double bd = 1e30;
  for (TopExp_Explorer ex(s, TopAbs_EDGE); ex.More(); ex.Next())
  {
    const TopoDS_Edge& e = TopoDS::Edge(ex.Current());
    double a, b;
    occ::handle<Geom_Curve> c = BRep_Tool::Curve(e, a, b);
    if (c.IsNull()) continue;
    const double dd = c->Value(0.5 * (a + b)).Distance(mid);
    if (dd < bd) { bd = dd; best = e; }
  }
  return best;
}

static int gen(const std::string& dir)
{
  // L1: L-shaped wall 2 mm thick (outer 20x20, height 10), inner concave vertical edge at (2,2) filleted r0.5
  {
    TopoDS_Shape a = BRepPrimAPI_MakeBox(20, 20, 10).Shape();
    TopoDS_Shape b = BRepPrimAPI_MakeBox(gp_Pnt(2, 2, -1), gp_Pnt(21, 21, 11)).Shape();
    TopoDS_Shape L = BRepAlgoAPI_Cut(a, b).Shape();
    save(L, dir, "lwall_sharp");
    BRepFilletAPI_MakeFillet mf(L);
    mf.Add(0.5, findEdge(L, gp_Pnt(2, 2, 5)));
    mf.Build();
    save(mf.Shape(), dir, "lwall_r05");
    save(BRepBuilderAPI_NurbsConvert(mf.Shape()).Shape(), dir, "lwall_r05_nurbs");
  }
  // S1: step block (20x10x10 + 10x10x10 on top of x<10), concave edge along y at x=10,z=10 filleted r1
  {
    TopoDS_Shape a = BRepPrimAPI_MakeBox(20, 10, 10).Shape();
    TopoDS_Shape b = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 10), gp_Pnt(10, 10, 20)).Shape();
    BRepAlgoAPI_Fuse fu(a, b);
    fu.SimplifyResult();
    TopoDS_Shape S = fu.Shape();
    BRepFilletAPI_MakeFillet mf(S);
    mf.Add(1.0, findEdge(S, gp_Pnt(10, 5, 10)));
    mf.Build();
    save(mf.Shape(), dir, "step_r1");
    save(BRepBuilderAPI_NurbsConvert(mf.Shape()).Shape(), dir, "step_r1_nurbs");
  }
  // C1: box corner with three concave-meeting fillets is complex; use a pocket: box 20x20x10 minus box pocket
  // (5..15, 5..15, 4..11); fillet the 4 vertical pocket edges r1 and the pocket floor edges r1 -> concave
  // spherical/toroidal corners (analytic) and the NURBS copy (free-form, no analytic status)
  {
    TopoDS_Shape a = BRepPrimAPI_MakeBox(20, 20, 10).Shape();
    TopoDS_Shape b = BRepPrimAPI_MakeBox(gp_Pnt(5, 5, 4), gp_Pnt(15, 15, 11)).Shape();
    TopoDS_Shape P = BRepAlgoAPI_Cut(a, b).Shape();
    BRepFilletAPI_MakeFillet mf(P);
    for (TopExp_Explorer ex(P, TopAbs_EDGE); ex.More(); ex.Next())
    {
      const TopoDS_Edge& e = TopoDS::Edge(ex.Current());
      double f0, f1;
      occ::handle<Geom_Curve> c = BRep_Tool::Curve(e, f0, f1);
      const gp_Pnt m = c->Value(0.5 * (f0 + f1));
      if (m.X() > 4.9 && m.X() < 15.1 && m.Y() > 4.9 && m.Y() < 15.1 && m.Z() < 9.9) mf.Add(1.0, e);
    }
    mf.Build();
    if (mf.IsDone())
    {
      save(mf.Shape(), dir, "pocket_r1");
      save(BRepBuilderAPI_NurbsConvert(mf.Shape()).Shape(), dir, "pocket_r1_nurbs");
    }
    else printf("GEN pocket_r1 FILLET-FAIL\n");
  }
  return 0;
}


// inspect <result.brep> <input> <t>: signed volume, shells, and the exact-offset distance test: every boundary
// point of a correct offset (or of the offset side of a thick solid) lies at distance |t| from the input boundary
// (Maekawa 1999). Samples 7x7 interior points per result face; per face: ORIG (all d < 1e-5), OFFS (all within
// 1% of |t|), MIXED (walls of a thick solid, or defects). close = samples with 1e-5 < d < 0.99|t| on faces that
// are neither ORIG nor walls touching an ORIG face - reported per class.
static int inspect(const char* rp, const char* ip, double t)
{
  TopoDS_Shape r = readAny(rp), s = readAny(ip);
  if (r.IsNull() || s.IsNull()) { printf("INS READ-FAIL\n"); return 3; }
  GProp_GProps g; BRepGProp::VolumeProperties(r, g);
  std::string sh;
  int nsh = 0;
  for (TopExp_Explorer ex(r, TopAbs_SHELL); ex.More(); ex.Next())
  {
    nsh++; int k = 0;
    for (TopExp_Explorer e(ex.Current(), TopAbs_FACE); e.More(); e.Next()) k++;
    sh += std::to_string(k) + (ex.Current().Closed() ? "c" : "o") + ",";
  }
  Bnd_Box bx; BRepBndLib::Add(r, bx);
  double x0, y0, z0, x1, y1, z1; bx.Get(x0, y0, z0, x1, y1, z1);
  const double at = std::abs(t);
  int nOrig = 0, nOffs = 0, nMixed = 0, closeS = 0, farS = 0, allS = 0, wrongSide = 0;
  BRepClass3d_SolidClassifier inS(s);
  // distance to the input BOUNDARY (a vertex inside a solid has distance 0 to the solid itself)
  TopoDS_Compound bnd; BRep_Builder cb; cb.MakeCompound(bnd);
  for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next()) cb.Add(bnd, ex.Current());
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(r, TopAbs_FACE, fm);
  for (int k = 1; k <= fm.Extent(); k++)
  {
    const TopoDS_Face& f = TopoDS::Face(fm(k));
    TopLoc_Location L; occ::handle<Geom_Surface> S = BRep_Tool::Surface(f, L);
    if (S.IsNull()) continue;
    double u0, u1, v0, v1; BRepTools::UVBounds(f, u0, u1, v0, v1);
    BRepTopAdaptor_FClass2d cls(f, 1e-9);
    int n0 = 0, nO = 0, nc = 0, nfar = 0, nt = 0, nw = 0;
    for (int i = 1; i < 8; i++) for (int j = 1; j < 8; j++)
    {
      const double u = u0 + (u1 - u0) * i / 8, v = v0 + (v1 - v0) * j / 8;
      if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) continue;
      gp_Pnt P = S->Value(u, v).Transformed(L.Transformation());
      BRepExtrema_DistShapeShape dss(BRepBuilderAPI_MakeVertex(P).Vertex(), bnd);
      if (!dss.IsDone()) continue;
      const double d = dss.Value();
      nt++;
      if (d < 1e-5) n0++;
      else if (std::abs(d - at) <= 0.01 * at) nO++;
      else if (d < 0.99 * at) nc++;
      else nfar++;
      if (d >= 1e-5)
      {
        inS.Perform(P, 1e-6);
        const TopAbs_State st = inS.State();
        if ((t > 0 && st == TopAbs_IN) || (t < 0 && st == TopAbs_OUT)) nw++;
      }
    }
    if (!nt) continue;
    allS += nt;
    if (n0 == nt) nOrig++;
    else if (nO == nt) nOffs++;
    else { nMixed++; closeS += nc; farS += nfar; }
    wrongSide += nw;
  }
  printf("INS vol=%.4f shells=%d[%s] bbox=(%.2f,%.2f,%.2f)-(%.2f,%.2f,%.2f) faces=%d orig=%d offs=%d mixed=%d "
         "mixedCloseSamples=%d mixedFarSamples=%d wrongSideSamples=%d samples=%d\n",
         g.Mass(), nsh, sh.c_str(), x0, y0, z0, x1, y1, z1, fm.Extent(), nOrig, nOffs, nMixed, closeS, farS, wrongSide, allS);
  return 0;
}

static int faces(const char* ip)
{
  TopoDS_Shape s = readAny(ip);
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
  for (int k = 1; k <= fm.Extent(); k++)
  {
    GProp_GProps g; BRepGProp::SurfaceProperties(fm(k), g);
    const gp_Pnt c = g.CentreOfMass();
    printf("FACE %d %s area=%.4f c=(%.3f,%.3f,%.3f)\n", k, BRep_Tool::Surface(TopoDS::Face(fm(k)))->DynamicType()->Name(), g.Mass(), c.X(), c.Y(), c.Z());
  }
  return 0;
}

int main(int argc, char** argv)
{
  if (argc >= 3 && !strcmp(argv[1], "faces")) return faces(argv[2]);
  if (argc >= 5 && !strcmp(argv[1], "inspect")) return inspect(argv[2], argv[3], atof(argv[4]));
  if (argc >= 3 && !strcmp(argv[1], "gen")) return gen(argv[2]);
  if (argc < 9) { printf("usage\n"); return 2; }
  TopoDS_Shape s = readAny(argv[2]);
  if (s.IsNull()) { printf("READ-FAIL\n"); return 3; }
  const std::string op = argv[3];
  const double t = atof(argv[4]);
  const GeomAbs_JoinType join = !strcmp(argv[5], "int") ? GeomAbs_Intersection : GeomAbs_Arc;
  const bool inter = atoi(argv[6]) != 0, self = atoi(argv[7]) != 0;
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  NCollection_List<TopoDS_Shape> cl;
  std::string rem = argv[8];
  std::map<int, bool> removed;
  if (rem == "largest") { int k = largestPlane(fm); if (k) { cl.Append(fm(k)); removed[k] = true; } }
  else if (rem != "none")
  {
    char buf[256]; strncpy(buf, rem.c_str(), 255); buf[255] = 0;
    for (char* p = strtok(buf, ","); p; p = strtok(nullptr, ",")) { int k = atoi(p); cl.Append(fm(k)); removed[k] = true; }
  }
  // fold predictor over the offset faces
  int foldF = 0; double gMinJ = 1e30; std::string foldList;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    if (removed.count(k)) continue;
    double mj; int nn, nt;
    foldFace(TopoDS::Face(fm(k)), t, mj, nn, nt);
    if (nt && mj < gMinJ) gMinJ = mj;
    if (nn > 0)
    {
      foldF++;
      occ::handle<Geom_Surface> S = BRep_Tool::Surface(TopoDS::Face(fm(k)));
      foldList += std::to_string(k) + ":" + S->DynamicType()->Name() + ":" + std::to_string(nn) + "/" + std::to_string(nt) + " ";
    }
  }
  GProp_GProps g0;
  BRepGProp::VolumeProperties(s, g0);
  std::string exc = "-";
  int done = 0, err = -1;
  TopoDS_Shape r;
  auto t0 = std::chrono::steady_clock::now();
  try
  {
    if (op == "thick")
    {
      BRepOffsetAPI_MakeThickSolid mk;
      mk.MakeThickSolidByJoin(s, cl, t, 1.e-7, BRepOffset_Skin, inter, self, join);
      done = mk.IsDone(); err = (int)mk.MakeOffset().Error();
      if (done) r = mk.Shape();
    }
    else
    {
      BRepOffsetAPI_MakeOffsetShape mk;
      mk.PerformByJoin(s, t, 1.e-7, BRepOffset_Skin, inter, self, join);
      done = mk.IsDone(); err = (int)mk.MakeOffset().Error();
      if (done) r = mk.Shape();
    }
  }
  catch (Standard_Failure const& e) { exc = std::string("Standard_Failure:") + (e.GetMessageString() ? e.GetMessageString() : ""); for (auto& c : exc) if (c == ' ') c = '_'; }
  catch (...) { exc = "unknown"; }
  const long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
  std::string bop, gr = "ERR";
  double vol = 0;
  int nf = 0;
  if (exc != "-") gr = "EXC";
  else if (done && !r.IsNull())
  {
    gr = grade(r, bop);
    GProp_GProps g; BRepGProp::VolumeProperties(r, g); vol = g.Mass();
    for (TopExp_Explorer e(r, TopAbs_FACE); e.More(); e.Next()) nf++;
    if (argc > 9) BRepTools::Write(r, argv[9]);
  }
  PROCESS_MEMORY_COUNTERS pmc; GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc));
  printf("RES op=%s t=%g join=%s inter=%d self=%d done=%d err=%d exc=%s ms=%lld grade=%s bop=%s nf=%d vol0=%.4f vol=%.4f "
         "foldFaces=%d minJ=%.4g peakMB=%.0f removed=%s folds=[%s]\n",
         op.c_str(), t, argv[5], (int)inter, (int)self, done, err, exc.c_str(), ms, gr.c_str(), bop.empty() ? "-" : bop.c_str(), nf,
         g0.Mass(), vol, foldF, gMinJ, pmc.PeakWorkingSetSize / 1048576.0, [&]{ std::string q; for (auto& kv : removed) q += std::to_string(kv.first) + ","; return q.empty() ? std::string("-") : q; }().c_str(), foldList.c_str());
  return 0;
}
