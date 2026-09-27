// probe.cpp - issue 034 lane: M4 anatomy + curvature sign check
//   probe m4 <in> <t> <removeIdx|largest> : MakeOffsetShape with closing faces -> offset shell anatomy
//   probe curv <in> <faceIdx> <u> <v>      : GeomLProp_SLProps curvatures + D2-based factors
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepBuilderAPI_NurbsConvert.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepGProp.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepTools.hxx>
#include <BRepTopAdaptor_FClass2d.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <GeomLProp_SLProps.hxx>
#include <Geom_Plane.hxx>
#include <Geom_Surface.hxx>
#include <STEPControl_Reader.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <cstdio>
#include <cstring>
#include <string>
static TopoDS_Shape readAny(const char* p)
{
  std::string s(p); TopoDS_Shape r;
  if (s.size() > 5 && (s.substr(s.size() - 5) == ".step" || s.substr(s.size() - 4) == ".stp"))
  { STEPControl_Reader rd; if (rd.ReadFile(p) != IFSelect_RetDone) return r; rd.TransferRoots(); r = rd.OneShape(); }
  else { BRep_Builder bb; BRepTools::Read(r, p, bb); }
  if (r.IsNull() || r.ShapeType() == TopAbs_SOLID) return r;
  double best = -1; TopoDS_Shape bs;
  for (TopExp_Explorer ex(r, TopAbs_SOLID); ex.More(); ex.Next())
  { GProp_GProps g; BRepGProp::VolumeProperties(ex.Current(), g); if (std::abs(g.Mass()) > best) { best = std::abs(g.Mass()); bs = ex.Current(); } }
  return bs.IsNull() ? r : bs;
}
static int largestPlane(const TopTools_IndexedMapOfShape& fm)
{
  int of = 0; double best = -1.;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    const TopoDS_Face& f = TopoDS::Face(fm(k));
    if (occ::handle<Geom_Plane>::DownCast(BRep_Tool::Surface(f)).IsNull()) continue;
    GProp_GProps g; BRepGProp::SurfaceProperties(f, g);
    if (g.Mass() > best + 1e-9) { best = g.Mass(); of = k; }
  }
  return of;
}

#include <GeomAdaptor_Surface.hxx>
#include <Geom_BSplineSurface.hxx>
static bool fct(const Geom_Surface& S, double u, double v, double d, double& f, double& su, double& sv)
{
  gp_Pnt P; gp_Vec Su, Sv, Suu, Svv, Suv;
  S.D2(u, v, P, Su, Sv, Suu, Svv, Suv);
  gp_Vec N = Su.Crossed(Sv); double nm = N.Magnitude(); double E = Su.SquareMagnitude(), G = Sv.SquareMagnitude(), F = Su.Dot(Sv);
  double den = E * G - F * F; su = sqrt(E); sv = sqrt(G);
  if (nm < 1e-300 || nm <= 1e-9 * sqrt(E * G) || den <= 0) return false;
  N.Divide(nm);
  double L = Suu.Dot(N), M = Suv.Dot(N), NN = Svv.Dot(N);
  double K = (L * NN - M * M) / den, H = (E * NN + G * L - 2 * F * M) / (2 * den);
  double disc = sqrt(std::max(H * H - K, 0.));
  f = std::min(1 - d * (H + disc), 1 - d * (H - disc));
  return true;
}
static int foldcmd(const char* in, double t)
{
  TopoDS_Shape s = readAny(in); TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
  for (int k = 1; k <= fm.Extent(); k++)
  {
    const TopoDS_Face& F = TopoDS::Face(fm(k));
    occ::handle<Geom_Surface> S = BRep_Tool::Surface(F);
    GeomAdaptor_Surface gas(S); if (gas.GetType() == GeomAbs_Plane) continue;
    double d = F.Orientation() == TopAbs_REVERSED ? -t : t;
    double u0, u1, v0, v1; BRepTools::UVBounds(F, u0, u1, v0, v1);
    int n = 16; double mn = 1e30, mu = 0, mv = 0, msu = 0, msv = 0; int bad = 0;
    for (int i = 0; i <= n; i++) for (int j = 0; j <= n; j++)
    {
      double u = u0 + (u1 - u0) * i / n, v = v0 + (v1 - v0) * j / n, f, su, sv;
      if (!fct(*S, u, v, d, f, su, sv)) { bad++; continue; }
      if (f < mn) { mn = f; mu = (double)i / n; mv = (double)j / n; msu = su; msv = sv; }
    }
    printf("face %d %s d=%g min=%g at (%.3f,%.3f) |Su|=%.3g |Sv|=%.3g singular=%d\n", k, S->DynamicType()->Name(), d, mn, mu, mv, msu, msv, bad);
  }
  return 0;
}

