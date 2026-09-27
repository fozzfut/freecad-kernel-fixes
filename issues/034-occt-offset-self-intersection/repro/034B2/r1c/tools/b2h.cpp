// b2h.cpp - issue 034 lane B2 test harness (NOT kernel code).
//   b2h <in.brep> <offset|thick> <t> <arc|int> <remove: none|largest|i,j,..> [out.brep|-] [mcN] [refVol]
// Runs the plain OCCT call (BRepOffsetAPI_MakeOffsetShape::PerformByJoin / MakeThickSolidByJoin, tol 1e-7, Skin,
// Intersection=false, SelfInter=false - the FreeCAD call) with whatever TKOffset.dll the loader picks (the one next
// to the exe first), then grades the result:
//   grade  : BRepCheck + BOP self-check (chk034b.hxx)
//   oracle : every result face on S or at |t| from S (distance ONLY as a test oracle, never in the kernel)
//   mc     : N deterministic pseudo-random points in the box: membership in the result vs membership in the
//            point-set definition of the offset/thick solid (distance to the boundary of S); disagreements outside
//            a thin numerical band = wrong geometry (independent of how the kernel built it)
//   ref    : optional independent volume
// Verdict EXACT = grade OK + oracle MIX 0 + mc disagreements 0 (+ volume within 1e-6 rel of ref when given).
#include "memcap.hxx"
#include "chk034b.hxx"
#include <BRepBndLib.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <Bnd_Box.hxx>
#include <Geom_Plane.hxx>
#include <GeomLib_IsPlanarSurface.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <Standard_Failure.hxx>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <psapi.h>

static int largestPlane(const TopTools_IndexedMapOfShape& fm)
{
  int best = 0; double ba = -1;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    TopLoc_Location L;
    GeomLib_IsPlanarSurface pl(BRep_Tool::Surface(TopoDS::Face(fm(k)), L), 1e-7);
    if (!pl.IsPlanar()) continue;
    GProp_GProps g; BRepGProp::SurfaceProperties(fm(k), g);
    if (g.Mass() > ba * (1 + 1e-6)) { ba = g.Mass(); best = k; }  // ties (equal area within 1e-6): lowest index
  }
  return best;
}

static unsigned long long g_rng = 0x9E3779B97F4A7C15ull;
static double rnd01()
{
  g_rng ^= g_rng << 13; g_rng ^= g_rng >> 7; g_rng ^= g_rng << 17;
  return (g_rng >> 11) * (1.0 / 9007199254740992.0);
}

