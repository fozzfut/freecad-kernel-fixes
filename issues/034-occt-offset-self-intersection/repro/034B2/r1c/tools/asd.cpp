// asd.cpp <asdes.brep> : per (face + descendant edges) compound: face centroid/type/uv box/surface bounds, each edge: ends, pcurve on face?
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <Geom_Surface.hxx>
#include <TopoDS_Iterator.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Vertex.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; BRepTools::Read(s, argv[1], b);
  int k = 0;
  for (TopoDS_Iterator it(s); it.More(); it.Next())
  {
    k++; TopoDS_Face F; int ne = 0;
    for (TopoDS_Iterator j(it.Value()); j.More(); j.Next()) if (j.Value().ShapeType() == TopAbs_FACE) F = TopoDS::Face(j.Value());
    GProp_GProps g; BRepGProp::SurfaceProperties(F, g); gp_Pnt c = g.CentreOfMass();
    TopLoc_Location L; auto S = BRep_Tool::Surface(F, L); double a0,a1,b0,b1,u0,u1,v0,v1; S->Bounds(a0,a1,b0,b1); BRepTools::UVBounds(F,u0,u1,v0,v1);
    printf("C%d face type=%d c=(%.3f %.3f %.3f) area=%.3f uv=[%.3g,%.3g]x[%.3g,%.3g] surf=[%.3g,%.3g]x[%.3g,%.3g]\n", k, (int)GeomAdaptor_Surface(S).GetType(), c.X(), c.Y(), c.Z(), g.Mass(), u0,u1,v0,v1,a0,a1,b0,b1);
    for (TopoDS_Iterator j(it.Value()); j.More(); j.Next())
    {
      if (j.Value().ShapeType() != TopAbs_EDGE) continue;
      const TopoDS_Edge& E = TopoDS::Edge(j.Value()); TopoDS_Vertex V1, V2; TopExp::Vertices(E, V1, V2);
      double f, l; auto pc = BRep_Tool::CurveOnSurface(E, F, f, l);
      gp_Pnt p1 = V1.IsNull() ? gp_Pnt() : BRep_Tool::Pnt(V1), p2 = V2.IsNull() ? gp_Pnt() : BRep_Tool::Pnt(V2);
      printf("   e%d ori=%d (%.3f %.3f %.3f)-(%.3f %.3f %.3f) pc=%d tol=%.1e\n", ++ne, (int)E.Orientation(), p1.X(),p1.Y(),p1.Z(),p2.X(),p2.Y(),p2.Z(), pc.IsNull()?0:1, BRep_Tool::Tolerance(E));
    }
  }
  return 0;
}
