p = 'C:/dev/occt8-mig/offset-034b/tools/e3.cpp'
s = open('C:/dev/occt8-mig/offset-034b/tools/e2.cpp').read()
s = s.replace("// e2.cpp - issue 034 stage B experiment E2",
              "// e3.cpp - issue 034 stage B experiment E3 (E2 + inverted parts of the raw faces removed before the arrangement)\n// e2.cpp - issue 034 stage B experiment E2", 1)
gen = r'''
#include <GeomAPI_ProjectPointOnCurve.hxx>
// raw face of the stock offset with the shape it was generated from (face -> offset face, edge -> tube, vertex -> ball)
struct RawGen034b
{
  int          type = 0; // 0 none, 1 face, 2 edge, 3 vertex
  TopoDS_Shape gen;
};
static double g_t = 0; // signed offset of the run

// true if the raw face is inverted at (u,v): its offset map has a negative principal factor there
static bool invertedAt(const TopoDS_Face& RF, const RawGen034b& g, double u, double v)
{
  TopLoc_Location L;
  occ::handle<Geom_Surface> S = BRep_Tool::Surface(RF, L);
  occ::handle<Geom_Surface> B = S;
  if (auto rt = occ::down_cast<Geom_RectangularTrimmedSurface>(B)) B = rt->BasisSurface();
  if (auto os = occ::down_cast<Geom_OffsetSurface>(B))
  {
    double f;
    return factor(os->BasisSurface(), u, v, os->Offset(), f) && f < 0;
  }
  if (g.type == 0 || g.type == 3) return false;
  if (GeomAdaptor_Surface(B).GetType() == GeomAbs_Plane && g.type == 1) return false;
  gp_Pnt P; gp_Vec du, dv;
  S->D1(u, v, P, du, dv);
  gp_Vec n = du.Crossed(dv);
  if (n.Magnitude() < 1e-12) return true; // singular point of the raw surface: treat as fold
  n.Transform(L.Transformation());
  P.Transform(L.Transformation());
  if (RF.Orientation() == TopAbs_REVERSED) n.Reverse();
  if (g.type == 2)
  {
    double a0, a1;
    TopLoc_Location EL;
    occ::handle<Geom_Curve> C = BRep_Tool::Curve(TopoDS::Edge(g.gen), EL, a0, a1);
    if (C.IsNull()) return false;
    gp_Pnt Pl = P.Transformed(EL.Transformation().Inverted());
    GeomAPI_ProjectPointOnCurve pc(Pl, C, a0, a1);
    if (!pc.NbPoints()) return false;
    gp_Pnt c = pc.NearestPoint().Transformed(EL.Transformation());
    return n.Dot(gp_Vec(c, P)) < 0;
  }
  // face generator, surface not an offset surface: compare with the generator normal at the projection
  const TopoDS_Face& GF = TopoDS::Face(g.gen);
  TopLoc_Location GL;
  occ::handle<Geom_Surface> GS = BRep_Tool::Surface(GF, GL);
  GeomAPI_ProjectPointOnSurf pr(P.Transformed(GL.Transformation().Inverted()), GS);
  if (!pr.NbPoints()) return false;
  double gu, gv;
  pr.LowerDistanceParameters(gu, gv);
  gp_Pnt q; gp_Vec gu1, gv1;
  GS->D1(gu, gv, q, gu1, gv1);
  gp_Vec N = gu1.Crossed(gv1);
  N.Transform(GL.Transformation());
  if (GF.Orientation() == TopAbs_REVERSED) N.Reverse();
  return n.Dot(N) * (g_t > 0 ? 1 : -1) < 0;
}

// share of inverted samples over an (n+1) x (n+1) grid of the face (-1: none sampled)
static double invertedShare(const TopoDS_Face& F, const RawGen034b& g, int n)
{
  double u0, u1, v0, v1;
  BRepTools::UVBounds(F, u0, u1, v0, v1);
  BRepTopAdaptor_FClass2d cls(F, 1e-9);
  int in = 0, inv = 0;
  for (int i = 0; i <= n; i++)
    for (int j = 0; j <= n; j++)
    {
      double u = u0 + (u1 - u0) * (0.02 + 0.96 * i / n), v = v0 + (v1 - v0) * (0.02 + 0.96 * j / n);
      TopAbs_State st = cls.Perform(gp_Pnt2d(u, v));
      if (st == TopAbs_OUT) continue;
      in++;
      if (invertedAt(F, g, u, v)) inv++;
    }
  return in ? double(inv) / in : -1;
}
'''
s = s.replace("struct SelfUnion034b\n", gen + "\nstruct SelfUnion034b\n", 1)
a = s.index("static SelfUnion034b selfUnion(const TopoDS_Shape& raw, int N)")
b = s.index("  out.nPieces = (int)pieces.size();")
newpieces = r'''static SelfUnion034b selfUnion(const TopoDS_Shape& raw, int N,
                               const NCollection_IndexedDataMap<TopoDS_Shape, RawGen034b, TopTools_ShapeMapHasher>& gens)
{
  SelfUnion034b out;
  // 1. pieces: inverted parts of the raw faces are removed (they never bound the offset)
  std::vector<TopoDS_Face> pieces;
  int nDrop = 0, nWhole = 0;
  for (TopExp_Explorer ex(raw, TopAbs_FACE); ex.More(); ex.Next())
  {
    TopoDS_Face F = TopoDS::Face(ex.Current());
    RawGen034b g;
    if (gens.Contains(F)) g = gens.FindFromKey(F);
    double sh = invertedShare(F, g, 16);
    if (sh <= 0) { pieces.push_back(F); continue; }
    out.nFold++;
    if (sh >= 1.0) { nWhole++; continue; }
    occ::handle<GridSplit034b> gs = new GridSplit034b();
    gs->N = N;
    ShapeUpgrade_FaceDivide fd(F);
    fd.SetSplitSurfaceTool(gs);
    fd.Perform();
    TopoDS_Shape r = fd.Result();
    for (TopExp_Explorer e2(r, TopAbs_FACE); e2.More(); e2.Next())
    {
      TopoDS_Face sf = TopoDS::Face(e2.Current());
      if (invertedShare(sf, g, 6) > 0) { nDrop++; continue; }
      pieces.push_back(sf);
    }
  }
  out.msg += "whole=" + std::to_string(nWhole) + " dropSub=" + std::to_string(nDrop) + " ";
'''
s = s[:a] + newpieces + s[b:]
s = s.replace('''  TopoDS_Shape r0 = runOffset(s, cl, thick, t, join, done, err, exc);''',
              '''  NCollection_IndexedDataMap<TopoDS_Shape, RawGen034b, TopTools_ShapeMapHasher> gens;
  g_t = t;
  TopoDS_Shape r0 = runOffset(s, cl, thick, t, join, done, err, exc, &gens);''')
