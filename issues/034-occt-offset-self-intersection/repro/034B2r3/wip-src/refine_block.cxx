//! Parameters of the points of a lens (length along the traced curve in the
//! scaled variables, in which both preimages are smooth up to the miter
//! points, where s passes through 0 linearly) and interpolants of the two
//! preimage curves.
static bool lensParams034c(const XTracer034c&              theTr,
                           NCollection_Sequence<XPt034c>& thePts,
                           occ::handle<Geom2d_Curve>&     theC1,
                           occ::handle<Geom2d_Curve>&     theC2)
{
  const int aN = thePts.Length();
  if (aN < 2)
  {
    return false;
  }
  thePts.ChangeValue(1).L = 0.;
  for (int i = 2; i <= aN; ++i)
  {
    double aD = 0.;
    for (int k = 0; k < 4; ++k)
    {
      const double aX = (thePts.Value(i).C[k] - thePts.Value(i - 1).C[k]) * theTr.Scale(k);
      aD += aX * aX;
    }
    aD = std::sqrt(aD);
    if (!(aD > 0.))
    {
      return false;
    }
    thePts.ChangeValue(i).L = thePts.Value(i - 1).L + aD;
  }
  occ::handle<NCollection_HArray1<gp_Pnt2d>> aP1  = new NCollection_HArray1<gp_Pnt2d>(1, aN);
  occ::handle<NCollection_HArray1<gp_Pnt2d>> aP2  = new NCollection_HArray1<gp_Pnt2d>(1, aN);
  occ::handle<NCollection_HArray1<double>>   aPar = new NCollection_HArray1<double>(1, aN);
  for (int i = 1; i <= aN; ++i)
  {
    aP1->SetValue(i, thePts.Value(i).P);
    aP2->SetValue(i, thePts.Value(i).Q);
    aPar->SetValue(i, thePts.Value(i).L);
  }
  Geom2dAPI_Interpolate anI1(aP1, aPar, false, Precision::PConfusion());
  Geom2dAPI_Interpolate anI2(aP2, aPar, false, Precision::PConfusion());
  anI1.Perform();
  anI2.Perform();
  if (!anI1.IsDone() || !anI2.IsDone())
  {
    return false;
  }
  theC1 = anI1.Curve();
  theC2 = anI2.Curve();
  return true;
}

//! Adds exact points of X (corrector of the tracer from the middle of an
//! interval) where the offsets of the interpolated preimage curves differ by
//! more than theTol in the middle of the interval. False when a point cannot
//! be corrected or the refinement does not converge (out of scope).
static bool refineLens034c(const XTracer034c&              theTr,
                           const Geom_Surface&             theS,
                           const double                    theDD,
                           NCollection_Sequence<XPt034c>& thePts,
                           const double                    theTol)
{
  for (int aRound = 0; aRound < 24; ++aRound)
  {
    occ::handle<Geom2d_Curve> aC1, aC2;
    if (!lensParams034c(theTr, thePts, aC1, aC2))
    {
      return LENS034C_FAIL(false);
    }
    NCollection_Sequence<XPt034c> aNew;
    int                           anAdded = 0;
    double                        aWorst  = 0.;
    aNew.Append(thePts.First());
    for (int i = 1; i < thePts.Length(); ++i)
    {
      const XPt034c&    aA   = thePts.Value(i);
      const XPt034c&    aB   = thePts.Value(i + 1);
      const double      aLm  = 0.5 * (aA.L + aB.L);
      const gp_Pnt2d    aP   = aC1->Value(aLm);
      const gp_Pnt2d    aQ   = aC2->Value(aLm);
      const OffEval034c anEp = offD1034c(theS, aP.X(), aP.Y(), theDD);
      const OffEval034c anEq = offD1034c(theS, aQ.X(), aQ.Y(), theDD);
      if (!anEp.Ok || !anEq.Ok)
      {
        return LENS034C_FAIL(false);
      }
      const double aDev = anEp.O.Distance(anEq.O);
      aWorst            = std::max(aWorst, aDev);
      if (aDev > theTol)
      {
        // the exact point of X near the middle: corrector on the hyperplane
        // through the middle of the chord, normal to the chord
        double aX[4], aT[4], aYp[4], aTn = 0.;
        for (int k = 0; k < 4; ++k)
        {
          aX[k]  = 0.5 * (aA.C[k] + aB.C[k]);
          aT[k]  = (aB.C[k] - aA.C[k]) * theTr.Scale(k);
          aYp[k] = aX[k] * theTr.Scale(k);
          aTn += aT[k] * aT[k];
        }
        aTn = std::sqrt(aTn);
        if (!(aTn > 0.))
        {
          return LENS034C_FAIL(false);
        }
        for (int k = 0; k < 4; ++k)
        {
          aT[k] /= aTn;
        }
        int anIt = 0;
        if (!theTr.Correct(aX, aT, aYp, anIt, 1.e-3 * theTol) || !(aX[3] > 0.))
        {
          return LENS034C_FAIL(false);
        }
        XPt034c aM;
        double  aG[3], aJ[3][4];
        if (!theTr.Eval(aX, aG, aJ, &aM))
        {
          return LENS034C_FAIL(false);
        }
        aNew.Append(aM);
        ++anAdded;
      }
      aNew.Append(aB);
    }
    LENS034C_TRACE("lens034c: refine round %d points %d worst %.3e added %d\n", aRound, thePts.Length(), aWorst,
                   anAdded);
    thePts = aNew;
    if (anAdded == 0)
    {
      return true;
    }
    if (thePts.Length() > 4000)
    {
      return LENS034C_FAIL(false);
    }
  }
  return LENS034C_FAIL(false);
}

