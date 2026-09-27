// gen.cpp - issue 034 lane B2: parametric family generator (NOT kernel code).
//   gen <family> <r> <variant: a|n> <placement: 0|1|2> <out.brep> [extra]
// family: step   L-step block, concave fillet radius r along the inner edge (ends on two side planes)
//         lwall  L-shaped wall (extruded L), concave vertical fillet r (ends on top/bottom planes)
//         pocket 20x20x10 block with a 10x10x5 pocket, all pocket edges below the rim filleted r
//         rbox   box 20x14x10 with all 12 edges filleted r (closed blend network)
//         boss   plate 30x30x5 + cylinder boss R=6 h=6, concave fillet r at the boss root (torus)
//         vfil   L-step with a VARIABLE radius fillet r .. 3r along the edge (partial fold across a threshold)
//         dimple plate 20x20x5 whose top is a B-spline with a smooth dent of depth r*... (extra = dent width)
// variant: a = as built (analytic where the modeller makes it), n = every face converted to NURBS
// placement: 0 = identity, 1 = rotated 30 deg about (1,2,3) + moved (7,-3,11), 2 = rotated 90 deg about z + moved (-50,20,5)
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakePolygon.hxx>
#include <BRepBuilderAPI_NurbsConvert.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <string>
#include <BRep_Tool.hxx>
#include <GeomAPI_PointsToBSplineSurface.hxx>
#include <Geom_BSplineSurface.hxx>
#include <ShapeUpgrade_UnifySameDomain.hxx>
#include <TColgp_Array2OfPnt.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <BRepBuilderAPI_Sewing.hxx>
#include <BRepBuilderAPI_MakeSolid.hxx>
#include <BRepLib.hxx>
#include <ShapeUpgrade_ShapeDivideContinuity.hxx>
#include <Standard_Failure.hxx>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

static TopoDS_Shape unify(const TopoDS_Shape& s)
{
  ShapeUpgrade_UnifySameDomain u(s, true, true, true);
  u.Build();
  return u.Shape();
}

// edges whose midpoint satisfies pred
template <class P> static void addEdges(BRepFilletAPI_MakeFillet& mf, const TopoDS_Shape& s, double r, P pred)
{
  TopTools_IndexedMapOfShape em;
  TopExp::MapShapes(s, TopAbs_EDGE, em);
  for (int i = 1; i <= em.Extent(); i++)
  {
    BRepAdaptor_Curve c(TopoDS::Edge(em(i)));
    gp_Pnt m = c.Value(0.5 * (c.FirstParameter() + c.LastParameter()));
    if (pred(m)) mf.Add(r, TopoDS::Edge(em(i)));
  }
}

