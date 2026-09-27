// x3.cpp - A2 round 2: new members of the pinch-off / cavity class (a thick solid whose hollow splits
// into components; a component no opening reaches is a closed cavity = extra shell of offset faces).
//   x3 list | x3 run <case>   -> one RV line (as review/rva2.cpp)
#include <BRepAlgoAPI_Check.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_NurbsConvert.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRep_Tool.hxx>
#include <BRep_Builder.hxx>
#include <TopoDS_Compound.hxx>
#include <GProp_GProps.hxx>
#include <ShapeUpgrade_UnifySameDomain.hxx>
#include <Standard_Failure.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <functional>
#include <string>
#include <vector>

static gp_Trsf placeTrsf()
{
  gp_Trsf r, t;
  r.SetRotation(gp_Ax1(gp_Pnt(7, -4, 2), gp_Dir(1, 2, 3)), 30. * M_PI / 180.);
  t.SetTranslation(gp_Vec(13.5, -250.25, 41.));
  return t * r;
}
static TopoDS_Face faceAt(const TopoDS_Shape& s, const gp_Dir& n)
{
  TopoDS_Face best; double bz = -1e300;
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next())
  {
    GProp_GProps g; BRepGProp::SurfaceProperties(e.Current(), g);
    double z = gp_Vec(g.CentreOfMass().XYZ()).Dot(gp_Vec(n));
    if (z > bz + 1e-9) { bz = z; best = TopoDS::Face(e.Current()); }
  }
  return best;
}
static TopoDS_Shape box(double x, double y, double z, double dx, double dy, double dz)
{
  return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape();
}
static TopoDS_Shape fuse(const TopoDS_Shape& a, const TopoDS_Shape& b) { return BRepAlgoAPI_Fuse(a, b).Shape(); }
static TopoDS_Shape cut(const TopoDS_Shape& a, const TopoDS_Shape& b) { return BRepAlgoAPI_Cut(a, b).Shape(); }
static TopoDS_Shape solid1(const TopoDS_Shape& s) { TopExp_Explorer e(s, TopAbs_SOLID); return e.More() ? e.Current() : s; }
static TopoDS_Shape unify(const TopoDS_Shape& s)
{
  ShapeUpgrade_UnifySameDomain u(s, true, true, false); u.Build(); return u.Shape();
}

struct Case { std::string name; std::function<TopoDS_Shape()> build; gp_Dir rm; double t; GeomAbs_JoinType join; };

