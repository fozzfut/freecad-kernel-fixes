// thkdiag <in.brep> <t> [out.brep]: PartDesign-like thickness (largest plane open, Skin, Arc) of a solid, then
// BRepCheck + BRepAlgoAPI_Check of the result; prints each BOP fault (status, shape type, centre) and every
// BRepCheck-invalid sub-shape centre, so a fault can be placed (at the fillet corner or elsewhere).
#include "down3.hxx"
#include <BRep_Builder.hxx>
#include <BRepCheck_ListOfStatus.hxx>
#include <BRepCheck_Result.hxx>
#include <BOPAlgo_Alerts.hxx>
#include <Bnd_Box.hxx>
#include <BRepBndLib.hxx>

static void ctr(const TopoDS_Shape& s, char* b)
{
  Bnd_Box bx;
  BRepBndLib::Add(s, bx);
  if (bx.IsVoid()) { sprintf(b, "(void)"); return; }
  double x0, y0, z0, x1, y1, z1;
  bx.Get(x0, y0, z0, x1, y1, z1);
  sprintf(b, "(%.3f,%.3f,%.3f) size %.3f", (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2,
          std::max(x1 - x0, std::max(y1 - y0, z1 - z0)));
}

int main(int argc, char** argv)
{
  TopoDS_Shape s;
  BRep_Builder bb;
  if (!BRepTools::Read(s, argv[1], bb)) { printf("READ-FAIL\n"); return 3; }
  const double t = atof(argv[2]);
  TopTools_IndexedMapOfShape fm;
  const int of = down3::largestPlane(s, fm);
  NCollection_List<TopoDS_Shape> cl;
  cl.Append(fm(of));
  BRepOffsetAPI_MakeThickSolid mk;
  mk.MakeThickSolidByJoin(s, cl, t, 1.e-7, BRepOffset_Skin, false, false, GeomAbs_Arc);
  if (!mk.IsDone()) { printf("THK ERR %d\n", (int)mk.MakeOffset().Error()); return 0; }
  const TopoDS_Shape r = mk.Shape();
  if (argc > 3) BRepTools::Write(r, argv[3]);
  printf("THK done grade=%s\n", down3::grade(r).c_str());
  BRepCheck_Analyzer an(r);
  for (const TopAbs_ShapeEnum ty : {TopAbs_VERTEX, TopAbs_EDGE, TopAbs_WIRE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID})
  {
    TopTools_IndexedMapOfShape m;
    TopExp::MapShapes(r, ty, m);
    for (int k = 1; k <= m.Extent(); k++)
    {
      const occ::handle<BRepCheck_Result>& res = an.Result(m(k));
      if (res.IsNull()) continue;
      bool bad = false;
      for (res->InitContextIterator(); res->MoreShapeInContext(); res->NextShapeInContext())
        for (const BRepCheck_Status st : res->StatusOnShape())
          if (st != BRepCheck_NoError) { bad = true; }
      for (const BRepCheck_Status st : res->Status())
        if (st != BRepCheck_NoError) bad = true;
      if (bad) { char b[128]; ctr(m(k), b); printf("  INVALID type %d %s\n", (int)ty, b); }
    }
  }
  BRepAlgoAPI_Check ck(r);
  for (const BOPAlgo_CheckResult& cr : ck.Result())
  {
    char b1[128] = "", b2[128] = "";
    if (!cr.GetShape1().IsNull()) ctr(cr.GetShape1(), b1);
    NCollection_List<TopoDS_Shape>::Iterator it(cr.GetFaultyShapes1());
    if (it.More()) ctr(it.Value(), b2);
    printf("  BOP status %d s1 type %d %s fault %s\n", (int)cr.GetCheckStatus(),
           cr.GetShape1().IsNull() ? -1 : (int)cr.GetShape1().ShapeType(), b1, b2);
  }
  return 0;
}
