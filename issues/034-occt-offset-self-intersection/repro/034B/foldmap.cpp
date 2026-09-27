// foldmap.cpp - issue 034 stage B geometry probe.
//   foldmap faces <in.brep>                 : faces (type, orientation, area, centroid) + neighbours per edge with
//                                             the dihedral angle at the edge middle (0 = tangent) and convexity
//   foldmap map <in.brep> <face> <d> [N]    : ASCII map of the smallest principal offset factor 1 - d*k over an
//                                             N x N UV grid of the face ('#' < 0 fold, '+' < 0.3, '.' >= 0.3,
//                                             ' ' outside); d = signed offset along the outward normal of the solid
//   foldmap edges <in.brep> <face> <d>      : per boundary edge of the face: min factor along the edge (pcurve)
#include <BRepAdaptor_Surface.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRepTopAdaptor_FClass2d.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepLProp_SLProps.hxx>
#include <GProp_GProps.hxx>
#include <Geom2d_Curve.hxx>
#include <Geom_Surface.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <TopoDS_Compound.hxx>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static TopoDS_Shape readB(const char* p)
{
  TopoDS_Shape r;
  BRep_Builder bb;
  BRepTools::Read(r, p, bb);
  return r;
}

// smallest principal factor at (u,v), d along the natural normal (caller flips for REVERSED faces)
static bool factor(const occ::handle<Geom_Surface>& S, double u, double v, double d, double& f, double& k1, double& k2)
{
  gp_Pnt P;
  gp_Vec Su, Sv, Suu, Svv, Suv;
  S->D2(u, v, P, Su, Sv, Suu, Svv, Suv);
  gp_Vec N = Su.Crossed(Sv);
  double nm = N.Magnitude();
  double E = Su.SquareMagnitude(), G = Sv.SquareMagnitude(), F = Su.Dot(Sv), den = E * G - F * F;
  if (nm < 1e-300 || den <= 0) return false;
  N.Divide(nm);
  double L = Suu.Dot(N), M = Suv.Dot(N), NN = Svv.Dot(N);
  double K = (L * NN - M * M) / den, H = (E * NN + G * L - 2 * F * M) / (2 * den);
  double disc = std::sqrt(std::max(H * H - K, 0.));
  k1 = H + disc; k2 = H - disc; // curvature along natural normal: sphere with outward normal -> -1/R
  f = std::min(1 - d * k1, 1 - d * k2);
  return true;
}

static const char* stype(const TopoDS_Face& f)
{
  static const char* n[] = {"Plane", "Cylinder", "Cone", "Sphere", "Torus", "Bezier", "BSpline", "Revolution", "Extrusion", "Offset", "Other"};
  BRepAdaptor_Surface a(f, false);
  int t = (int)a.GetType();
  return (t >= 0 && t <= 10) ? n[t] : "?";
}

static gp_Dir outNormal(const TopoDS_Face& f, const gp_Pnt2d& uv)
{
  BRepAdaptor_Surface a(f, false);
  gp_Pnt p; gp_Vec du, dv;
  a.D1(uv.X(), uv.Y(), p, du, dv);
  gp_Vec n = du.Crossed(dv);
  if (n.Magnitude() < 1e-12) return gp_Dir(0, 0, 1);
  if (f.Orientation() == TopAbs_REVERSED) n.Reverse();
  return gp_Dir(n);
}

