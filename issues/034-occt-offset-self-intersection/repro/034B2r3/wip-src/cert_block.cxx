//=======================================================================
// Issue 034 lane B2 round 3: certificate of the lenses of a face.
//
// The lens search finds the folds from samples; the certificate proves, with
// the interval bounds of the round-2 vanishing proof (Bezier patches, rounded
// interval arithmetic, patchVanishes034b), that BOTH principal offset factors
// are positive at every point of the face outside the lenses: the offset of
// the kept pieces is regular (no fold is left in the result). A patch box is
//  - skipped when it lies outside the face or inside a lens (with a margin
//    that covers the chords of the lens polygon),
//  - proven when the factors are bounded away from 0 on the whole box,
//  - cut in two otherwise.
// A box that stays unresolved at the depth limit is accepted only in the
// neighbourhood of a miter point (the end of the self-intersection curve on
// the fold, where a factor is 0 at a point of the lens boundary: no interval
// bound can separate it - the miter point region of Park-Hong-Kim-Elber, CAGD
// 2021) or of the part of the face boundary between the two preimages of an
// exit (the fold meets the boundary inside the lens there). Any other
// unresolved box, a box of a fold everywhere outside the lenses, or a surface
// without an exact Bezier form refutes the certificate (the face is then out
// of the scope of the lens pass: an error, never a silent result).
//=======================================================================

