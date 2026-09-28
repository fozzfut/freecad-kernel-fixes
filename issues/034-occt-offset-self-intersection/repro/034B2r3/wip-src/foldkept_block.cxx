//! Issue 034 lane B2 round 3: true if the result keeps a FOLDED point of
//! some face. A point x of a face where a principal offset factor 1 - d*k is
//! negative is never on the offset (Maekawa 1999: the offset point is closer
//! than |d| to points of the face near x), so an image face of the offset
//! that contains the offset of such a point is wrong geometry - also when it
//! is valid and does not interfere with other faces (a fold inside one face:
//! the self-interference check of the BOP compares different faces only, and
//! the distance samples of the stage A guard can miss a small fold). The
//! folded points are found on a grid of the face (the same factor as the
//! stage A guard, strictly negative); the image faces live on the offset of
//! the face surface in the same parameters, so the test is a 2D
//! classification of the folded parameters in the image faces (curvature and
//! parameters only; for an image on another surface the offset point is
//! projected on it - an error-raising control, never a construction).
static bool foldedPointKept034c(
  const TopoDS_Shape&                                                       theFaces,
  const NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher>&      theCaps,
  const NCollection_DataMap<TopoDS_Shape, double, TopTools_ShapeMapHasher>& theFaceOffset,
  const double                                                              theOffset,
  const BRepAlgo_Image&                                                     theInit)
{
  try
  {
    OCC_CATCH_SIGNALS
    for (TopExp_Explorer anExp(theFaces, TopAbs_FACE); anExp.More(); anExp.Next())
    {
      const TopoDS_Face& aF = TopoDS::Face(anExp.Current());
      if (theCaps.Contains(aF) || !theInit.HasImage(aF))
      {
        continue;
      }
      TopLoc_Location           aLoc;
      occ::handle<Geom_Surface> aS = BRep_Tool::Surface(aF, aLoc);
      if (aS.IsNull())
      {
        continue;
      }
      while (!occ::down_cast<Geom_RectangularTrimmedSurface>(aS).IsNull())
      {
        aS = occ::down_cast<Geom_RectangularTrimmedSurface>(aS)->BasisSurface();
      }
      const GeomAdaptor_Surface aGAS(aS);
      if (aGAS.GetType() == GeomAbs_Plane)
      {
        continue;
      }
      const double* anOff = theFaceOffset.Seek(aF);
      const double  aD    = (aF.Orientation() == TopAbs_REVERSED) ? -(anOff ? *anOff : theOffset)
                                                                  : (anOff ? *anOff : theOffset);
      double aU0, aU1, aV0, aV1;
      BRepTools::UVBounds(aF, aU0, aU1, aV0, aV1);
      if (!(aU1 > aU0) || !(aV1 > aV0))
      {
        continue;
      }
      int aNU = 32, aNV = 32;
      if (aGAS.GetType() == GeomAbs_BSplineSurface)
      {
        const occ::handle<Geom_BSplineSurface> aBS = aGAS.BSpline();
        aNU = std::min(std::max(aNU, 2 * (aBS->NbUKnots() - 1)), 96);
        aNV = std::min(std::max(aNV, 2 * (aBS->NbVKnots() - 1)), 96);
      }
      // the folded samples of the face (cell centres)
      NCollection_Sequence<gp_Pnt2d>                       aFolded;
      std::unique_ptr<IntTools_FClass2d>                   aClsF;
      for (int i = 0; i < aNU; ++i)
      {
        for (int j = 0; j < aNV; ++j)
        {
          const gp_Pnt2d aP(aU0 + (aU1 - aU0) * (i + 0.5) / aNU, aV0 + (aV1 - aV0) * (j + 0.5) / aNV);
          double         aFct;
          if (!offsetFactor034(*aS, aP.X(), aP.Y(), aU1 - aU0, aV1 - aV0, aD, aFct) || !(aFct < -1.e-6))
          {
            continue;
          }
          if (!aClsF)
          {
            aClsF.reset(new IntTools_FClass2d(aF, Precision::PConfusion()));
          }
          if (aClsF->Perform(aP) == TopAbs_IN)
          {
            aFolded.Append(aP);
          }
        }
      }
      if (aFolded.IsEmpty())
      {
        continue;
      }
      NCollection_List<TopoDS_Shape> anImages;
      theInit.LastImage(aF, anImages);
      for (NCollection_List<TopoDS_Shape>::Iterator anItI(anImages); anItI.More(); anItI.Next())
      {
        for (TopExp_Explorer anExpI(anItI.Value(), TopAbs_FACE); anExpI.More(); anExpI.Next())
        {
          const TopoDS_Face&        anI = TopoDS::Face(anExpI.Current());
          TopLoc_Location           aLocI;
          occ::handle<Geom_Surface> aSI = BRep_Tool::Surface(anI, aLocI);
          if (aSI.IsNull())
          {
            continue;
          }
          while (!occ::down_cast<Geom_RectangularTrimmedSurface>(aSI).IsNull())
          {
            aSI = occ::down_cast<Geom_RectangularTrimmedSurface>(aSI)->BasisSurface();
          }
          // the image surface in the parameters of the face surface? (the
          // offset point O(u,v) = S(u,v) + d N(u,v) evaluated on both, at
          // three parameters of the folded samples)
          auto anOffsetPoint = [&](const gp_Pnt2d& theUV, gp_Pnt& theO) {
            gp_Pnt aP;
            gp_Vec aDu, aDv;
            aS->D1(theUV.X(), theUV.Y(), aP, aDu, aDv);
            gp_Vec aN = aDu.Crossed(aDv);
            if (aN.Magnitude() <= gp::Resolution())
            {
              return false;
            }
            aN.Normalize();
            theO = aP.Translated(aN * aD);
            if (!aLoc.IsIdentity())
            {
              theO.Transform(aLoc.Transformation());
            }
            if (!aLocI.IsIdentity())
            {
              theO.Transform(aLocI.Transformation().Inverted());
            }
            return true;
          };
          bool isSameParam = true;
          for (int k = 1; k <= aFolded.Length() && isSameParam; k += std::max(1, aFolded.Length() / 3))
          {
            gp_Pnt aO;
            isSameParam = anOffsetPoint(aFolded.Value(k), aO)
                          && aSI->Value(aFolded.Value(k).X(), aFolded.Value(k).Y()).Distance(aO)
                               <= 1.e-9 * (1. + aO.XYZ().Modulus());
          }
          IntTools_FClass2d aClsI(anI, Precision::PConfusion());
          for (int k = 1; k <= aFolded.Length(); ++k)
          {
            gp_Pnt2d aUV = aFolded.Value(k);
            if (!isSameParam)
            {
              // the offset point projected on the image surface (control)
              gp_Pnt aO;
              if (!anOffsetPoint(aUV, aO))
              {
                continue;
              }
              GeomAPI_ProjectPointOnSurf aProj(aO, aSI);
              if (!aProj.IsDone() || aProj.NbPoints() == 0
                  || aProj.LowerDistance() > 10. * BRep_Tool::Tolerance(anI) + Precision::Confusion())
              {
                continue;
              }
              double aU, aV;
              aProj.LowerDistanceParameters(aU, aV);
              aUV.SetCoord(aU, aV);
            }
            if (aClsI.Perform(aUV) == TopAbs_IN)
            {
              LENS034C_TRACE("lens034c: folded point (%.6f %.6f) kept in the result%s", aUV.X(), aUV.Y(), "\n");
              return true;
            }
          }
        }
      }
    }
  }
  catch (Standard_Failure const&)
  {
  }
  return false;
}

