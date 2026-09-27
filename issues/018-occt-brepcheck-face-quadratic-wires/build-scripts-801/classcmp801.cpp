// classcmp801.cpp -- defect 018, ported to OCCT 8.0.1 (types and line references only): BRepCheck_WireClass2d (generated copy of BRepTopAdaptor_FClass2d, compiled INTO this
// exe from the OCCT worktree) against the original BRepTopAdaptor_FClass2d of the TKTopAlgo.dll found on PATH.
// For every wire of every face with >= 2 wires of the listed shapes, the one-wire face is built exactly like
// BRepCheck_Face::ClassifyWires builds it (BRepCheck_Face.cxx:368-378 @V8_0_1), then:
//   1) PerformInfinitePoint() of copy and original are equal;
//   2) Perform(P, false) of copy and original are equal for P = the point the original IsInside()
//      classifies for every other wire of the face (its code, BRepCheck_Face.cxx:871-944 @V8_0_1), a 9 x 9 grid over the
//      wire's (u, v) box enlarged 3 times around its centre, and 64 seeded random points in that enlarged box;
//   3) wherever the copy says IsFarOutside(P), the ORIGINAL returns the copy's OutsideState() (the shortcut is sound)
//      and does not throw (a skipped Perform must not hide an exception of stock); a throw from the copy's own
//      IsFarOutside/NearBox (calls stock never makes) is a failure too (FARWRONG/NEAROUT);
//   4) every P that is not IsFarOutside lies inside the copy's NearBox() when NearBox() is true.
// Every call of the two classifiers (constructor, PerformInfinitePoint, Perform) runs in its own try: an outcome is
// a state or an exception (its dynamic type and message). The same exception in both is the same answer - counted in
// same_exc, not a failure; different outcomes are a MISMATCH. A throwing constructor in both ends that wire (nothing
// left to compare). An exception outside the classifier calls (the harness's own point selection or UV bounds) is an
// EXCEPTION line and ends that wire, not a failure (both classifiers never saw it).
// Usage: classcmp <list.txt> <out.tsv>      (a Job Object caps the process at 1 GB of committed memory; CHECKCMP_CAP_MB lowers it)
//   one line per shape: file, wires, points, mismatches (1+2), far, far_wrong (3), near_outside_box (4), same_exc
// and lines "MISMATCH/FARWRONG/NEAROUT\t..." for the first 20 failures, "SAMEEXC/EXCEPTION\t..." for the first 20
// notes. Exit code 1 if mismatches + far_wrong + near_outside_box is not 0 - the one gate.
// Additions to the plan's text (marked "addition"): per wire also the ends/middles of its own pcurves (boundary), 13
// non-finite/huge points and the two points at the edge of IsFarOutside on 8 rays; a line
// "FALLBACK\t<file>\torien-1 n\tnopoly n\tother n" for shapes with wires whose classifier cannot use the shortcut.
#include <BRepCheck_WireClass2d.hxx>

#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepTools.hxx>
#include <BRepTopAdaptor_FClass2d.hxx>
#include <Bnd_Box2d.hxx>
#include <Geom2d_Curve.hxx>
#include <Geom_Curve.hxx>
#include <Precision.hxx>
#include <Standard_Failure.hxx>
#include <Standard_Type.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <NCollection_IndexedMap.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Wire.hxx>
#include <windows.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <fstream>
#include <memory>
#include <random>
#include <string>
#include <vector>