static std::vector<Case> cases()
{
  std::vector<Case> v;
  // variant: 0 analytic, 1 rotated+moved, 2 NURBS; the removed face is the one extreme along rm (rotated with the shape)
  auto add = [&](const std::string& n, std::function<TopoDS_Shape()> b, gp_Dir rm, std::vector<double> ts) {
    for (int var = 0; var < 3; var++)
      for (double t : ts)
        for (int j = 0; j < 2; j++)
        {
          char nm[200];
          snprintf(nm, sizeof nm, "%s_%s_t%g_%s", n.c_str(), var == 0 ? "a" : var == 1 ? "rot" : "nurbs", t, j ? "int" : "arc");
          gp_Dir r = rm;
          if (var == 1) r.Transform(placeTrsf());
          auto bb = [b, var]() {
            TopoDS_Shape s = solid1(b());
            if (var == 1) s = BRepBuilderAPI_Transform(s, placeTrsf(), true).Shape();
            if (var == 2) s = BRepBuilderAPI_NurbsConvert(s, true).Shape();
            return s;
          };
          v.push_back({nm, bb, r, t, j ? GeomAbs_Intersection : GeomAbs_Arc});
        }
  };
  // A: 2.5D dumbbell refined (coplanar faces merged): the bottom/top faces of the kept piece touch the opening AND
  //    bound the pinched-off far chamber (the offset of one rim face is split between the hollow and the cavity)
  for (double h : {0.6, 1.5, 2.6})
  {
    char n[64]; snprintf(n, sizeof n, "flatbell_h%g", h);
    add(n, [h]() { return unify(fuse(fuse(box(0, 0, 0, 20, 20, 20), box(40, -2.5, 0, 30, 25, 20)), box(19, 10 - h / 2, 0, 22, h, 20))); },
        gp_Dir(-1, 0, 0), {-1});
  }
  // B: chain of three chambers, two necks -> two cavities
  add("chain3_h1", []() {
    TopoDS_Shape s = fuse(box(0, 0, 0, 20, 20, 20), box(40, 0, 0, 20, 20, 20));
    s = fuse(s, box(80, 0, 0, 20, 20, 20));
    s = fuse(s, box(19, 4, 9.5, 22, 12, 1));
    return fuse(s, box(59, 4, 9.5, 22, 12, 1)); }, gp_Dir(-1, 0, 0), {-1});
  // C: two spheres joined by a rod of radius 0.8 (< |t|); sphere 1 cut flat at x = -8 (the opening)
  add("spherebell_r0.8", []() {
    TopoDS_Shape s1 = cut(BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), 10).Shape(), box(-20, -20, -20, 12, 40, 40));
    TopoDS_Shape s = fuse(s1, BRepPrimAPI_MakeSphere(gp_Pnt(30, 0, 0), 10).Shape());
    return fuse(s, BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(8, 0, 0), gp::DX()), 0.8, 14).Shape()); }, gp_Dir(-1, 0, 0), {-1});
  // D: two vertical cylinders joined by a thin web, top of cylinder 1 removed
  add("cylbell_h1", []() {
    TopoDS_Shape s = fuse(BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp::DZ()), 10, 20).Shape(),
                          BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(35, 0, 0), gp::DZ()), 12, 20).Shape());
    return fuse(s, box(8, -0.5, 2, 20, 1, 16)); }, gp_Dir(-1, 0, 0), {-1});
  // E: outward: box with an inner chamber reached from outside by a slot of width w; offset +1 seals the slot
  //    (w < 2t) and the chamber core becomes a cavity; bottom removed; w = 3 is the no-seal control
  for (double w : {1.0, 3.0})
  {
    char n[64]; snprintf(n, sizeof n, "slotbox_w%g", w);
    add(n, [w]() {
      TopoDS_Shape s = cut(box(0, 0, 0, 40, 40, 40), box(10, 10, 10, 20, 20, 20));
      return cut(s, box(29, 20 - w / 2, 14, 12, w, 12)); }, gp_Dir(0, 0, -1), {1});
  }
  // F (cost only, not a class member): plate 10*n x 10*n x 6 with n*n blind holes r2 depth 4 from the bottom, top removed
  for (int n : {10, 20})
  {
    char nm[64]; snprintf(nm, sizeof nm, "holeplate_n%d_t-1_arc", n);
    v.push_back({nm, [n]() {
      TopoDS_Shape s = box(0, 0, 0, 10. * n, 10. * n, 6);
      TopoDS_Compound c; BRep_Builder b; b.MakeCompound(c);
      for (int i = 0; i < n; i++) for (int j = 0; j < n; j++)
        b.Add(c, BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(5 + 10. * i, 5 + 10. * j, -1), gp::DZ()), 2, 5).Shape());
      return solid1(cut(s, c)); }, gp_Dir(0, 0, 1), -1, GeomAbs_Arc});
  }
  return v;
}

int main(int argc, char** argv)
{
  auto all = cases();
  if (argc >= 2 && !strcmp(argv[1], "list")) { for (auto& c : all) printf("%s\n", c.name.c_str()); return 0; }
  if (argc < 3) return 2;
  for (auto& c : all)
  {
    if (c.name != argv[2]) continue;
    try
    {
      TopoDS_Shape s = c.build();
      bool vin = BRepCheck_Analyzer(s).IsValid();
      NCollection_List<TopoDS_Shape> f; f.Append(faceAt(s, c.rm));
      auto t0 = std::chrono::steady_clock::now();
      BRepOffsetAPI_MakeThickSolid m;
      m.MakeThickSolidByJoin(s, f, c.t, 1e-7, BRepOffset_Skin, false, false, c.join);
      int done = m.IsDone(), err = (int)m.MakeOffset().Error();
      double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
      TopoDS_Shape r; if (done) r = m.Shape();
      int valid = -1, nsh = 0, nso = 0; double vol = 0; std::string bop = "-";
      if (done && !r.IsNull())
      {
        valid = BRepCheck_Analyzer(r).IsValid();
        for (TopExp_Explorer e(r, TopAbs_SHELL); e.More(); e.Next()) nsh++;
        for (TopExp_Explorer e(r, TopAbs_SOLID); e.More(); e.Next()) nso++;
        GProp_GProps g; BRepGProp::VolumeProperties(r, g); vol = g.Mass();
        if (valid) { BRepAlgoAPI_Check ck(r, true, true); bop = ck.IsValid() ? "clean" : "faults"; }
      }
      printf("RV %s inValid=%d done=%d err=%d valid=%d bop=%s solids=%d shells=%d vol=%.4f ms=%.0f\n", c.name.c_str(), (int)vin,
             done, err, valid, bop.c_str(), nso, nsh, vol, ms);
    }
    catch (Standard_Failure const& e) { printf("RV %s EXC %s\n", c.name.c_str(), e.GetMessageString()); }
    return 0;
  }
  printf("RV %s NOCASE\n", argv[2]);
  return 1;
}
