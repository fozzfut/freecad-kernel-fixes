// Defect 025 native diagnostic; stock OCCT versus exact-algorithm prepared-data prototype.
// Private generated classes only. No production DLL or public OCCT header is modified.
#include <DiagnosticFClass2d.hxx>
#include <PreparedFClass2d.hxx>
#include <BRepTopAdaptor_FClass2d.hxx>
#include <BRepClass_FaceClassifier.hxx>
#include <BRepTools.hxx>
#include <BRep_Tool.hxx>
#include <BRep_Builder.hxx>
#include <Geom2d_Curve.hxx>
#include <gp_Vec2d.hxx>
#include <gp_Pnt2d.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <Standard_Failure.hxx>
#include <windows.h>
#include <psapi.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <random>
#include <string>
#include <vector>
using Clock = std::chrono::steady_clock;
static double elapsed(Clock::time_point t) { return std::chrono::duration<double>(Clock::now()-t).count(); }
struct Answer {
  int state=-1;
  std::string error;
  bool operator==(const Answer& o) const { return state==o.state && error==o.error; }
};
template<class F> Answer invoke(F f) {
  Answer a;
  try { a.state=(int)f(); }
  catch(const Standard_Failure& e) { a.error=std::string(e.DynamicType()->Name())+":"+e.GetMessageString(); }
  catch(const std::exception& e) { a.error=std::string("std:")+e.what(); }
  return a;
}
static int count(const TopoDS_Shape& s, TopAbs_ShapeEnum type) {
  int n=0; for(TopExp_Explorer it(s,type);it.More();it.Next()) ++n; return n;
}
struct Queries { std::vector<gp_Pnt2d> points; std::string name; };
static std::vector<Queries> makeQueries(const TopoDS_Face& face) {
  double u0,u1,v0,v1; BRepTools::UVBounds(face,u0,u1,v0,v1);
  if(!std::isfinite(u0+u1+v0+v1) || std::max({fabs(u0),fabs(u1),fabs(v0),fabs(v1)})>1e8) return {};
  Queries grid, boundarySet; grid.name="random"; boundarySet.name="boundary";
  std::mt19937 rng(250925); std::uniform_real_distribution<double> dist(-0.05,1.05);
  for(int i=0;i<512;++i) grid.points.emplace_back(u0+(u1-u0)*dist(rng),v0+(v1-v0)*dist(rng));
  int ne=count(face,TopAbs_EDGE),stride=std::max(1,ne/128),i=0;
  for(TopExp_Explorer it(face,TopAbs_EDGE);it.More();it.Next(),++i) {
    if(i%stride) continue;
    double first,last; auto curve=BRep_Tool::CurveOnSurface(TopoDS::Edge(it.Current()),face,first,last);
    if(curve.IsNull() || !std::isfinite(first+last) || fabs(first)+fabs(last)>1e8) continue;
    gp_Pnt2d p; gp_Vec2d tangent;
    curve->D1(first+(last-first)*0.43213918,p,tangent);
    boundarySet.points.push_back(p);
    const double norm=tangent.Magnitude();
    if(norm>1e-15) for(double offset : {-1e-3,-1e-6,1e-6,1e-3})
      boundarySet.points.emplace_back(p.X()-tangent.Y()/norm*offset,p.Y()+tangent.X()/norm*offset);
  }
  return {grid,boundarySet};
}
int main(int argc,char**argv) {
  if(argc!=3) { std::cerr<<"usage: probe list.txt out.tsv\n"; return 2; }
  HANDLE job=CreateJobObjectW(nullptr,nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION li={}; li.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_PROCESS_MEMORY;
  li.ProcessMemoryLimit=SIZE_T(1024)*1024*1024;
  if(!job || !SetInformationJobObject(job,JobObjectExtendedLimitInformation,&li,sizeof li) || !AssignProcessToJobObject(job,GetCurrentProcess())) {
    std::cerr<<"CAP_FAILED "<<GetLastError()<<"\n"; return 3;
  }
  MEMORYSTATUSEX mem={};mem.dwLength=sizeof mem;GlobalMemoryStatusEx(&mem);
  if(mem.ullAvailPhys<SIZE_T(1024)*1024*1024 || mem.ullAvailPageFile<SIZE_T(4)*1024*1024*1024) {
    std::cerr<<"MEMORY_GATE ram="<<mem.ullAvailPhys<<" commit="<<mem.ullAvailPageFile<<"\n";return 77;
  }
  std::ofstream out(argv[2]);
  out<<"file\tface\twires\tedges\tset\tpoints\tpolygons\tfirst_orientation\tstock_s\tdiagnostic_s\tprepared_s\tstock_setup_s\tprepared_setup_s\twire_tests\tambiguous\tbad_wire\tmismatches\n";
  out<<std::setprecision(9);
  std::ifstream list(argv[1]);std::string path; unsigned long long total=0,mismatch=0;
  int failures=0;
  while(std::getline(list,path)) {
    if(!path.empty() && path.back()=='\r')path.pop_back(); if(path.empty() || path[0]=='#')continue;
    try {
      TopoDS_Shape shape;BRep_Builder builder;
      if(!BRepTools::Read(shape,path.c_str(),builder)) { std::cerr<<"READ_FAILED "<<path<<"\n";++failures;continue; }
      int fi=0;std::vector<std::pair<int,TopoDS_Face>> faces;
      for(TopExp_Explorer it(shape,TopAbs_FACE);it.More();it.Next()) {
        ++fi;auto face=TopoDS::Face(it.Current());
        if(count(face,TopAbs_WIRE)>1 || shape.ShapeType()==TopAbs_FACE) faces.emplace_back(fi,face);
      }
      // Top has two similar perforated faces: retain both to detect orientation/layout differences.
      for(const auto& entry:faces) {
        auto face=entry.second;int wires=count(face,TopAbs_WIRE),edges=count(face,TopAbs_EDGE);
        auto sets=makeQueries(face);
        for(const auto& qs:sets) {
          auto t=Clock::now();BRepTopAdaptor_FClass2d stock(face,1e-7);double stockSetup=elapsed(t);
          DiagnosticFClass2d diagnostic(face,1e-7);
          t=Clock::now();PreparedFClass2d prepared(face,1e-7);double preparedSetup=elapsed(t);
          std::vector<Answer> ref;ref.reserve(qs.points.size());
          t=Clock::now();for(const auto& p:qs.points)ref.push_back(invoke([&]{return stock.Perform(p);}));double stockTime=elapsed(t);
          unsigned long long wrong=0;
          t=Clock::now();for(size_t i=0;i<qs.points.size();++i) if(!(invoke([&]{return diagnostic.Perform(qs.points[i]);})==ref[i]))++wrong;
          double diagTime=elapsed(t);
          t=Clock::now();for(size_t i=0;i<qs.points.size();++i) {
            auto a=invoke([&]{return prepared.Perform(qs.points[i]);});
            if(!(a==ref[i])) { ++wrong; if(wrong<=3)std::cerr<<"MISMATCH "<<path<<" face "<<entry.first<<" i "<<i<<" expected "<<ref[i].state<<" got "<<a.state<<"\n"; }
          }
          double preparedTime=elapsed(t);
          out<<path<<'\t'<<entry.first<<'\t'<<wires<<'\t'<<edges<<'\t'<<qs.name<<'\t'<<qs.points.size()<<'\t'<<diagnostic.polygons()<<'\t'<<diagnostic.firstOrientation()<<'\t'<<stockTime<<'\t'<<diagTime<<'\t'<<preparedTime<<'\t'<<stockSetup<<'\t'<<preparedSetup<<'\t'<<diagnostic.wireTests<<'\t'<<diagnostic.ambiguous<<'\t'<<diagnostic.badWire<<'\t'<<wrong<<std::endl;
          total+=qs.points.size();mismatch+=wrong;
          std::cout<<"FACE "<<entry.first<<" wires="<<wires<<" "<<qs.name<<" fallback="<<diagnostic.ambiguous+diagnostic.badWire<<"/"<<qs.points.size()<<" stock="<<stockTime<<" prepared="<<preparedTime<<" mismatch="<<wrong<<std::endl;
        }
      }
    } catch(const Standard_Failure& e) {std::cerr<<"EXCEPTION "<<path<<" "<<e.GetMessageString()<<"\n";++failures;}
  }
  PROCESS_MEMORY_COUNTERS pm={};pm.cb=sizeof pm;GetProcessMemoryInfo(GetCurrentProcess(),&pm,sizeof pm);
  std::cout<<"VERDICT points="<<total<<" mismatches="<<mismatch<<" failures="<<failures<<" peak_ws="<<pm.PeakWorkingSetSize<<" peak_commit="<<pm.PeakPagefileUsage<<std::endl;
  return mismatch||failures?1:0;
}