#include <BOPAlgo_CheckerSI.hxx>
#include <BOPDS_DS.hxx>
static int bopdetail(const char* in)
{
  BRep_Builder bb; TopoDS_Shape s; BRepTools::Read(s, in, bb);
  BOPAlgo_CheckerSI ch; NCollection_List<TopoDS_Shape> a; a.Append(s); ch.SetArguments(a); ch.SetNonDestructive(true);
  ch.Perform();
  const BOPDS_DS& ds = *ch.PDS();
  static const char* T[] = {"COMPOUND","COMPSOLID","SOLID","SHELL","FACE","WIRE","EDGE","VERTEX","SHAPE"};
  int n = 0;
  for (NCollection_Map<BOPDS_Pair>::Iterator it(ds.Interferences()); it.More(); it.Next())
  {
    int i1, i2; it.Value().Indices(i1, i2);
    if (ds.IsNewShape(i1) || ds.IsNewShape(i2)) continue;
    const TopoDS_Shape &a1 = ds.Shape(i1), &a2 = ds.Shape(i2);
    BRepExtrema_DistShapeShape d(a1, a2);
    double t1 = a1.ShapeType()==TopAbs_VERTEX ? BRep_Tool::Tolerance(TopoDS::Vertex(a1)) : a1.ShapeType()==TopAbs_EDGE ? BRep_Tool::Tolerance(TopoDS::Edge(a1)) : a1.ShapeType()==TopAbs_FACE ? BRep_Tool::Tolerance(TopoDS::Face(a1)) : 0;
    double t2 = a2.ShapeType()==TopAbs_VERTEX ? BRep_Tool::Tolerance(TopoDS::Vertex(a2)) : a2.ShapeType()==TopAbs_EDGE ? BRep_Tool::Tolerance(TopoDS::Edge(a2)) : a2.ShapeType()==TopAbs_FACE ? BRep_Tool::Tolerance(TopoDS::Face(a2)) : 0;
    printf("PAIR %s/%s dist=%.3g tol1=%.3g tol2=%.3g\n", T[a1.ShapeType()], T[a2.ShapeType()], d.IsDone() ? d.Value() : -1, t1, t2);
    n++;
  }
  printf("pairs=%d hasErrors=%d\n", n, (int)ch.HasErrors());
  return 0;
}