//! Bezier patches of theS over [U0,U1]x[V0,V1]: B-spline / Bezier surfaces
//! directly, other surfaces through their exact B-spline form (extrusions and
//! revolutions of B-spline curves and conics). False when there is none.
static bool bezierPatches034c(const occ::handle<Geom_Surface>& theS,
                              const double                     theU0,
                              const double                     theU1,
                              const double                     theV0,
                              const double                     theV1,
                              std::vector<Patch034b>&          thePatches)
{
  occ::handle<Geom_Surface> aS = theS;
  while (!occ::down_cast<Geom_RectangularTrimmedSurface>(aS).IsNull())
  {
    aS = occ::down_cast<Geom_RectangularTrimmedSurface>(aS)->BasisSurface();
  }
  if (occ::handle<Geom_BezierSurface> aBz = occ::down_cast<Geom_BezierSurface>(aS))
  {
    const double aU0 = std::max(theU0, 0.), aU1 = std::min(theU1, 1.);
    const double aV0 = std::max(theV0, 0.), aV1 = std::min(theV1, 1.);
    if (!(aU1 > aU0) || !(aV1 > aV0))
    {
      return false;
    }
    occ::handle<Geom_BezierSurface> aSeg = occ::down_cast<Geom_BezierSurface>(aBz->Copy());
    aSeg->Segment(aU0, aU1, aV0, aV1);
    Patch034b aP;
    if (!bezierPatch034b(aSeg, aU0, aU1, aV0, aV1, aP))
    {
      return false;
    }
    thePatches.push_back(std::move(aP));
    return true;
  }
  occ::handle<Geom_BSplineSurface> aBS = occ::down_cast<Geom_BSplineSurface>(aS);
  if (aBS.IsNull())
  {
    const GeomAbs_SurfaceType aT = GeomAdaptor_Surface(aS).GetType();
    if (aT != GeomAbs_SurfaceOfExtrusion && aT != GeomAbs_SurfaceOfRevolution)
    {
      return false;
    }
    try
    {
      OCC_CATCH_SIGNALS
      aBS = GeomConvert::SurfaceToBSplineSurface(aS);
    }
    catch (Standard_Failure const&)
    {
      return false;
    }
    if (aBS.IsNull())
    {
      return false;
    }
  }
  else
  {
    aBS = occ::down_cast<Geom_BSplineSurface>(aBS->Copy());
  }
  // a periodic form is clamped over one period (the same geometry); the face
  // range is taken inside the knot range by whole periods
  double aSU0, aSU1, aSV0, aSV1;
  aBS->Bounds(aSU0, aSU1, aSV0, aSV1);
  double aU0 = theU0, aU1 = theU1, aV0 = theV0, aV1 = theV1;
  if (aBS->IsUPeriodic())
  {
    const double aT = aBS->UPeriod();
    const double aK = std::floor((aU0 - aSU0) / aT + Precision::PConfusion());
    aU0 -= aK * aT;
    aU1 -= aK * aT;
    aBS->SetUNotPeriodic();
    aBS->Bounds(aSU0, aSU1, aSV0, aSV1);
    if (aU1 > aSU1 + Precision::PConfusion())
    {
      return false; // the face crosses the seam of the B-spline form
    }
  }
  if (aBS->IsVPeriodic())
  {
    const double aT = aBS->VPeriod();
    const double aK = std::floor((aV0 - aSV0) / aT + Precision::PConfusion());
    aV0 -= aK * aT;
    aV1 -= aK * aT;
    aBS->SetVNotPeriodic();
    aBS->Bounds(aSU0, aSU1, aSV0, aSV1);
    if (aV1 > aSV1 + Precision::PConfusion())
    {
      return false;
    }
  }
  aU0 = std::max(aU0, aSU0);
  aU1 = std::min(aU1, aSU1);
  aV0 = std::max(aV0, aSV0);
  aV1 = std::min(aV1, aSV1);
  if (!(aU1 - aU0 > Precision::PConfusion()) || !(aV1 - aV0 > Precision::PConfusion()))
  {
    return false;
  }
  // parameters of the converted form = parameters of the face (checked on
  // the middle of the range: the conversion keeps the parametrisation)
  {
    const double aUm = 0.5 * (aU0 + aU1), aVm = 0.5 * (aV0 + aV1);
    const double aShiftU = aUm - 0.5 * (theU0 + theU1), aShiftV = aVm - 0.5 * (theV0 + theV1);
    const gp_Pnt aP1 = aBS->Value(aUm, aVm), aP2 = theS->Value(aUm - aShiftU, aVm - aShiftV);
    if (aP1.Distance(aP2) > 1.e-9 * (1. + aP1.XYZ().Modulus()))
    {
      return false;
    }
  }
  GeomConvert_BSplineSurfaceToBezierSurface aConv(aBS, aU0, aU1, aV0, aV1, Precision::PConfusion());
  NCollection_Array1<double> aUK(1, aConv.NbUPatches() + 1), aVK(1, aConv.NbVPatches() + 1);
  aConv.UKnots(aUK);
  aConv.VKnots(aVK);
  // the patch boxes are expressed in the parameters of the face
  const double aDU = aU0 - theU0, aDV = aV0 - theV0;
  for (int i = 1; i <= aConv.NbUPatches(); ++i)
  {
    for (int j = 1; j <= aConv.NbVPatches(); ++j)
    {
      Patch034b aP;
      if (!bezierPatch034b(aConv.Patch(i, j), aUK(i) - aDU, aUK(i + 1) - aDU, aVK(j) - aDV, aVK(j + 1) - aDV, aP))
      {
        return false;
      }
      thePatches.push_back(std::move(aP));
    }
  }
  return true;
}

//! Lens polygons and singular points of a face for the certificate
struct LensCert034c
{
  NCollection_Sequence<NCollection_Sequence<gp_Pnt2d>> Polys;  //!< closed lens polygons (unwrapped UV)
  NCollection_Sequence<gp_Pnt2d>                       Miters; //!< miter points (unwrapped UV)
  NCollection_Sequence<std::pair<gp_Pnt2d, gp_Pnt2d>>  Exits;  //!< face boundary segments inside a lens
  double UPer = 0., VPer = 0.;
  double Margin = 0.; //!< covers the chords of the polygons (UV)
};