static int faces(const char* in)
{
  TopoDS_Shape s = readB(in);
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  TopTools_IndexedDataMapOfShapeListOfShape ef;
  TopExp::MapShapesAndAncestors(s, TopAbs_EDGE, TopAbs_FACE, ef);
  for (int i = 1; i <= fm.Extent(); i++)
  {
    const TopoDS_Face& F = TopoDS::Face(fm(i));
    GProp_GProps g;
    BRepGProp::SurfaceProperties(F, g);
    gp_Pnt c = g.CentreOfMass();
    printf("F%d %s %s area=%.5g c=(%.4f %.4f %.4f)\n", i, stype(F), F.Orientation() == TopAbs_REVERSED ? "R" : "F", g.Mass(), c.X(), c.Y(), c.Z());
    for (TopExp_Explorer ex(F, TopAbs_EDGE); ex.More(); ex.Next())
    {
      const TopoDS_Edge& E = TopoDS::Edge(ex.Current());
      if (BRep_Tool::Degenerated(E)) { printf("   e deg\n"); continue; }
      const TopTools_ListOfShape& L = ef.FindFromKey(E);
      int other = 0;
      TopoDS_Face OF;
      for (TopTools_ListOfShape::Iterator it(L); it.More(); it.Next())
        if (!it.Value().IsSame(F)) { OF = TopoDS::Face(it.Value()); other = fm.FindIndex(OF); }
      double a0, a1;
      occ::handle<Geom_Curve> C = BRep_Tool::Curve(E, a0, a1);
      double tm = 0.5 * (a0 + a1);
      gp_Pnt pm = C.IsNull() ? gp_Pnt() : C->Value(tm);
      double ang = -1; int cvx = 0;
      if (!OF.IsNull() && !C.IsNull())
      {
        double b0, b1;
        occ::handle<Geom2d_Curve> c1 = BRep_Tool::CurveOnSurface(E, F, b0, b1);
        occ::handle<Geom2d_Curve> c2 = BRep_Tool::CurveOnSurface(E, OF, b0, b1);
        gp_Dir n1 = outNormal(F, c1->Value(tm)), n2 = outNormal(OF, c2->Value(tm));
        ang = n1.Angle(n2) * 180 / M_PI;
        // convexity: tangent of the edge in F, cross n1 -> points into F or out
        gp_Pnt p; gp_Vec tg;
        C->D1(tm, p, tg);
        if (E.Orientation() == TopAbs_REVERSED) tg.Reverse();
        gp_Vec inF = gp_Vec(n1).Crossed(tg); // points into the face for a FORWARD edge in a FORWARD face loop
        double sgn = inF.Dot(gp_Vec(n2));
        cvx = sgn > 1e-9 ? -1 : (sgn < -1e-9 ? 1 : 0);
      }
      printf("   e->F%d %s ang=%.2f %s mid=(%.3f %.3f %.3f)\n", other, OF.IsNull() ? "-" : stype(OF), ang,
             ang < 0 ? "" : (ang < 1 ? "tangent" : (cvx > 0 ? "convex" : (cvx < 0 ? "concave" : "?"))), pm.X(), pm.Y(), pm.Z());
    }
  }
  return 0;
}

static int map(const char* in, int fi, double d, int N)
{
  TopoDS_Shape s = readB(in);
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  const TopoDS_Face& F = TopoDS::Face(fm(fi));
  TopLoc_Location L;
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(F, L);
  double dd = F.Orientation() == TopAbs_REVERSED ? -d : d;
  double u0, u1, v0, v1;
  BRepTools::UVBounds(F, u0, u1, v0, v1);
  BRepTopAdaptor_FClass2d cls(F, 1e-7);
  printf("face F%d %s uv=[%g %g]x[%g %g] d=%g\n", fi, stype(F), u0, u1, v0, v1, d);
  double fmin = 1e30, um = 0, vm = 0, k1m = 0, k2m = 0;
  int nin = 0, nneg = 0;
  std::vector<std::string> rows;
  for (int j = N - 1; j >= 0; j--)
  {
    std::string row;
    double v = v0 + (v1 - v0) * (j + 0.5) / N;
    for (int i = 0; i < N; i++)
    {
      double u = u0 + (u1 - u0) * (i + 0.5) / N;
      if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) { row += ' '; continue; }
      double f, k1, k2;
      if (!factor(S, u, v, dd, f, k1, k2)) { row += '?'; continue; }
      nin++;
      if (f < 0) nneg++;
      if (f < fmin) { fmin = f; um = u; vm = v; k1m = k1; k2m = k2; }
      row += f < 0 ? '#' : (f < 0.3 ? '+' : '.');
    }
    rows.push_back(row);
  }
  for (auto& r : rows) printf("  |%s|\n", r.c_str());
  gp_Pnt P = S->Value(um, vm).Transformed(L.Transformation());
  printf("min factor %.4f at uv=(%g %g) xyz=(%.4f %.4f %.4f) k=(%.4f %.4f) (radius %.4f) in=%d fold=%d\n", fmin, um, vm,
         P.X(), P.Y(), P.Z(), k1m, k2m, 1 / std::max(std::abs(k1m), std::abs(k2m)), nin, nneg);
  return 0;
}

