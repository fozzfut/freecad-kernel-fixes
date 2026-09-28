// loc034b.cpp (round 2 = loc034.cpp + variant floc, variant filter, members conea/nsph/dome/rbsp/afil T2)
// loc034.cpp - lane R-034-loc (issue 034): offset / thick solid of LOCATED inputs.
//   Class: an input carrying a TopLoc_Location (Shape.Moved / FreeCAD Placement / Shape.transformed with a rigid
//   matrix) must behave exactly like its geometry-transformed twin (BRepBuilderAPI_Transform copy=true = FreeCAD
//   transformGeometry) and like the unlocated shape moved by the same transformation.
//   loc034 list                  : case names
//   loc034 run <case>            : one LOC line per placement variant:
//      none   : unlocated input (base frame)
//      geo    : geometry copy transformed by T (reference twin)
//      loc    : input.Moved(T)               (location on the root)
//      subloc : every FACE of the input carries T (compound-free: sewn shell rebuilt from located faces is not
//               needed - we move the solid's shells), i.e. location below the root: solid(shell.Moved(T))
//      nest   : root location T1 on top of sub-shape location T2 (T = T1*T2)
//   Result fields: done, error code, build ms, BRepCheck valid, BOP faults, nsolid/nshell/nface, volume, area,
//   centroid and bounding box MAPPED BACK to the base frame (T^-1) so all variants compare to "none".
#include <BRepAlgoAPI_Check.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBndLib.hxx>
#include <BRepBuilderAPI_NurbsConvert.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCone.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepPrimAPI_MakeTorus.hxx>
#include <BRepPrimAPI_MakeRevol.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <GeomAPI_PointsToBSpline.hxx>
#include <Geom_BSplineCurve.hxx>
#include <TColgp_Array1OfPnt.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <Bnd_Box.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Iterator.hxx>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <functional>
#include <string>
#include <vector>

static gp_Trsf T1()
{
  gp_Trsf r, t;
  r.SetRotation(gp_Ax1(gp_Pnt(-3, 5, 1), gp_Dir(1, 2, 3)), 47. * M_PI / 180.);
  t.SetTranslation(gp_Vec(13.1, -7.3, 21.9));
  return t * r;
}
static gp_Trsf T2()
{
  gp_Trsf r, t;
  r.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(-2, 1, 0.5)), -73. * M_PI / 180.);
  t.SetTranslation(gp_Vec(-201.5, 88.25, -9.));
  return t * r;
}
static gp_Trsf TFAR() // far from the origin (FreeCAD assemblies)
{
  gp_Trsf r, t;
  r.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0.3, -0.8, 0.52)), 111. * M_PI / 180.);
  t.SetTranslation(gp_Vec(2.5e4, -1.3e4, 7.7e3));
  return t * r;
}

static gp_Trsf T4() // root location of the 5829 world BREP (FreeCAD body placement of testCase5829)
{
  TopoDS_Shape r;
  BRep_Builder bb;
  BRepTools::Read(r, "C:/dev/occt8-mig/offset-034/cases/f5829_world.brep", bb);
  TopExp_Explorer e(r, TopAbs_SOLID);
  return e.More() ? e.Current().Location().Transformation() : r.Location().Transformation();
}
static TopoDS_Shape box(double x, double y, double z, double dx, double dy, double dz)
{
  return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape();
}
static TopoDS_Shape solid1(const TopoDS_Shape& s)
{
  TopExp_Explorer e(s, TopAbs_SOLID);
  return e.More() ? e.Current() : s;
}
static TopoDS_Shape filletEdges(const TopoDS_Shape& s, double r, std::function<bool(const TopoDS_Edge&)> sel)
{
  BRepFilletAPI_MakeFillet f(s);
  TopTools_IndexedMapOfShape m;
  TopExp::MapShapes(s, TopAbs_EDGE, m);
  for (int i = 1; i <= m.Extent(); i++)
    if (sel(TopoDS::Edge(m(i))))
      f.Add(r, TopoDS::Edge(m(i)));
  f.Build();
  return f.IsDone() ? solid1(f.Shape()) : TopoDS_Shape();
}
static bool vertical(const TopoDS_Edge& e)
{
  TopoDS_Vertex a, b;
  TopExp::Vertices(e, a, b);
  gp_Vec v(BRep_Tool::Pnt(a), BRep_Tool::Pnt(b));
  return std::abs(v.Z()) > 0.99 * v.Magnitude();
}

