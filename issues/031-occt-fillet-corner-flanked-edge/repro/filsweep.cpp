// filsweep: identity sweep for issue 031 (lane fillet-corner). For every input BREP, for up to MAXV vertices,
// every subset (size >= 1, at most 31) of the edges at that vertex is filleted (2 radii) and chamfered (1 distance)
// with BRepFilletAPI_MakeFillet / MakeChamfer; one line per operation: status, faces, volume, BRepCheck validity,
// md5 of the result's BREP text. Two TKFillet builds are compared by diffing the output files.
// usage: filsweep <out.txt> <maxv> <in1.brep> [in2.brep ...]    (1 GB Job Object cap)
// round 2: FILSWEEP_DOWN=1 appends the downstream checks of down.hxx to every done operation ("| self=.. thk-=..
// thk+=.. cut=.. fil2=.. fil3=.. step=.."), thickness t = 0.25 r, cut / second fillet at the vertex; meant with
// FILSWEEP_ONLY (the changed operations), because the checks cost seconds each.
#include "down.hxx"
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepFilletAPI_MakeChamfer.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <GCPnts_AbscissaPoint.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <Standard_Failure.hxx>
#include <windows.h>
#include <wincrypt.h>
#include <cstdio>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>
#include <typeinfo>

static std::string md5(const std::string& s)
{
  HCRYPTPROV p = 0; HCRYPTHASH h = 0; BYTE d[16]; DWORD n = 16; char out[33];
  CryptAcquireContextA(&p, nullptr, nullptr, PROV_RSA_FULL, CRYPT_VERIFYCONTEXT);
  CryptCreateHash(p, CALG_MD5, 0, 0, &h);
  CryptHashData(h, (const BYTE*)s.data(), (DWORD)s.size(), 0);
  CryptGetHashParam(h, HP_HASHVAL, d, &n, 0);
  for (int i = 0; i < 16; i++) sprintf(out + 2 * i, "%02x", d[i]);
  CryptDestroyHash(h); CryptReleaseContext(p, 0);
  return std::string(out, 32);
}

static std::string fp(const TopoDS_Shape& r)
{
  TopTools_IndexedMapOfShape fm; TopExp::MapShapes(r, TopAbs_FACE, fm);
  GProp_GProps g; BRepGProp::VolumeProperties(r, g);
  BRepCheck_Analyzer an(r);
  std::ostringstream os; BRepTools::Write(r, os);
  char b[160];
  sprintf(b, "faces=%d vol=%.9g valid=%d md5=%s", fm.Extent(), g.Mass(), an.IsValid() ? 1 : 0, md5(os.str()).c_str());
  return b;
}

