// checkcmp801.cpp -- defect 018 bench, ported to OCCT 8.0.1 (FreeCAD 26.3 weekly; types only, same dumps): BRepCheck_Analyzer exactly as FreeCAD 1.1.1 calls it (BRepCheck_Analyzer(shape):
// geometric controls on, serial - TopoShape.cpp:1426, FeaturePartBoolean.cpp:55, FCBRepAlgoAPI_BooleanOperation.cpp:54-60
// @0108fd4) and a canonical dump of EVERY status it records, so two TKTopAlgo.dll builds can be compared status by
// status. The OCCT DLLs come from PATH (run_check.py puts the variant's directory first); this exe's directory and
// the working directory must hold no DLL.
//
//   checkcmp check  <list.txt> <first> <count> <out.tsv> <dumpdir|-> <par 0|1>
//        shapes first..first+count-1 (0-based lines of list.txt). Before each shape "BEGIN\t<index>\t<file>" is
//        written and flushed; after it "<index>\t<file>\tOK\t<seconds>\t<valid>\t<nsub>\t<digest>\t<par>" or
//        "<index>\t<file>\tFAIL\t<reason>". A BEGIN without its result line is a crash (run_check.py resumes).
//   checkcmp phases <brep> <out.tsv>
//        whole shape: "<file>\tALL\t<seconds of BRepCheck_Analyzer(shape) + IsValid()>"; then per face with >= 2
//        wires: face index, wires, edges, vertices, statuses of IntersectWires / ClassifyWires / OrientationOfWires
//        on a fresh BRepCheck_Face, their seconds, the seconds of the sub-shape scans of BRepCheck_Wire / Edge /
//        Vertex::InContext (BRepCheck_Wire.cxx:205-209, BRepCheck_Edge.cxx:271-276, BRepCheck_Vertex.cxx:89-95),
//        and of BRepCheck_Analyzer(face) + IsValid().
//   checkcmp fillet <brep> <out.tsv>
//        the core of PartDesign::Fillet (FeatureFillet.cpp:117,126 @0108fd4): fillet R 0.5 of the first circular
//        edge of the highest face with the most wires, then BRepAlgo::IsValid(args, result, false, false).
//        "<file>\t<fillet s>\t<IsValid s>\t<valid>\t<done>"
//   checkcmp cut    <brep> <out.tsv>
//        the core of Part::Cut: BRepCheck_Analyzer of both arguments (FCBRepAlgoAPI_BooleanOperation.cpp:54-60),
//        BRepAlgoAPI_Cut by a 3 x 3 box at the min corner, BRepCheck_Analyzer of the result (FeaturePartBoolean.cpp:55).
//        "<file>\t<inputs s>\t<cut s>\t<result s>\t<valid>"
//   checkcmp gen    <outdir>
//        the synthetic corpus (gen() below); prints one line per file.
//   checkcmp step2brep <in.step> <out.brep>
//        STEP -> BREP once, with the DLLs on PATH (run it with the stock weekly bin only), so every variant reads
//        the same BREP (the STEP reader is not under test).
//   checkcmp probe  <out.tsv>
//        what the corpus of statuses cannot see - is this TKTopAlgo.dll built like the weekly's (LibPack, exceptions on)?
//        "PROBE\tMakeEdgeClosed\t<0|1>": BRepLib_MakeEdge sets E.Closed (upstream since 7.9.0, #297) - stock 1;
//        "PROBE\tFuseEdgesNullShape\t<type|none>": Standard_NullObject_Raise_if (BRepLib_FuseEdges.cxx:207) throws
//        only when OCCT's exceptions are compiled in (BUILD_RELEASE_DISABLE_EXCEPTIONS=OFF) - stock Standard_NullObject;
// A Job Object caps the process at 1 GB of committed memory (owner rule 23.09) (CHECKCMP_CAP_MB lowers it).
#include <BRep_Builder.hxx>
#include <STEPControl_Reader.hxx>
#include <BRep_Tool.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <BRepAlgo.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepBndLib.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakePolygon.hxx>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepCheck_Face.hxx>
#include <BRepCheck_Status.hxx>
#include <NCollection_IndexedMap.hxx>
#include <NCollection_List.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <BRepCheck_Result.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
#include <BRepLib.hxx>
#include <BRepLib_FuseEdges.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepTools.hxx>
#include <Bnd_Box.hxx>
#include <ElSLib.hxx>
#include <GProp_GProps.hxx>
#include <Geom_Plane.hxx>
#include <Precision.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Wire.hxx>
#include <gp.hxx>
#include <gp_Ax3.hxx>
#include <gp_Circ.hxx>
#include <gp_Pln.hxx>
#include <windows.h>
#include <psapi.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <random>
#include <string>
#include <vector>

