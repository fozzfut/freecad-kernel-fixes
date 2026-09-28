//! Miter points of the lenses of a face (UV in the parameter range of the
//! face) and the extent of the lenses (UV), for the certificate
struct LensCert034c
{
  NCollection_Sequence<gp_Pnt2d> Miters;
  double                         Extent = 0.;
};

//! The certificate on one region of the surface theS: a face theF that holds
//! no lens (a piece of a split face, or a face without fold samples). theDD:
//! offset along the natural normal of theS. Returns 1 proven (both principal
//! factors positive at every point of theF, except in the miter regions),
//! 0 refuted, -1 not applicable (no exact Bezier form in the parameters of
//! the face: the lenses then rest on the samples - every fold sample lies
//! inside a lens).
static int certifyRegion034c(const TopoDS_Face&               theF,
                             const occ::handle<Geom_Surface>& theS,
                             const double                     theDD,
                             const LensCert034c&              theCert)
{
  double aU0, aU1, aV0, aV1;
  BRepTools::UVBounds(theF, aU0, aU1, aV0, aV1);
  std::vector<Patch034b> aStack;
  if (!bezierPatches034c(theS, aU0, aU1, aV0, aV1, aStack))
  {
    LENS034C_TRACE("lens034c: certificate not applicable (no Bezier form)\n");
    return -1;
  }
  // the boundary of the region sampled in UV: a box whose middle is farther
  // from every sample than its half diagonal plus the sampling gap does not
  // meet the boundary, and the classifier decides it at its middle
  NCollection_Sequence<gp_Pnt2d> aBnd;
  double                         aGap = 0.;
  for (TopExp_Explorer anExp(theF.Oriented(TopAbs_FORWARD), TopAbs_EDGE); anExp.More(); anExp.Next())
  {
    double                          aF, aL;
    const occ::handle<Geom2d_Curve> aC = BRep_Tool::CurveOnSurface(TopoDS::Edge(anExp.Current()), theF, aF, aL);
    if (aC.IsNull())
    {
      return LENS034C_FAIL(0);
    }
    gp_Pnt2d aPrev = aC->Value(aF);
    for (int i = 0; i <= 512; ++i)
    {
      const gp_Pnt2d aP = aC->Value(aF + (aL - aF) * i / 512.);
      aGap              = std::max(aGap, aP.Distance(aPrev));
      aBnd.Append(aP);
      aPrev = aP;
    }
  }
  IntTools_FClass2d aCls(theF, Precision::PConfusion());
  int               aBudget = 32768;
  while (!aStack.empty())
  {
    Patch034b aP = std::move(aStack.back());
    aStack.pop_back();
    if (--aBudget < 0)
    {
      LENS034C_TRACE("lens034c: certificate budget exhausted%s", "\n");
      return LENS034C_FAIL(0);
    }
    const gp_Pnt2d aMid(0.5 * (aP.U0 + aP.U1), 0.5 * (aP.V0 + aP.V1));
    const double   aDiag = std::sqrt((aP.U1 - aP.U0) * (aP.U1 - aP.U0) + (aP.V1 - aP.V0) * (aP.V1 - aP.V0));
    double         aDMin = RealLast();
    for (int i = 1; i <= aBnd.Length(); ++i)
    {
      aDMin = std::min(aDMin, aMid.Distance(aBnd.Value(i)));
    }
    if (aDMin > 0.5 * aDiag + aGap && aCls.Perform(aMid) == TopAbs_OUT)
    {
      continue; // the box lies outside the region
    }
    const int aRes = patchVanishes034b(aP, theDD, 1.);
    if (aRes == 2)
    {
      continue; // both factors positive on the box
    }
    if (aP.Depth >= THE_VANISH_DEPTH_034B)
    {
      // the miter region: the fold curve touches the lens boundary at the
      // miter point (tangent: the gap grows with the square of the distance),
      // so the unresolved boxes lie within ~sqrt(box * extent) of it
      const double aR = 4. * aDiag + std::sqrt(aDiag * theCert.Extent);
      bool         isMiter = false;
      for (int m = 1; m <= theCert.Miters.Length() && !isMiter; ++m)
      {
        const gp_Pnt2d& aM = theCert.Miters.Value(m);
        const double    aX = std::max({aP.U0 - aM.X(), aM.X() - aP.U1, 0.});
        const double    aY = std::max({aP.V0 - aM.Y(), aM.Y() - aP.V1, 0.});
        isMiter            = std::sqrt(aX * aX + aY * aY) <= aR;
      }
      if (isMiter)
      {
        continue;
      }
      LENS034C_TRACE("lens034c: certificate refuted by box (%.6f %.6f)x(%.6f %.6f) result %d\n", aP.U0, aP.U1, aP.V0,
                     aP.V1, aRes);
      return LENS034C_FAIL(0);
    }
    const double aBu = bend034b(aP, true), aBv = bend034b(aP, false);
    const bool   isU = aP.NU > 0 && (aBu >= aBv || aP.NV == 0);
    Patch034b    aA, aB;
    split034b(aP, isU, aA, aB);
    aStack.push_back(std::move(aA));
    aStack.push_back(std::move(aB));
  }
  return 1;
}

