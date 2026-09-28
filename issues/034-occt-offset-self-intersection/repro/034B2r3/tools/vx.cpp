// vx.cpp <in.brep> : volume (default and adaptive eps 1e-9), optimal bbox, validity (test side)
#include "memcap.hxx"
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRepBndLib.hxx>
#include <Bnd_Box.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; if (!BRepTools::Read(s, argv[1], b)) { puts("READ-FAIL"); return 1; }
  GProp_GProps g1, g2; BRepGProp::VolumeProperties(s, g1); BRepGProp::VolumeProperties(s, g2, 1.e-9, true);
  Bnd_Box bx; BRepBndLib::AddOptimal(s, bx, false, false);
  double x0, y0, z0, x1, y1, z1; bx.Get(x0, y0, z0, x1, y1, z1);
  printf("vol=%.9f volA=%.9f box=(%.6f %.6f %.6f)-(%.6f %.6f %.6f) valid=%d\n", g1.Mass(), g2.Mass(), x0, y0, z0, x1, y1, z1,
         (int)BRepCheck_Analyzer(s).IsValid());
  return 0;
}
