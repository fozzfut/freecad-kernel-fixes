// filcorner: BRepFilletAPI_MakeFillet on a BREP (lane fillet-corner, issue 031).
// usage: filcorner <in.brep> <out.brep> <radius> <edge index 1-based, TopExp::MapShapes order = FreeCAD EdgeN>...
// prints: TKFillet path, IsDone, faces, BRepCheck validity; writes out.brep when done.
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <Standard_Failure.hxx>
#include <windows.h>
#include <psapi.h>
#include <cstdio>
#include <typeinfo>
#include <cstdlib>
int main(int argc, char** argv)
{
  if (argc < 5) { printf("usage\n"); return 2; }
  // 1 GB cap (owner rule)
  HANDLE job = CreateJobObjectW(nullptr, nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
  li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY;
  li.ProcessMemoryLimit = (SIZE_T)1024 * 1024 * 1024;
  SetInformationJobObject(job, JobObjectExtendedLimitInformation, &li, sizeof(li));
  AssignProcessToJobObject(job, GetCurrentProcess());
  HMODULE h = GetModuleHandleA("TKFillet.dll");
  char path[MAX_PATH] = {0};
  if (h) GetModuleFileNameA(h, path, MAX_PATH);
  printf("TKFillet=%s\n", path);
  TopoDS_Shape s; BRep_Builder b;
  if (!BRepTools::Read(s, argv[1], b)) { printf("READ-FAIL\n"); return 3; }
  TopTools_IndexedMapOfShape em; TopExp::MapShapes(s, TopAbs_EDGE, em);
  double r = atof(argv[3]);
  try {
    BRepFilletAPI_MakeFillet mf(s);
    for (int i = 4; i < argc; i++) mf.Add(r, TopoDS::Edge(em(atoi(argv[i]))));
    mf.Build();
    printf("DONE=%d\n", mf.IsDone() ? 1 : 0);
    if (!mf.IsDone()) { printf("NBFAULTY_EDGES=%d NBFAULTY_VERTICES=%d\n", mf.NbFaultyContours(), mf.NbFaultyVertices()); return 1; }
    TopoDS_Shape res = mf.Shape();
    TopTools_IndexedMapOfShape fm; TopExp::MapShapes(res, TopAbs_FACE, fm);
    BRepCheck_Analyzer an(res);
    printf("FACES=%d VALID=%d\n", fm.Extent(), an.IsValid() ? 1 : 0);
    BRepTools::Write(res, argv[2]);
  } catch (Standard_Failure const& e) { printf("EXC %s: %s\n", typeid(e).name(), e.GetMessageString()); return 4; }
  return 0;
}