typedef std::chrono::steady_clock Clock;
static double since (Clock::time_point t0) { return std::chrono::duration<double>(Clock::now() - t0).count(); }

static void capMemory (SIZE_T bytes)
{
  HANDLE job = CreateJobObjectW (nullptr, nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
  li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY;
  li.ProcessMemoryLimit = bytes;
  SetInformationJobObject (job, JobObjectExtendedLimitInformation, &li, sizeof (li));
  AssignProcessToJobObject (job, GetCurrentProcess());
}

static bool readBrep (const std::string& path, TopoDS_Shape& shape)
{
  BRep_Builder bb;
  try { return BRepTools::Read (shape, path.c_str(), bb) && !shape.IsNull(); }
  catch (const Standard_Failure&) { return false; }
}

// ------------------------------------------------------------------ status dump
static const char THE_TAG[] = "CZSHFWEV";   // TopAbs_COMPOUND .. TopAbs_VERTEX

struct Dump
{
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> maps[8];
  std::string text;
  long nsub = 0;
};

static std::string statuses (const NCollection_List<BRepCheck_Status>& theList)
{
  std::string s;
  for (NCollection_List<BRepCheck_Status>::Iterator it (theList); it.More(); it.Next())
  {
    s += ' ';
    s += std::to_string ((int) it.Value());
  }
  return s;
}

static std::string ref (const Dump& d, const TopoDS_Shape& s)
{
  const int t = (int) s.ShapeType();
  return std::string (1, THE_TAG[t]) + std::to_string (d.maps[t].FindIndex (s));   // 0: not a sub-shape
}

// Every sub-shape (per type, in TopExp::MapShapes order): its own status list in stored order, then one line per
// context shape (sorted: the context map iterates in hash order) with the status list on that context.
static void dumpAnalyzer (const TopoDS_Shape& shape, const BRepCheck_Analyzer& ana, Dump& d)
{
  for (int t = 0; t < 8; ++t)
    TopExp::MapShapes (shape, (TopAbs_ShapeEnum) t, d.maps[t]);
  std::string out;
  for (int t = 0; t < 8; ++t)
  {
    for (int k = 1; k <= d.maps[t].Extent(); ++k)
    {
      const TopoDS_Shape& sub = d.maps[t](k);
      ++d.nsub;
      const std::string me = ref (d, sub);
      Handle(BRepCheck_Result) R;
      try { R = ana.Result (sub); }
      catch (const Standard_Failure&) { out += me + " unknown\n"; continue; }
      if (R.IsNull()) { out += me + " null\n"; continue; }
      out += me + " :" + statuses (R->Status()) + "\n";
      std::vector<std::string> ctx;
      for (R->InitContextIterator(); R->MoreShapeInContext(); R->NextShapeInContext())
        ctx.push_back (me + " @" + ref (d, R->ContextualShape()) + " :" + statuses (R->StatusOnShape()) + "\n");
      std::sort (ctx.begin(), ctx.end());
      for (const std::string& c : ctx) out += c;
    }
  }
  d.text.swap (out);
}

static uint64_t fnv (const std::string& s)
{
  uint64_t h = 1469598103934665603ULL;
  for (unsigned char c : s) { h ^= c; h *= 1099511628211ULL; }
  return h;
}

static std::string baseName (const std::string& p)
{
  const size_t k = p.find_last_of ("/\\");
  return k == std::string::npos ? p : p.substr (k + 1);
}

static int check (const char* listPath, int first, int count, const char* outTsv, const char* dumpDir, bool par)
{
  std::vector<std::string> files;
  { std::ifstream in (listPath); std::string line;
    while (std::getline (in, line)) { if (!line.empty() && line.back() == '\r') line.pop_back(); if (!line.empty()) files.push_back (line); } }
  FILE* f = std::fopen (outTsv, "a");
  if (!f) return 2;
  for (int i = first; i < first + count && i < (int) files.size(); ++i)
  {
    std::fprintf (f, "BEGIN\t%d\t%s\n", i, files[i].c_str());
    std::fflush (f);
    TopoDS_Shape shape;
    if (!readBrep (files[i], shape)) { std::fprintf (f, "%d\t%s\tFAIL\tread\n", i, files[i].c_str()); std::fflush (f); continue; }
    try
    {
      const auto t0 = Clock::now();
      BRepCheck_Analyzer ana (shape, true, par ? true : false);
      const bool valid = ana.IsValid() == true;
      const double secs = since (t0);
      Dump d;
      dumpAnalyzer (shape, ana, d);
      if (std::string (dumpDir) != "-")
      {
        const std::string p = std::string (dumpDir) + "/" + std::to_string (i) + "_" + baseName (files[i]) + ".txt";
        FILE* df = std::fopen (p.c_str(), "wb");
        if (df) { std::fwrite (d.text.data(), 1, d.text.size(), df); std::fclose (df); }
      }
      std::fprintf (f, "%d\t%s\tOK\t%.6f\t%d\t%ld\t%016llx\t%d\n", i, files[i].c_str(), secs, valid ? 1 : 0, d.nsub,
                    (unsigned long long) fnv (d.text), par ? 1 : 0);
    }
    catch (const Standard_Failure& e)
    {
      std::fprintf (f, "%d\t%s\tFAIL\texception %s\n", i, files[i].c_str(), e.GetMessageString());
    }
    std::fflush (f);
  }
  std::fclose (f);
  return 0;
}

// ------------------------------------------------------------------ phases
static double scan (const TopoDS_Shape& S, TopAbs_ShapeEnum T, const NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher>& subs, int& found)
{
  const auto t0 = Clock::now();
  found = 0;
  for (int k = 1; k <= subs.Extent(); ++k)
  {
    TopExp_Explorer exp (S, T);
    for (; exp.More(); exp.Next())
      if (exp.Current().IsSame (subs (k)))
        break;
    found += exp.More() ? 1 : 0;
  }
  return since (t0);
}

static int phases (const char* path, const char* outTsv)
{
  TopoDS_Shape shape;
  if (!readBrep (path, shape)) return 3;
  FILE* f = std::fopen (outTsv, "a");
  if (!f) return 2;
  {
    const auto t0 = Clock::now();
    BRepCheck_Analyzer ana (shape);
    const bool valid = ana.IsValid() == true;
    std::fprintf (f, "%s\tALL\t%.6f\t%d\n", path, since (t0), valid ? 1 : 0);
    std::fflush (f);
  }
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> faces;
  TopExp::MapShapes (shape, TopAbs_FACE, faces);
  for (int k = 1; k <= faces.Extent(); ++k)
  {
    const TopoDS_Face& F = TopoDS::Face (faces (k));
    NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> W, E, V;
    TopExp::MapShapes (F, TopAbs_WIRE, W);
    if (W.Extent() < 2) continue;
    TopExp::MapShapes (F, TopAbs_EDGE, E);
    TopExp::MapShapes (F, TopAbs_VERTEX, V);
    int sti = -1, stc = -1, sto = -1;
    double ti = 0., tc = 0., to = 0.;
    try
    {
      Handle(BRepCheck_Face) R = new BRepCheck_Face (F);
      auto t0 = Clock::now(); sti = (int) R->IntersectWires();     ti = since (t0);
      t0 = Clock::now();      stc = (int) R->ClassifyWires();      tc = since (t0);
      t0 = Clock::now();      sto = (int) R->OrientationOfWires(); to = since (t0);
    }
    catch (const Standard_Failure&) { sti = stc = sto = -2; }
    int fw = 0, fe = 0, fv = 0;
    const double sw = scan (F, TopAbs_WIRE, W, fw), se = scan (F, TopAbs_EDGE, E, fe), sv = scan (F, TopAbs_VERTEX, V, fv);
    const auto t0 = Clock::now();
    BRepCheck_Analyzer anaF (F);
    const bool validF = anaF.IsValid() == true;
    const double taf = since (t0);
    std::fprintf (f, "%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%.6f\t%.6f\t%.6f\t%.6f\t%.6f\t%.6f\t%.6f\t%d\n", path, k,
                  W.Extent(), E.Extent(), V.Extent(), sti, stc, sto, ti, tc, to, sw, se, sv, taf, validF ? 1 : 0);
    std::fflush (f);
  }
  std::fclose (f);
  return 0;
}

// ------------------------------------------------------------------ fillet / cut (FreeCAD feature cores)
static TopoDS_Face faceWithMostWires (const TopoDS_Shape& shape)
{
  TopoDS_Face best; int bestW = -1; double bestZ = -1e300;
  for (TopExp_Explorer e (shape, TopAbs_FACE); e.More(); e.Next())
  {
    const TopoDS_Face& F = TopoDS::Face (e.Current());
    NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> W; TopExp::MapShapes (F, TopAbs_WIRE, W);
    Bnd_Box b; BRepBndLib::Add (F, b);
    double x0, y0, z0, x1, y1, z1; b.Get (x0, y0, z0, x1, y1, z1);
    const double z = 0.5 * (z0 + z1);
    if (W.Extent() > bestW || (W.Extent() == bestW && z > bestZ)) { best = F; bestW = W.Extent(); bestZ = z; }
  }
  return best;
}

static int fillet (const char* path, const char* outTsv)
{
  TopoDS_Shape shape;
  if (!readBrep (path, shape)) return 3;
  const TopoDS_Face F = faceWithMostWires (shape);
  TopoDS_Edge edge;
  for (TopExp_Explorer e (F, TopAbs_EDGE); e.More() && edge.IsNull(); e.Next())
    if (BRepAdaptor_Curve (TopoDS::Edge (e.Current())).GetType() == GeomAbs_Circle)
      edge = TopoDS::Edge (e.Current());
  if (edge.IsNull()) return 4;
  auto t0 = Clock::now();
  BRepFilletAPI_MakeFillet mk (shape);
  mk.Add (0.5, edge);
  mk.Build();
  const double tf = since (t0);
  const bool done = mk.IsDone() == true;
  double tv = 0.; bool valid = false;
  if (done)
  {
    NCollection_List<TopoDS_Shape> args; args.Append (shape);
    t0 = Clock::now();
    valid = BRepAlgo::IsValid (args, mk.Shape(), false, false) == true;
    tv = since (t0);
  }
  FILE* f = std::fopen (outTsv, "a");
  std::fprintf (f, "%s\t%.6f\t%.6f\t%d\t%d\n", path, tf, tv, valid ? 1 : 0, done ? 1 : 0);
  std::fclose (f);
  return 0;
}

static int cut (const char* path, const char* outTsv)
{
  TopoDS_Shape shape;
  if (!readBrep (path, shape)) return 3;
  Bnd_Box b; BRepBndLib::Add (shape, b);
  double x0, y0, z0, x1, y1, z1; b.Get (x0, y0, z0, x1, y1, z1);
  const TopoDS_Shape tool = BRepPrimAPI_MakeBox (gp_Pnt (x0 - 1., y0 - 1., z0 - 1.), 3., 3., (z1 - z0) + 2.).Shape();
  auto t0 = Clock::now();
  const bool v1 = BRepCheck_Analyzer (shape).IsValid() == true;
  const bool v2 = BRepCheck_Analyzer (tool).IsValid() == true;
  const double tin = since (t0);
  t0 = Clock::now();
  BRepAlgoAPI_Cut op;
  NCollection_List<TopoDS_Shape> a, t; a.Append (shape); t.Append (tool);
  op.SetArguments (a); op.SetTools (t); op.SetRunParallel (true); op.SetNonDestructive (true);
  op.Build();
  const double top = since (t0);
  double tout = 0.; bool v3 = false;
  if (op.IsDone())
  {
    t0 = Clock::now();
    v3 = BRepCheck_Analyzer (op.Shape()).IsValid() == true;
    tout = since (t0);
  }
  FILE* f = std::fopen (outTsv, "a");
  std::fprintf (f, "%s\t%.6f\t%.6f\t%.6f\t%d\n", path, tin, top, tout, (v1 && v2 && v3) ? 1 : 0);
  std::fclose (f);
  return 0;
}

// ------------------------------------------------------------------ synthetic corpus
static gp_Pnt at (const gp_Pln& pl, double u, double v) { return ElSLib::Value (u, v, pl); }

static TopoDS_Wire circleW (const gp_Pln& pl, double u, double v, double r, bool hole)
{
  gp_Circ c (gp_Ax2 (at (pl, u, v), pl.Axis().Direction(), pl.XAxis().Direction()), r);
  TopoDS_Wire w = BRepBuilderAPI_MakeWire (BRepBuilderAPI_MakeEdge (c).Edge()).Wire();
  if (hole) w.Reverse();
  return w;
}

static TopoDS_Wire rectW (const gp_Pln& pl, double u0, double v0, double u1, double v1, bool hole)
{
  TopoDS_Wire w = BRepBuilderAPI_MakePolygon (at (pl, u0, v0), at (pl, u1, v0), at (pl, u1, v1), at (pl, u0, v1),
                                              true).Wire();
  if (hole) w.Reverse();
  return w;
}

// A face on pl with the wires in the given order (no checks, no reordering) and stored pcurves.
static TopoDS_Face faceOf (const gp_Pln& pl, const std::vector<TopoDS_Wire>& wires)
{
  BRep_Builder B;
  TopoDS_Face F;
  B.MakeFace (F, new Geom_Plane (pl), Precision::Confusion());
  for (const TopoDS_Wire& w : wires) B.Add (F, w);
  for (TopExp_Explorer e (F, TopAbs_EDGE); e.More(); e.Next())
    BRepLib::BuildPCurveForEdgeOnPlane (TopoDS::Edge (e.Current()), F);
  return F;
}

static std::vector<TopoDS_Wire> gridWires (const gp_Pln& pl, int n, double size, double r, double du = 0., double dv = 0.)
{
  std::vector<TopoDS_Wire> w;
  w.push_back (rectW (pl, du, dv, du + size, dv + size, false));
  const double step = size / n;
  for (int i = 0; i < n; ++i)
    for (int j = 0; j < n; ++j)
      w.push_back (circleW (pl, du + step * (i + 0.5), dv + step * (j + 0.5), r, true));
  return w;
}

static void save (const std::string& dir, const std::string& name, const TopoDS_Shape& s)
{
  const std::string p = dir + "/" + name + ".brep";
  BRepTools::Write (s, p.c_str());
  std::printf ("%s\n", p.c_str());
  std::fflush (stdout);
}

static TopoDS_Shape bopPlate (int n)
{
  TopoDS_Shape box = BRepPrimAPI_MakeBox (200., 200., 10.).Shape();
  NCollection_List<TopoDS_Shape> args, tools;
  args.Append (box);
  const double step = 200. / n;
  for (int i = 0; i < n; ++i)
    for (int j = 0; j < n; ++j)
      tools.Append (BRepPrimAPI_MakeCylinder (gp_Ax2 (gp_Pnt (step * (i + 0.5), step * (j + 0.5), -10.), gp::DZ()), 1.5, 30.).Shape());
  BRepAlgoAPI_Cut op;
  op.SetArguments (args); op.SetTools (tools); op.SetRunParallel (true);
  op.Build();
  return op.Shape();
}

static TopoDS_Shape tube (int na, int nh)
{
  TopoDS_Shape cyl = BRepPrimAPI_MakeCylinder (gp_Ax2 (gp::Origin(), gp::DZ()), 20., 100.).Shape();
  NCollection_List<TopoDS_Shape> args, tools;
  args.Append (cyl);
  for (int a = 0; a < na; ++a)
    for (int h = 0; h < nh; ++h)
    {
      const double ang = 2. * M_PI * (a + 0.5) / na, z = 100. * (h + 0.5) / nh;
      tools.Append (BRepPrimAPI_MakeCylinder (gp_Ax2 (gp_Pnt (0., 0., z), gp_Dir (std::cos (ang), std::sin (ang), 0.)), 1.5, 30.).Shape());
    }
  BRepAlgoAPI_Cut op;
  op.SetArguments (args); op.SetTools (tools); op.SetRunParallel (true);
  op.Build();
  return op.Shape();
}

static int gen (const std::string& dir)
{
  const gp_Pln xy;                                                     // origin (0,0,0), normal +Z
  // valid plates: face + prism (fast), and BOP like FreeCAD's Part::Cut (bench fixture holes1024)
  for (int n : {4, 8, 16, 32, 64})
  {
    const TopoDS_Face F = faceOf (xy, gridWires (xy, n, 200., 1.5));
    save (dir, "face_grid_" + std::to_string (n * n), F);
    save (dir, "prism_plate_" + std::to_string (n * n), BRepPrimAPI_MakePrism (F, gp_Vec (0., 0., 10.)).Shape());
  }
  for (int n : {16, 32})
    save (dir, "bop_plate_" + std::to_string (n * n), bopPlate (n));
  // placement of the (u, v) origin: far away, and rotated axes
  save (dir, "face_offset_1024", faceOf (xy, gridWires (xy, 32, 200., 1.5, 5000., -3000.)));
  const gp_Pln rot (gp_Ax3 (gp_Pnt (7., -3., 2.), gp::DZ(), gp_Dir (1., 1., 0.)));
  save (dir, "face_rotated_1024", faceOf (rot, gridWires (rot, 32, 200., 1.5)));
  { // one row of 1024 holes
    std::vector<TopoDS_Wire> w;
    w.push_back (rectW (xy, 0., 0., 6400., 10., false));
    for (int i = 0; i < 1024; ++i) w.push_back (circleW (xy, 6.25 * (i + 0.5), 5., 1.5, true));
    save (dir, "face_row_1024", faceOf (xy, w));
  }
  { // jittered centres and radii, seeded
    std::mt19937 rng (18);
    std::uniform_real_distribution<double> jit (-1., 1.), rad (0.5, 1.4);
    std::vector<TopoDS_Wire> w;
    w.push_back (rectW (xy, 0., 0., 200., 200., false));
    for (int i = 0; i < 32; ++i)
      for (int j = 0; j < 32; ++j)
        w.push_back (circleW (xy, 6.25 * (i + 0.5) + jit (rng), 6.25 * (j + 0.5) + jit (rng), rad (rng), true));
    save (dir, "face_jitter_1024", faceOf (xy, w));
  }
  { // square holes
    std::vector<TopoDS_Wire> w;
    w.push_back (rectW (xy, 0., 0., 200., 200., false));
    for (int i = 0; i < 16; ++i)
      for (int j = 0; j < 16; ++j)
        w.push_back (rectW (xy, 12.5 * i + 3., 12.5 * j + 3., 12.5 * i + 9., 12.5 * j + 9., true));
    save (dir, "face_squares_256", faceOf (xy, w));
  }
  { // pairs of square holes sharing one corner vertex (the common-vertex branch of Intersect())
    std::vector<TopoDS_Wire> w;
    w.push_back (rectW (xy, 0., 0., 200., 200., false));
    for (int i = 0; i < 4; ++i)
    {
      const double u = 20. + 40. * i, v = 50.;
      const TopoDS_Vertex s = BRepBuilderAPI_MakeVertex (at (xy, u + 10., v + 10.));
      TopoDS_Wire a = BRepBuilderAPI_MakePolygon (BRepBuilderAPI_MakeVertex (at (xy, u, v)), BRepBuilderAPI_MakeVertex (at (xy, u + 10., v)),
                                                  s, BRepBuilderAPI_MakeVertex (at (xy, u, v + 10.)), true).Wire();
      TopoDS_Wire b = BRepBuilderAPI_MakePolygon (s, BRepBuilderAPI_MakeVertex (at (xy, u + 20., v + 10.)),
                                                  BRepBuilderAPI_MakeVertex (at (xy, u + 20., v + 20.)),
                                                  BRepBuilderAPI_MakeVertex (at (xy, u + 10., v + 20.)), true).Wire();
      a.Reverse(); b.Reverse();
      w.push_back (a); w.push_back (b);
    }
    save (dir, "face_sharedvertex_8", faceOf (xy, w));
  }
  // invalid faces: each should reach the check it is named after (Task 2 records what stock says)
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 4, 200., 1.5);
    w.push_back (circleW (xy, 25. + 3., 25., 1.5, true));             // tangent to the hole at (25, 25)
    save (dir, "bad_touch_16", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 4, 200., 1.5);
    w.push_back (circleW (xy, 25. + 2.25, 25., 1.5, true));           // overlaps the hole at (25, 25)
    save (dir, "bad_cross_16", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 32, 200., 1.5);
    w.push_back (circleW (xy, 6.25 * 31.5 - 2.25, 6.25 * 31.5, 1.5, true));   // overlaps the LAST hole
    save (dir, "bad_cross_last_1024", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 32, 200., 1.5);
    w.insert (w.begin() + 1, circleW (xy, 3.125 + 2.25, 3.125, 1.5, true));  // second wire overlaps the first hole
    save (dir, "bad_cross_first_1024", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 4, 200., 1.5);
    w.push_back (circleW (xy, 250., 100., 1.5, true));                // outside the outer wire
    save (dir, "bad_outside_16", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 4, 200., 1.5);
    w.push_back (circleW (xy, 100., 100., 5., true));                 // big hole ...
    w.push_back (circleW (xy, 100., 100., 1., true));                 // ... and a hole inside it
    save (dir, "bad_nested_16", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 4, 200., 1.5);
    w.push_back (circleW (xy, 100., 100., 1.5, false));               // a hole oriented like the outer wire
    save (dir, "bad_orient_16", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 32, 200., 1.5);
    w.back().Reverse();                                               // the last hole mis-oriented
    save (dir, "bad_orient_1024", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 4, 200., 1.5);
    w.push_back (w.back());                                           // the same wire twice
    save (dir, "bad_dup_16", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 4, 200., 1.5);
    const TopoDS_Vertex a = BRepBuilderAPI_MakeVertex (at (xy, 90., 110.)), b = BRepBuilderAPI_MakeVertex (at (xy, 110., 110.));
    w.push_back (BRepBuilderAPI_MakeWire (BRepBuilderAPI_MakeEdge (a, b).Edge(), BRepBuilderAPI_MakeEdge (b, a).Edge()).Wire());
    save (dir, "bad_badwire_16", faceOf (xy, w));                      // 2-segment loop: TabOrien -1 in FClass2d
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 4, 200., 1.5);
    w.erase (w.begin());                                              // holes only, no outer wire
    save (dir, "bad_holesonly_16", faceOf (xy, w));
  }
  {
    std::vector<TopoDS_Wire> w = gridWires (xy, 32, 200., 1.5);
    std::rotate (w.begin(), w.begin() + 1, w.end());                  // valid, but the outer wire comes last
    save (dir, "face_outerlast_1024", faceOf (xy, w));
  }
  // periodic surface: lateral face of a cylinder with radial holes
  save (dir, "tube_holes_64", tube (8, 8));
  save (dir, "tube_holes_256", tube (16, 16));
  return 0;
}