// Addition to the plan (review of Task 1, note 3): which wires take the fallback path of the classifier
// (TabOrien(1) == -1: Perform goes to BRepClass_FaceClassifier) and which have no usable polygon for IsFarOutside.
// Private members of the copy are read through the standard explicit-instantiation rule (access checks do not apply
// to the template arguments of an explicit instantiation); the OCCT header stays as the plan writes it.
template <class Tag, typename Tag::type M> struct PrivateOf { friend typename Tag::type get (Tag) { return M; } };
struct OrienTag { typedef NCollection_Sequence<int> BRepCheck_WireClass2d::*type; friend type get (OrienTag); };
struct ClassTag { typedef NCollection_Sequence<CSLib_Class2d> BRepCheck_WireClass2d::*type; friend type get (ClassTag); };
struct PolyOkTag { typedef bool BRepCheck_WireClass2d::*type; friend type get (PolyOkTag); };
template struct PrivateOf<OrienTag, &BRepCheck_WireClass2d::TabOrien>;
template struct PrivateOf<ClassTag, &BRepCheck_WireClass2d::TabClass>;
template struct PrivateOf<PolyOkTag, &BRepCheck_WireClass2d::myPolyOk>;

static void capMemory (SIZE_T bytes)   // the cap of checkcmp: 1 GB of committed memory
{
  HANDLE job = CreateJobObjectW (nullptr, nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
  li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY;
  li.ProcessMemoryLimit = bytes;
  SetInformationJobObject (job, JobObjectExtendedLimitInformation, &li, sizeof (li));
  AssignProcessToJobObject (job, GetCurrentProcess());
}

// the outcome of one classifier call: a state, or the exception it threw ("<type>: <message>")
struct Outcome
{
  int state = -1;
  std::string exc;
  bool operator== (const Outcome& o) const { return state == o.state && exc == o.exc; }
  std::string str() const { return exc.empty() ? std::to_string (state) : exc; }
};

template <class F> static Outcome outcomeOf (F f)
{
  Outcome r;
  try { r.state = (int) f(); }
  catch (const Standard_Failure& e) { r.exc = std::string (e.ExceptionType()) + ": " + e.GetMessageString(); }
  catch (...) { r.exc = "non-OCCT exception"; }
  return r;
}

// == the point selection of IsInside(), BRepCheck_Face.cxx:876-930 @V8_0_1
static bool pointOf (const TopoDS_Wire& theWire, const TopoDS_Face& theFace, gp_Pnt2d& thePoint)
{
  double aParameter, aFirst, aLast;
  for (TopExp_Explorer anExplorer (theWire, TopAbs_EDGE); anExplorer.More(); anExplorer.Next())
  {
    const TopoDS_Edge& anEdge = TopoDS::Edge (anExplorer.Current());
    Handle(Geom2d_Curve) aCurve2D = BRep_Tool::CurveOnSurface (anEdge, theFace, aFirst, aLast);
    if (!Precision::IsNegativeInfinite (aFirst) && !Precision::IsPositiveInfinite (aLast))
    {
      aParameter = (aFirst + aLast) * 0.5;
      if (Abs (aParameter - aFirst) < Precision::PConfusion()) continue;
      double aFirst3D, aLast3D;
      Handle(Geom_Curve) aCurve = BRep_Tool::Curve (anEdge, aFirst3D, aLast3D);
      if (aCurve.IsNull()) continue;
      gp_Pnt aPoints[2];
      aCurve->D0 (aFirst, aPoints[0]);
      aCurve->D0 ((aFirst3D + aLast3D) / 2., aPoints[1]);
      if (aPoints[0].Distance (aPoints[1]) < Precision::Confusion()) continue;
    }
    else if (Precision::IsNegativeInfinite (aFirst) && Precision::IsPositiveInfinite (aLast)) aParameter = 0.;
    else if (Precision::IsNegativeInfinite (aFirst)) aParameter = aLast - 1.;
    else aParameter = aFirst + 1.;
    thePoint = aCurve2D->Value (aParameter);
    return true;
  }
  return false;
}

int main (int argc, char** argv)
{
  if (argc < 3) { std::fprintf (stderr, "usage: classcmp <list.txt> <out.tsv>\n"); return 2; }
  // owner RAM budget 23.09: at most 1 GB per test process; CHECKCMP_CAP_MB can only lower it
  SIZE_T aCapMb = 1024;
  if (const char* anEnv = std::getenv ("CHECKCMP_CAP_MB"))
  {
    const long aV = std::atol (anEnv);
    if (aV > 0 && (SIZE_T) aV < aCapMb) aCapMb = (SIZE_T) aV;
  }
  capMemory (aCapMb << 20);
  std::vector<std::string> files;
  { std::ifstream in (argv[1]); std::string line;
    while (std::getline (in, line)) { if (!line.empty() && line.back() == '\r') line.pop_back(); if (!line.empty()) files.push_back (line); } }
  FILE* out = std::fopen (argv[2], "a");
  long allBad = 0;
  int printed = 0, noted = 0;
  for (const std::string& file : files)
  {
    TopoDS_Shape shape; BRep_Builder bb;
    if (!BRepTools::Read (shape, file.c_str(), bb)) { std::fprintf (out, "%s\tREADFAIL\n", file.c_str()); continue; }
    long wires = 0, points = 0, mism = 0, farCount = 0, farWrong = 0, nearOut = 0, sameExc = 0;
    long fbOrien = 0, fbNoPoly = 0, fbMulti = 0, fbNone = 0;   // addition: fallback report (FALLBACK line)
    NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> faces; TopExp::MapShapes (shape, TopAbs_FACE, faces);
    for (int k = 1; k <= faces.Extent(); ++k)
    {
      const TopoDS_Face& F = TopoDS::Face (faces (k));
      std::vector<TopoDS_Wire> ws;
      for (TopExp_Explorer e (F.Oriented (TopAbs_FORWARD), TopAbs_WIRE); e.More(); e.Next()) ws.push_back (TopoDS::Wire (e.Current()));
      if (ws.size() < 2) continue;
      for (size_t i = 0; i < ws.size(); ++i)
      {
        try
        {
          ++wires;
          BRep_Builder B;
          TopoDS_Shape aLocal = F.EmptyCopied();
          TopoDS_Face nf = TopoDS::Face (aLocal);
          nf.Orientation (TopAbs_FORWARD);
          B.Add (nf, ws[i]);
          std::unique_ptr<BRepTopAdaptor_FClass2d> origP;
          std::unique_ptr<BRepCheck_WireClass2d> copyP;
          const Outcome mo = outcomeOf ([&] { origP.reset (new BRepTopAdaptor_FClass2d (nf, Precision::PConfusion())); return 0; });
          const Outcome mc = outcomeOf ([&] { copyP.reset (new BRepCheck_WireClass2d (nf, Precision::PConfusion())); return 0; });
          if (!(mo == mc))
          {
            ++mism;
            if (printed++ < 20) std::fprintf (out, "MISMATCH\t%s\tface %d wire %d\tconstructor\torig %s copy %s\n", file.c_str(), k, (int) i, mo.str().c_str(), mc.str().c_str());
            continue;
          }
          if (!mo.exc.empty())
          {
            ++sameExc;
            if (noted++ < 20) std::fprintf (out, "SAMEEXC\t%s\tface %d wire %d\tconstructor\t%s\n", file.c_str(), k, (int) i, mo.exc.c_str());
            continue;
          }
          BRepTopAdaptor_FClass2d& orig = *origP;
          BRepCheck_WireClass2d& copy = *copyP;
          {   // addition: which path Perform() takes for this one-wire classifier
            const int nClass = (copy.*get (ClassTag())).Length();
            const NCollection_Sequence<int>& orien = copy.*get (OrienTag());
            if (nClass == 0) ++fbNone;
            else if (orien (1) == -1) ++fbOrien;
            else if (nClass != 1) ++fbMulti;
            else if (!(copy.*get (PolyOkTag()))) ++fbNoPoly;
          }
          const Outcome io = outcomeOf ([&] { return orig.PerformInfinitePoint(); });
          const Outcome ic = outcomeOf ([&] { return copy.PerformInfinitePoint(); });
          if (!(io == ic))
          {
            ++mism;
            if (printed++ < 20) std::fprintf (out, "MISMATCH\t%s\tface %d wire %d\tinfinite point\torig %s copy %s\n", file.c_str(), k, (int) i, io.str().c_str(), ic.str().c_str());
          }
          else if (!io.exc.empty())
          {
            ++sameExc;
            if (noted++ < 20) std::fprintf (out, "SAMEEXC\t%s\tface %d wire %d\tinfinite point\t%s\n", file.c_str(), k, (int) i, io.exc.c_str());
          }
          std::vector<gp_Pnt2d> pts;
          for (size_t j = 0; j < ws.size(); ++j) { gp_Pnt2d p; if (j != i && pointOf (ws[j], nf, p)) pts.push_back (p); }
          Bnd_Box2d box; BRepTools::AddUVBounds (nf, box);
          if (!box.IsVoid())
          {
            double u0, v0, u1, v1; box.Get (u0, v0, u1, v1);
            const double cu = 0.5 * (u0 + u1), cv = 0.5 * (v0 + v1), hu = 1.5 * (u1 - u0) + 1e-6, hv = 1.5 * (v1 - v0) + 1e-6;
            for (int a = 0; a < 9; ++a)
              for (int b = 0; b < 9; ++b)
                pts.push_back (gp_Pnt2d (cu - hu + 2. * hu * a / 8., cv - hv + 2. * hv * b / 8.));
            std::mt19937 rng ((unsigned) (k * 7919 + i));
            std::uniform_real_distribution<double> ru (cu - hu, cu + hu), rv (cv - hv, cv + hv);
            for (int r = 0; r < 64; ++r) pts.push_back (gp_Pnt2d (ru (rng), rv (rng)));
            // addition: points on the boundary of the wire itself (ends and middles of its first 16 pcurves) and
            // non-finite / huge coordinates - the copy must give the original's answer on these too
            int ne = 0;
            for (TopExp_Explorer e (ws[i], TopAbs_EDGE); e.More() && ne < 16; e.Next(), ++ne)
            {
              double f, l;
              Handle(Geom2d_Curve) c2 = BRep_Tool::CurveOnSurface (TopoDS::Edge (e.Current()), nf, f, l);
              if (c2.IsNull() || Precision::IsInfinite (f) || Precision::IsInfinite (l)) continue;
              pts.push_back (c2->Value (f)); pts.push_back (c2->Value (l)); pts.push_back (c2->Value (0.5 * (f + l)));
            }
            const double nan = std::numeric_limits<double>::quiet_NaN(), inf = std::numeric_limits<double>::infinity();
            const double sp[][2] = { {nan, cv}, {cu, nan}, {nan, nan}, {inf, cv}, {-inf, cv}, {cu, inf}, {cu, -inf},
                                     {inf, inf}, {-inf, -inf}, {1e300, cv}, {-1e300, cv}, {cu, 1e300}, {cu, -1e300} };
            for (const auto& q : sp) pts.push_back (gp_Pnt2d (q[0], q[1]));
          }
          double nu0 = 0., nv0 = 0., nu1 = 0., nv1 = 0.;
          // NearBox and IsFarOutside are calls stock never makes: a throw there would change the analyzer's outcome
          const Outcome nb = outcomeOf ([&] { return copy.NearBox (nu0, nv0, nu1, nv1)  ? 1 : 0; });
          if (!nb.exc.empty())
          {
            ++nearOut;
            if (printed++ < 20) std::fprintf (out, "NEAROUT\t%s\tface %d wire %d\tNearBox threw %s\n", file.c_str(), k, (int) i, nb.exc.c_str());
          }
          const bool hasNear = nb.state == 1;
          if (!box.IsVoid())
          {   // addition: the sharp edge of IsFarOutside - bisect along 8 rays from the box centre to the first
              // "far" point and test the last point that is not far and the first that is
            double u0, v0, u1, v1; box.Get (u0, v0, u1, v1);
            const double cu = 0.5 * (u0 + u1), cv = 0.5 * (v0 + v1), hu = (u1 - u0) + 1e-6, hv = (v1 - v0) + 1e-6;
            const int dirs[8][2] = { {1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {-1, -1}, {1, -1}, {-1, 1} };
            for (const auto& d : dirs)
            {
              auto at = [&] (double t) { return gp_Pnt2d (cu + d[0] * hu * t, cv + d[1] * hv * t); };
              double lo = 0., hi = 1e6;
              if (copy.IsFarOutside (at (lo)) || !copy.IsFarOutside (at (hi))) continue;
              for (int it = 0; it < 200; ++it)
              {
                const double m = 0.5 * (lo + hi);
                if (m <= lo || m >= hi) break;
                (copy.IsFarOutside (at (m)) ? hi : lo) = m;
              }
              pts.push_back (at (lo)); pts.push_back (at (hi));
            }
          }
          for (const gp_Pnt2d& p : pts)
          {
            ++points;
            const Outcome so = outcomeOf ([&] { return orig.Perform (p, false); });
            const Outcome sc = outcomeOf ([&] { return copy.Perform (p, false); });
            if (!(so == sc))
            {
              ++mism;
              if (printed++ < 20) std::fprintf (out, "MISMATCH\t%s\tface %d wire %d\tP %.17g %.17g\torig %s copy %s\n", file.c_str(), k, (int) i, p.X(), p.Y(), so.str().c_str(), sc.str().c_str());
            }
            else if (!so.exc.empty())
            {
              ++sameExc;
              if (noted++ < 20) std::fprintf (out, "SAMEEXC\t%s\tface %d wire %d\tP %.17g %.17g\t%s\n", file.c_str(), k, (int) i, p.X(), p.Y(), so.exc.c_str());
            }
            const Outcome fo = outcomeOf ([&] { return copy.IsFarOutside (p) ? 1 : 0; });
            if (!fo.exc.empty())
            {
              ++farWrong;
              if (printed++ < 20) std::fprintf (out, "FARWRONG\t%s\tface %d wire %d\tP %.17g %.17g\tIsFarOutside threw %s\n", file.c_str(), k, (int) i, p.X(), p.Y(), fo.exc.c_str());
            }
            else if (fo.state == 1)
            {
              ++farCount;
              if (!so.exc.empty() || so.state != (int) copy.OutsideState())
              {
                ++farWrong;
                if (printed++ < 20) std::fprintf (out, "FARWRONG\t%s\tface %d wire %d\tP %.17g %.17g\torig %s\n", file.c_str(), k, (int) i, p.X(), p.Y(), so.str().c_str());
              }
            }
            else if (hasNear && std::isfinite (p.X()) && std::isfinite (p.Y())   // NearBox covers finite points only
                     && (p.X() < nu0 || p.X() > nu1 || p.Y() < nv0 || p.Y() > nv1))
            {
              ++nearOut;
              if (printed++ < 20) std::fprintf (out, "NEAROUT\t%s\tface %d wire %d\tP %.17g %.17g\n", file.c_str(), k, (int) i, p.X(), p.Y());
            }
          }
        }
        catch (const Standard_Failure& e)   // outside the compared calls: the harness's point selection, UV bounds
        {
          if (noted++ < 20) std::fprintf (out, "EXCEPTION\t%s\tface %d wire %d\t%s: %s\n", file.c_str(), k, (int) i, e.ExceptionType(), e.GetMessageString());
        }
      }
    }
    std::fprintf (out, "%s\t%ld\t%ld\t%ld\t%ld\t%ld\t%ld\t%ld\n", file.c_str(), wires, points, mism, farCount, farWrong, nearOut, sameExc);
    if (fbOrien + fbNoPoly + fbMulti + fbNone)   // addition: 5 fields, never taken for the 8-field shape line
      std::fprintf (out, "FALLBACK\t%s\torien-1 %ld\tnopoly %ld\tother %ld\n", file.c_str(), fbOrien, fbNoPoly, fbMulti + fbNone);
    std::fflush (out);
    allBad += mism + farWrong + nearOut;
  }
  std::fclose (out);
  return allBad ? 1 : 0;
}
