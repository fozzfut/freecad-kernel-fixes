// locprobe.cpp <brep> [t as|twin [largest]] : located-face census of an input; optional offset (Arc, Skin,
//   PerformByJoin like off034). twin = locations baked into a geometry copy (BRepBuilderAPI_Transform copy):
//   whole input -> every child of the root baked; largest -> the largest solid (off034 corpus input) baked.
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS_Compound.hxx>
#include <TopoDS_Iterator.hxx>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main(int argc, char** argv)
{
  TopoDS_Shape s;
  BRep_Builder b;
  if (argc < 2 || !BRepTools::Read(s, argv[1], b))
  {
    printf("PROBE read-failed\n");
    return 1;
  }
  int nf = 0, nl = 0, nsub = 0;
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next())
  {
    nf++;
    if (!e.Current().Location().IsIdentity())
      nl++;
  }
  for (TopoDS_Iterator it(s, false, false); it.More(); it.Next())
    if (!it.Value().Location().IsIdentity())
      nsub++;
  printf("PROBE type=%d rootLoc=%d faces=%d locatedFaces=%d locatedChildren=%d\n", (int)s.ShapeType(),
         s.Location().IsIdentity() ? 0 : 1, nf, nl, nsub);
  if (argc < 4)
    return 0;
  const bool twin    = !strcmp(argv[3], "twin");
  const bool largest = argc >= 5 && !strcmp(argv[4], "largest");
  if (largest)
  {
    double       best = -1;
    TopoDS_Shape bs;
    for (TopExp_Explorer ex(s, TopAbs_SOLID); ex.More(); ex.Next())
    {
      GProp_GProps g;
      BRepGProp::VolumeProperties(ex.Current(), g);
      if (std::abs(g.Mass()) > best)
      {
        best = std::abs(g.Mass());
        bs   = ex.Current();
      }
    }
    s = bs;
    printf("PROBE largest rootLoc=%d vol=%.4f\n", s.Location().IsIdentity() ? 0 : 1, best);
    if (twin)
    {
      gp_Trsf T = s.Location().Transformation();
      s         = BRepBuilderAPI_Transform(s.Located(TopLoc_Location()), T, true).Shape();
    }
  }
  else if (twin)
  {
    TopoDS_Compound c;
    b.MakeCompound(c);
    for (TopoDS_Iterator it(s); it.More(); it.Next())
    {
      gp_Trsf T = it.Value().Location().Transformation();
      b.Add(c, BRepBuilderAPI_Transform(it.Value().Located(TopLoc_Location()), T, true).Shape());
    }
    s = c;
  }
  int nl2 = 0;
  for (TopExp_Explorer e(s, TopAbs_FACE); e.More(); e.Next())
    if (!e.Current().Location().IsIdentity())
      nl2++;
  const double t    = atof(argv[2]);
  auto         t0   = std::chrono::steady_clock::now();
  int          done = 0, err = -1;
  try
  {
    BRepOffsetAPI_MakeOffsetShape mk;
    mk.PerformByJoin(s, t, 1e-7, BRepOffset_Skin, false, false, GeomAbs_Arc, false);
    done = mk.IsDone();
    err  = mk.MakeOffset().Error();
  }
  catch (Standard_Failure&)
  {
    err = -2;
  }
  printf("PROBE %s%s t=%g locatedFaces=%d done=%d err=%d ms=%.0f\n", argv[3], largest ? "/largest" : "", t, nl2, done,
         err, std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count());
  fflush(stdout);
  return 0;
}
