// offloc: localise an offset failure (issue 031 round 2). Faces of <shape.brep> whose bounding box comes within D of
// point P form an open shell; it is offset by t (BRepOffsetAPI_MakeOffsetShape::PerformByJoin, Skin, Arc, tol 1e-7).
// usage: offloc <shape.brep> <x,y,z> <D> <t> [join: arc|int]
#include "down.hxx"
#include <BRep_Builder.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <Bnd_Box.hxx>
#include <BRepBndLib.hxx>
#include <TopoDS_Shell.hxx>
#include <windows.h>
#include <sstream>
#include <vector>
#include <algorithm>
int main(int argc, char** argv)
{
  if (argc < 5) return 2;
  HANDLE job = CreateJobObjectW(nullptr, nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
  li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY;
  li.ProcessMemoryLimit = (SIZE_T)1024 * 1024 * 1024;
  SetInformationJobObject(job, JobObjectExtendedLimitInformation, &li, sizeof(li));
  AssignProcessToJobObject(job, GetCurrentProcess());
  TopoDS_Shape s; BRep_Builder bb;
  if (!BRepTools::Read(s, argv[1], bb)) return 3;
  double x = 0, y = 0, z = 0;
  std::string sel(argv[2]);
  std::vector<int> only;
  if (sel.rfind("F:", 0) == 0) { std::stringstream ss(sel.substr(2)); std::string tk; while (std::getline(ss, tk, ',')) only.push_back(atoi(tk.c_str())); }
  else sscanf(argv[2], "%lf,%lf,%lf", &x, &y, &z);
  const gp_Pnt P(x, y, z);
  const double D = atof(argv[3]), t = atof(argv[4]);
  const bool inter = argc > 5 && std::string(argv[5]) == "int";
  TopoDS_Shell sh; bb.MakeShell(sh);
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(s, TopAbs_FACE, fm);
  int n = 0;
  for (int k = 1; k <= fm.Extent(); k++)
  {
    Bnd_Box b; BRepBndLib::Add(fm(k), b);
    if (!only.empty()) { if (std::find(only.begin(), only.end(), k) == only.end()) continue; }
    else if (b.Distance(Bnd_Box(P.XYZ(), P.XYZ())) > D) continue; // box distance
    bb.Add(sh, fm(k)); n++;
    printf(" F%d", k);
  }
  printf("\nfaces=%d\n", n);
  try
  {
    BRepOffsetAPI_MakeOffsetShape mk;
    mk.PerformByJoin(sh, t, 1e-7, BRepOffset_Skin, false, false, inter ? GeomAbs_Intersection : GeomAbs_Arc);
    if (!mk.IsDone()) { printf("OFFSET FAIL err=%d\n", (int)mk.MakeOffset().Error()); return 0; }
    TopTools_IndexedMapOfShape om; TopExp::MapShapes(mk.Shape(), TopAbs_FACE, om);
    printf("OFFSET DONE faces=%d valid=%d\n", om.Extent(), BRepCheck_Analyzer(mk.Shape()).IsValid() ? 1 : 0);
    if (argc > 6) BRepTools::Write(mk.Shape(), argv[6]);
  }
  catch (Standard_Failure const& e) { printf("OFFSET EXC %s\n", e.GetMessageString()); }
  return 0;
}
