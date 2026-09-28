// gen4.cpp - issue 034 lane B2 round 3 LIGHT class-family generator (test side, NOT kernel code).
//   gen4 ell   <a> <b> <H> <a|n> <plc> <out>            elliptic cylinder (partial fold for b^2/a < d < b)
//   gen4 wave  <amp> <per> <np> <a|n> <plc> <out>       block 0..L x 0..W, top = extrusion along y of a clamped cubic
//                                                        B-spline profile z = 10 + amp*cos(2 pi x/per) (np poles)
//   gen4 bump  <h> <sharp> <n> <a|n> <plc> <out>                 block 40x30, top = bicubic B-spline n x n poles, a bump
//                                                        (closed fold region inside the face: two miter ends)
//   gen4 ridge <h> <sharp> <n> <a|n> <plc> <out>                 block 40x30, top = bicubic B-spline, ridge along x running
//                                                        out at x = 0 and x = 40 (fold band exits two sides)
//   gen4 loft  <a> <b> <r> <H> <a|n> <plc> <out>          lofted wall ellipse a x b -> circle r (fold ends inside)
//   gen4 saddle <c> <sharp> <n> <a|n> <plc> <out>                block, top saddle z = 10 + c(x'^2 - y'^2)/..: convex in y
// placement: 0 identity; 1 = TopLoc_Location (rotation 30 deg about (1,2,3) + (7,-3,11)); 2 = the same baked into
// the geometry (world placement).
// Prints the largest convex / concave principal curvature of the free-form face(s) (fold thresholds of inward /
// outward offsets: radius 1/k).
#include "memcap.hxx"
#include <BRepAlgoAPI_Common.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepBuilderAPI_NurbsConvert.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepLProp_SLProps.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepOffsetAPI_ThruSections.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <Geom_BSplineCurve.hxx>
#include <Geom_BSplineSurface.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <gp_Circ.hxx>
#include <gp_Elips.hxx>
#include <NCollection_Array1.hxx>
#include <NCollection_Array2.hxx>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>

static TopoDS_Shape place(const TopoDS_Shape& s, int plc)
{
  if (plc == 0) return s;
  gp_Trsf t;
  t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 2, 3)), 30. * M_PI / 180.);
  gp_Trsf m;
  m.SetTranslation(gp_Vec(7, -3, 11));
  t = m * t;
  return BRepBuilderAPI_Transform(s, t, plc == 2).Shape();
}

static occ::handle<Geom_BSplineCurve> clampedCubic(const NCollection_Array1<gp_Pnt>& thePoles)
{
  const int n = thePoles.Length(), nk = n - 2;
  NCollection_Array1<double> k(1, nk);
  NCollection_Array1<int>    m(1, nk);
  for (int i = 1; i <= nk; i++) { k(i) = i - 1; m(i) = 1; }
  m(1) = m(nk) = 4;
  return new Geom_BSplineCurve(thePoles, k, m, 3);
}

static occ::handle<Geom_BSplineSurface> clampedBicubic(const NCollection_Array2<gp_Pnt>& thePoles)
{
  const int nu = thePoles.ColLength(), nv = thePoles.RowLength();
  NCollection_Array1<double> ku(1, nu - 2), kv(1, nv - 2);
  NCollection_Array1<int>    mu(1, nu - 2), mv(1, nv - 2);
  for (int i = 1; i <= nu - 2; i++) { ku(i) = i - 1; mu(i) = 1; }
  for (int i = 1; i <= nv - 2; i++) { kv(i) = i - 1; mv(i) = 1; }
  mu(1) = mu(nu - 2) = mv(1) = mv(nv - 2) = 4;
  return new Geom_BSplineSurface(thePoles, ku, kv, mu, mv, 3, 3);
}

// solid below the top face: prism of the face down, common with the box [x0,x1]x[y0,y1]x[0,zt]
static TopoDS_Shape underFace(const TopoDS_Face& theTop, double x0, double x1, double y0, double y1, double zt)
{
  TopoDS_Shape pr = BRepPrimAPI_MakePrism(theTop, gp_Vec(0, 0, -60.)).Shape();
  TopoDS_Shape bx = BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, 0.), gp_Pnt(x1, y1, zt)).Shape();
  return BRepAlgoAPI_Common(pr, bx).Shape();
}

static void curvatures(const TopoDS_Shape& s)
{
  double kConv = 0., kConc = 0.; // convex = the solid bulges out (inward offsets fold)
  for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next())
  {
    const TopoDS_Face& f = TopoDS::Face(ex.Current());
    BRepAdaptor_Surface bas(f);
    if (bas.GetType() == GeomAbs_Plane) continue;
    double u0, u1, v0, v1;
    BRepTools::UVBounds(f, u0, u1, v0, v1);
    for (int i = 0; i <= 200; i++)
      for (int j = 0; j <= 200; j++)
      {
        BRepLProp_SLProps pr(bas, u0 + (u1 - u0) * i / 200., v0 + (v1 - v0) * j / 200., 2, 1e-9);
        if (!pr.IsCurvatureDefined()) continue;
        double k1 = pr.MaxCurvature(), k2 = pr.MinCurvature();
        // SLProps curvature sign is w.r.t. the surface normal Su x Sv; outward normal of the solid face:
        const double sg = (f.Orientation() == TopAbs_REVERSED) ? -1. : 1.;
        // convex (bulging outwards): curvature w.r.t. the outward normal negative
        for (double k : {k1 * sg, k2 * sg})
        {
          kConv = std::max(kConv, -k);
          kConc = std::max(kConc, k);
        }
      }
  }
  printf("  convex kmax=%.6f (inward fold beyond r=%.6f)  concave kmax=%.6f (outward fold beyond r=%.6f)\n", kConv,
         kConv > 0 ? 1. / kConv : 0., kConc, kConc > 0 ? 1. / kConc : 0.);
}

