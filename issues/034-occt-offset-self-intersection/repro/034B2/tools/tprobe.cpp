// tprobe.cpp <in.brep> <t> <faceIdx|largest> <out.brep> : MakeThickSolidByJoin, dump MakeOffset().Shape() even when not done
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <GeomLib_IsPlanarSurface.hxx>
#include <BRep_Tool.hxx>
#include <cstdio>
#include <cstdlib>
#include <cstring>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b; BRepTools::Read(s, argv[1], b);
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
  int k = atoi(argv[3]);
  if (!strcmp(argv[3], "largest"))
  {
    double ba = -1;
    for (int i = 1; i <= fm.Extent(); i++) { TopLoc_Location L; GeomLib_IsPlanarSurface pl(BRep_Tool::Surface(TopoDS::Face(fm(i)), L), 1e-7); if (!pl.IsPlanar()) continue; GProp_GProps g; BRepGProp::SurfaceProperties(fm(i), g); if (g.Mass() > ba * (1 + 1e-6)) { ba = g.Mass(); k = i; } }
  }
  NCollection_List<TopoDS_Shape> cl; cl.Append(fm(k));
  BRepOffsetAPI_MakeThickSolid mk;
  mk.MakeThickSolidByJoin(s, cl, atof(argv[2]), 1e-7, BRepOffset_Skin, false, false, GeomAbs_Arc);
  const TopoDS_Shape& r = mk.MakeOffset().Shape();
  int nf = 0, ns = 0, nsh = 0; for (TopExp_Explorer e(r, TopAbs_FACE); e.More(); e.Next()) nf++;
  for (TopExp_Explorer e(r, TopAbs_SHELL); e.More(); e.Next()) nsh++;
  for (TopExp_Explorer e(r, TopAbs_SOLID); e.More(); e.Next()) ns++;
  printf("done=%d err=%d type=%d nf=%d shells=%d solids=%d inputFaces=%d\n", (int)mk.IsDone(), (int)mk.MakeOffset().Error(), r.IsNull() ? -1 : (int)r.ShapeType(), nf, nsh, ns, fm.Extent());
  if (!r.IsNull()) BRepTools::Write(r, argv[4]);
  return 0;
}
