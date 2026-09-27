// bopinfo <in.brep> : BRepCheck verdict + BOPAlgo_ArgumentAnalyzer faults with the faces involved (type, area, centre)
#include "memcap.hxx"
#include <BOPAlgo_ArgumentAnalyzer.hxx>
#include <BOPAlgo_CheckResult.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Edge.hxx>
#include <cstdio>
static void desc(const TopoDS_Shape& s, const TopTools_IndexedMapOfShape& fm, const TopTools_IndexedMapOfShape& em)
{
  GProp_GProps g;
  if (s.ShapeType() == TopAbs_FACE)
  {
    BRepGProp::SurfaceProperties(s, g);
    BRepAdaptor_Surface a(TopoDS::Face(s), false);
    printf("   F%d type=%d area=%.3g c=(%.4f %.4f %.4f)\n", fm.FindIndex(s), (int)a.GetType(), g.Mass(), g.CentreOfMass().X(), g.CentreOfMass().Y(), g.CentreOfMass().Z());
  }
  else if (s.ShapeType() == TopAbs_EDGE)
  {
    BRepGProp::LinearProperties(s, g);
    printf("   E%d len=%.3g tol=%.2g c=(%.4f %.4f %.4f)\n", em.FindIndex(s), g.Mass(), BRep_Tool::Tolerance(TopoDS::Edge(s)), g.CentreOfMass().X(), g.CentreOfMass().Y(), g.CentreOfMass().Z());
  }
  else printf("   type %d\n", (int)s.ShapeType());
}
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder bb; BRepTools::Read(s, argv[1], bb);
  TopTools_IndexedMapOfShape fm, em;
  TopExp::MapShapes(s, TopAbs_FACE, fm); TopExp::MapShapes(s, TopAbs_EDGE, em);
  BRepCheck_Analyzer ca(s);
  printf("valid=%d faces=%d edges=%d\n", (int)ca.IsValid(), fm.Extent(), em.Extent());
  BOPAlgo_ArgumentAnalyzer an;
  an.SetShape1(s);
  an.SelfInterMode() = true; an.SmallEdgeMode() = true; an.ArgumentTypeMode() = true; an.RebuildFaceMode() = true;
  an.TangentMode() = true; an.MergeVertexMode() = true; an.MergeEdgeMode() = true; an.ContinuityMode() = true; an.CurveOnSurfaceMode() = true;
  an.Perform();
  for (const BOPAlgo_CheckResult& r : an.GetCheckResult())
  {
    printf("status %d\n", (int)r.GetCheckStatus());
    for (NCollection_List<TopoDS_Shape>::Iterator it(r.GetFaultyShapes1()); it.More(); it.Next()) desc(it.Value(), fm, em);
  }
  return 0;
}
