// x2.cpp - A2 round 2 experiment: which faces make up each shell of a thick solid result.
//   x2 brep <file> <t> <arc|int> <top|toprot>
//   x2 neck <h> <a|rot|nurbs> <arc|int>      (review family: two boxes + web of thickness h)
// Per shell: faces by origin (ORIG remaining input face, CLOSE image of a removed face, OFF image of a
// remaining face, GEN image of an edge/vertex, UNK), closed flag, signed volume.
#include <BRepAlgoAPI_Check.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_NurbsConvert.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>

static gp_Trsf placeTrsf()
{
  gp_Trsf r, t;
  r.SetRotation(gp_Ax1(gp_Pnt(7, -4, 2), gp_Dir(1, 2, 3)), 30. * M_PI / 180.);
  t.SetTranslation(gp_Vec(13.5, -250.25, 41.));
  return t * r;
}
static int extremeFace(const TopoDS_Shape& s, const gp_Dir& n)
{
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  int best = 0; double bz = -1e300;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    GProp_GProps g; BRepGProp::SurfaceProperties(fm(k), g);
    double z = gp_Vec(g.CentreOfMass().XYZ()).Dot(gp_Vec(n));
    if (z > bz + 1e-9) { bz = z; best = k; }
  }
  return best;
}
static TopoDS_Shape box(double x, double y, double z, double dx, double dy, double dz)
{
  return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape();
}
int main(int argc, char** argv)
{
  if (argc < 5) return 2;
  TopoDS_Shape s; gp_Dir rmDir(0, 0, 1); double t = 0; GeomAbs_JoinType join = GeomAbs_Arc;
  if (!strcmp(argv[1], "brep"))
  {
    BRep_Builder bb; BRepTools::Read(s, argv[2], bb);
    TopExp_Explorer ex(s, TopAbs_SOLID); if (ex.More()) s = ex.Current();
    t = atof(argv[3]); join = !strcmp(argv[4], "int") ? GeomAbs_Intersection : GeomAbs_Arc;
    if (!strcmp(argv[5], "toprot")) rmDir.Transform(placeTrsf());
  }
  else
  {
    double h = atof(argv[2]);
    TopoDS_Shape u = BRepAlgoAPI_Fuse(BRepAlgoAPI_Fuse(box(0, 0, 0, 20, 20, 20), box(40, 0, 0, 30, 25, 20)).Shape(),
                                      box(19, 4, 10 - h / 2, 22, 12, h)).Shape();
    TopExp_Explorer ex(u, TopAbs_SOLID); s = ex.Current();
    rmDir = gp_Dir(-1, 0, 0);
    if (!strcmp(argv[3], "rot")) { s = BRepBuilderAPI_Transform(s, placeTrsf(), true).Shape(); rmDir.Transform(placeTrsf()); }
    if (!strcmp(argv[3], "nurbs")) s = BRepBuilderAPI_NurbsConvert(s, true).Shape();
    t = -1; join = !strcmp(argv[4], "int") ? GeomAbs_Intersection : GeomAbs_Arc;
  }
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
  const int rk = extremeFace(s, rmDir);
  NCollection_List<TopoDS_Shape> cl; cl.Append(fm(rk));
  BRepOffsetAPI_MakeThickSolid mk;
  mk.MakeThickSolidByJoin(s, cl, t, 1e-7, BRepOffset_Skin, false, false, join);
  if (!mk.IsDone()) { printf("X2 done=0 err=%d\n", (int)mk.MakeOffset().Error()); return 0; }
  const TopoDS_Shape r = mk.Shape();
  std::map<const void*, std::string> cls;
  for (int k = 1; k <= fm.Extent(); k++)
    if (k != rk) cls[BRep_Tool::Surface(TopoDS::Face(fm(k))).get()] = "ORIG";
  const BRepAlgo_Image& im = mk.MakeOffset().OffsetFacesFromShapes();
  for (NCollection_List<TopoDS_Shape>::Iterator it(im.Roots()); it.More(); it.Next())
  {
    const TopoDS_Shape& root = it.Value();
    std::string c = root.ShapeType() != TopAbs_FACE ? "GEN" : root.IsSame(fm(rk)) ? "CLOSE" : "OFF";
    if (!im.HasImage(root)) continue;
    NCollection_List<TopoDS_Shape> li; im.LastImage(root, li);
    for (NCollection_List<TopoDS_Shape>::Iterator j(li); j.More(); j.Next())
      for (TopExp_Explorer f(j.Value(), TopAbs_FACE); f.More(); f.Next())
      {
        const void* p = BRep_Tool::Surface(TopoDS::Face(f.Current())).get();
        auto e = cls.find(p);
        cls[p] = (e == cls.end() || e->second == c) ? c : e->second + "|" + c;
      }
  }
  GProp_GProps g; BRepGProp::VolumeProperties(r, g);
  printf("X2 done=1 valid=%d vol=%.3f\n", (int)BRepCheck_Analyzer(r).IsValid(), g.Mass());
  int n = 0;
  for (TopExp_Explorer sh(r, TopAbs_SHELL); sh.More(); sh.Next())
  {
    std::map<std::string, int> cnt; int nf = 0;
    for (TopExp_Explorer f(sh.Current(), TopAbs_FACE); f.More(); f.Next())
    {
      nf++;
      auto e = cls.find(BRep_Tool::Surface(TopoDS::Face(f.Current())).get());
      cnt[e == cls.end() ? "UNK" : e->second]++;
    }
    GProp_GProps gs; BRepGProp::VolumeProperties(sh.Current(), gs);
    std::string c; for (auto& kv : cnt) c += kv.first + "=" + std::to_string(kv.second) + " ";
    printf("  shell%d or=%d closed=%d nf=%d vol=%.3f %s\n", ++n, (int)sh.Current().Orientation(), (int)sh.Current().Closed(), nf, gs.Mass(), c.c_str());
  }
  return 0;
}
