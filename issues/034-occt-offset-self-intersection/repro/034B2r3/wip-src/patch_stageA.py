p = 'C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx'
s = open(p, encoding='utf-8', newline='').read()
NL = chr(92) + 'n'


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:90], s.count(old))
    s = s.replace(old, new)


# 1. certifyRegion034c: a limit, the proof before the (lazy) boundary test
rep('''static int certifyRegion034c(const TopoDS_Face&               theF,
                             const occ::handle<Geom_Surface>& theS,
                             const double                     theDD,
                             const LensCert034c&              theCert)
{''', '''static int certifyRegion034c(const TopoDS_Face&               theF,
                             const occ::handle<Geom_Surface>& theS,
                             const double                     theDD,
                             const LensCert034c&              theCert,
                             const double                     theLimit = 0.,
                             const int                        theBudget = 32768)
{''')
rep('''  NCollection_Sequence<std::pair<gp_Pnt2d, gp_Pnt2d>> aBnd;
  double                                              aGap = 0.;
  for (TopExp_Explorer anExp(theF.Oriented(TopAbs_FORWARD), TopAbs_EDGE); anExp.More(); anExp.Next())
  {
    double                          aF, aL;
    const occ::handle<Geom2d_Curve> aC = BRep_Tool::CurveOnSurface(TopoDS::Edge(anExp.Current()), theF, aF, aL);
    if (aC.IsNull())
    {
      return LENS034C_FAIL(0);
    }
    gp_Pnt2d aPrev = aC->Value(aF);
    for (int i = 1; i <= 512; ++i)
    {
      const gp_Pnt2d aP = aC->Value(aF + (aL - aF) * i / 512.);
      const gp_Pnt2d aM = aC->Value(aF + (aL - aF) * (i - 0.5) / 512.);
      aGap = std::max(aGap, 2. * aM.Distance(gp_Pnt2d(0.5 * (aP.X() + aPrev.X()), 0.5 * (aP.Y() + aPrev.Y()))));
      aBnd.Append(std::make_pair(aPrev, aP));
      aPrev = aP;
    }
  }''', '''  NCollection_Sequence<std::pair<gp_Pnt2d, gp_Pnt2d>> aBnd;
  double                                              aGap    = 0.;
  bool                                                isBnd   = false; // computed on the first box not proven
  auto                                                aMakeBnd = [&]() {
    isBnd = true;
    for (TopExp_Explorer anExp(theF.Oriented(TopAbs_FORWARD), TopAbs_EDGE); anExp.More(); anExp.Next())
    {
      double                          aF, aL;
      const occ::handle<Geom2d_Curve> aC = BRep_Tool::CurveOnSurface(TopoDS::Edge(anExp.Current()), theF, aF, aL);
      if (aC.IsNull())
      {
        return false;
      }
      gp_Pnt2d aPrev = aC->Value(aF);
      for (int i = 1; i <= 512; ++i)
      {
        const gp_Pnt2d aP = aC->Value(aF + (aL - aF) * i / 512.);
        const gp_Pnt2d aM = aC->Value(aF + (aL - aF) * (i - 0.5) / 512.);
        aGap = std::max(aGap, 2. * aM.Distance(gp_Pnt2d(0.5 * (aP.X() + aPrev.X()), 0.5 * (aP.Y() + aPrev.Y()))));
        aBnd.Append(std::make_pair(aPrev, aP));
        aPrev = aP;
      }
    }
    return true;
  };''')
rep('''  IntTools_FClass2d aCls(theF, Precision::PConfusion());
  int               aBudget = 32768;
  while (!aStack.empty())
  {
    Patch034b aP = std::move(aStack.back());
    aStack.pop_back();
    if (--aBudget < 0)
    {
      LENS034C_TRACE("lens034c: certificate budget exhausted%s", "''' + NL + '''");
      return LENS034C_FAIL(0);
    }
    const gp_Pnt2d aMid(0.5 * (aP.U0 + aP.U1), 0.5 * (aP.V0 + aP.V1));
    const double   aDiag = std::sqrt((aP.U1 - aP.U0) * (aP.U1 - aP.U0) + (aP.V1 - aP.V0) * (aP.V1 - aP.V0));
    double         aDMin = RealLast();
    for (int i = 1; i <= aBnd.Length(); ++i)
    {
      aDMin = std::min(aDMin, aSegDist(aMid, aBnd.Value(i).first, aBnd.Value(i).second));
    }
    if (aDMin > 0.5 * aDiag + aGap && aCls.Perform(aMid) == TopAbs_OUT)
    {
      continue; // the box lies outside the region
    }
    const int aRes = patchVanishes034b(aP, theDD, 1.);
    if (aRes == 2)
    {
      continue; // both factors positive on the box
    }''', '''  std::unique_ptr<IntTools_FClass2d> aCls;
  int                                aBudget = theBudget;
  while (!aStack.empty())
  {
    Patch034b aP = std::move(aStack.back());
    aStack.pop_back();
    if (--aBudget < 0)
    {
      LENS034C_TRACE("lens034c: certificate budget exhausted%s", "''' + NL + '''");
      return LENS034C_FAIL(0);
    }
    const int aRes = patchVanishes034b(aP, theDD, 1. - theLimit);
    if (aRes == 2)
    {
      continue; // both factors above the limit on the box
    }
    const gp_Pnt2d aMid(0.5 * (aP.U0 + aP.U1), 0.5 * (aP.V0 + aP.V1));
    const double   aDiag = std::sqrt((aP.U1 - aP.U0) * (aP.U1 - aP.U0) + (aP.V1 - aP.V0) * (aP.V1 - aP.V0));
    if (!isBnd && !aMakeBnd())
    {
      return LENS034C_FAIL(0);
    }
    if (!aCls)
    {
      aCls.reset(new IntTools_FClass2d(theF, Precision::PConfusion()));
    }
    double aDMin = RealLast();
    for (int i = 1; i <= aBnd.Length(); ++i)
    {
      aDMin = std::min(aDMin, aSegDist(aMid, aBnd.Value(i).first, aBnd.Value(i).second));
    }
    if (aDMin > 0.5 * aDiag + aGap && aCls->Perform(aMid) == TopAbs_OUT)
    {
      continue; // the box lies outside the region
    }''')
