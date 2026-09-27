// boxprobe.cpp: why do wires of a face get no #1375 box? (replica of ComputeWireUVBounds, BRepCheck_Face.cxx:828-867 @V8_0_1)
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepTools.hxx>
#include <BndLib_Add2dCurve.hxx>
#include <Bnd_Box2d.hxx>
#include <Geom2dAdaptor_Curve.hxx>
#include <Precision.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <cstdio>
int main(int argc, char** argv)
{
  TopoDS_Shape s; BRep_Builder b;
  if (!BRepTools::Read(s, argv[1], b)) return 3;
  int k = 0;
  for (TopExp_Explorer ef(s, TopAbs_FACE); ef.More(); ef.Next(), ++k)
  {
    const TopoDS_Face F = TopoDS::Face(ef.Current().Oriented(TopAbs_FORWARD));
    int nw = 0, notClosed = 0, nullPc = 0, clamped = 0, ok = 0;
    for (TopExp_Explorer ew(F, TopAbs_WIRE); ew.More(); ew.Next()) ++nw;
    if (nw < 10) continue;
    for (TopExp_Explorer ew(F, TopAbs_WIRE); ew.More(); ew.Next())
    {
      const TopoDS_Wire& W = TopoDS::Wire(ew.Current());
      if (!BRep_Tool::IsClosed(W)) { ++notClosed; continue; }
      bool bad = false;
      for (TopExp_Explorer ee(W, TopAbs_EDGE); ee.More() && !bad; ee.Next())
      {
        double f, l;
        const occ::handle<Geom2d_Curve> pc = BRep_Tool::CurveOnSurface(TopoDS::Edge(ee.Current()), F, f, l);
        if (pc.IsNull()) { ++nullPc; bad = true; break; }
        const Geom2dAdaptor_Curve ac(pc);
        if (Precision::IsInfinite(f) || Precision::IsInfinite(l) || f < ac.FirstParameter() || l > ac.LastParameter())
        { ++clamped; bad = true; if (clamped <= 3) std::printf("  clamped: f %.17g l %.17g curve %.17g %.17g type %s\n", f, l, ac.FirstParameter(), ac.LastParameter(), pc->DynamicType()->Name()); }
      }
      if (!bad) ++ok;
    }
    std::printf("face %d wires %d box %d notClosed %d nullPcurve %d clamped %d\n", k, nw, ok, notClosed, nullPc, clamped);
  }
  return 0;
}
