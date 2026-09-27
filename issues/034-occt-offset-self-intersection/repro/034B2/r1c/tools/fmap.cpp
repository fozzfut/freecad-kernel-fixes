// fmap.cpp <in.brep> <d> <faceIdx> [N] : character map of the smallest principal offset factor sign over the UV box of one face
//   '.' outside the face, '+' factor > 0, '-' factor < 0, '0' |factor| < 0.05, 'x' singular normal. Then edges with degeneracy.
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <Geom_Surface.hxx>
#include <Geom_BSplineSurface.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <IntTools_FClass2d.hxx>
#include <Precision.hxx>
#include <cmath>
#include <cstdio>
#include <cstdlib>
static int factor(const Geom_Surface& S, double u, double v, double d, double& f, double& k1, double& k2)
{
  gp_Pnt P; gp_Vec Su, Sv, Suu, Svv, Suv; S.D2(u, v, P, Su, Sv, Suu, Svv, Suv);
  gp_Vec N = Su.Crossed(Sv); double nm = N.Magnitude();
  double E = Su.SquareMagnitude(), G = Sv.SquareMagnitude(), F = Su.Dot(Sv), den = E * G - F * F;
  if (nm < 1e-300 || den <= 0 || nm <= 1e-9 * std::sqrt(E * G)) return 0;
  N.Divide(nm);
  double L = Suu.Dot(N), M = Suv.Dot(N), NN = Svv.Dot(N);
  double K = (L * NN - M * M) / den, H = (E * NN + G * L - 2 * F * M) / (2 * den);
  double disc = std::sqrt(std::max(H * H - K, 0.));
  k1 = H + disc; k2 = H - disc;
  f = std::min(1 - d * k1, 1 - d * k2);
  return 1;
}
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; BRepTools::Read(s, argv[1], b);
  double t = atof(argv[2]); int want = atoi(argv[3]); int N = argc > 4 ? atoi(argv[4]) : 48; int k = 0;
  for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next())
  {
    k++; if (k != want) continue;
    TopoDS_Face F = TopoDS::Face(ex.Current()); TopLoc_Location L;
    const occ::handle<Geom_Surface>& S = BRep_Tool::Surface(F, L);
    double d = F.Orientation() == TopAbs_REVERSED ? -t : t;
    double u0, u1, v0, v1; BRepTools::UVBounds(F, u0, u1, v0, v1);
    double su0, su1, sv0, sv1; S->Bounds(su0, su1, sv0, sv1);
    printf("face %d orient=%d uv=[%g,%g]x[%g,%g] surf=[%g,%g]x[%g,%g] %s\n", k, (int)F.Orientation(), u0, u1, v0, v1, su0, su1, sv0, sv1, S->DynamicType()->Name());
    occ::handle<Geom_BSplineSurface> bs = occ::down_cast<Geom_BSplineSurface>(S);
    if (!bs.IsNull()) printf("bspline deg %d x %d poles %d x %d rational %d %d\n", bs->UDegree(), bs->VDegree(), bs->NbUPoles(), bs->NbVPoles(), bs->IsURational(), bs->IsVRational());
    IntTools_FClass2d cls(F, Precision::PConfusion());
    double mn = 1e30; double mu = 0, mv = 0, mk1 = 0, mk2 = 0;
    for (int j = N; j >= 0; j--)
    {
      for (int i = 0; i <= N; i++)
      {
        double u = u0 + (u1 - u0) * i / N, v = v0 + (v1 - v0) * j / N, f, k1, k2;
        bool in = cls.Perform(gp_Pnt2d(u, v)) != TopAbs_OUT;
        if (!factor(*S, u, v, d, f, k1, k2)) { putchar(in ? 'x' : ','); continue; }
        if (in && f < mn) { mn = f; mu = u; mv = v; mk1 = k1; mk2 = k2; }
        char c = f < -0.0 ? '-' : '+'; if (std::fabs(f) < 0.05) c = '0';
        if (!in) c = (c == '-') ? '_' : (c == '0' ? 'o' : '.');
        putchar(c);
      }
      putchar('\n');
    }
    printf("min in face %.4f at (%g,%g) k1=%g k2=%g\n", mn, mu, mv, mk1, mk2);
    int e = 0;
    for (TopExp_Explorer ee(F, TopAbs_EDGE); ee.More(); ee.Next())
    {
      e++; const TopoDS_Edge& E = TopoDS::Edge(ee.Current()); double a, bb;
      occ::handle<Geom2d_Curve> c = BRep_Tool::CurveOnSurface(E, F, a, bb);
      gp_Pnt2d p0 = c->Value(a), p1 = c->Value(bb);
      printf(" e%d deg=%d tol=%.2e uv (%g,%g)-(%g,%g)\n", e, (int)BRep_Tool::Degenerated(E), BRep_Tool::Tolerance(E), p0.X(), p0.Y(), p1.X(), p1.Y());
    }
  }
  return 0;
}