// ------------------------------------------------------------------ probe (the same code as e018-checks/probe018.cpp)
static int probe (const char* outTsv)
{
  FILE* f = std::fopen (outTsv, "a");
  if (!f) return 2;
  {
    const TopoDS_Edge e = BRepBuilderAPI_MakeEdge (gp_Circ (gp::XOY(), 5.)).Edge();
    std::fprintf (f, "PROBE\tMakeEdgeClosed\t%d\n", e.Closed() ? 1 : 0);
    std::fflush (f);
  }
  {
    std::string what = "none";
    try { BRepLib_FuseEdges fe ((TopoDS_Shape())); }
    catch (const Standard_Failure& e) { what = e.ExceptionType(); }
    std::fprintf (f, "PROBE\tFuseEdgesNullShape\t%s\n", what.c_str());
    std::fflush (f);
  }
  std::fclose (f);
  return 0;
}

int main (int argc, char** argv)
{
  if (argc < 3) { std::fprintf (stderr, "usage: see the header of checkcmp.cpp\n"); return 2; }
  // owner RAM budget 23.09: at most 1 GB per test process; CHECKCMP_CAP_MB can only lower it
  SIZE_T aCapMb = 1024;
  if (const char* anEnv = std::getenv ("CHECKCMP_CAP_MB"))
  {
    const long aV = std::atol (anEnv);
    if (aV > 0 && (SIZE_T) aV < aCapMb) aCapMb = (SIZE_T) aV;
  }
  capMemory (aCapMb << 20);
  const std::string mode = argv[1];
  if (mode == "check" && argc >= 8) return check (argv[2], std::atoi (argv[3]), std::atoi (argv[4]), argv[5], argv[6], std::atoi (argv[7]) != 0);
  if (mode == "phases" && argc >= 4) return phases (argv[2], argv[3]);
  if (mode == "fillet" && argc >= 4) return fillet (argv[2], argv[3]);
  if (mode == "cut" && argc >= 4) return cut (argv[2], argv[3]);
  if (mode == "gen") return gen (argv[2]);
  if (mode == "probe") return probe (argv[2]);
  if (mode == "step2brep" && argc >= 4)
  {
    STEPControl_Reader aReader;
    if (aReader.ReadFile (argv[2]) != IFSelect_RetDone) return 3;
    aReader.TransferRoots();
    const TopoDS_Shape aShape = aReader.OneShape();
    if (aShape.IsNull() || !BRepTools::Write (aShape, argv[3])) return 4;
    std::puts (argv[3]);
    return 0;
  }
  std::fprintf (stderr, "bad arguments\n");
  return 2;
}
