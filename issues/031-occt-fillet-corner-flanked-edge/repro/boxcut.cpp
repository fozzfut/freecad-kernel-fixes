// boxcut <in.brep> <x> <y> <z> <h>: cut and fuse with the axis-aligned box of half size h centred at (x,y,z);
// prints the grade of each (OK/BOP/INV/ERR) and the corner centre of the input (down3::cornerCentre, r = h/0.6)
#include "down3.hxx"
#include <BRep_Builder.hxx>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder bb;
  if (!BRepTools::Read(s, argv[1], bb)) { printf("READ-FAIL\n"); return 3; }
  const gp_Pnt P(atof(argv[2]), atof(argv[3]), atof(argv[4]));
  const double h = atof(argv[5]);
  const gp_Pnt C = down3::cornerCentre(s, P, h / 0.6 * 2);
  printf("centre (%.4f,%.4f,%.4f) cut=%s fuse=%s\n", C.X(), C.Y(), C.Z(),
         down3::boolop(s, down3::box(P, h, false), false).c_str(), down3::boolop(s, down3::box(P, h, false), true).c_str());
  return 0;
}