int main(int argc, char** argv)
{
  if (argc >= 3 && !strcmp(argv[1], "bopdetail")) return bopdetail(argv[2]);
  if (argc >= 4 && !strcmp(argv[1], "fold")) return foldcmd(argv[2], atof(argv[3]));
  if (argc >= 3 && !strcmp(argv[1], "gen2"))
  {
    std::string d = argv[2];
    BRepTools::Write(BRepPrimAPI_MakeBox(20, 30, 5).Shape(), (d + "/box20x30x5.brep").c_str());
    BRepTools::Write(BRepPrimAPI_MakeCylinder(5, 12).Shape(), (d + "/cyl_r5.brep").c_str());
    BRepTools::Write(BRepPrimAPI_MakeSphere(4).Shape(), (d + "/sphere_r4.brep").c_str());
    TopoDS_Shape b = BRepPrimAPI_MakeBox(20, 20, 10).Shape();
    BRepFilletAPI_MakeFillet mf(b);
    for (TopExp_Explorer ex(b, TopAbs_EDGE); ex.More(); ex.Next()) mf.Add(2.0, TopoDS::Edge(ex.Current()));
    mf.Build();
    BRepTools::Write(mf.Shape(), (d + "/box_fillet_r2.brep").c_str());
    BRepTools::Write(BRepBuilderAPI_NurbsConvert(mf.Shape()).Shape(), (d + "/box_fillet_r2_nurbs.brep").c_str());
    printf("gen2 ok\n");
    return 0;
  }
  if (argc >= 6 && !strcmp(argv[1], "curv"))
  {
    TopoDS_Shape s = readAny(argv[2]); TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
    const TopoDS_Face& f = TopoDS::Face(fm(atoi(argv[3])));
    occ::handle<Geom_Surface> S = BRep_Tool::Surface(f);
    double u0, u1, v0, v1; BRepTools::UVBounds(f, u0, u1, v0, v1);
    const double u = u0 + (u1 - u0) * atof(argv[4]), v = v0 + (v1 - v0) * atof(argv[5]);
    GeomLProp_SLProps pr(S, u, v, 2, 1e-9);
    printf("%s ori=%d defined=%d kmin=%g kmax=%g N=(%g,%g,%g) P=(%g,%g,%g)\n", S->DynamicType()->Name(), (int)f.Orientation(),
           (int)pr.IsCurvatureDefined(), pr.MinCurvature(), pr.MaxCurvature(), pr.Normal().X(), pr.Normal().Y(), pr.Normal().Z(),
           pr.Value().X(), pr.Value().Y(), pr.Value().Z());
    return 0;
  }
  if (argc < 5) return 2;
  TopoDS_Shape s = readAny(argv[2]); const double t = atof(argv[3]);
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
  int rk = !strcmp(argv[4], "largest") ? largestPlane(fm) : atoi(argv[4]);
  BRepOffset_MakeOffset mo; mo.Initialize(s, t, 1e-7, BRepOffset_Skin, false, false, GeomAbs_Arc, false, false);
  mo.AddFace(TopoDS::Face(fm(rk)));
  mo.MakeOffsetShape();
  printf("removed=%d done=%d err=%d\n", rk, (int)mo.IsDone(), (int)mo.Error());
  const TopoDS_Shape& os = mo.Shape();
  if (os.IsNull()) { printf("null\n"); return 0; }
  TopoDS_Compound bnd; BRep_Builder cb; cb.MakeCompound(bnd);
  for (int k = 1; k <= fm.Extent(); k++) cb.Add(bnd, fm(k));
  int nf = 0;
  for (TopExp_Explorer ex(os, TopAbs_FACE); ex.More(); ex.Next())
  {
    nf++;
    const TopoDS_Face& f = TopoDS::Face(ex.Current());
    int same = 0; for (int k = 1; k <= fm.Extent(); k++) if (fm(k).IsSame(f)) same = k;
    occ::handle<Geom_Surface> S = BRep_Tool::Surface(f);
    double u0, u1, v0, v1; BRepTools::UVBounds(f, u0, u1, v0, v1);
    BRepTopAdaptor_FClass2d cls(f, 1e-9);
    double dmin = 1e30, dmax = -1;
    for (int i = 1; i < 5; i++) for (int j = 1; j < 5; j++)
    {
      const double u = u0 + (u1 - u0) * i / 5, v = v0 + (v1 - v0) * j / 5;
      if (cls.Perform(gp_Pnt2d(u, v)) != TopAbs_IN) continue;
      BRepExtrema_DistShapeShape d(BRepBuilderAPI_MakeVertex(S->Value(u, v)).Vertex(), bnd);
      if (!d.IsDone()) continue;
      dmin = std::min(dmin, d.Value()); dmax = std::max(dmax, d.Value());
    }
    printf("  face %d %s sameAsInput=%d d=[%.4g,%.4g]\n", nf, S->DynamicType()->Name(), same, dmin, dmax);
  }
  printf("offset shell faces=%d input faces=%d\n", nf, fm.Extent());
  return 0;
}