s = s.replace('''static TopoDS_Shape runOffset(const TopoDS_Shape& s, const NCollection_List<TopoDS_Shape>& cl, bool thick, double t,
                              GeomAbs_JoinType join, int& done, int& err, std::string& exc)''', '''static void collectGens(BRepOffset_MakeOffset& mo, const TopoDS_Shape& s,
                        NCollection_IndexedDataMap<TopoDS_Shape, RawGen034b, TopTools_ShapeMapHasher>* gens)
{
  if (!gens) return;
  const TopAbs_ShapeEnum ty[3] = {TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX};
  for (int k = 0; k < 3; k++)
  {
    TopTools_IndexedMapOfShape m;
    TopExp::MapShapes(s, ty[k], m);
    for (int i = 1; i <= m.Extent(); i++)
    {
      const NCollection_List<TopoDS_Shape>& L = mo.Generated(m(i));
      for (NCollection_List<TopoDS_Shape>::Iterator it(L); it.More(); it.Next())
      {
        if (it.Value().ShapeType() != TopAbs_FACE || gens->Contains(it.Value())) continue;
        RawGen034b g;
        g.type = k + 1;
        g.gen = m(i);
        gens->Add(it.Value(), g);
      }
    }
  }
}

static TopoDS_Shape runOffset(const TopoDS_Shape& s, const NCollection_List<TopoDS_Shape>& cl, bool thick, double t,
                              GeomAbs_JoinType join, int& done, int& err, std::string& exc,
                              NCollection_IndexedDataMap<TopoDS_Shape, RawGen034b, TopTools_ShapeMapHasher>* gens = nullptr)''')
cnt = s.count('''      done = mk.IsDone(); err = (int)mk.MakeOffset().Error();
      if (done) r = mk.Shape();''')
assert cnt == 2, cnt
s = s.replace('''      done = mk.IsDone(); err = (int)mk.MakeOffset().Error();
      if (done) r = mk.Shape();''', '''      done = mk.IsDone(); err = (int)mk.MakeOffset().Error();
      if (done) { r = mk.Shape(); collectGens(mk.MakeOffset(), s, gens); }''')
s = s.replace("try { su = selfUnion(r0, N); }", "try { su = selfUnion(r0, N, gens); }")
s = s.replace('"/" + tag + "_union.brep"', '"/" + tag + "_e3.brep"')
open(p, 'w').write(s)
print("ok")
