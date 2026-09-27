// curvk <in.brep> <x> <y> <z> <rad>: for every BSpline/Bezier face whose centre is within rad of (x,y,z): max
// |principal curvature| over a 60x60 grid of points inside the face (BRepClass), its location, and the signed
// curvatures there (outward normal: positive = convex). Min radius = 1/kmax.
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepClass_FaceClassifier.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRepLProp_SLProps.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <cstdio>
#include <cmath>

int main(int argc, char** argv)
{
  TopoDS_Shape s;
  BRep_Builder bb;
  if (!BRepTools::Read(s, argv[1], bb)) { printf("READ-FAIL\n"); return 3; }
  const gp_Pnt C(atof(argv[2]), atof(argv[3]), atof(argv[4]));
  const double rad = atof(argv[5]);
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  for (int i = 1; i <= fm.Extent(); i++)
  {
    const TopoDS_Face&  F = TopoDS::Face(fm(i));
    BRepAdaptor_Surface S(F);
    if (S.GetType() != GeomAbs_BSplineSurface && S.GetType() != GeomAbs_BezierSurface) continue;
    GProp_GProps g;
    BRepGProp::SurfaceProperties(F, g);
    if (g.CentreOfMass().Distance(C) > rad) continue;
    double u0, u1, v0, v1;
    BRepTools::UVBounds(F, u0, u1, v0, v1);
    double kmax = 0, kmin1 = 0, kmin2 = 0;
    gp_Pnt at;
    int    nin = 0;
    const int N = 60;
    for (int a = 0; a <= N; a++)
      for (int b = 0; b <= N; b++)
      {
        const double u = u0 + (u1 - u0) * a / N, v = v0 + (v1 - v0) * b / N;
        BRepClass_FaceClassifier cl(F, gp_Pnt2d(u, v), 1e-7);
        if (cl.State() != TopAbs_IN) continue;
        nin++;
        BRepLProp_SLProps pr(S, u, v, 2, 1e-9);
        if (!pr.IsCurvatureDefined()) continue;
        double k1 = pr.MaxCurvature(), k2 = pr.MinCurvature();
        if (F.Orientation() == TopAbs_REVERSED) { k1 = -k1; k2 = -k2; }
        const double k = std::max(std::abs(k1), std::abs(k2));
        if (k > kmax) { kmax = k; kmin1 = k1; kmin2 = k2; at = pr.Value(); }
      }
    printf("F%d area %.4f in %d kmax %.2f (minR %.4f) k1 %.2f k2 %.2f at (%.3f,%.3f,%.3f)\n", i, g.Mass(), nin, kmax,
           kmax > 0 ? 1. / kmax : 0., kmin1, kmin2, at.X(), at.Y(), at.Z());
  }
  return 0;
}
