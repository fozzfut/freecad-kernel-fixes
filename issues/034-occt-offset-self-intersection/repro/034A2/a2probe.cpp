// a2probe.cpp - issue 034 stage A2 probe: structure of thick-solid / offset results.
//   a2probe gen <dir>   : parametric family of the class (closed input shell, removed faces tangent to their
//                          blends; analytic + NURBS; rotated placements) written as BREP + a key file
//   a2probe run <in.brep> <thick|offset> <t> <arc|int> <removeSpec> [out.brep]
//        removeSpec: none | top (the plane face with the highest centroid along +Z of the LOCAL frame, i.e. the
//                    face that was the top before the placement) | <1-based face list>
//   Prints one A2 line: done, err, BRepCheck verdict and the failing sub-shape statuses, BOP self-interference,
//   shells with (faces, free edges, edges with unbalanced orientation, non-manifold edges), ms.
#include <BRepAlgoAPI_Check.hxx>
#include <BRepBuilderAPI_NurbsConvert.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepCheck_ListOfStatus.hxx>
#include <BRepCheck_Result.hxx>
#include <BRepCheck_Status.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepTools.hxx>
#include <STEPControl_Reader.hxx>
#include <GProp_GProps.hxx>
#include <Geom_Plane.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <gp_Ax1.hxx>
#include <gp_Trsf.hxx>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>

static std::string shellInfo(const TopoDS_Shape& r)
{
  std::string s;
  int         n = 0;
  for (TopExp_Explorer ex(r, TopAbs_SHELL); ex.More(); ex.Next())
  {
    ++n;
    std::map<const void*, std::pair<int, int>> uses; // TShape -> (forward, reversed)
    int nf = 0;
    for (TopExp_Explorer ef(ex.Current(), TopAbs_FACE); ef.More(); ef.Next())
    {
      ++nf;
      for (TopExp_Explorer ee(ef.Current(), TopAbs_EDGE); ee.More(); ee.Next())
      {
        const TopoDS_Edge& e = TopoDS::Edge(ee.Current());
        if (BRep_Tool::Degenerated(e))
          continue;
        auto& u = uses[e.TShape().get()];
        if (e.Orientation() == TopAbs_FORWARD)
          u.first++;
        else if (e.Orientation() == TopAbs_REVERSED)
          u.second++;
      }
    }
    int fr = 0, unb = 0, nm = 0;
    for (auto& kv : uses)
    {
      const int t = kv.second.first + kv.second.second;
      if (t == 1)
        fr++;
      if (kv.second.first != kv.second.second)
        unb++;
      if (t > 2)
        nm++;
    }
    char b[128];
    snprintf(b, sizeof b, "%d:f%d/free%d/unb%d/nm%d/%s%s,", n, nf, fr, unb, nm, ex.Current().Closed() ? "c" : "o",
             ex.Current().Orientation() == TopAbs_REVERSED ? "R" : "F");
    s += b;
  }
  return std::to_string(n) + "[" + s + "]";
}

static std::string checkInfo(const TopoDS_Shape& r, bool& valid)
{
  BRepCheck_Analyzer an(r);
  valid = an.IsValid();
  if (valid)
    return "-";
  std::map<std::string, int> st;
  const TopAbs_ShapeEnum     types[] = {TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE, TopAbs_VERTEX};
  const char*                tn[]    = {"So", "Sh", "Fa", "Wi", "Ed", "Ve"};
  for (int k = 0; k < 6; k++)
  {
    TopTools_IndexedMapOfShape m;
    TopExp::MapShapes(r, types[k], m);
    for (int i = 1; i <= m.Extent(); i++)
    {
      const occ::handle<BRepCheck_Result>& res = an.Result(m(i));
      if (res.IsNull())
        continue;
      for (res->InitContextIterator(); res->MoreShapeInContext(); res->NextShapeInContext())
        for (BRepCheck_ListOfStatus::Iterator it(res->StatusOnShape()); it.More(); it.Next())
          if (it.Value() != BRepCheck_NoError)
            st[std::string(tn[k]) + std::to_string((int)it.Value())]++;
      for (BRepCheck_ListOfStatus::Iterator it(res->Status()); it.More(); it.Next())
        if (it.Value() != BRepCheck_NoError)
          st[std::string(tn[k]) + "s" + std::to_string((int)it.Value())]++;
    }
  }
  std::string s;
  for (auto& kv : st)
    s += kv.first + "x" + std::to_string(kv.second) + ",";
  return s;
}

