// edg.cpp <compound.brep> : lists faces (bbox) and edges (ends, orientation, length) of a compound (lane B2 r2 debugging)
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepBndLib.hxx>
#include <Bnd_Box.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Iterator.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <cstdio>
static void dump(const TopoDS_Shape& s, int lvl)
{
  if (s.ShapeType() == TopAbs_COMPOUND) { for (TopoDS_Iterator it(s); it.More(); it.Next()) dump(it.Value(), lvl + 1); return; }
  if (s.ShapeType() == TopAbs_FACE)
  {
    Bnd_Box b; BRepBndLib::Add(s, b, false); double a, c, d, e, f, g; b.Get(a, c, d, e, f, g);
    int ne = 0; for (TopExp_Explorer x(s, TopAbs_EDGE); x.More(); x.Next()) ne++;
    printf("FACE ori=%d box=(%.3f %.3f %.3f)-(%.3f %.3f %.3f) edges=%d\n", (int)s.Orientation(), a, c, d, e, f, g, ne);
    return;
  }
  if (s.ShapeType() == TopAbs_EDGE)
  {
    const TopoDS_Edge& E = TopoDS::Edge(s);
    double f, l; BRep_Tool::Range(E, f, l);
    TopoDS_Vertex v1, v2; TopExp::Vertices(E, v1, v2);
    gp_Pnt p1 = v1.IsNull() ? gp_Pnt(1e9, 0, 0) : BRep_Tool::Pnt(v1), p2 = v2.IsNull() ? gp_Pnt(1e9, 0, 0) : BRep_Tool::Pnt(v2);
    double len = -1; try { BRepAdaptor_Curve c(E); len = GCPnts_AbscissaPoint::Length(c); } catch (...) {}
    printf("  EDGE ori=%d (%.3f %.3f %.3f)->(%.3f %.3f %.3f) len=%.3f tol=%.1e\n", (int)E.Orientation(), p1.X(), p1.Y(), p1.Z(), p2.X(), p2.Y(), p2.Z(), len, BRep_Tool::Tolerance(E));
    return;
  }
  for (TopoDS_Iterator it(s); it.More(); it.Next()) dump(it.Value(), lvl + 1);
}
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; if (!BRepTools::Read(s, argv[1], b)) { puts("READ-FAIL"); return 1; }
  dump(s, 0); return 0;
}
