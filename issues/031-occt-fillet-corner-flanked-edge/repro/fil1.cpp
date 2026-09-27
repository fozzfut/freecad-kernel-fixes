// fil1: fillet single edges of a result alone and report how each ends, including SEH exception codes
// (issue 031 round 2: find crashes in a second fillet). usage: fil1 <res.brep> <x,y,z> <R> <radius> [edge ...]
// without edge indices: every edge with a vertex within R of the point.
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepTools.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <Standard_Failure.hxx>
#include <windows.h>
#include <dbghelp.h>
#include <cstdio>
#include <typeinfo>
#include <vector>

static TopoDS_Shape gS;
static TopoDS_Edge  gE;
static double       gR;
static char         gMsg[256];

static int doFillet()
{
  try
  {
    BRepFilletAPI_MakeFillet mf(gS);
    mf.Add(gR, gE);
    mf.Build();
    if (!mf.IsDone()) { sprintf(gMsg, "NOTDONE"); return 1; }
    sprintf(gMsg, "DONE valid=%d", BRepCheck_Analyzer(mf.Shape()).IsValid() ? 1 : 0);
    return 0;
  }
  catch (Standard_Failure const& e)
  {
    sprintf(gMsg, "OCCEXC %s %s", typeid(e).name(), e.GetMessageString() ? e.GetMessageString() : "");
    return 2;
  }
}

static void walk(CONTEXT* ctx)
{
  HANDLE p = GetCurrentProcess(), t = GetCurrentThread();
  static bool init = false;
  if (!init) { SymSetOptions(SYMOPT_LOAD_LINES | SYMOPT_UNDNAME); SymInitialize(p, nullptr, TRUE); init = true; }
  CONTEXT c = *ctx;
  STACKFRAME64 f = {};
  f.AddrPC.Offset = c.Rip; f.AddrPC.Mode = AddrModeFlat;
  f.AddrFrame.Offset = c.Rbp; f.AddrFrame.Mode = AddrModeFlat;
  f.AddrStack.Offset = c.Rsp; f.AddrStack.Mode = AddrModeFlat;
  for (int n = 0; n < 24; n++)
  {
    if (!StackWalk64(IMAGE_FILE_MACHINE_AMD64, p, t, &f, &c, nullptr, SymFunctionTableAccess64, SymGetModuleBase64, nullptr)) break;
    char buf[sizeof(SYMBOL_INFO) + 512] = {};
    SYMBOL_INFO* si = (SYMBOL_INFO*)buf; si->SizeOfStruct = sizeof(SYMBOL_INFO); si->MaxNameLen = 511;
    DWORD64 d = 0; IMAGEHLP_LINE64 ln = {}; ln.SizeOfStruct = sizeof(ln); DWORD dl = 0;
    const bool hs = SymFromAddr(p, f.AddrPC.Offset, &d, si);
    const bool hl = SymGetLineFromAddr64(p, f.AddrPC.Offset, &dl, &ln);
    char mod[MAX_PATH] = "?"; HMODULE hm = nullptr;
    GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)f.AddrPC.Offset, &hm);
    if (hm) GetModuleFileNameA(hm, mod, MAX_PATH);
    const char* mb = strrchr(mod, 92); 
    printf("   #%d %s!%s %s:%lu\n", n, mb ? mb + 1 : mod, hs ? si->Name : "?", hl ? ln.FileName : "", hl ? ln.LineNumber : 0);
  }
}

static int filt(EXCEPTION_POINTERS* ep, DWORD& code)
{
  code = ep->ExceptionRecord->ExceptionCode;
  if (getenv("FIL1_STACK")) walk(ep->ContextRecord);
  return EXCEPTION_EXECUTE_HANDLER;
}

static int sehFillet(DWORD& code)
{
  __try
  {
    return doFillet();
  }
  __except (filt(GetExceptionInformation(), code))
  {
    return 3;
  }
}

int main(int argc, char** argv)
{
  if (argc < 5) return 2;
  HANDLE job = CreateJobObjectW(nullptr, nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
  li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY;
  li.ProcessMemoryLimit = (SIZE_T)1024 * 1024 * 1024;
  SetInformationJobObject(job, JobObjectExtendedLimitInformation, &li, sizeof(li));
  AssignProcessToJobObject(job, GetCurrentProcess());
  BRep_Builder bb;
  if (!BRepTools::Read(gS, argv[1], bb)) return 3;
  double x, y, z;
  sscanf(argv[2], "%lf,%lf,%lf", &x, &y, &z);
  const gp_Pnt P(x, y, z);
  const double Rn = atof(argv[3]);
  gR              = atof(argv[4]);
  TopTools_IndexedMapOfShape em;
  TopExp::MapShapes(gS, TopAbs_EDGE, em);
  std::vector<int> ids;
  for (int a = 5; a < argc; a++) ids.push_back(atoi(argv[a]));
  if (ids.empty())
    for (int k = 1; k <= em.Extent(); k++)
    {
      TopoDS_Vertex v1, v2;
      TopExp::Vertices(TopoDS::Edge(em(k)), v1, v2);
      if (v1.IsNull() || v2.IsNull() || BRep_Tool::Degenerated(TopoDS::Edge(em(k)))) continue;
      if (BRep_Tool::Pnt(v1).Distance(P) < Rn || BRep_Tool::Pnt(v2).Distance(P) < Rn) ids.push_back(k);
    }
  for (int k : ids)
  {
    gE = TopoDS::Edge(em(k));
    BRepAdaptor_Curve c(gE);
    DWORD code = 0;
    gMsg[0]    = 0;
    const int rc = sehFillet(code);
    printf("E%d type=%d len~%.4f rc=%d %s code=0x%08lx\n", k, (int)c.GetType(),
           c.Value(c.FirstParameter()).Distance(c.Value(c.LastParameter())), rc, gMsg, code);
    fflush(stdout);
  }
  return 0;
}