static double maxTol(const TopoDS_Shape& s)
{
  double m = 0;
  for (TopExp_Explorer e(s, TopAbs_EDGE); e.More(); e.Next()) m = std::max(m, BRep_Tool::Tolerance(TopoDS::Edge(e.Current())));
  for (TopExp_Explorer e(s, TopAbs_VERTEX); e.More(); e.Next()) m = std::max(m, BRep_Tool::Tolerance(TopoDS::Vertex(e.Current())));
  return m;
}
static TopoDS_Shape readBrep(const char* p)
{
  TopoDS_Shape r;
  std::string sp(p);
  if (sp.size() > 5 && (sp.substr(sp.size() - 5) == ".step" || sp.substr(sp.size() - 4) == ".stp"))
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
  if (!r.IsNull() && r.ShapeType() == TopAbs_COMPOUND)
  {
    TopExp_Explorer ex(r, TopAbs_SOLID);
    if (ex.More())
      r = ex.Current();
  }
  return r;
}

// the face whose centroid is highest along up (the top plane of the generated cases, also as NURBS)
static int topFace(const TopTools_IndexedMapOfShape& fm, const gp_Dir& up)
{
  int    best = 0;
  double bz   = -1e300;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    const TopoDS_Face& f = TopoDS::Face(fm(k));
    GProp_GProps g;
    BRepGProp::SurfaceProperties(f, g);
    const double z = gp_Vec(g.CentreOfMass().XYZ()).Dot(gp_Vec(up));
    if (z > bz + 1e-9)
    {
      bz   = z;
      best = k;
    }
  }
  return best;
}

static FILE* g_keys = nullptr;
static void  save(const TopoDS_Shape& s, const std::string& dir, const std::string& name, const char* upTag)
{
  const std::string p = dir + "/" + name + ".brep";
  BRepTools::Write(s, p.c_str());
  GProp_GProps g;
  BRepGProp::VolumeProperties(s, g);
  bool v;
  checkInfo(s, v);
  printf("GEN %s vol=%.6f valid=%d up=%s\n", name.c_str(), g.Mass(), (int)v, upTag);
}

// rotation used for placement variants: 30 deg about (1,2,3) through (7,-4,2), plus a translation
static gp_Trsf placeTrsf()
{
  gp_Trsf r, t;
  r.SetRotation(gp_Ax1(gp_Pnt(7, -4, 2), gp_Dir(1, 2, 3)), 30. * M_PI / 180.);
  t.SetTranslation(gp_Vec(13.5, -250.25, 41.));
  return t * r;
}

