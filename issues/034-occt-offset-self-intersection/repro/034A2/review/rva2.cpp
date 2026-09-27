// rva2.cpp - review A2 (issue 034): false-positive probe on VALID inputs outside the A2 class.
//   rva2 list            : prints case names
//   rva2 run <case>      : builds the input in code, runs the offset, prints one RV line
// Verdict fields: done err valid(BRepCheck) bop(self-interference of the result, only if valid) shells vol ms
#include <BRepAlgoAPI_Check.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_NurbsConvert.hxx>
#include <BRepBuilderAPI_Sewing.hxx>
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
#include <BRepPrimAPI_MakeHalfSpace.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <gp_Pln.hxx>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <functional>
#include <string>
#include <vector>

static TopoDS_Face faceAt(const TopoDS_Shape& s, const gp_Dir& n, double side) // planar face with centroid extreme along n
{
  TopoDS_Face best;
  double      bz = -1e300;
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next())
  {
    GProp_GProps g;
    BRepGProp::SurfaceProperties(e.Current(), g);
    double z = side * gp_Vec(g.CentreOfMass().XYZ()).Dot(gp_Vec(n));
    if (z > bz + 1e-9) { bz = z; best = TopoDS::Face(e.Current()); }
  }
  return best;
}
static TopoDS_Shape comp(std::vector<TopoDS_Shape> v)
{
  TopoDS_Compound c;
  BRep_Builder    b;
  b.MakeCompound(c);
  for (auto& s : v) b.Add(c, s);
  return c;
}
static TopoDS_Shape box(double x, double y, double z, double dx, double dy, double dz)
{
  return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape();
}
static TopoDS_Shape firstSolid(const TopoDS_Shape& s)
{
  TopExp_Explorer e(s, TopAbs_SOLID);
  return e.More() ? e.Current() : s;
}
static TopoDS_Shape nurbs(const TopoDS_Shape& s) { return BRepBuilderAPI_NurbsConvert(s, true).Shape(); }

struct Case
{
  std::string                                                   name;
  std::function<void(TopoDS_Shape&, NCollection_List<TopoDS_Shape>&)> build;
  const char*                                                   op; // offset | thick | thicken
  double                                                        t;
  GeomAbs_JoinType                                              join;
};