int main(int argc, char** argv)
{
  if (argc < 3) { puts("usage: see header"); return 2; }
  std::string fam = argv[1];
  TopoDS_Shape s;
  int plc = 0; const char* out = nullptr; bool nb = false;
  if (fam == "ell")
  {
    double a = atof(argv[2]), b = atof(argv[3]), H = atof(argv[4]);
    nb = argv[5][0] == 'n'; plc = atoi(argv[6]); out = argv[7];
    gp_Elips el(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0)), a, b);
    TopoDS_Face f = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(el)).Wire());
    s = BRepPrimAPI_MakePrism(f, gp_Vec(0, 0, H)).Shape();
  }
  else if (fam == "wave")
  {
    double amp = atof(argv[2]), per = atof(argv[3]);
    int np = atoi(argv[4]);
    nb = argv[5][0] == 'n'; plc = atoi(argv[6]); out = argv[7];
    const double L = 40., W = 20.;
    // poles of a cubic B-spline approximating 10 + amp cos(2 pi x / per): pole heights scaled so that the curve
    // reaches the amplitude (control-polygon of a sampled cosine); the exact shape is whatever the spline is
    NCollection_Array1<gp_Pnt> p(1, np);
    for (int i = 1; i <= np; i++)
    {
      const double x = L * (i - 1) / (np - 1);
      p(i) = gp_Pnt(x, 0., 10. + amp * std::cos(2 * M_PI * x / per));
    }
    occ::handle<Geom_BSplineCurve> c = clampedCubic(p);
    TopoDS_Edge et = BRepBuilderAPI_MakeEdge(c);
    gp_Pnt a0 = c->Value(c->FirstParameter()), a1 = c->Value(c->LastParameter());
    TopoDS_Edge e1 = BRepBuilderAPI_MakeEdge(a1, gp_Pnt(a1.X(), 0, 0));
    TopoDS_Edge e2 = BRepBuilderAPI_MakeEdge(gp_Pnt(a1.X(), 0, 0), gp_Pnt(a0.X(), 0, 0));
    TopoDS_Edge e3 = BRepBuilderAPI_MakeEdge(gp_Pnt(a0.X(), 0, 0), a0);
    BRepBuilderAPI_MakeWire mw(et, e1, e2, e3);
    TopoDS_Face f = BRepBuilderAPI_MakeFace(mw.Wire(), true);
    s = BRepPrimAPI_MakePrism(f, gp_Vec(0, W, 0)).Shape();
  }
  else if (fam == "bump" || fam == "ridge" || fam == "saddle")
  {
    double h = atof(argv[2]), sh = atof(argv[3]);
    int n = atoi(argv[4]);
    nb = argv[5][0] == 'n'; plc = atoi(argv[6]); out = argv[7];
    const double L = 40., W = 30.;
    NCollection_Array2<gp_Pnt> p(1, n, 1, n);
    for (int i = 1; i <= n; i++)
      for (int j = 1; j <= n; j++)
      {
        const double x = L * (i - 1) / (n - 1), y = W * (j - 1) / (n - 1);
        const double xs = (x - L / 2) / (L / 2), ys = (y - W / 2) / (W / 2); // -1..1
        double z = 10.;
        if (fam == "bump")
          z += h * std::exp(-sh * (xs * xs + 2.5 * ys * ys));
        else if (fam == "ridge")
          z += h * std::exp(-sh * ys * ys);
        else
          z += h * (0.3 * xs * xs - ys * ys) * std::exp(-sh * ys * ys);
        p(i, j) = gp_Pnt(x, y, z);
      }
    occ::handle<Geom_BSplineSurface> bs = clampedBicubic(p);
    TopoDS_Face ft = BRepBuilderAPI_MakeFace(bs, 1e-7);
    s = underFace(ft, 0., L, 0., W, 30.);
    if (s.ShapeType() == TopAbs_COMPOUND)
    {
      TopExp_Explorer ex(s, TopAbs_SOLID);
      if (ex.More()) s = ex.Current();
    }
  }
  else if (fam == "loft")
  {
    double a = atof(argv[2]), b = atof(argv[3]), r = atof(argv[4]), H = atof(argv[5]);
    nb = argv[6][0] == 'n'; plc = atoi(argv[7]); out = argv[8];
    gp_Elips el(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0)), a, b);
    gp_Circ ci(gp_Ax2(gp_Pnt(0, 0, H), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0)), r);
    BRepOffsetAPI_ThruSections ts(true, false);
    ts.AddWire(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(el)).Wire());
    ts.AddWire(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(ci)).Wire());
    ts.Build();
    s = ts.Shape();
  }
  else { puts("unknown family"); return 2; }
  if (nb) s = BRepBuilderAPI_NurbsConvert(s, true).Shape();
  s = place(s, plc);
  GProp_GProps g;
  BRepGProp::VolumeProperties(s, g);
  int nf = 0;
  for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next()) nf++;
  printf("%s faces=%d vol=%.6f valid=%d\n", out, nf, g.Mass(), (int)BRepCheck_Analyzer(s).IsValid());
  curvatures(s);
  BRepTools::Write(s, out);
  return 0;
}