//! true if the (closed) box meets the segment
static bool boxMeetsSegment034c(const double theU0, const double theU1, const double theV0, const double theV1,
                                const gp_Pnt2d& theA, const gp_Pnt2d& theB)
{
  // Liang-Barsky clipping
  double       aT0 = 0., aT1 = 1.;
  const double aDx = theB.X() - theA.X(), aDy = theB.Y() - theA.Y();
  const double aP[4] = {-aDx, aDx, -aDy, aDy};
  const double aQ[4] = {theA.X() - theU0, theU1 - theA.X(), theA.Y() - theV0, theV1 - theA.Y()};
  for (int k = 0; k < 4; ++k)
  {
    if (aP[k] == 0.)
    {
      if (aQ[k] < 0.)
      {
        return false;
      }
      continue;
    }
    const double aR = aQ[k] / aP[k];
    if (aP[k] < 0.)
    {
      aT0 = std::max(aT0, aR);
    }
    else
    {
      aT1 = std::min(aT1, aR);
    }
    if (aT0 > aT1)
    {
      return false;
    }
  }
  return true;
}

//! box position against the lenses: 1 inside a lens (with the margin), 0 not
static int boxInLens034c(const LensCert034c& theC, double theU0, double theU1, double theV0, double theV1)
{
  theU0 -= theC.Margin;
  theU1 += theC.Margin;
  theV0 -= theC.Margin;
  theV1 += theC.Margin;
  for (int l = 1; l <= theC.Polys.Length(); ++l)
  {
    const NCollection_Sequence<gp_Pnt2d>& aPoly = theC.Polys.Value(l);
    for (int aKu = -1; aKu <= 1; ++aKu)
    {
      for (int aKv = -1; aKv <= 1; ++aKv)
      {
        if ((aKu != 0 && theC.UPer == 0.) || (aKv != 0 && theC.VPer == 0.))
        {
          continue;
        }
        const double aSu = aKu * theC.UPer, aSv = aKv * theC.VPer;
        // the four corners inside, no edge of the polygon meets the box
        bool isIn = inPoly034c(aPoly, gp_Pnt2d(theU0 - aSu, theV0 - aSv))
                    && inPoly034c(aPoly, gp_Pnt2d(theU1 - aSu, theV0 - aSv))
                    && inPoly034c(aPoly, gp_Pnt2d(theU0 - aSu, theV1 - aSv))
                    && inPoly034c(aPoly, gp_Pnt2d(theU1 - aSu, theV1 - aSv));
        for (int a = 1; isIn && a <= aPoly.Length(); ++a)
        {
          const gp_Pnt2d& aA = aPoly.Value(a);
          const gp_Pnt2d& aB = aPoly.Value(a == aPoly.Length() ? 1 : a + 1);
          isIn = !boxMeetsSegment034c(theU0 - aSu, theU1 - aSu, theV0 - aSv, theV1 - aSv, aA, aB);
        }
        if (isIn)
        {
          return 1;
        }
      }
    }
  }
  return 0;
}

//! true if the box lies in the region of a miter point or of an exit
//! segment (see the header of this block)
static bool boxSingular034c(const LensCert034c& theC, const double theU0, const double theU1, const double theV0,
                            const double theV1)
{
  const double aDiag = std::sqrt((theU1 - theU0) * (theU1 - theU0) + (theV1 - theV0) * (theV1 - theV0));
  for (int aKu = -1; aKu <= 1; ++aKu)
  {
    for (int aKv = -1; aKv <= 1; ++aKv)
    {
      if ((aKu != 0 && theC.UPer == 0.) || (aKv != 0 && theC.VPer == 0.))
      {
        continue;
      }
      const double aSu = aKu * theC.UPer, aSv = aKv * theC.VPer;
      const double aR  = 4. * aDiag + theC.Margin;
      for (int m = 1; m <= theC.Miters.Length(); ++m)
      {
        const gp_Pnt2d& aM = theC.Miters.Value(m);
        const double    aX = std::max({theU0 - aSu - aM.X(), aM.X() - (theU1 - aSu), 0.});
        const double    aY = std::max({theV0 - aSv - aM.Y(), aM.Y() - (theV1 - aSv), 0.});
        if (std::sqrt(aX * aX + aY * aY) <= aR)
        {
          return true;
        }
      }
      for (int e = 1; e <= theC.Exits.Length(); ++e)
      {
        if (boxMeetsSegment034c(theU0 - aSu - aR, theU1 - aSu + aR, theV0 - aSv - aR, theV1 - aSv + aR,
                                theC.Exits.Value(e).first, theC.Exits.Value(e).second))
        {
          return true;
        }
      }
    }
  }
  return false;
}

