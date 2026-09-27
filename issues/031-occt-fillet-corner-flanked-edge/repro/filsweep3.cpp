// filsweep3 (issue 031 round 3): the operations of filsweep (every subset of <= 5 edges at a vertex, fillet 0.1 /
// 0.35 min-length, chamfer 0.2) restricted to a keys file, each followed by the timed downstream checks of
// down3.hxx. One line per operation:
//   <key> r=<r> self=<STATUS>:<ms> faces=.. vol=.. | thk-0.3=OK:120 ... step=OK:40
// A watchdog stops the process when one step runs longer than FS3_HANG_MS (default 60000) and writes
//   HANG <key> <check> <ms>
// so the driver can go on with the remaining keys. 1 GB Job Object cap.
// usage: filsweep3 <out.txt> <keys.txt>      (keys: "<path> s<i> v<n> op<k> e=<ids>,")
#include "down3.hxx"
#include <BRep_Builder.hxx>
#include <BRepFilletAPI_MakeChamfer.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <algorithm>
#include <fstream>
#include <map>
#include <sstream>
#include <thread>

static FILE* gOut = nullptr;

static void watchdog(long long lim)
{
  for (;;)
  {
    Sleep(250);
    const long long s = dog3::since;
    if (s != 0 && dog3::now() - s > lim)
    {
      fprintf(gOut, "HANG %s %lld\n", dog3::label, dog3::now() - s);
      fflush(gOut);
      fclose(gOut);
      TerminateProcess(GetCurrentProcess(), 7);
    }
  }
}

