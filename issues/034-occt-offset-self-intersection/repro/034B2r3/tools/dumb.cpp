// dumb.cpp <out.brep> : the review A2 "dumbbell_rod" solid (two boxes + rod r0.8) and the index of its -X face
#include "memcap.hxx"
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepTools.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <cstdio>
int main(int, char** argv)
{
  auto box = [](double x, double y, double z, double a, double b, double c) { return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), a, b, c).Shape(); };
  TopoDS_Shape u = BRepAlgoAPI_Fuse(BRepAlgoAPI_Fuse(box(0, 0, 0, 20, 20, 20), box(40, 0, 0, 20, 20, 20)).Shape(),
                                    BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(19, 10, 10), gp::DX()), 0.8, 22).Shape()).Shape();
  TopExp_Explorer ex(u, TopAbs_SOLID); TopoDS_Shape s = ex.Current();
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
  for (int i = 1; i <= fm.Extent(); i++) { GProp_GProps g; BRepGProp::SurfaceProperties(fm(i), g); gp_Pnt c = g.CentreOfMass(); if (c.X() < 1e-9) printf("minusX face %d\n", i); }
  BRepTools::Write(s, argv[1]);
  return 0;
}