static int gen(const std::string& dir)
{
  struct Box
  {
    double L, W, H, r;
    int    edges; // 12 = all, 4 = the 4 top edges, 8 = the 8 non-top edges, 16 = all + top edges of other kind
  };
  const Box boxes[] = {{100, 60, 40, 5, 12}, {120, 80, 50, 8, 12}, {30, 20, 10, 2, 12}, {100, 60, 40, 5, 4},
                       {100, 60, 40, 5, 8},  {50, 50, 50, 10, 12}};
  for (const Box& b : boxes)
  {
    TopoDS_Shape                   b0 = BRepPrimAPI_MakeBox(b.L, b.W, b.H).Shape();
    BRepFilletAPI_MakeFillet       mf(b0);
    int                            n = 0;
    for (TopExp_Explorer ex(b0, TopAbs_EDGE); ex.More(); ex.Next())
    {
      TopTools_IndexedMapOfShape vm;
      TopExp::MapShapes(ex.Current(), TopAbs_VERTEX, vm);
      bool top = true;
      for (int i = 1; i <= vm.Extent(); i++)
        top = top && std::abs(BRep_Tool::Pnt(TopoDS::Vertex(vm(i))).Z() - b.H) < 1e-9;
      if (b.edges == 12 || (b.edges == 4 && top) || (b.edges == 8 && !top))
      {
        mf.Add(b.r, TopoDS::Edge(ex.Current()));
        n++;
      }
    }
    mf.Build();
    if (!mf.IsDone())
    {
      printf("GEN fail box\n");
      continue;
    }
    char nm[128];
    snprintf(nm, sizeof nm, "fbox%g_%g_%g_r%g_e%d", b.L, b.W, b.H, b.r, b.edges);
    save(mf.Shape(), dir, nm, "z");
    save(BRepBuilderAPI_NurbsConvert(mf.Shape()).Shape(), dir, std::string(nm) + "_nurbs", "z");
    save(BRepBuilderAPI_Transform(mf.Shape(), placeTrsf(), true).Shape(), dir, std::string(nm) + "_rot", "rot");
  }
  // cylinder r20 h30, top circular edge filleted r3 (torus tangent to the top plane), and both edges
  for (int both = 0; both < 2; both++)
  {
    TopoDS_Shape             c = BRepPrimAPI_MakeCylinder(20, 30).Shape();
    BRepFilletAPI_MakeFillet mf(c);
    for (TopExp_Explorer ex(c, TopAbs_EDGE); ex.More(); ex.Next())
    {
      const TopoDS_Edge& e = TopoDS::Edge(ex.Current());
      if (BRep_Tool::IsClosed(e, TopoDS::Face(TopExp_Explorer(c, TopAbs_FACE).Current())) && false)
        continue;
      double                      a, bb;
      occ::handle<Geom_Curve>     cu = BRep_Tool::Curve(e, a, bb);
      if (cu.IsNull())
        continue;
      const gp_Pnt p0 = cu->Value(a), p1 = cu->Value(bb);
      if (p0.Distance(p1) > 1e-6)
        continue; // seam line
      if (std::abs(p0.Z() - 30) < 1e-9 || both)
        mf.Add(3., e);
    }
    mf.Build();
    if (!mf.IsDone())
    {
      printf("GEN fail cyl\n");
      continue;
    }
    const std::string nm = both ? "fcyl20_30_r3_both" : "fcyl20_30_r3_top";
    save(mf.Shape(), dir, nm, "z");
    save(BRepBuilderAPI_NurbsConvert(mf.Shape()).Shape(), dir, nm + "_nurbs", "z");
    save(BRepBuilderAPI_Transform(mf.Shape(), placeTrsf(), true).Shape(), dir, nm + "_rot", "rot");
  }
  return 0;
}

