# builds e5.cpp from pieces of e3.cpp (generator map, inversion test) and e4.cpp (elements) + wind034b.hxx
import re
e3 = open('C:/dev/occt8-mig/offset-034b/tools/e3.cpp').read().split('\n')
e4 = open('C:/dev/occt8-mig/offset-034b/tools/e4.cpp').read().split('\n')

def block(lines, start_pat):
    # from the line matching start_pat to the end of its top-level brace block
    for i, l in enumerate(lines):
        if l.startswith(start_pat):
            depth = 0
            seen = False
            out = []
            for j in range(i, len(lines)):
                out.append(lines[j])
                depth += lines[j].count('{') - lines[j].count('}')
                if '{' in lines[j]:
                    seen = True
                if seen and depth == 0:
                    return '\n'.join(out)
    raise Exception(start_pat)

head = '''// e5.cpp - issue 034 stage B experiment E5 (harness, NOT kernel code): E2/E4 with the winding classification of
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
'''
parts = [head]
parts.append(block(e4, 'class GridSplit034b'))
parts.append(block(e4, 'static void splitFace('))
parts.append(block(e4, 'static bool factor('))
parts.append(block(e4, 'static bool faceFolds('))
parts.append(block(e4, 'static gp_Dir outNormal('))
parts.append(block(e4, 'static int edgeKind('))
parts.append('struct Element { std::string kind; TopoDS_Shape solid; };')
parts.append(block(e4, 'static TopoDS_Shape orientedSolid('))
parts.append(block(e4, 'static TopoDS_Shape slab('))
parts.append(block(e4, 'static TopoDS_Shape tube('))
parts.append(block(e4, 'static int largestPlane('))
parts.append('''struct RawGen034b
{
  int          type = 0; // 0 none, 1 face, 2 edge, 3 vertex
  TopoDS_Shape gen;
};
static double g_t = 0; // signed offset of the run''')
parts.append(block(e3, 'static bool invertedAt('))
parts.append(block(e3, 'static double invertedShare('))
parts.append(block(e3, 'static void collectGens('))
# runOffset with gens (e3 version) - its signature spans 3 lines
parts.append(block(e3, 'static TopoDS_Shape runOffset('))
parts.append(block(e4, 'static void report('))
body = r'''
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
'''
parts.append(body)
src = '\n\n'.join(parts)
# report() of e4 has no done/err args - the stock call uses the e4 signature
open('C:/dev/occt8-mig/offset-034b/tools/e5.cpp', 'w').write(src)
print('ok', len(src))