int main(int argc, char** argv)
{
  if (argc < 4) { printf("usage\n"); return 2; }
  HANDLE job = CreateJobObjectW(nullptr, nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
  li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY;
  li.ProcessMemoryLimit = (SIZE_T)1024 * 1024 * 1024;
  SetInformationJobObject(job, JobObjectExtendedLimitInformation, &li, sizeof(li));
  AssignProcessToJobObject(job, GetCurrentProcess());
  char path[MAX_PATH] = {0};
  HMODULE hm = GetModuleHandleA("TKFillet.dll");
  if (hm) GetModuleFileNameA(hm, path, MAX_PATH);
  FILE* o = fopen(argv[1], "w");
  fprintf(stderr, "TKFillet=%s\n", path);
  int maxv = atoi(argv[2]);
  // optional: FILSWEEP_ONLY=<file of "path sI vN opK e=..." keys> and FILSWEEP_DUMP=<dir>: run only those, write BREPs
  std::vector<std::string> only;
  const char* onlyf = getenv("FILSWEEP_ONLY");
  const char* dumpd = getenv("FILSWEEP_DUMP");
  const bool  downc = getenv("FILSWEEP_DOWN") != nullptr;
  if (onlyf) { FILE* f = fopen(onlyf, "r"); char ln[2048]; while (f && fgets(ln, sizeof ln, f)) { std::string t(ln); while (!t.empty() && (t.back() == 10 || t.back() == 13)) t.pop_back(); if (!t.empty()) only.push_back(t); } if (f) fclose(f); }
  long nops = 0, ndone = 0;
  for (int a = 3; a < argc; a++)
  {
    TopoDS_Shape s; BRep_Builder bb;
    if (!BRepTools::Read(s, argv[a], bb)) { fprintf(o, "READ-FAIL %s\n", argv[a]); continue; }
    // each solid separately (compounds of bodies)
    std::vector<TopoDS_Shape> solids;
    for (TopExp_Explorer ex(s, TopAbs_SOLID); ex.More(); ex.Next()) solids.push_back(ex.Current());
    if (solids.empty()) solids.push_back(s);
    for (size_t si = 0; si < solids.size(); si++)
    {
      const TopoDS_Shape& S = solids[si];
      TopTools_IndexedMapOfShape vm; TopExp::MapShapes(S, TopAbs_VERTEX, vm);
      TopTools_IndexedMapOfShape em; TopExp::MapShapes(S, TopAbs_EDGE, em);
      TopTools_IndexedDataMapOfShapeListOfShape ve; TopExp::MapShapesAndUniqueAncestors(S, TopAbs_VERTEX, TopAbs_EDGE, ve);
      int nv = vm.Extent();
      int step = nv > maxv ? (nv + maxv - 1) / maxv : 1;
      for (int vi = 1; vi <= nv; vi += step)
      {
        const TopoDS_Shape& V = vm(vi);
        if (!ve.Contains(V)) continue;
        std::vector<int> E; double minlen = 1e100;
        for (const TopoDS_Shape& e : ve.FindFromKey(V))
        {
          const TopoDS_Edge& ed = TopoDS::Edge(e);
          if (BRep_Tool::Degenerated(ed)) continue;
          int ix = em.FindIndex(ed);
          if (ix == 0 || std::find(E.begin(), E.end(), ix) != E.end()) continue;
          E.push_back(ix);
          BRepAdaptor_Curve c(ed);
          double L = GCPnts_AbscissaPoint::Length(c);
          minlen = std::min(minlen, L);
        }
        std::sort(E.begin(), E.end());
        int ne = (int)std::min<size_t>(E.size(), 5);
        if (ne == 0) continue;
        for (int mask = 1; mask < (1 << ne); mask++)
        {
          std::string ids;
          for (int k = 0; k < ne; k++) if (mask & (1 << k)) ids += std::to_string(E[k]) + ",";
          double rads[3] = {0.1 * minlen, 0.35 * minlen, 0.2 * minlen};
          for (int op = 0; op < 3; op++)
          {
            char keyb[1024];
            sprintf(keyb, "%s s%zu v%d op%d e=%s", argv[a], si, vi, op, ids.c_str());
            if (onlyf && std::find(only.begin(), only.end(), std::string(keyb)) == only.end()) continue;
            nops++;
            std::string res;
            try
            {
              TopoDS_Shape r;
              if (op < 2)
              {
                BRepFilletAPI_MakeFillet mf(S);
                for (int k = 0; k < ne; k++) if (mask & (1 << k)) mf.Add(rads[op], TopoDS::Edge(em(E[k])));
                mf.Build();
                if (mf.IsDone()) r = mf.Shape(); else res = "NOTDONE";
              }
              else
              {
                BRepFilletAPI_MakeChamfer mc(S);
                for (int k = 0; k < ne; k++) if (mask & (1 << k)) mc.Add(rads[op], TopoDS::Edge(em(E[k])));
                mc.Build();
                if (mc.IsDone()) r = mc.Shape(); else res = "NOTDONE";
              }
              if (!r.IsNull()) { res = fp(r); ndone++;
                if (downc)
                {
                  std::vector<TopoDS_Edge> keep;
                  for (int k = 0; k < (int)E.size(); k++)
                    if (k >= ne || !(mask & (1 << k))) keep.push_back(TopoDS::Edge(em(E[k])));
                  char tmpf[MAX_PATH];
                  sprintf(tmpf, "%s.%lu.step.tmp", argv[1], GetCurrentProcessId());
                  res += " | " + down::all(r, keep, BRep_Tool::Pnt(TopoDS::Vertex(V)), rads[op], 0.25 * rads[op], tmpf);
                }
                if (dumpd) { char fn[1024]; sprintf(fn, "%s/c%ld.brep", dumpd, nops); BRepTools::Write(r, fn); res += std::string(" dump=") + fn; } }
            }
            catch (Standard_Failure const& e) { res = std::string("EXC ") + typeid(e).name(); }
            catch (...) { res = "EXC ..."; }
            fprintf(o, "%s s%zu v%d op%d r=%.6g e=%s %s\n", argv[a], si, vi, op, rads[op], ids.c_str(), res.c_str());
            fflush(o);
          }
        }
      }
    }
  }
  fprintf(o, "SWEEP-DONE ops=%ld done=%ld\n", nops, ndone);
  fclose(o);
  fprintf(stderr, "SWEEP-DONE ops=%ld done=%ld\n", nops, ndone);
  return 0;
}