int main(int argc, char** argv)
{
  if (argc < 3) { printf("usage\n"); return 2; }
  HANDLE job = CreateJobObjectW(nullptr, nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
  li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY;
  li.ProcessMemoryLimit = (SIZE_T)1024 * 1024 * 1024;
  SetInformationJobObject(job, JobObjectExtendedLimitInformation, &li, sizeof(li));
  AssignProcessToJobObject(job, GetCurrentProcess());
  char path[MAX_PATH] = {0};
  HMODULE hm = GetModuleHandleA("TKFillet.dll");
  if (hm) GetModuleFileNameA(hm, path, MAX_PATH);
  fprintf(stderr, "TKFillet=%s\n", path);
  gOut = fopen(argv[1], "a");
  const char* hl  = getenv("FS3_HANG_MS");
  const bool  nod = getenv("FS3_NODOWN") != nullptr;
  std::thread(watchdog, hl ? atoll(hl) : 60000LL).detach();
  // keys grouped by file
  std::vector<std::string> keys;
  {
    std::ifstream f(argv[2]);
    std::string   l;
    while (std::getline(f, l))
    {
      while (!l.empty() && (l.back() == '\r' || l.back() == '\n' || l.back() == ' ')) l.pop_back();
      if (!l.empty()) keys.push_back(l);
    }
  }
  std::map<std::string, TopoDS_Shape> cache;
  for (const std::string& key : keys)
  {
    if (key.rfind("CASE ", 0) == 0)
    {
      // CASE <name> <file> <r> <e1,e2,...>: one fillet of the listed edges (this order, radius r); whole-body
      // checks once, local checks at every input vertex where >= 2 filleted and >= 1 unfilleted edges meet
      std::istringstream cs(key.substr(5));
      std::string        name, file, rs, es;
      cs >> name >> file >> rs >> es;
      const double r = atof(rs.c_str());
      TopoDS_Shape S;
      BRep_Builder bb;
      if (!BRepTools::Read(S, file.c_str(), bb)) { fprintf(gOut, "READ-FAIL %s\n", file.c_str()); continue; }
      TopTools_IndexedMapOfShape em;
      TopExp::MapShapes(S, TopAbs_EDGE, em);
      std::vector<int> ids;
      {
        std::stringstream s2(es);
        std::string       tok;
        while (std::getline(s2, tok, ',')) if (!tok.empty()) ids.push_back(atoi(tok.c_str()));
      }
      TopoDS_Shape res;
      down3::Timed self = down3::timed("CASE " + name + " self", [&]() -> std::string {
        BRepFilletAPI_MakeFillet mf(S);
        for (int k : ids) mf.Add(r, TopoDS::Edge(em(k)));
        mf.Build();
        if (!mf.IsDone()) return "ERR";
        res = mf.Shape();
        return down3::grade(res);
      });
      char h[256];
      sprintf(h, "CASE %s r=%g self=%s:%lld", name.c_str(), r, self.st.c_str(), self.ms);
      std::string line = h;
      if (!res.IsNull())
      {
        GProp_GProps g;
        BRepGProp::VolumeProperties(res, g);
        char b[128];
        sprintf(b, " vol=%.9g", g.Mass());
        line += b;
        char tmpf[MAX_PATH];
        sprintf(tmpf, "%s.%lu.step.tmp", argv[1], GetCurrentProcessId());
        line += " |" + down3::all("CASE " + name, res, {}, gp_Pnt(1e9, 1e9, 1e9), r, tmpf, true);
        if (const char* dd = getenv("FS3_DUMP"))
        {
          char fn[1024];
          sprintf(fn, "%s/case_%s.brep", dd, name.c_str());
          BRepTools::Write(res, fn);
        }
      }
      fprintf(gOut, "%s\n", line.c_str());
      fflush(gOut);
      if (res.IsNull()) continue;
      TopTools_IndexedDataMapOfShapeListOfShape ve;
      TopExp::MapShapesAndUniqueAncestors(S, TopAbs_VERTEX, TopAbs_EDGE, ve);
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
        char         kb[256];
        sprintf(kb, "CASE %s @(%.3f,%.3f,%.3f)", name.c_str(), V.X(), V.Y(), V.Z());
        char tmpf[MAX_PATH];
        sprintf(tmpf, "%s.%lu.step.tmp", argv[1], GetCurrentProcessId());
        std::string l2 = std::string(kb) + " |" + down3::all(kb, res, keep, V, r, tmpf, false);
        fprintf(gOut, "%s\n", l2.c_str());
        fflush(gOut);
      }
      continue;
    }
    std::istringstream ks(key);
    std::string        file, ss, vs, ops, es;
    ks >> file >> ss >> vs >> ops >> es;
    const int si = atoi(ss.c_str() + 1), vi = atoi(vs.c_str() + 1), op = atoi(ops.c_str() + 2);
    if (!cache.count(file))
    {
      TopoDS_Shape s;
      BRep_Builder bb;
      if (!BRepTools::Read(s, file.c_str(), bb)) { fprintf(gOut, "READ-FAIL %s\n", file.c_str()); continue; }
      cache[file] = s;
    }
    std::vector<TopoDS_Shape> solids;
    for (TopExp_Explorer ex(cache[file], TopAbs_SOLID); ex.More(); ex.Next()) solids.push_back(ex.Current());
    if (solids.empty()) solids.push_back(cache[file]);
    const TopoDS_Shape&        S = solids[si];
    TopTools_IndexedMapOfShape vm, em;
    TopExp::MapShapes(S, TopAbs_VERTEX, vm);
    TopExp::MapShapes(S, TopAbs_EDGE, em);
    TopTools_IndexedDataMapOfShapeListOfShape ve;
    TopExp::MapShapesAndUniqueAncestors(S, TopAbs_VERTEX, TopAbs_EDGE, ve);
    const TopoDS_Shape& V = vm(vi);
    std::vector<int>    E;
    double              minlen = 1e100;
    for (const TopoDS_Shape& e : ve.FindFromKey(V))
    {
      const TopoDS_Edge& ed = TopoDS::Edge(e);
      if (BRep_Tool::Degenerated(ed)) continue;
      int ix = em.FindIndex(ed);
      if (ix == 0 || std::find(E.begin(), E.end(), ix) != E.end()) continue;
      E.push_back(ix);
      BRepAdaptor_Curve c(ed);
      minlen = std::min(minlen, GCPnts_AbscissaPoint::Length(c));
    }
    std::sort(E.begin(), E.end());
    std::vector<int> sel;
    {
      std::stringstream s2(es.substr(2));
      std::string       tok;
      while (std::getline(s2, tok, ',')) if (!tok.empty()) sel.push_back(atoi(tok.c_str()));
    }
    const double rads[3] = {0.1 * minlen, 0.35 * minlen, 0.2 * minlen};
    const double r       = rads[op];
    TopoDS_Shape res;
    down3::Timed self = down3::timed(key + " self", [&]() -> std::string {
      if (op < 2)
      {
        BRepFilletAPI_MakeFillet mf(S);
        for (int k : sel) mf.Add(r, TopoDS::Edge(em(k)));
        mf.Build();
        if (!mf.IsDone()) return "ERR";
        res = mf.Shape();
      }
      else
      {
        BRepFilletAPI_MakeChamfer mc(S);
        for (int k : sel) mc.Add(r, TopoDS::Edge(em(k)));
        mc.Build();
        if (!mc.IsDone()) return "ERR";
        res = mc.Shape();
      }
      return down3::grade(res);
    });
    char head[256];
    sprintf(head, " r=%.6g self=%s:%lld", r, self.st.c_str(), self.ms);
    std::string line = key + head;
    if (!res.IsNull())
    {
      TopTools_IndexedMapOfShape fm;
      TopExp::MapShapes(res, TopAbs_FACE, fm);
      GProp_GProps g;
      BRepGProp::VolumeProperties(res, g);
      char b[256];
      const gp_Pnt Vp = BRep_Tool::Pnt(TopoDS::Vertex(V));
      const gp_Pnt Pc = down3::cornerCentre(res, Vp, r);
      sprintf(b, " faces=%d vol=%.9g V=%.6f,%.6f,%.6f P=%.6f,%.6f,%.6f", fm.Extent(), g.Mass(), Vp.X(), Vp.Y(), Vp.Z(),
              Pc.X(), Pc.Y(), Pc.Z());
      line += b;
      if (!nod)
      {
        std::vector<TopoDS_Edge> keep;
        for (int ix : E)
          if (std::find(sel.begin(), sel.end(), ix) == sel.end()) keep.push_back(TopoDS::Edge(em(ix)));
        char tmpf[MAX_PATH];
        sprintf(tmpf, "%s.%lu.step.tmp", argv[1], GetCurrentProcessId());
        line += " |" + down3::all(key, res, keep, BRep_Tool::Pnt(TopoDS::Vertex(V)), r, tmpf);
      }
      if (const char* dd = getenv("FS3_DUMP"))
      {
        static int n = 0;
        char       fn[1024];
        sprintf(fn, "%s/%lu_%d.brep", dd, GetCurrentProcessId(), ++n);
        BRepTools::Write(res, fn);
        line += std::string(" dump=") + fn;
      }
    }
    fprintf(gOut, "%s\n", line.c_str());
    fflush(gOut);
  }
  fprintf(gOut, "FS3-DONE\n");
  fclose(gOut);
  return 0;
}