// face index (1-based, TopExp map order) with the largest centroid projection on n (base frame)
static int faceAt(const TopoDS_Shape& s, const gp_Dir& n)
{
  TopTools_IndexedMapOfShape m;
  TopExp::MapShapes(s, TopAbs_FACE, m);
  int    best = 0;
  double bz   = -1e300;
  for (int i = 1; i <= m.Extent(); i++)
  {
    GProp_GProps g;
    BRepGProp::SurfaceProperties(m(i), g);
    double z = gp_Vec(g.CentreOfMass().XYZ()).Dot(gp_Vec(n));
    if (z > bz + 1e-9)
    {
      bz   = z;
      best = i;
    }
  }
  return best;
}

struct Case
{
  std::string                    name;
  std::function<TopoDS_Shape()> build;
  std::vector<gp_Dir>            rm; // removed faces (thick) - empty = offset shape
  double                         t;
  GeomAbs_JoinType               join;
  int                            trsf; // 1 = T1, 2 = T2, 3 = TFAR
};

static TopoDS_Shape readBrep(const char* p)
{
  TopoDS_Shape r;
  BRep_Builder bb;
  BRepTools::Read(r, p, bb);
  return solid1(r);
}

// strip every location of a shape by baking it into the geometry: the "local" 5829 twin
static std::vector<Case> cases()
{
  std::vector<Case> v;
  auto add = [&](const std::string& n, std::function<TopoDS_Shape()> b, std::vector<gp_Dir> rm,
                 std::vector<double> ts, std::vector<int> trs = {1}) {
    for (int tr : trs)
      for (double t : ts)
        for (int j = 0; j < 2; j++)
        {
          char nm[200];
          snprintf(nm, sizeof nm, "%s_%s%g_%s_T%d", n.c_str(), rm.empty() ? "off" : "thk", t, j ? "int" : "arc", tr);
          v.push_back({nm, b, rm, t, j ? GeomAbs_Intersection : GeomAbs_Arc, tr});
        }
  };
  const gp_Dir pZ(0, 0, 1), mX(-1, 0, 0), pX(1, 0, 0);
  auto B    = []() { return box(0, 0, 0, 50, 35, 22); };
  auto CYL  = []() { return BRepPrimAPI_MakeCylinder(10, 20).Shape(); };
  auto CONE = []() { return BRepPrimAPI_MakeCone(10, 4, 15).Shape(); };
  auto SPH  = []() { return BRepPrimAPI_MakeSphere(8).Shape(); };
  auto TOR  = []() { return BRepPrimAPI_MakeTorus(12, 4).Shape(); };
  auto VFIL = []() { return filletEdges(box(0, 0, 0, 50, 35, 22), 4, vertical); };
  auto AFIL = []() { return filletEdges(box(0, 0, 0, 50, 35, 22), 4, [](const TopoDS_Edge&) { return true; }); };
  auto HOLE = []() {
    return solid1(BRepAlgoAPI_Cut(box(0, 0, 0, 40, 30, 10),
                                  BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(20, 15, -1), gp::DZ()), 5, 12).Shape())
                    .Shape());
  };
  auto NBOX = []() { return BRepBuilderAPI_NurbsConvert(box(0, 0, 0, 30, 20, 12), true).Shape(); };
  auto NVFL = []() { return BRepBuilderAPI_NurbsConvert(filletEdges(box(0, 0, 0, 40, 30, 20), 3, vertical), true).Shape(); };
  auto POCK = []() { return solid1(BRepAlgoAPI_Cut(box(0, 0, 0, 40, 40, 10), box(10, 10, 4, 20, 20, 7)).Shape()); };
  add("box", B, {pZ}, {-1.2, 1.2}, {1, 2, 3});
  add("box", B, {}, {2, -2}, {1, 3});
  add("box2rm", B, {pZ, mX}, {-1.5}, {1});
  add("cyl", CYL, {pZ}, {-1, 1}, {1, 3});
  add("cyl", CYL, {}, {1.5}, {1});
  add("cone", CONE, {pZ}, {-1}, {1});
  add("cone", CONE, {}, {1}, {2});
  add("sph", SPH, {}, {1, -1}, {1, 3});
  add("sph", SPH, {pZ}, {-1}, {1});
  add("tor", TOR, {}, {1}, {1});
  add("vfil", VFIL, {pZ}, {-1.2, 1}, {1, 3});
  add("vfil", VFIL, {}, {1, -1}, {2});
  add("afil", AFIL, {}, {1, -1}, {1, 3});
  add("afil", AFIL, {pZ}, {-1.2}, {1});
  add("hole", HOLE, {pZ}, {-1}, {1, 2});
  add("hole", HOLE, {}, {1}, {1});
  add("pock", POCK, {pZ}, {-1}, {1});
  add("nbox", NBOX, {pZ}, {-1}, {1, 3});
  add("nvfl", NVFL, {pZ}, {-1}, {1});
  add("nvfl", NVFL, {}, {1}, {2});
  // round 2 members: every face kind with a singular point (degenerated edge) under a location
  auto CONEA = []() { return BRepPrimAPI_MakeCone(10, 0, 15).Shape(); };             // apex
  auto NSPH  = []() { return BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakeSphere(8).Shape(), true).Shape(); };
  auto DOME  = []() { return BRepPrimAPI_MakeSphere(gp_Ax2(), 10, 0, M_PI / 2).Shape(); }; // half sphere
  auto RBSP  = []() {
    // B-spline profile from the axis (0,0,10) down to (6,0,0), closed along the axis, revolved 360 deg:
    // a surface of revolution of a B-spline with a pole on the axis (degenerated edge)
    TColgp_Array1OfPnt p(1, 4);
    p(1) = gp_Pnt(0, 0, 10); p(2) = gp_Pnt(4, 0, 8.5); p(3) = gp_Pnt(6, 0, 4); p(4) = gp_Pnt(6.5, 0, 0);
    occ::handle<Geom_BSplineCurve> c = GeomAPI_PointsToBSpline(p).Curve();
    TopoDS_Edge e1 = BRepBuilderAPI_MakeEdge(c);
    TopoDS_Edge e2 = BRepBuilderAPI_MakeEdge(gp_Pnt(6.5, 0, 0), gp_Pnt(0, 0, 0));
    TopoDS_Edge e3 = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(0, 0, 10));
    TopoDS_Face f  = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(e1, e2, e3).Wire(), true);
    return solid1(BRepPrimAPI_MakeRevol(f, gp_Ax1(gp_Pnt(0, 0, 0), gp::DZ())).Shape());
  };
  const gp_Dir mZ(0, 0, -1);
  add("conea", CONEA, {}, {1, -1}, {1, 3});
  add("conea", CONEA, {mZ}, {-1}, {1, 2});
  add("nsph", NSPH, {}, {1}, {1, 3});
  add("dome", DOME, {mZ}, {-1, 1}, {1, 3});
  add("rbsp", RBSP, {}, {1}, {1, 3});
  add("rbsp", RBSP, {mZ}, {-1}, {1});
  add("afil", AFIL, {}, {1}, {2});
  auto F5829 = []() {
    // the 5829 fillet in WORLD coordinates (located BREP) with its root location stripped = the body-local shape
    // FreeCAD passes (T4 = that root location = the body Placement)
    TopoDS_Shape w = readBrep("C:/dev/occt8-mig/offset-034/cases/f5829_world.brep");
    return w.Located(TopLoc_Location());
  };
  add("f5829", F5829, {pZ}, {-1, -0.5}, {4, 1});
  add("f5829", F5829, {}, {-1}, {4});
  return v;
}

