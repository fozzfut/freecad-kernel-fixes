// insp.cpp <in.brep> : faces (type, area, centroid, #wires, #edges) + free-edge count of the whole shape
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <GeomAdaptor_Surface.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <TopoDS.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; BRepTools::Read(s, argv[1], b);
  int k = 0;
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next())
  {
    k++; GProp_GProps g; BRepGProp::SurfaceProperties(e.Current(), g);
    TopLoc_Location L; GeomAdaptor_Surface ga(BRep_Tool::Surface(TopoDS::Face(e.Current()), L));
    int nw = 0, ne = 0; for (TopExp_Explorer w(e.Current(), TopAbs_WIRE); w.More(); w.Next()) nw++;
    for (TopExp_Explorer w(e.Current(), TopAbs_EDGE); w.More(); w.Next()) ne++;
    printf("F%d type=%d ori=%d area=%.4f c=(%.3f %.3f %.3f) wires=%d edges=%d\n", k, (int)ga.GetType(), (int)e.Current().Orientation(), g.Mass(), g.CentreOfMass().X(), g.CentreOfMass().Y(), g.CentreOfMass().Z(), nw, ne);
  }
  TopTools_IndexedDataMapOfShapeListOfShape m; TopExp::MapShapesAndAncestors(s, TopAbs_EDGE, TopAbs_FACE, m);
  int fr = 0; for (int i = 1; i <= m.Extent(); i++) if (m(i).Extent() == 1 && !BRep_Tool::Degenerated(TopoDS::Edge(m.FindKey(i)))) fr++;
  printf("edges=%d free=%d\n", m.Extent(), fr);
  return 0;
}
