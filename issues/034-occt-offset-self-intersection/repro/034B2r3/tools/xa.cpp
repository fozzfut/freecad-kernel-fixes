// xa.cpp <in.brep> <axis 0|1|2> <pos> : sum of the areas (adaptive, eps 1e-10) of the planar faces that lie in the
// plane coordinate[axis] = pos (test side: the cross-section of a prism result)
#include "memcap.hxx"
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <Bnd_Box.hxx>
#include <BRepBndLib.hxx>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <BRepBuilderAPI_Transform.hxx>
#include <cstring>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; if (!BRepTools::Read(s, argv[1], b)) { puts("READ-FAIL"); return 1; }
  const int ax = atoi(argv[2]); const double pos = atof(argv[3]);
  if (argc > 4 && (!strcmp(argv[4], "p1") || !strcmp(argv[4], "p2")))
  {
    // inverse of the gen4 placement (rotation 30 deg about (1,2,3), then translation (7,-3,11))
    gp_Trsf t; t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 2, 3)), 30. * M_PI / 180.);
    gp_Trsf m; m.SetTranslation(gp_Vec(7, -3, 11)); t = m * t;
    s = BRepBuilderAPI_Transform(s, t.Inverted(), true).Shape();
  }
  double sum = 0; int n = 0;
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next())
  {
    BRepAdaptor_Surface bas(TopoDS::Face(e.Current()));
    (void)bas; // any face lying in the plane (a planar B-spline too)
    Bnd_Box bx; BRepBndLib::AddOptimal(e.Current(), bx, false, false);
    double c0[3], c1[3]; bx.Get(c0[0], c0[1], c0[2], c1[0], c1[1], c1[2]);
    if (std::abs(c0[ax] - pos) > 1e-5 || std::abs(c1[ax] - pos) > 1e-5) continue;
    GProp_GProps g; BRepGProp::SurfaceProperties(e.Current(), g, 1e-10); sum += g.Mass(); n++;
  }
  printf("XA n=%d area=%.10f\n", n, sum);
  return 0;
}