int main(int argc, char** argv)
{
  if (argc < 6) { printf("usage: b2h in op t join remove [out] [mcN] [ref]\n"); return 2; }
  TopoDS_Shape s;
  BRep_Builder bb;
  if (!BRepTools::Read(s, argv[1], bb) || s.IsNull()) { printf("READ-FAIL\n"); return 3; }
  if (!getenv("B2_RAW") && s.ShapeType() != TopAbs_SOLID) { TopExp_Explorer ex(s, TopAbs_SOLID); if (ex.More()) s = ex.Current(); }  // B2_RAW: pass a compound as FreeCAD does
  const bool thick = !strcmp(argv[2], "thick");
  const double t = atof(argv[3]);
  const GeomAbs_JoinType join = !strcmp(argv[4], "int") ? GeomAbs_Intersection : GeomAbs_Arc;
  const char* outp = argc > 6 ? argv[6] : "-";
  const int mcN = argc > 7 ? atoi(argv[7]) : 0;
  const double ref = argc > 8 ? atof(argv[8]) : 0;
  const char* refShape = argc > 9 ? argv[9] : "-";
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  NCollection_List<TopoDS_Shape> cl;
  std::vector<TopoDS_Face> rem;
  std::string rs = argv[5];
  if (thick)
  {
    if (rs == "largest") { int k = largestPlane(fm); if (!k) { puts("NO-PLANE"); return 4; } cl.Append(fm(k)); rem.push_back(TopoDS::Face(fm(k))); }
    else if (rs != "none")
    {
      char buf[256]; strncpy(buf, rs.c_str(), 255); buf[255] = 0;
      for (char* p = strtok(buf, ","); p; p = strtok(nullptr, ",")) { int k = atoi(p); cl.Append(fm(k)); rem.push_back(TopoDS::Face(fm(k))); }
    }
  }
  GProp_GProps g0; BRepGProp::VolumeProperties(s, g0);
  TopoDS_Shape r;
  int done = 0, err = -1;
  std::string exc = "-";
  auto t0 = std::chrono::steady_clock::now();
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
  long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
  std::string bop; int ns = 0;
  std::string gr = exc != "-" ? "EXC" : (done && !r.IsNull() ? grade034b(r, bop, ns) : "ERR");
  double vol = 0; int nf = 0;
  Oracle034b o;
  if (!r.IsNull() && done)
  {
    GProp_GProps g; BRepGProp::VolumeProperties(r, g); vol = g.Mass();
    for (TopExp_Explorer e(r, TopAbs_FACE); e.More(); e.Next()) nf++;
    o = distOracle034b(r, s, t, rem, 1e-4, std::max(1e-4, 2e-3 * std::abs(t)));
    if (strcmp(outp, "-")) BRepTools::Write(r, outp);
  }
  // Monte-Carlo membership (test oracle only)
  int mcBad = -1, mcIn = 0, mcSkip = 0;
  std::string mcNote;
  if (mcN > 0 && (gr == "OK" || gr == "BOP" || gr == "INV"))
  {
    bool ok = true;
    std::vector<gp_Pln> caps;
    if (thick && t > 0)
      for (const TopoDS_Face& f : rem)
      {
        TopLoc_Location L;
        GeomLib_IsPlanarSurface pl(BRep_Tool::Surface(f, L), 1e-7);
        if (!pl.IsPlanar()) { ok = false; mcNote = "nonplanar-cap"; break; }
        gp_Pln P = pl.Plan().Transformed(L.Transformation());
        {  // orient the plane like the surface normal at the face middle
          double u0, u1, v0, v1; BRepTools::UVBounds(f, u0, u1, v0, v1);
          gp_Pnt pp; gp_Vec du, dv; BRep_Tool::Surface(f, L)->D1(0.5 * (u0 + u1), 0.5 * (v0 + v1), pp, du, dv);
          gp_Vec nn = du.Crossed(dv).Transformed(L.Transformation());
          if (nn.Dot(gp_Vec(P.Axis().Direction())) < 0) P.SetAxis(P.Axis().Reversed());
        }
        if (f.Orientation() == TopAbs_REVERSED) P.SetAxis(P.Axis().Reversed());
        caps.push_back(P);  // outward normal of S at the removed face
      }
    if (ok)
    {
      Bnd_Box bx; BRepBndLib::Add(r, bx); BRepBndLib::Add(s, bx);
      double x0, y0, z0, x1, y1, z1; bx.Get(x0, y0, z0, x1, y1, z1);
      TopoDS_Compound shellS; BRep_Builder cb; cb.MakeCompound(shellS);
      for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next())
      {
        bool isRem = false;
        for (const TopoDS_Face& rf : rem) if (rf.IsSame(ex.Current())) isRem = true;
        if (!isRem) cb.Add(shellS, ex.Current());
      }
      BRepExtrema_DistShapeShape dss; dss.LoadS2(shellS);
      BRepClass3d_SolidClassifier cS(s), cR(r);
      const double at = std::abs(t), band = std::max(1e-5, 1e-4 * at);
      double resTol = 1e-7;
      for (TopExp_Explorer ee(r, TopAbs_EDGE); ee.More(); ee.Next()) resTol = std::max(resTol, BRep_Tool::Tolerance(TopoDS::Edge(ee.Current())));
      resTol = 10 * resTol + band;
      mcBad = 0;
      for (int i = 0; i < mcN; i++)
      {
        gp_Pnt p(x0 + (x1 - x0) * rnd01(), y0 + (y1 - y0) * rnd01(), z0 + (z1 - z0) * rnd01());
        cS.Perform(p, 1e-7);
        cR.Perform(p, 1e-7);
        if (cR.State() == TopAbs_ON || cS.State() == TopAbs_ON) { mcSkip++; continue; }
        const bool inS = cS.State() == TopAbs_IN, inR = cR.State() == TopAbs_IN;
        dss.LoadS1(BRepBuilderAPI_MakeVertex(p).Vertex());
        dss.Perform();
        if (!dss.IsDone()) { mcSkip++; continue; }
        const double dist = dss.Value();
        if (std::abs(dist - at) < band) { mcSkip++; continue; }
        bool truth;
        if (!thick) truth = t > 0 ? (inS || dist < at) : (inS && dist > at);
        else if (t < 0) truth = inS && dist < at;
        else
        {
          truth = !inS && dist < at;
          for (const gp_Pln& P : caps)
          {
            double sd = gp_Vec(P.Location(), p).Dot(gp_Vec(P.Axis().Direction()));
            if (std::abs(sd) < band) { truth = false; mcSkip++; goto next; }
            if (sd > 0) truth = false;
          }
        }
        if (truth) mcIn++;
        if (truth != inR)
        {
          // a disagreement within the tolerance of the result boundary is numerical, not geometry
          BRepExtrema_DistShapeShape dr(BRepBuilderAPI_MakeVertex(p).Vertex(), r);
          if (dr.IsDone() && dr.Value() <= resTol) { mcSkip++; continue; }
          mcBad++;
        }
      next:;
      }
    }
  }
  // symmetric difference with an independently built reference solid (test oracle)
  double sd = -1;
  if (strcmp(refShape, "-") && !r.IsNull() && done)
  {
    TopoDS_Shape rs; BRep_Builder rb;
    if (BRepTools::Read(rs, refShape, rb) && !rs.IsNull())
    {
      try
      {
        BRepAlgoAPI_Cut c1(r, rs), c2(rs, r);
        GProp_GProps p1, p2;
        if (c1.IsDone() && c2.IsDone())
        {
          BRepGProp::VolumeProperties(c1.Shape(), p1); BRepGProp::VolumeProperties(c2.Shape(), p2);
          sd = std::abs(p1.Mass()) + std::abs(p2.Mass());
        }
      }
      catch (...) { sd = -2; }
    }
  }
  std::string remc = "-";
  if (!rem.empty())
  {
    GProp_GProps gr; BRepGProp::SurfaceProperties(rem[0], gr);
    char b[96]; snprintf(b, 96, "(%.3f,%.3f,%.3f)", gr.CentreOfMass().X(), gr.CentreOfMass().Y(), gr.CentreOfMass().Z()); remc = b;
  }
  std::string verdict;
  if (gr == "EXC" || gr == "ERR") verdict = "ERROR";
  else if (gr == "OK" && sd >= 0)
    verdict = sd <= 1e-6 * std::max(1.0, std::abs(vol)) ? "EXACT" : "WRONG";
  else if (gr == "OK" && o.nMix == 0 && mcBad <= 0 && (ref <= 0 || std::abs(vol - ref) <= 1e-6 * std::abs(ref) + 1e-6))
    verdict = mcBad == 0 ? "EXACT" : "EXACT?";
  else verdict = "WRONG";
  PROCESS_MEMORY_COUNTERS pmc; GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc));
  printf("R %s done=%d err=%d exc=%s ms=%lld grade=%s bop=%s nsol=%d nf=%d vol=%.5f vol0=%.5f ref=%.5f "
         "oracle S=%d OFF=%d WALL=%d MIX=%d mc=%d/%d/%d%s%s sd=%.3g rem=%s peakMB=%.0f\n",
         verdict.c_str(), done, err, exc.c_str(), ms, gr.c_str(), bop.empty() ? "-" : bop.c_str(), ns, nf, vol, g0.Mass(), ref,
         o.nS, o.nOff, o.nWall, o.nMix, mcBad, mcIn, mcSkip, mcNote.empty() ? "" : " ", mcNote.c_str(), sd, remc.c_str(),
         pmc.PeakWorkingSetSize / 1048576.0);
  return 0;
}
