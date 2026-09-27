// canon.cpp <in.brep> [tol] : GeomConvert_SurfToAnaSurf on every B-spline face (type, gap) - lane B2 r2 debugging
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <GeomConvert_SurfToAnaSurf.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <cstdio>
#include <cstdlib>
#include <algorithm>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; BRepTools::Read(s, argv[1], b);
  const double tol = argc > 2 ? atof(argv[2]) : 1e-7;
  int k = 0;
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next())
  {
    k++;
    const TopoDS_Face& f = TopoDS::Face(e.Current());
    TopLoc_Location L; auto S = BRep_Tool::Surface(f, L);
    GeomAdaptor_Surface ga(S);
    if (ga.GetType() != GeomAbs_BSplineSurface) continue;
    double u0, u1, v0, v1; BRepTools::UVBounds(f, u0, u1, v0, v1); double a0,a1,b0,b1; S->Bounds(a0,a1,b0,b1); printf("  uv %.17g %.17g %.17g %.17g surf %.17g %.17g %.17g %.17g",u0,u1,v0,v1,a0,a1,b0,b1); puts(""); u0=std::max(u0,a0); u1=std::min(u1,a1); v0=std::max(v0,b0); v1=std::min(v1,b1);
    GeomConvert_SurfToAnaSurf c(S);
    auto a = c.ConvertToAnalytical(tol, u0, u1, v0, v1);
    GeomConvert_SurfToAnaSurf c2(S);
    auto a2 = c2.ConvertToAnalytical(1e-3, u0, u1, v0, v1);
    printf("F%d tol=%g -> %s gap=%.3g | tol 1e-3 -> %s gap=%.3g ftol=%.2g\n", k, tol, a.IsNull() ? "null" : a->DynamicType()->Name(), c.Gap(),
           a2.IsNull() ? "null" : a2->DynamicType()->Name(), c2.Gap(), BRep_Tool::Tolerance(f));
  }
  return 0;
}
