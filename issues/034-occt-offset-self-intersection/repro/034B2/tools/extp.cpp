// extp.cpp: does GeomLib::ExtendSurfByLength keep the parametrisation of the original part?
#include <GeomLib.hxx>
#include <Geom_BSplineSurface.hxx>
#include <GeomAPI_PointsToBSplineSurface.hxx>
#include <TColgp_Array2OfPnt.hxx>
#include <cstdio>
#include <cmath>
int main()
{
  TColgp_Array2OfPnt p(1, 6, 1, 6);
  for (int i = 1; i <= 6; i++) for (int j = 1; j <= 6; j++) p(i, j) = gp_Pnt(i * 2.0, j * 1.5, std::sin(i * 0.7) + 0.3 * j * j * 0.1);
  occ::handle<Geom_BSplineSurface> s = GeomAPI_PointsToBSplineSurface(p, 3, 8, GeomAbs_C2, 1e-6).Surface();
  double u0, u1, v0, v1; s->Bounds(u0, u1, v0, v1);
  occ::handle<Geom_BoundedSurface> e = occ::down_cast<Geom_BoundedSurface>(s->Copy());
  GeomLib::ExtendSurfByLength(e, 3.0, 1, true, false); GeomLib::ExtendSurfByLength(e, 3.0, 1, true, true);
  GeomLib::ExtendSurfByLength(e, 3.0, 1, false, false); GeomLib::ExtendSurfByLength(e, 3.0, 1, false, true);
  double a0, a1, b0, b1; e->Bounds(a0, a1, b0, b1);
  double mx = 0;
  for (int i = 0; i <= 10; i++) for (int j = 0; j <= 10; j++)
  { double u = u0 + (u1 - u0) * i / 10, v = v0 + (v1 - v0) * j / 10; mx = std::max(mx, s->Value(u, v).Distance(e->Value(u, v))); }
  printf("orig [%g %g]x[%g %g] ext [%g %g]x[%g %g] maxdev at same params %g\n", u0, u1, v0, v1, a0, a1, b0, b1, mx);
  return 0;
}