rep('''        LENS034C_TRACE("lens034c:   factor at the middle %.6e, class %d, dmin %.3e diag %.3e gap %.3e''' + NL + '''", aG,
                       (int)aCls.Perform(aMid), aDMin, aDiag, aGap);''', '''        LENS034C_TRACE("lens034c:   factor at the middle %.6e, class %d, dmin %.3e diag %.3e gap %.3e''' + NL + '''", aG,
                       (int)aCls->Perform(aMid), aDMin, aDiag, aGap);''')
# 2. wrapper for stage A, defined after certifyRegion034c
anchor = '''//! Parameters of the points of a lens (length along the traced curve in the'''
rep(anchor, '''//! Stage A detection, certified part (issue 034 B2 round 3): 0 when the
//! interval bound cannot show both principal factors above the stage A
//! trigger on the whole face (a narrow fold between the samples, or a factor
//! close to it: the result is then checked), 1 proven, -1 not applicable (no
//! exact Bezier form: the samples decide, as before). The budget bounds the
//! cost; an exhausted budget is "not proven" (a check, never a skipped one).
static int certifyFoldTrigger034c(const TopoDS_Face& theF, const occ::handle<Geom_Surface>& theS, const double theDD)
{
  try
  {
    OCC_CATCH_SIGNALS
    const LensCert034c aNone;
    return certifyRegion034c(theF, theS, theDD, aNone, THE_FOLD_TRIGGER_034, 4096);
  }
  catch (Standard_Failure const&)
  {
    return 0;
  }
}

''' + anchor)
# 3. stage A: forward declaration + the certified part after the samples
rep('''//! True if the offset of the face by theOffset (along the outward normal of
//! the face in its shape) can fold, i.e. some sampled offset factor is below
//! THE_FOLD_TRIGGER_034. Exceptions count as "can fold" (the result is checked).
static bool faceMayFold034(const TopoDS_Face& theF, const double theOffset)''', '''static int certifyFoldTrigger034c(const TopoDS_Face&               theF,
                                  const occ::handle<Geom_Surface>& theS,
                                  const double                     theDD);

//! True if the offset of the face by theOffset (along the outward normal of
//! the face in its shape) can fold, i.e. some sampled offset factor is below
//! THE_FOLD_TRIGGER_034 (round 3 of lane B2: or, for a free-form face with an
//! exact Bezier form, the interval bound cannot show every factor above it).
//! Exceptions count as "can fold" (the result is checked).
static bool faceMayFold034(const TopoDS_Face& theF, const double theOffset)''')
rep('''          if (aFct < THE_FOLD_TRIGGER_034)
          {
            return true;
          }
          if (aFct < aMin)
          {
            aMin    = aFct;
            aMinU   = aU;
            aMinV   = aV;
            isMoved = true;
          }
        }
        if (!isMoved)
        {
          aHU *= 0.5;
          aHV *= 0.5;
        }
      }
    }
    return false;''', '''          if (aFct < THE_FOLD_TRIGGER_034)
          {
            return true;
          }
          if (aFct < aMin)
          {
            aMin    = aFct;
            aMinU   = aU;
            aMinV   = aV;
            isMoved = true;
          }
        }
        if (!isMoved)
        {
          aHU *= 0.5;
          aHV *= 0.5;
        }
      }
    }
    // Issue 034 lane B2 round 3: a narrow fold between the samples (a crest
    // of a B-spline profile, a small bump) is caught by the interval bound of
    // the principal factors on the Bezier patches of the face
    switch (aType)
    {
      case GeomAbs_BSplineSurface:
      case GeomAbs_BezierSurface:
      case GeomAbs_SurfaceOfExtrusion:
      case GeomAbs_SurfaceOfRevolution: {
        occ::handle<Geom_Surface> aB = aS;
        while (!occ::down_cast<Geom_RectangularTrimmedSurface>(aB).IsNull())
        {
          aB = occ::down_cast<Geom_RectangularTrimmedSurface>(aB)->BasisSurface();
        }
        if (certifyFoldTrigger034c(theF, aB, aD) == 0)
        {
          return true;
        }
        break;
      }
      default:
        break;
    }
    return false;''')
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