static std::vector<Case> cases()
{
  std::vector<Case> v;
  auto add = [&](std::string n, std::function<void(TopoDS_Shape&, NCollection_List<TopoDS_Shape>&)> b, const char* op,
                 std::vector<double> ts) {
    for (double t : ts)
      for (int j = 0; j < 2; j++)
      {
        char nm[160];
        snprintf(nm, sizeof nm, "%s_%s%g_%s", n.c_str(), op, t, j ? "int" : "arc");
        v.push_back({nm, b, op, t, j ? GeomAbs_Intersection : GeomAbs_Arc});
      }
  };
  // 1 solid with an inner void (2 closed shells)
  auto voidbox = [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) {
    s = firstSolid(BRepAlgoAPI_Cut(box(0, 0, 0, 40, 40, 40), box(10, 10, 10, 20, 20, 20)).Shape());
  };
  add("voidbox", voidbox, "offset", {1, -1});
  add("voidbox_top", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { voidbox(s, f); f.Append(faceAt(s, gp::DZ(), 1)); }, "thick", {-2, 2});
  // 2 compound of two separated boxes
  auto twob = [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { s = comp({box(0, 0, 0, 20, 20, 20), box(50, 0, 0, 20, 20, 20)}); };
  add("twoboxes", twob, "offset", {1, -1});
  add("twoboxes_top1", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { twob(s, f); f.Append(faceAt(s, gp::DX(), -1)); }, "thick", {-2, 2});
  add("twoboxes_top2", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) {
    twob(s, f);
    f.Append(faceAt(s, gp::DX(), -1)); f.Append(faceAt(s, gp::DX(), 1)); }, "thick", {-2});
  // 3 open shell (box without top) and a single face
  auto openshell = [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) {
    TopoDS_Shape b = box(0, 0, 0, 30, 20, 10);
    TopoDS_Face  top = faceAt(b, gp::DZ(), 1);
    BRepBuilderAPI_Sewing sw;
    for (TopExp_Explorer e(b, TopAbs_FACE); e.More(); e.Next()) if (!e.Current().IsSame(top)) sw.Add(e.Current());
    sw.Perform();
    s = sw.SewedShape();
  };
  add("openshell", openshell, "offset", {1, -1});
  add("openshell", openshell, "thicken", {2, -2});
  add("planeface", [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>&) { s = BRepBuilderAPI_MakeFace(gp_Pln(), 0, 30, 0, 20).Shape(); }, "thicken", {2});
  add("cylface", [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>&) { s = BRepBuilderAPI_MakeFace(gp_Cylinder(gp_Ax3(), 10), 0, 3, 0, 20).Shape(); }, "thicken", {1});
  // 4 seams / degenerated edges
  add("sphere", [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>&) { s = BRepPrimAPI_MakeSphere(15).Shape(); }, "offset", {2, -2});
  auto hemi = [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) {
    s = firstSolid(BRepAlgoAPI_Cut(BRepPrimAPI_MakeSphere(15).Shape(), box(-20, -20, 0, 40, 40, 40)).Shape());
  };
  add("hemisphere_flat", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { hemi(s, f); f.Append(faceAt(s, gp::DZ(), 1)); }, "thick", {-1, 1});
  auto cyl = [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>&) { s = BRepPrimAPI_MakeCylinder(10, 30).Shape(); };
  add("cylinder", cyl, "offset", {1, -1});
  add("cylinder_top", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { cyl(s, f); f.Append(faceAt(s, gp::DZ(), 1)); }, "thick", {-1, 1});
  add("tube", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { cyl(s, f); f.Append(faceAt(s, gp::DZ(), 1)); f.Append(faceAt(s, gp::DZ(), -1)); }, "thick", {-1, 1});
  add("cone_base", [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { s = BRepPrimAPI_MakeCone(15, 0, 30).Shape(); f.Append(faceAt(s, gp::DZ(), -1)); }, "thick", {-1});
  add("torus", [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>&) { s = BRepPrimAPI_MakeTorus(20, 5).Shape(); }, "offset", {1, -1});
  // 5 genus 1: box with a through hole, top removed; square tube (top+bottom removed)
  add("holebox_top", [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) {
    s = firstSolid(BRepAlgoAPI_Cut(box(0, 0, 0, 40, 40, 20), BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(20, 20, -5), gp::DZ()), 6, 30).Shape()).Shape());
    f.Append(faceAt(s, gp::DZ(), 1)); }, "thick", {-1, 1});
  add("sqtube", [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) {
    s = box(0, 0, 0, 30, 30, 30); f.Append(faceAt(s, gp::DZ(), 1)); f.Append(faceAt(s, gp::DZ(), -1)); }, "thick", {-2, 2});
  // 6 fillets NOT tangent to the removed face (vertical edges only), analytic + NURBS
  auto vfil = [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f, bool nb) {
    TopoDS_Shape b = box(0, 0, 0, 60, 40, 30);
    BRepFilletAPI_MakeFillet mf(b);
    for (TopExp_Explorer e(b, TopAbs_EDGE); e.More(); e.Next())
    {
      TopoDS_Vertex v1, v2;
      TopExp::Vertices(TopoDS::Edge(e.Current()), v1, v2);
      gp_Pnt p1 = BRep_Tool::Pnt(v1), p2 = BRep_Tool::Pnt(v2);
      if (std::abs(p1.X() - p2.X()) < 1e-9 && std::abs(p1.Y() - p2.Y()) < 1e-9) mf.Add(5, TopoDS::Edge(e.Current()));
    }
    s = mf.Shape();
    if (nb) s = nurbs(s);
    f.Append(faceAt(s, gp::DZ(), 1));
  };
  add("vfilbox_top", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { vfil(s, f, false); }, "thick", {-2, 2});
  add("vfilboxN_top", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { vfil(s, f, true); }, "thick", {-2, 2});
  add("vfilbox", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { vfil(s, f, false); f.Clear(); }, "offset", {2, -2});
  add("vfilboxN", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { vfil(s, f, true); f.Clear(); }, "offset", {2, -2});
  // 7 "neck" thinner than 2t: correct shell has a closed void from one open piece
  add("dumbbell_plate", [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) {
    TopoDS_Shape u = BRepAlgoAPI_Fuse(BRepAlgoAPI_Fuse(box(0, 0, 0, 20, 20, 20), box(40, 0, 0, 20, 20, 20)).Shape(), box(19, 5, 9.6, 22, 10, 0.8)).Shape();
    s = firstSolid(u); f.Append(faceAt(s, gp::DX(), -1)); }, "thick", {-1});
  add("dumbbell_rod", [](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) {
    TopoDS_Shape u = BRepAlgoAPI_Fuse(BRepAlgoAPI_Fuse(box(0, 0, 0, 20, 20, 20), box(40, 0, 0, 20, 20, 20)).Shape(),
                                      BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(19, 10, 10), gp::DX()), 0.8, 22).Shape()).Shape();
    s = firstSolid(u); f.Append(faceAt(s, gp::DX(), -1)); }, "thick", {-1});
  // 7b family: two boxes joined by a web of thickness h (< 2|t| -> the far box becomes a closed void), placements
  for (double h : {0.4, 1.0, 1.6, 1.9, 2.5})
    for (int rot = 0; rot < 3; rot++)
    {
      char nm[64];
      snprintf(nm, sizeof nm, "neck_h%g_%s", h, rot == 0 ? "a" : rot == 1 ? "rot" : "nurbs");
      add(nm, [h, rot](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) {
        TopoDS_Shape u = BRepAlgoAPI_Fuse(BRepAlgoAPI_Fuse(box(0, 0, 0, 20, 20, 20), box(40, 0, 0, 30, 25, 20)).Shape(),
                                          box(19, 4, 10 - h / 2, 22, 12, h)).Shape();
        s = firstSolid(u);
        if (rot == 1)
        {
          gp_Trsf r, t;
          r.SetRotation(gp_Ax1(gp_Pnt(7, -4, 2), gp_Dir(1, 2, 3)), 30. * M_PI / 180.);
          t.SetTranslation(gp_Vec(13.5, -250.25, 41.));
          s = BRepBuilderAPI_Transform(s, t * r, true).Shape();
          // removed face: the one whose normal is the image of -X
          gp_Dir nx = gp_Dir(-1, 0, 0).Transformed(t * r);
          f.Append(faceAt(s, nx, 1));
          return;
        }
        if (rot == 2) s = nurbs(s);
        f.Append(faceAt(s, gp::DX(), -1)); }, "thick", {-1});
    }
  // 8 thick of a solid with void, void kept (closed piece -> 2 shells)
  add("voidbox_side", [&](TopoDS_Shape& s, NCollection_List<TopoDS_Shape>& f) { voidbox(s, f); f.Append(faceAt(s, gp::DX(), 1)); }, "thick", {-1});
  return v;
}