static double ms(std::chrono::steady_clock::time_point a)
{
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - a).count();
}

static TopoDS_Shape subLoc(const TopoDS_Shape& s, const TopLoc_Location& L)
{
  // same solid TShape children, each shell carrying L: solid( shell.Moved(L) ) - location below the root
  BRep_Builder b;
  TopoDS_Solid so;
  b.MakeSolid(so);
  for (TopoDS_Iterator it(s); it.More(); it.Next())
    b.Add(so, it.Value().Moved(L));
  so.Orientation(s.Orientation());
  return so;
}

static const char* gOnly = nullptr;
static void runCase(const Case& c)
{
  TopoDS_Shape base = c.build();
  if (base.IsNull())
  {
    printf("LOC %s BUILD-FAILED\n", c.name.c_str());
    return;
  }
  int nInner = 0;
  for (TopExp_Explorer e(base, TopAbs_FACE); e.More(); e.Next())
    if (!e.Current().Location().IsIdentity())
      nInner++;
  if (nInner)
    printf("LOC %s INFO base-faces-located=%d\n", c.name.c_str(), nInner);
  gp_Trsf T = c.trsf == 1 ? T1() : c.trsf == 2 ? T2() : c.trsf == 3 ? TFAR() : T4();
  std::vector<int> rmIdx;
  for (auto& d : c.rm)
    rmIdx.push_back(faceAt(base, d));
  const char* vars[] = {"none", "geo", "loc", "subloc", "nest", "geon", "floc"};
  for (int var = 0; var < 7; var++)
  {
    if (gOnly && strcmp(gOnly, vars[var]))
      continue;
    TopoDS_Shape s;
    gp_Trsf      Tv = T;
    if (var == 0)
    {
      s  = base;
      Tv = gp_Trsf();
    }
    else if (var == 1)
      s = BRepBuilderAPI_Transform(base, T, true).Shape();
    else if (var == 2)
      s = base.Moved(TopLoc_Location(T));
    else if (var == 3)
      s = subLoc(base, TopLoc_Location(T));
    else if (var == 6)
    {
      // location on every FACE (shells/solid unlocated): faces from a sewing/STEP import
      TopLoc_Location L(T);
      BRep_Builder    b;
      TopoDS_Solid    so;
      b.MakeSolid(so);
      for (TopoDS_Iterator it(base); it.More(); it.Next())
      {
        TopoDS_Shell sh;
        b.MakeShell(sh);
        for (TopoDS_Iterator jt(it.Value()); jt.More(); jt.Next())
          b.Add(sh, jt.Value().Moved(L));
        sh.Closed(it.Value().Closed());
        // the iterator already composed the solid and shell orientations into each face: keep the new
        // shell and solid FORWARD (setting them again would invert a REVERSED shell twice)
        b.Add(so, sh);
      }
      s = so;
    }
    else if (var == 5)
    {
      // geometry twin with the SAME composed matrix as "nest" (TA*TB, rounded like TopLoc composes it):
      // separates rounding sensitivity of the algorithm from location handling
      gp_Trsf TB = T2();
      gp_Trsf TA = T * TB.Inverted();
      s          = BRepBuilderAPI_Transform(base, TA * TB, true).Shape();
    }
    else
    {
      // T = TA * TB : TB below the root (shells), TA on the root
      gp_Trsf TB = T2();
      gp_Trsf TA = T * TB.Inverted();
      s          = subLoc(base, TopLoc_Location(TB)).Moved(TopLoc_Location(TA));
    }
    TopTools_IndexedMapOfShape fm;
    TopExp::MapShapes(s, TopAbs_FACE, fm);
    NCollection_List<TopoDS_Shape> faces;
    for (int i : rmIdx)
      faces.Append(fm(i));
    bool         done = false;
    int          err  = -1;
    std::string  exc;
    TopoDS_Shape r;
    auto         t0 = std::chrono::steady_clock::now();
    try
    {
      if (c.rm.empty())
      {
        BRepOffsetAPI_MakeOffsetShape mk;
        mk.PerformByJoin(s, c.t, 1e-7, BRepOffset_Skin, false, false, c.join, false);
        done = mk.IsDone();
        err  = mk.MakeOffset().Error();
        if (done)
          r = mk.Shape();
      }
      else
      {
        BRepOffsetAPI_MakeThickSolid mk;
        mk.MakeThickSolidByJoin(s, faces, c.t, 1e-7, BRepOffset_Skin, false, false, c.join, false);
        done = mk.IsDone();
        err  = mk.MakeOffset().Error();
        if (done)
          r = mk.Shape();
      }
    }
    catch (Standard_Failure& f)
    {
      exc = f.GetMessageString() ? f.GetMessageString() : "SF";
      for (auto& ch : exc)
        if (ch == ' ')
          ch = '_';
      if (exc.empty())
        exc = "SF";
    }
    catch (...)
    {
      exc = "EXC";
    }
    double bt = ms(t0);
    if (!done || r.IsNull())
    {
      printf("LOC %s %s done=%d err=%d exc=%s ms=%.1f grade=ERR\n", c.name.c_str(), vars[var], done ? 1 : 0, err,
             exc.empty() ? "-" : exc.c_str(), bt);
      continue;
    }
    // map the result back to the base frame (location only - exact)
    TopoDS_Shape rb = r.Moved(TopLoc_Location(Tv.Inverted()));
    bool         valid = BRepCheck_Analyzer(rb).IsValid();
    int          bop   = 0;
    try
    {
      BRepAlgoAPI_Check ck(rb, false, true);
      bop = ck.IsValid() ? 0 : ck.Result().Extent();
    }
    catch (...)
    {
      bop = -1;
    }
    int ns = 0, nsh = 0, nf = 0;
    for (TopExp_Explorer e(rb, TopAbs_SOLID); e.More(); e.Next())
      ns++;
    for (TopExp_Explorer e(rb, TopAbs_SHELL); e.More(); e.Next())
      nsh++;
    TopTools_IndexedMapOfShape rf;
    TopExp::MapShapes(rb, TopAbs_FACE, rf);
    nf = rf.Extent();
    GProp_GProps gv, ga;
    BRepGProp::VolumeProperties(rb, gv);
    BRepGProp::SurfaceProperties(rb, ga);
    gp_Pnt cg = ga.CentreOfMass();
    Bnd_Box bx;
    BRepBndLib::AddOptimal(rb, bx, false, false);
    double x0, y0, z0, x1, y1, z1;
    bx.Get(x0, y0, z0, x1, y1, z1);
    const char* g = !valid ? "INV" : bop ? "BOP" : "OK";
    printf("LOC %s %s done=1 err=%d exc=- ms=%.1f grade=%s valid=%d bop=%d ns=%d nsh=%d nf=%d vol=%.9g area=%.9g "
           "c=%.9g,%.9g,%.9g bb=%.7g,%.7g,%.7g,%.7g,%.7g,%.7g\n",
           c.name.c_str(), vars[var], err, bt, g, valid ? 1 : 0, bop, ns, nsh, nf, gv.Mass(), ga.Mass(), cg.X(),
           cg.Y(), cg.Z(), x0, y0, z0, x1, y1, z1);
    fflush(stdout);
  }
}

int main(int argc, char** argv)
{
  auto cs = cases();
  if (argc >= 2 && !strcmp(argv[1], "list"))
  {
    for (auto& c : cs)
      printf("%s\n", c.name.c_str());
    return 0;
  }
  if (argc >= 3 && !strcmp(argv[1], "run"))
  {
    if (argc >= 4)
      gOnly = argv[3];
    for (auto& c : cs)
      if (c.name == argv[2])
      {
        runCase(c);
        return 0;
      }
    printf("LOC %s NO-SUCH-CASE\n", argv[2]);
    return 1;
  }
  printf("usage: loc034 list | run <case>\n");
  return 2;
}
