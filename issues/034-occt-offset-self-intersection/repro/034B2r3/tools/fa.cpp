// fa.cpp <in.brep> : area of every face (default and with eps 1e-10), volume variants (test side)
#include "memcap.hxx"
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRep_Tool.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; if (!BRepTools::Read(s, argv[1], b)) return 1;
  int i = 0;
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next())
  {
    GProp_GProps g1, g2; BRepGProp::SurfaceProperties(e.Current(), g1); double er = BRepGProp::SurfaceProperties(e.Current(), g2, 1e-10);
    TopLoc_Location L; GeomAdaptor_Surface ga(BRep_Tool::Surface(TopoDS::Face(e.Current()), L));
    printf("F%d type=%d area=%.9f areaEps=%.9f err=%.2e c=(%.3f %.3f %.3f)\n", ++i, (int)ga.GetType(), g1.Mass(), g2.Mass(), er,
           g1.CentreOfMass().X(), g1.CentreOfMass().Y(), g1.CentreOfMass().Z());
  }
  GProp_GProps v1, v2, v3; BRepGProp::VolumeProperties(s, v1); double er2 = BRepGProp::VolumeProperties(s, v2, 1e-10, true);
  BRepGProp::VolumeProperties(s, v3, true, false, true); // UseTriangulation? (only closed, skip shared)
  printf("vol=%.9f volEps=%.9f (err %.2e) vol3=%.9f\n", v1.Mass(), v2.Mass(), er2, v3.Mass());
  return 0;
}