int main(int argc, char** argv)
{
  auto all = cases();
  if (argc >= 2 && !strcmp(argv[1], "list"))
  {
    for (auto& c : all) printf("%s\n", c.name.c_str());
    return 0;
  }
  if (argc < 3) return 2;
  for (auto& c : all)
  {
    if (c.name != argv[2]) continue;
    TopoDS_Shape                   s, r;
    NCollection_List<TopoDS_Shape> f;
    int                            done = 0, err = -1;
    std::string                    exc = "-";
    double                         ms  = 0;
    try
    {
      c.build(s, f);
      bool vin = BRepCheck_Analyzer(s).IsValid();
      auto t0  = std::chrono::steady_clock::now();
      if (!strcmp(c.op, "offset"))
      {
        BRepOffsetAPI_MakeOffsetShape m;
        m.PerformByJoin(s, c.t, 1e-7, BRepOffset_Skin, false, false, c.join);
        done = m.IsDone(); err = (int)m.MakeOffset().Error(); if (done) r = m.Shape();
      }
      else if (!strcmp(c.op, "thick"))
      {
        BRepOffsetAPI_MakeThickSolid m;
        m.MakeThickSolidByJoin(s, f, c.t, 1e-7, BRepOffset_Skin, false, false, c.join);
        done = m.IsDone(); err = (int)m.MakeOffset().Error(); if (done) r = m.Shape();
      }
      else
      {
        BRepOffset_MakeOffset m;
        m.Initialize(s, c.t, 1e-7, BRepOffset_Skin, false, false, c.join, true);
        m.MakeOffsetShape();
        done = m.IsDone(); err = (int)m.Error(); if (done) r = m.Shape();
      }
      ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
      int    valid = -1, nsh = 0, nso = 0;
      double vol   = 0;
      std::string bop = "-";
      if (done && !r.IsNull())
      {
        valid = BRepCheck_Analyzer(r).IsValid();
        for (TopExp_Explorer e(r, TopAbs_SHELL); e.More(); e.Next()) nsh++;
        for (TopExp_Explorer e(r, TopAbs_SOLID); e.More(); e.Next()) nso++;
        GProp_GProps g;
        BRepGProp::VolumeProperties(r, g);
        vol = g.Mass();
        if (valid)
        {
          BRepAlgoAPI_Check ck(r, true, true);
          bop = ck.IsValid() ? "clean" : "faults";
        }
      }
      printf("RV %s inValid=%d done=%d err=%d valid=%d bop=%s solids=%d shells=%d vol=%.4f ms=%.0f exc=%s\n", c.name.c_str(), (int)vin, done, err,
             valid, bop.c_str(), nso, nsh, vol, ms, exc.c_str());
    }
    catch (Standard_Failure const& e)
    {
      printf("RV %s EXC %s\n", c.name.c_str(), e.GetMessageString());
    }
    return 0;
  }
  printf("RV %s NOCASE\n", argv[2]);
  return 1;
}