int main(int argc, char** argv)
{
  if (argc >= 11 && std::string(argv[1]) == "cutbox")
  {
    // gen cutbox <in.brep> x0 y0 z0 x1 y1 z1 <placement> <out.brep> : reference solid = in minus the box (box moved
    // with the same placement as the family members)
    TopoDS_Shape in; BRep_Builder bb; BRepTools::Read(in, argv[2], bb);
    TopoDS_Shape bx = BRepPrimAPI_MakeBox(gp_Pnt(atof(argv[3]), atof(argv[4]), atof(argv[5])), gp_Pnt(atof(argv[6]), atof(argv[7]), atof(argv[8]))).Shape();
    int plc = atoi(argv[9]);
    if (plc)
    {
      gp_Trsf rot, tr;
      if (plc == 1) { rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 2, 3)), M_PI / 6); tr.SetTranslation(gp_Vec(7, -3, 11)); }
      else { rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp::DZ()), M_PI / 2); tr.SetTranslation(gp_Vec(-50, 20, 5)); }
      bx = BRepBuilderAPI_Transform(bx, tr * rot, true).Shape();
    }
    TopoDS_Shape r = BRepAlgoAPI_Cut(in, bx).Shape();
    BRepTools::Write(r, argv[10]);
    puts(argv[10]);
    return 0;
  }
  if (argc >= 12 && std::string(argv[1]) == "cuttri")
  {
    // gen cuttri <in.brep> z0 z1 x1 y1 x2 y2 x3 y3 <placement> <out.brep> : in minus the triangle prism (same placement)
    TopoDS_Shape in; BRep_Builder bb; BRepTools::Read(in, argv[2], bb);
    const double z0 = atof(argv[3]), z1 = atof(argv[4]);
    BRepBuilderAPI_MakePolygon pg(gp_Pnt(atof(argv[5]), atof(argv[6]), z0), gp_Pnt(atof(argv[7]), atof(argv[8]), z0),
                                  gp_Pnt(atof(argv[9]), atof(argv[10]), z0), true);
    TopoDS_Shape pr = BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(pg.Wire(), true).Face(), gp_Vec(0, 0, z1 - z0)).Shape();
    int plc = atoi(argv[11]);
    if (plc)
    {
      gp_Trsf rot, tr;
      if (plc == 1) { rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 2, 3)), M_PI / 6); tr.SetTranslation(gp_Vec(7, -3, 11)); }
      else { rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp::DZ()), M_PI / 2); tr.SetTranslation(gp_Vec(-50, 20, 5)); }
      pr = BRepBuilderAPI_Transform(pr, tr * rot, true).Shape();
    }
    TopoDS_Shape r = BRepAlgoAPI_Cut(in, pr).Shape();
    BRepTools::Write(r, argv[12]);
    puts(argv[12]);
    return 0;
  }
  if (argc >= 10 && std::string(argv[1]) == "refbox")
  {
    // gen refbox x0 y0 z0 x1 y1 z1 <placement> <out.brep> : independent reference = a plain box, same placement
    TopoDS_Shape bx = BRepPrimAPI_MakeBox(gp_Pnt(atof(argv[2]), atof(argv[3]), atof(argv[4])), gp_Pnt(atof(argv[5]), atof(argv[6]), atof(argv[7]))).Shape();
    int plc = atoi(argv[8]);
    if (plc)
    {
      gp_Trsf rot, tr;
      if (plc == 1) { rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 2, 3)), M_PI / 6); tr.SetTranslation(gp_Vec(7, -3, 11)); }
      else { rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp::DZ()), M_PI / 2); tr.SetTranslation(gp_Vec(-50, 20, 5)); }
      bx = BRepBuilderAPI_Transform(bx, tr * rot, true).Shape();
    }
    BRepTools::Write(bx, argv[9]);
    puts(argv[9]);
    return 0;
  }
  if (argc < 6) { printf("usage\n"); return 2; }
  const std::string fam = argv[1];
  const double r = atof(argv[2]);
  const bool nurbs = argv[3][0] == 'n' || argv[3][0] == 'm';
  const bool split = argv[3][0] == 'm';
  const int plc = atoi(argv[4]);
  const char* out = argv[5];
  const double extra = argc > 6 ? atof(argv[6]) : 0;
  TopoDS_Shape s;
  try
  {
    if (fam == "step" || fam == "vfil")
    {
      TopoDS_Shape a = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), gp_Pnt(20, 10, 10)).Shape();
      TopoDS_Shape b = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), gp_Pnt(10, 10, 20)).Shape();
      s = unify(BRepAlgoAPI_Fuse(a, b).Shape());
      BRepFilletAPI_MakeFillet mf(s);
      TopTools_IndexedMapOfShape em;
      TopExp::MapShapes(s, TopAbs_EDGE, em);
      for (int i = 1; i <= em.Extent(); i++)
      {
        BRepAdaptor_Curve c(TopoDS::Edge(em(i)));
        gp_Pnt m = c.Value(0.5 * (c.FirstParameter() + c.LastParameter()));
        if (std::abs(m.X() - 10) < 1e-6 && std::abs(m.Z() - 10) < 1e-6)
        {
          if (fam == "step") mf.Add(r, TopoDS::Edge(em(i)));
          else mf.Add(r, 3 * r, TopoDS::Edge(em(i)));
        }
      }
      mf.Build();
      s = mf.Shape();
    }
    else if (fam == "lwall")
    {
      TopoDS_Shape a = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), gp_Pnt(20, 2, 10)).Shape();
      TopoDS_Shape b = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), gp_Pnt(2, 20, 10)).Shape();
      s = unify(BRepAlgoAPI_Fuse(a, b).Shape());
      BRepFilletAPI_MakeFillet mf(s);
      addEdges(mf, s, r, [](const gp_Pnt& m) { return std::abs(m.X() - 2) < 1e-6 && std::abs(m.Y() - 2) < 1e-6; });
      mf.Build();
      s = mf.Shape();
    }
    else if (fam == "pocket")
    {
      TopoDS_Shape a = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), gp_Pnt(20, 20, 10)).Shape();
      TopoDS_Shape b = BRepPrimAPI_MakeBox(gp_Pnt(5, 5, 5), gp_Pnt(15, 15, 12)).Shape();
      s = BRepAlgoAPI_Cut(a, b).Shape();
      BRepFilletAPI_MakeFillet mf(s);
      addEdges(mf, s, r, [](const gp_Pnt& m) {
        return m.X() > 4.9 && m.X() < 15.1 && m.Y() > 4.9 && m.Y() < 15.1 && m.Z() < 9.99 && m.Z() > 4.9;
      });
      mf.Build();
      s = mf.Shape();
    }
    else if (fam == "rbox")
    {
      s = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), gp_Pnt(20, 14, 10)).Shape();
      BRepFilletAPI_MakeFillet mf(s);
      addEdges(mf, s, r, [](const gp_Pnt&) { return true; });
      mf.Build();
      s = mf.Shape();
    }
    else if (fam == "vbox" || fam == "tbox" || fam == "ebox" || fam == "vtbox")
    {
      // round-1 continuation (sharp rim edges): box 20x14x10 with only some edges filleted r
      //   vbox the 4 vertical edges, tbox the 4 top edges, ebox the one vertical edge x=0 y=0,
      //   vtbox the 4 vertical + 4 top edges (corner blends at the top, sharp bottom)
      s = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), gp_Pnt(20, 14, 10)).Shape();
      BRepFilletAPI_MakeFillet mf(s);
      if (fam == "vbox") addEdges(mf, s, r, [](const gp_Pnt& m) { return m.Z() > 1e-6 && m.Z() < 10 - 1e-6; });
      else if (fam == "tbox") addEdges(mf, s, r, [](const gp_Pnt& m) { return std::abs(m.Z() - 10) < 1e-6; });
      else if (fam == "ebox") addEdges(mf, s, r, [](const gp_Pnt& m) { return std::abs(m.X()) < 1e-6 && std::abs(m.Y()) < 1e-6; });
      else addEdges(mf, s, r, [](const gp_Pnt& m) { return m.Z() > 1e-6; });
      mf.Build();
      s = mf.Shape();
    }
    else if (fam == "tri")
    {
      // right triangular prism (legs 20 x 11.547 = 30/60/90 deg corners), height 10, the 3 vertical edges filleted r
      BRepBuilderAPI_MakePolygon pg(gp_Pnt(0, 0, 0), gp_Pnt(20, 0, 0), gp_Pnt(0, 20 * std::tan(M_PI / 6), 0), true);
      TopoDS_Face f = BRepBuilderAPI_MakeFace(pg.Wire(), true).Face();
      s = BRepPrimAPI_MakePrism(f, gp_Vec(0, 0, 10)).Shape();
      BRepFilletAPI_MakeFillet mf(s);
      addEdges(mf, s, r, [](const gp_Pnt& m) { return m.Z() > 1e-6 && m.Z() < 10 - 1e-6; });
      mf.Build();
      s = mf.Shape();
    }
    else if (fam == "tray")
    {
      // box 20x14x10 with an open pocket [2,18]x[2,12]x[2,10]; the 4 vertical pocket edges filleted r (concave),
      // pocket floor edges sharp (concave)
      TopoDS_Shape a = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), gp_Pnt(20, 14, 10)).Shape();
      TopoDS_Shape b = BRepPrimAPI_MakeBox(gp_Pnt(2, 2, 2), gp_Pnt(18, 12, 12)).Shape();
      s = BRepAlgoAPI_Cut(a, b).Shape();
      BRepFilletAPI_MakeFillet mf(s);
      addEdges(mf, s, r, [](const gp_Pnt& m) {
        return m.Z() > 2 + 1e-6 && m.Z() < 10 - 1e-6 && (std::abs(m.X() - 2) < 1e-6 || std::abs(m.X() - 18) < 1e-6)
               && (std::abs(m.Y() - 2) < 1e-6 || std::abs(m.Y() - 12) < 1e-6);
      });
      mf.Build();
      s = mf.Shape();
    }
    else if (fam == "boss")
    {
      TopoDS_Shape a = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), gp_Pnt(30, 30, 5)).Shape();
      TopoDS_Shape b = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(15, 15, 5), gp::DZ()), 6, 6).Shape();
      s = unify(BRepAlgoAPI_Fuse(a, b).Shape());
      BRepFilletAPI_MakeFillet mf(s);
      addEdges(mf, s, r, [](const gp_Pnt& m) { return std::abs(m.Z() - 5) < 1e-6 && std::abs(gp_Pnt(m.X(), m.Y(), 0).Distance(gp_Pnt(15, 15, 0)) - 6) < 1e-6; });
      mf.Build();
      s = mf.Shape();
    }
    else if (fam == "shaft")
    {
      // cylinder R5 h20, both circular edges filleted r (convex torus rings): inward offset > r -> sharp cylinder
      s = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp::DZ()), 5, 20).Shape();
      BRepFilletAPI_MakeFillet mf(s);
      TopTools_IndexedMapOfShape em;
      TopExp::MapShapes(s, TopAbs_EDGE, em);
      for (int i = 1; i <= em.Extent(); i++)
        if (!BRep_Tool::Degenerated(TopoDS::Edge(em(i))) && BRepAdaptor_Curve(TopoDS::Edge(em(i))).GetType() == GeomAbs_Circle)
          mf.Add(r, TopoDS::Edge(em(i)));
      mf.Build();
      s = mf.Shape();
    }
    else if (fam == "dimple")
    {
      // top z = 5 - r * exp(-(x^2+y^2)/w^2) on [-10,10]^2, w = extra (default 3): smallest concave radius at the
      // dent centre = w^2 / (2 r)
      const double w = extra > 0 ? extra : 3.0;
      const int n = 41;
      TColgp_Array2OfPnt pts(1, n, 1, n);
      for (int i = 1; i <= n; i++)
        for (int j = 1; j <= n; j++)
        {
          double x = -10 + 20.0 * (i - 1) / (n - 1), y = -10 + 20.0 * (j - 1) / (n - 1);
          pts(i, j) = gp_Pnt(x, y, 5 - r * std::exp(-(x * x + y * y) / (w * w)));
        }
      GeomAPI_PointsToBSplineSurface fit(pts, 3, 8, GeomAbs_C2, 1e-6);
      occ::handle<Geom_BSplineSurface> top = fit.Surface();
      TopoDS_Face ft = BRepBuilderAPI_MakeFace(top, 1e-7).Face();
      s = BRepPrimAPI_MakePrism(ft, gp_Vec(0, 0, -5 - r - 2)).Shape();
    }
    else { printf("bad family\n"); return 2; }
  }
  catch (Standard_Failure const& e) { printf("GEN-FAIL %s\n", e.GetMessageString()); return 4; }
  if (s.IsNull()) { printf("GEN-FAIL null\n"); return 4; }
  if (nurbs)
  {
    BRepBuilderAPI_NurbsConvert nc(s, true);
    s = nc.Shape();
    if (split)
    {
      // variant m: NURBS split at C0 knots into C1 faces (stock rejects C0 input faces)
      ShapeUpgrade_ShapeDivideContinuity dc(s);
      dc.SetBoundaryCriterion(GeomAbs_C1);
      dc.SetPCurveCriterion(GeomAbs_C1);
      dc.SetSurfaceCriterion(GeomAbs_C1);
      dc.Perform();
      s = dc.Result();
    }
  }
  if (plc)
  {
    gp_Trsf rot, tr;
    if (plc == 1) { rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 2, 3)), M_PI / 6); tr.SetTranslation(gp_Vec(7, -3, 11)); }
    else { rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp::DZ()), M_PI / 2); tr.SetTranslation(gp_Vec(-50, 20, 5)); }
    s = BRepBuilderAPI_Transform(s, tr * rot, true).Shape();  // copy = geometry really moved (world coordinates)
  }
  BRepTools::Write(s, out);
  int nf = 0;
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next()) nf++;
  printf("GEN %s r=%g %s plc=%d nf=%d -> %s\n", fam.c_str(), r, nurbs ? "nurbs" : "analytic", plc, nf, out);
  return 0;
}
