// fildown: fillet a BREP and run the downstream checks of down.hxx on the result (issue 031, round 2).
// usage: fildown <in.brep> <r> <e1,e2,...> <t> <openface|0> [out.brep]
//   edges     : 1-based edge indices (TopExp::MapShapes = FreeCAD EdgeN), filleted in this order with radius r
//   openface  : 1-based face index of the RESULT removed by the thickness; 0 = largest plane
//   corners   : every input vertex where >= 2 filleted edges and >= 1 unfilleted edge meet; the cut and the
//               second fillet (of the unfilleted edges there) are done at each
// env FD_TLIST=t1,t2,...: only the thickness, for each t (inside/outside), then exit.
// 1 GB Job Object cap.
#include "down.hxx"
#include <BRep_Builder.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <windows.h>
#include <vector>
#include <sstream>
#include <algorithm>

int main(int argc, char** argv)
{
  if (argc < 6) { printf("usage\n"); return 2; }
  HANDLE job = CreateJobObjectW(nullptr, nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
  li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY;
  li.ProcessMemoryLimit = (SIZE_T)1024 * 1024 * 1024;
  SetInformationJobObject(job, JobObjectExtendedLimitInformation, &li, sizeof(li));
  AssignProcessToJobObject(job, GetCurrentProcess());
  char path[MAX_PATH] = {0};
  HMODULE hm = GetModuleHandleA("TKFillet.dll");
  if (hm) GetModuleFileNameA(hm, path, MAX_PATH);
  printf("TKFillet=%s\n", path);
  TopoDS_Shape s;
  BRep_Builder bb;
  if (!BRepTools::Read(s, argv[1], bb)) { printf("READ-FAIL\n"); return 3; }
  const double r  = atof(argv[2]);
  const double t  = atof(argv[4]);
  const int    of = atoi(argv[5]);
  TopTools_IndexedMapOfShape em;
  TopExp::MapShapes(s, TopAbs_EDGE, em);
  std::vector<int> ids;
  {
    std::stringstream ss(argv[3]);
    std::string       tok;
    while (std::getline(ss, tok, ',')) if (!tok.empty()) ids.push_back(atoi(tok.c_str()));
  }
  TopoDS_Shape res;
  if (const char* given = getenv("FD_RES")) // the result is given (made by another build): checks only
  {
    if (!BRepTools::Read(res, given, bb)) { printf("READ-FAIL %s\n", given); return 3; }
  }
  else
  {
    BRepFilletAPI_MakeFillet mf(s);
    for (int k : ids) mf.Add(r, TopoDS::Edge(em(k)));
    try { mf.Build(); } catch (...) { printf("FILLET EXC\n"); return 1; }
    if (!mf.IsDone()) { printf("FILLET NOTDONE\n"); return 1; }
    res = mf.Shape();
  }
  if (const char* tb = getenv("FD_TOLBUMP")) // experiment: raise the tolerance of the first vertex (far from
  {                                          // the corner) to show the offset's dependence on the max tolerance
    TopTools_IndexedMapOfShape vm;
    TopExp::MapShapes(res, TopAbs_VERTEX, vm);
    BRep_Builder().UpdateVertex(TopoDS::Vertex(vm(1)), atof(tb));
    printf("TOLBUMP vertex 1 at (%.3f,%.3f,%.3f) -> %s\n", BRep_Tool::Pnt(TopoDS::Vertex(vm(1))).X(),
           BRep_Tool::Pnt(TopoDS::Vertex(vm(1))).Y(), BRep_Tool::Pnt(TopoDS::Vertex(vm(1))).Z(), tb);
  }
  if (argc > 6) BRepTools::Write(res, argv[6]);
  {
    double vt = 0.;
    for (TopExp_Explorer ex(res, TopAbs_VERTEX); ex.More(); ex.Next())
      vt = std::max(vt, BRep_Tool::Tolerance(TopoDS::Vertex(ex.Current())));
    printf("RESULT vol=%.9f maxvtol=%.3e\n", down::volume(res), vt);
  }
  if (const char* tl = getenv("FD_TLIST"))
  {
    std::stringstream ts(tl);
    std::string       tk;
    printf("TLIST");
    while (std::getline(ts, tk, ','))
      printf(" %s:%s/%s", tk.c_str(), down::thick(res, of, -atof(tk.c_str())).c_str(),
             down::thick(res, of, atof(tk.c_str())).c_str());
    printf("\n");
    return 0;
  }
  std::string own;
  down::okShape(res, own);
  printf("self=%s\n", own.c_str());
  printf("thk-=%s thk+=%s\n", down::thick(res, of, -t).c_str(), down::thick(res, of, t).c_str());
  TopTools_IndexedDataMapOfShapeListOfShape ve;
  TopExp::MapShapesAndUniqueAncestors(s, TopAbs_VERTEX, TopAbs_EDGE, ve);
  for (int k = 1; k <= ve.Extent(); k++)
  {
    int                      nf = 0;
    std::vector<TopoDS_Edge> keep;
    for (const TopoDS_Shape& e : ve(k))
    {
      if (BRep_Tool::Degenerated(TopoDS::Edge(e))) continue;
      if (std::find(ids.begin(), ids.end(), em.FindIndex(e)) != ids.end()) nf++;
      else keep.push_back(TopoDS::Edge(e));
    }
    if (nf < 2 || keep.empty()) continue;
    const gp_Pnt V = BRep_Tool::Pnt(TopoDS::Vertex(ve.FindKey(k)));
    printf("at (%.3f,%.3f,%.3f) cut=%s fil2=%s fil3=%s\n", V.X(), V.Y(), V.Z(), down::cut(res, V, r).c_str(),
           down::fil2(res, keep, V, r).c_str(), down::fil3(res, V, r).c_str());
  }
  char tmp[MAX_PATH];
  sprintf(tmp, "%s.%lu.step.tmp", argv[1], GetCurrentProcessId());
  printf("step=%s\n", down::step(res, tmp).c_str());
  return 0;
}
