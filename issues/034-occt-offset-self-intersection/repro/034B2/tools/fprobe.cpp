// fprobe.cpp <in.brep> <d> : per non-planar face: type, max/min smallest principal offset factor on a 33x33 grid, size, tol
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepBndLib.hxx>
#include <Bnd_Box.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <Geom_Surface.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Edge.hxx>
#include <IntTools_FClass2d.hxx>
#include <Precision.hxx>
#include <cmath>
#include <cstdio>
#include <cstdlib>
static bool factor(const Geom_Surface& S, double u, double v, double d, double& f)
{
  gp_Pnt P; gp_Vec Su, Sv, Suu, Svv, Suv; S.D2(u, v, P, Su, Sv, Suu, Svv, Suv);
  gp_Vec N = Su.Crossed(Sv); double nm = N.Magnitude();
  double E = Su.SquareMagnitude(), G = Sv.SquareMagnitude(), F = Su.Dot(Sv), den = E * G - F * F;
  if (nm < 1e-300 || den <= 0 || nm <= 1e-9 * std::sqrt(E * G)) return false;
  N.Divide(nm);
  double L = Suu.Dot(N), M = Suv.Dot(N), NN = Svv.Dot(N);
  double K = (L * NN - M * M) / den, H = (E * NN + G * L - 2 * F * M) / (2 * den);
  double disc = std::sqrt(std::max(H * H - K, 0.));
  f = std::min(1 - d * (H + disc), 1 - d * (H - disc));
  return true;
}
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; BRepTools::Read(s, argv[1], b);
  double t = atof(argv[2]); int k = 0;
  for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next())
  {
    k++;
    TopoDS_Face F = TopoDS::Face(ex.Current()); TopLoc_Location L;
    const occ::handle<Geom_Surface>& S = BRep_Tool::Surface(F, L);
    GeomAdaptor_Surface ga(S); if (ga.GetType() == GeomAbs_Plane) continue;
    double d = F.Orientation() == TopAbs_REVERSED ? -t : t;
    double u0, u1, v0, v1; BRepTools::UVBounds(F, u0, u1, v0, v1);
    IntTools_FClass2d cls(F, Precision::PConfusion());
    double mx = -1e30, mn = 1e30; int n = 0;
    for (int i = 0; i <= 32; i++) for (int j = 0; j <= 32; j++)
    {
      double u = u0 + (u1 - u0) * i / 32, v = v0 + (v1 - v0) * j / 32, f;
      if (cls.Perform(gp_Pnt2d(u, v)) == TopAbs_OUT) continue;
      if (!factor(*S, u, v, d, f)) continue;
      n++; mx = std::max(mx, f); mn = std::min(mn, f);
    }
    Bnd_Box bx; BRepBndLib::Add(F, bx, false);
    double tol = BRep_Tool::Tolerance(F);
    for (TopExp_Explorer e(F, TopAbs_EDGE); e.More(); e.Next()) tol = std::max(tol, BRep_Tool::Tolerance(TopoDS::Edge(e.Current())));
    printf("F%d type=%d n=%d max=%.3e min=%.3e diag=%.3g tol=%.2e max*diag=%.2e\n", k, (int)ga.GetType(), n, mx, mn, std::sqrt(bx.SquareExtent()), tol, mx * std::sqrt(bx.SquareExtent()));
  }
  return 0;
}