//! The certificate (see the header of this block). theDD: offset along the
//! natural normal of the surface.
static bool certifyLenses034c(const TopoDS_Face&               theF,
                              const occ::handle<Geom_Surface>& theS,
                              const double                     theDD,
                              const LensCert034c&              theCert)
{
  double aU0, aU1, aV0, aV1;
  BRepTools::UVBounds(theF, aU0, aU1, aV0, aV1);
  std::vector<Patch034b> aStack;
  if (!bezierPatches034c(theS, aU0, aU1, aV0, aV1, aStack))
  {
    return LENS034C_FAIL(false);
  }
  // the face boundary sampled in UV (boxes that meet none of it and whose
  // middle is outside the face lie outside the face)
  NCollection_Sequence<gp_Pnt2d> aBnd;
  double                         aGap = 0.;
  for (TopExp_Explorer anExp(theF.Oriented(TopAbs_FORWARD), TopAbs_EDGE); anExp.More(); anExp.Next())
  {
    double                          aF, aL;
    const occ::handle<Geom2d_Curve> aC = BRep_Tool::CurveOnSurface(TopoDS::Edge(anExp.Current()), theF, aF, aL);
    if (aC.IsNull())
    {
      return LENS034C_FAIL(false);
    }
    gp_Pnt2d aPrev = aC->Value(aF);
    for (int i = 0; i <= 256; ++i)
    {
      const gp_Pnt2d aP = aC->Value(aF + (aL - aF) * i / 256.);
      aGap              = std::max(aGap, aP.Distance(aPrev));
      aBnd.Append(aP);
      aPrev = aP;
    }
  }
  IntTools_FClass2d aCls(theF, Precision::PConfusion());
  int               aBudget = 16384;
  while (!aStack.empty())
  {
    Patch034b aP = std::move(aStack.back());
    aStack.pop_back();
    if (--aBudget < 0)
    {
      return LENS034C_FAIL(false);
    }
    // outside the face?
    {
      bool isNear = false;
      for (int i = 1; i <= aBnd.Length() && !isNear; ++i)
      {
        const gp_Pnt2d& aB = aBnd.Value(i);
        isNear = aB.X() >= aP.U0 - aGap && aB.X() <= aP.U1 + aGap && aB.Y() >= aP.V0 - aGap && aB.Y() <= aP.V1 + aGap;
      }
      if (!isNear && aCls.Perform(gp_Pnt2d(0.5 * (aP.U0 + aP.U1), 0.5 * (aP.V0 + aP.V1))) == TopAbs_OUT)
      {
        continue;
      }
    }
    if (boxInLens034c(theCert, aP.U0, aP.U1, aP.V0, aP.V1) == 1)
    {
      continue;
    }
    const int aRes = patchVanishes034b(aP, theDD, 1.);
    if (aRes == 2)
    {
      continue; // both factors positive on the box
    }
    if (aP.Depth >= THE_VANISH_DEPTH_034B)
    {
      if (boxSingular034c(theCert, aP.U0, aP.U1, aP.V0, aP.V1))
      {
        continue;
      }
      LENS034C_TRACE("lens034c: certificate refuted by box (%.6f %.6f)x(%.6f %.6f) result %d\n", aP.U0, aP.U1, aP.V0,
                     aP.V1, aRes);
      return LENS034C_FAIL(false);
    }
    const double aBu = bend034b(aP, true), aBv = bend034b(aP, false);
    const bool   isU = aP.NU > 0 && (aBu >= aBv || aP.NV == 0);
    Patch034b    aA, aB;
    split034b(aP, isU, aA, aB);
    aStack.push_back(std::move(aA));
    aStack.push_back(std::move(aB));
  }
  return true;
}