// verbatim copy of the A2 topology checks (BRepOffset_MakeOffset.cxx) for timing: a2probe stime <shape>
#include <NCollection_IndexedMap.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <NCollection_Vector.hxx>
#include <NCollection_Map.hxx>
namespace {
struct EdgeUses034
{
  int NbF   = 0;
  int NbR   = 0;
  int Face1 = 0;
  int Face2 = 0; //!< the first face of the second use (0 = none)
};

//! Collects the edge uses of the FORWARD/REVERSED faces of theS
//! (orientations composed as in the shape, like BRepCheck_Shell).
static void collectEdgeUses034(
  const TopoDS_Shape&                                            theS,
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher>& theEdges,
  NCollection_Vector<EdgeUses034>&                               theUses)
{
  int aFaceIdx = 0;
  for (TopExp_Explorer aFExp(theS, TopAbs_FACE); aFExp.More(); aFExp.Next())
  {
    const TopAbs_Orientation aFOr = aFExp.Current().Orientation();
    if (aFOr != TopAbs_FORWARD && aFOr != TopAbs_REVERSED)
    {
      continue;
    }
    ++aFaceIdx;
    for (TopExp_Explorer anEExp(aFExp.Current(), TopAbs_EDGE); anEExp.More(); anEExp.Next())
    {
      const TopoDS_Edge&       anE  = TopoDS::Edge(anEExp.Current());
      const TopAbs_Orientation anOr = anE.Orientation();
      if ((anOr != TopAbs_FORWARD && anOr != TopAbs_REVERSED) || BRep_Tool::Degenerated(anE))
      {
        continue;
      }
      const int anIdx = theEdges.Add(anE); // indices come in order 1, 2, ...
      if (anIdx > theUses.Length())
      {
        theUses.Append(EdgeUses034());
      }
      EdgeUses034& aU = theUses.ChangeValue(anIdx - 1);
      if (aU.NbF + aU.NbR == 0)
      {
        aU.Face1 = aFaceIdx;
      }
      else if (aU.NbF + aU.NbR == 1)
      {
        aU.Face2 = aFaceIdx;
      }
      (anOr == TopAbs_FORWARD ? aU.NbF : aU.NbR)++;
    }
  }
}

//! True if a shell of a solid of theS is open or incoherently oriented:
//! a non-degenerated edge used once (BRepCheck_NotClosed), or used by two
//! different faces with the same orientation (BRepCheck_BadOrientationOf
//! Subshape). Edges with more than two uses are left to BRepCheck.
static bool solidShellsBroken034(const TopoDS_Shape& theS)
{
  for (TopExp_Explorer aSoExp(theS, TopAbs_SOLID); aSoExp.More(); aSoExp.Next())
  {
    for (TopExp_Explorer aShExp(aSoExp.Current(), TopAbs_SHELL); aShExp.More(); aShExp.Next())
    {
      NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> anEdges;
      NCollection_Vector<EdgeUses034>                               aUses;
      collectEdgeUses034(aShExp.Current(), anEdges, aUses);
      for (int i = 0; i < aUses.Length(); ++i)
      {
        const EdgeUses034& aU  = aUses.Value(i);
        const int          aNb = aU.NbF + aU.NbR;
        if (aNb == 1 || (aNb == 2 && aU.NbF != 1 && aU.Face1 != aU.Face2))
        {
          return true;
        }
      }
    }
  }
  return false;
}

//! Largest number of shells a thick solid glued from the faces of theRest
//! (the input without the removed faces) and their offsets can have: per
//! connected piece of theRest, 1 if the piece has a free edge, else 2.
static int maxThickShells034(const TopoDS_Shape& theRest)
{
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> aFaces;
  for (TopExp_Explorer aFExp(theRest, TopAbs_FACE); aFExp.More(); aFExp.Next())
  {
    aFaces.Add(aFExp.Current());
  }
  const int aNbF = aFaces.Extent();
  if (aNbF == 0)
  {
    return 0;
  }
  // union-find over the faces through their shared edges
  NCollection_Array1<int> aParent(0, aNbF);
  for (int i = 0; i <= aNbF; ++i)
  {
    aParent(i) = i;
  }
  auto aFind = [&aParent](int theI) {
    while (aParent(theI) != theI)
    {
      aParent(theI) = aParent(aParent(theI));
      theI          = aParent(theI);
    }
    return theI;
  };
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> anEdges;
  NCollection_Vector<int> anEdgeFace; // first face of an edge
  NCollection_Vector<int> anEdgeUses;
  for (int iF = 1; iF <= aNbF; ++iF)
  {
    for (TopExp_Explorer anEExp(aFaces(iF), TopAbs_EDGE); anEExp.More(); anEExp.Next())
    {
      const TopoDS_Edge& anE = TopoDS::Edge(anEExp.Current());
      if (BRep_Tool::Degenerated(anE))
      {
        continue;
      }
      const int anIdx = anEdges.Add(anE); // indices come in order 1, 2, ...
      if (anIdx > anEdgeFace.Length())
      {
        anEdgeFace.Append(iF);
        anEdgeUses.Append(0);
      }
      ++anEdgeUses.ChangeValue(anIdx - 1);
      const int aR1 = aFind(anEdgeFace.Value(anIdx - 1)), aR2 = aFind(iF);
      if (aR1 != aR2)
      {
        aParent(aR1) = aR2;
      }
    }
  }
  NCollection_Map<int> anOpenRoots, aRoots;
  for (int i = 0; i < anEdgeUses.Length(); ++i)
  {
    if (anEdgeUses.Value(i) == 1)
    {
      anOpenRoots.Add(aFind(anEdgeFace.Value(i)));
    }
  }
  int aMax = 0;
  for (int iF = 1; iF <= aNbF; ++iF)
  {
    const int aR = aFind(iF);
    if (aRoots.Add(aR))
    {
      aMax += anOpenRoots.Contains(aR) ? 1 : 2;
    }
  }
  return aMax;
}

}
static int stime(const char* p)
{
  TopoDS_Shape s = readBrep(p);
  auto t0 = std::chrono::steady_clock::now();
  bool b = solidShellsBroken034(s);
  auto t1 = std::chrono::steady_clock::now();
  TopoDS_Compound c; BRep_Builder bb; bb.MakeCompound(c);
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next()) bb.Add(c, e.Current());
  auto t2 = std::chrono::steady_clock::now();
  int m = maxThickShells034(c);
  auto t3 = std::chrono::steady_clock::now();
  int nf = 0; for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next()) nf++;
  printf("STIME faces=%d broken=%d shellsUS=%lld maxShells=%d countUS=%lld\n", nf, (int)b,
         (long long)std::chrono::duration_cast<std::chrono::microseconds>(t1 - t0).count(), m,
         (long long)std::chrono::duration_cast<std::chrono::microseconds>(t3 - t2).count());
  return 0;
}
int main(int argc, char** argv)
{
  if (argc >= 3 && !strcmp(argv[1], "stime"))
    return stime(argv[2]);
  if (argc >= 3 && !strcmp(argv[1], "gen"))
    return gen(argv[2]);
  if (argc < 7)
  {
    printf("usage\n");
    return 2;
  }
  TopoDS_Shape s = readBrep(argv[2]);
  if (s.IsNull())
  {
    printf("READ-FAIL\n");
    return 3;
  }
  const std::string op   = argv[3];
  const double      t    = atof(argv[4]);
  const auto        join = !strcmp(argv[5], "int") ? GeomAbs_Intersection : GeomAbs_Arc;
  const std::string rem  = argv[6];
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  NCollection_List<TopoDS_Shape> cl;
  std::string                    remTag;
  if (rem == "top" || rem == "toprot")
  {
    gp_Dir up(0, 0, 1);
    if (rem == "toprot")
      up.Transform(placeTrsf());
    const int k = topFace(fm, up);
    cl.Append(fm(k));
    remTag = std::to_string(k);
  }
  else if (rem != "none")
  {
    char buf[256];
    strncpy(buf, rem.c_str(), 255);
    buf[255] = 0;
    for (char* p = strtok(buf, ","); p; p = strtok(nullptr, ","))
      cl.Append(fm(atoi(p)));
    remTag = rem;
  }
  int          done = 0, err = -1;
  std::string  exc  = "-";
  TopoDS_Shape r;
  auto         t0 = std::chrono::steady_clock::now();
  try
  {
    if (op == "thick")
    {
      BRepOffsetAPI_MakeThickSolid mk;
      mk.MakeThickSolidByJoin(s, cl, t, 1.e-7, BRepOffset_Skin, false, false, join);
      done = mk.IsDone();
      err  = (int)mk.MakeOffset().Error();
      if (done)
        r = mk.Shape();
    }
    else
    {
      BRepOffsetAPI_MakeOffsetShape mk;
      mk.PerformByJoin(s, t, 1.e-7, BRepOffset_Skin, false, false, join);
      done = mk.IsDone();
      err  = (int)mk.MakeOffset().Error();
      if (done)
        r = mk.Shape();
    }
  }
  catch (Standard_Failure const& e)
  {
    exc = "Standard_Failure";
  }
  const long long ms =
    std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
  std::string sh = "-", ck = "-", bop = "-";
  bool        valid = false;
  double      vol = 0;
  if (done && !r.IsNull())
  {
    sh = shellInfo(r);
    ck = checkInfo(r, valid);
    BRepAlgoAPI_Check bc(r);
    bop = bc.IsValid() ? "clean" : "faults";
    GProp_GProps g;
    BRepGProp::VolumeProperties(r, g);
    vol = g.Mass();
    if (argc > 7)
      BRepTools::Write(r, argv[7]);
  }
  GProp_GProps g0;
  BRepGProp::VolumeProperties(s, g0);
  std::string ish = shellInfo(s);
  printf("A2 op=%s t=%g join=%s rem=%s done=%d err=%d exc=%s ms=%lld valid=%d bop=%s vol0=%.4f vol=%.4f shells=%s "
         "in=%s check=%s tol0=%.3g tol=%.3g\n",
         op.c_str(), t, argv[5], remTag.c_str(), done, err, exc.c_str(), ms, (int)valid, bop.c_str(), g0.Mass(), vol,
         sh.c_str(), ish.c_str(), ck.c_str(), maxTol(s), r.IsNull() ? -1. : maxTol(r));
  return 0;
}