static int edges(const char* in, int fi, double d)
{
  TopoDS_Shape s = readB(in);
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  const TopoDS_Face& F = TopoDS::Face(fm(fi));
  TopLoc_Location L;
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(F, L);
  double dd = F.Orientation() == TopAbs_REVERSED ? -d : d;
  int k = 0;
  for (TopExp_Explorer ex(F, TopAbs_EDGE); ex.More(); ex.Next(), k++)
  {
    const TopoDS_Edge& E = TopoDS::Edge(ex.Current());
    double b0, b1;
    occ::handle<Geom2d_Curve> c = BRep_Tool::CurveOnSurface(E, F, b0, b1);
    if (c.IsNull()) continue;
    double fmin = 1e30; int nneg = 0;
    std::string pr;
    for (int i = 0; i <= 40; i++)
    {
      gp_Pnt2d uv = c->Value(b0 + (b1 - b0) * i / 40.);
      // step slightly inside is not needed for the factor (surface-wide), sample on the pcurve
      double f, k1, k2;
      if (!factor(S, uv.X(), uv.Y(), dd, f, k1, k2)) { pr += '?'; continue; }
      fmin = std::min(fmin, f);
      if (f < 0) nneg++;
      pr += f < 0 ? '#' : (f < 0.3 ? '+' : '.');
    }
    double a0, a1;
    occ::handle<Geom_Curve> C = BRep_Tool::Curve(E, a0, a1);
    gp_Pnt p0 = C.IsNull() ? gp_Pnt() : C->Value(a0), p1 = C.IsNull() ? gp_Pnt() : C->Value(a1);
    printf("edge %d %s len-pts (%.3f %.3f %.3f)-(%.3f %.3f %.3f) minf=%.4f neg=%d/41 %s\n", k, BRep_Tool::Degenerated(E) ? "DEG" : "",
           p0.X(), p0.Y(), p0.Z(), p1.X(), p1.Y(), p1.Z(), fmin, nneg, pr.c_str());
  }
  return 0;
}


// swallow map (TEST ORACLE ONLY): for grid points p of the face, q = p + d*N(p); '#' if dist(q, S) < |d| - tol
// (p's offset is swallowed by the rest of the solid), '.' if on the exact offset, ' ' outside the face
static int swallow(const char* in, int fi, double d, int N)
{
  TopoDS_Shape s = readB(in);
  TopTools_IndexedMapOfShape fm;
  TopExp::MapShapes(s, TopAbs_FACE, fm);
  const TopoDS_Face& F = TopoDS::Face(fm(fi));
  TopoDS_Compound shellS;
  BRep_Builder cb;
  cb.MakeCompound(shellS);
  for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next()) cb.Add(shellS, ex.Current());
  BRepExtrema_DistShapeShape dss;
  dss.LoadS2(shellS);
  BRepAdaptor_Surface a(F, true);
  double u0, u1, v0, v1;
  BRepTools::UVBounds(F, u0, u1, v0, v1);
  BRepTopAdaptor_FClass2d cls(F, 1e-7);
  int nin = 0, nsw = 0;
  std::vector<std::string> rows;
  for (int j = N - 1; j >= 0; j--)
  {
    std::string row;
    double v = v0 + (v1 - v0) * (j + 0.5) / N;
    for (int i = 0; i < N; i++)
    {
      double u = u0 + (u1 - u0) * (i + 0.5) / N;
      if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) { row += ' '; continue; }
      gp_Pnt p; gp_Vec du, dv;
      a.D1(u, v, p, du, dv);
      gp_Vec n = du.Crossed(dv);
      if (n.Magnitude() < 1e-12) { row += '?'; continue; }
      n.Normalize();
      if (F.Orientation() == TopAbs_REVERSED) n.Reverse();
      gp_Pnt q = p.Translated(n * d);
      dss.LoadS1(BRepBuilderAPI_MakeVertex(q).Vertex());
      dss.Perform();
      nin++;
      bool sw = dss.IsDone() && dss.Value() < std::abs(d) * (1 - 1e-4) - 1e-7;
      if (sw) nsw++;
      row += sw ? '#' : '.';
    }
    rows.push_back(row);
  }
  for (auto& r : rows) printf("  |%s|\n", r.c_str());
  printf("swallowed %d of %d\n", nsw, nin);
  return 0;
}

int main(int argc, char** argv)
{
  if (argc >= 3 && !strcmp(argv[1], "faces")) return faces(argv[2]);
  if (argc >= 5 && !strcmp(argv[1], "map")) return map(argv[2], atoi(argv[3]), atof(argv[4]), argc > 5 ? atoi(argv[5]) : 40);
  if (argc >= 5 && !strcmp(argv[1], "edges")) return edges(argv[2], atoi(argv[3]), atof(argv[4]));
  if (argc >= 5 && !strcmp(argv[1], "swallow")) return swallow(argv[2], atoi(argv[3]), atof(argv[4]), argc > 5 ? atoi(argv[5]) : 30);
  printf("usage\n");
  return 1;
}
