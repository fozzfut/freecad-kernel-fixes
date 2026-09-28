p = 'C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx'
s = open(p, encoding='utf-8', newline='').read()


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:90], s.count(old))
    s = s.replace(old, new)


# replace the polygon-based certificate by the per-region one
a = s.index('//! Lens polygons and singular points of a face for the certificate')
b = s.index('static int certifyLenses034c(')
b = s.index('\n}\n', b) + 3
s = s[:a] + open('C:/dev/occt8-mig/offset-034b2/r3c/src/cert2_block.cxx', encoding='utf-8').read() + s[b:]
# header comment of the block: the lens-polygon wording
rep('''// interval arithmetic, patchVanishes034b), that BOTH principal offset factors
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
// of the scope of the lens pass: an error, never a silent result).''',
    '''// interval arithmetic, patchVanishes034b), that BOTH principal offset factors
// are positive at every point of every piece of a split face that is not a
// lens (and of every face without fold samples): the offset of the kept
// pieces is regular (no fold is left in the result). The pieces are exact
// B-rep faces (bounded by the preimage curves, the rays and the original
// edges), so the certificate works on their domains. A patch box is
//  - skipped when it lies outside the piece,
//  - proven when the factors are bounded away from 0 on the whole box,
//  - cut in two otherwise.
// A box that stays unresolved at the depth limit is accepted only in the
// neighbourhood of a miter point (the end of the self-intersection curve on
// the fold, where a factor is 0 at a point of the lens boundary: no interval
// bound can separate it - the miter point region of Park-Hong-Kim-Elber, CAGD
// 2021). Any other unresolved box refutes the certificate (the face is then
// out of the scope of the lens pass: an error, never a silent result). A
// surface without an exact Bezier form in the face parameters is not
// certified (the lenses rest on the samples, as the stage A guard).''')
# no fold sample
rep('''    LensCert034c aNoLens;
    aNoLens.UPer = aDom.UPer();
    aNoLens.VPer = aDom.VPer();
    return certifyLenses034c(theF, aS, aDD, aNoLens) != 0 ? 0 : LENS034C_FAIL(-1);''',
    '''    const LensCert034c aNoLens;
    return certifyRegion034c(theF, aS, aDD, aNoLens) != 0 ? 0 : LENS034C_FAIL(-1);''')
# remove the polygon certificate at the end of findLenses
a = s.index('  // the certificate: every point of the face outside the lenses is regular\n  LensCert034c aCert;')
b = s.index('  return 1;\n}\n} // namespace', a)
s = s[:a] + s[b:]
# certificate of the pieces in lensSplitShape034c
rep('''    LensSplit034c aSplit;
    if (aFL.IsEmpty() || !lensSplit034c(aFL, theFaceOffset, theOffset, aSplit))
    {
      return false;
    }''', '''    LensSplit034c aSplit;
    if (aFL.IsEmpty() || !lensSplit034c(aFL, theFaceOffset, theOffset, aSplit))
    {
      return false;
    }
    // the certificate of every piece that is not a lens (see certifyRegion034c)
    for (int i = 1; i <= aFL.Extent(); ++i)
    {
      const TopoDS_Face&               aF = TopoDS::Face(aFL.FindKey(i));
      TopLoc_Location                  aLoc;
      occ::handle<Geom_Surface>        aS = BRep_Tool::Surface(aF, aLoc);
      while (!occ::down_cast<Geom_RectangularTrimmedSurface>(aS).IsNull())
      {
        aS = occ::down_cast<Geom_RectangularTrimmedSurface>(aS)->BasisSurface();
      }
      const double*      anOff = theFaceOffset.Seek(aF);
      const double       aDD   = (aF.Orientation() == TopAbs_REVERSED) ? -(anOff ? *anOff : theOffset)
                                                                       : (anOff ? *anOff : theOffset);
      const LensFace034c aDom(aF, aS);
      LensCert034c       aCert;
      for (int l = 1; l <= aFL(i).Length(); ++l)
      {
        const Lens034c& aL = aFL(i).Value(l);
        double          aMinU = RealLast(), aMaxU = -RealLast(), aMinV = RealLast(), aMaxV = -RealLast();
        for (int k = 1; k <= aL.Poly.Length(); ++k)
        {
          aMinU = std::min(aMinU, aL.Poly.Value(k).X());
          aMaxU = std::max(aMaxU, aL.Poly.Value(k).X());
          aMinV = std::min(aMinV, aL.Poly.Value(k).Y());
          aMaxV = std::max(aMaxV, aL.Poly.Value(k).Y());
        }
        aCert.Extent = std::max(aCert.Extent, std::sqrt((aMaxU - aMinU) * (aMaxU - aMinU) + (aMaxV - aMinV) * (aMaxV - aMinV)));
        for (int anEnd = 0; anEnd < 2; ++anEnd)
        {
          if (aL.Miter[anEnd])
          {
            aCert.Miters.Append(aDom.Wrap(anEnd == 0 ? aL.Pts.First().P : aL.Pts.Last().P));
          }
        }
      }
      for (NCollection_DataMap<TopoDS_Shape, TopoDS_Shape, TopTools_ShapeMapHasher>::Iterator anItO(aSplit.Origin);
           anItO.More();
           anItO.Next())
      {
        if (!anItO.Value().IsSame(aF) || aSplit.LensFaces.Contains(anItO.Key()))
        {
          continue;
        }
        if (certifyRegion034c(TopoDS::Face(anItO.Key()), aS, aDD, aCert) == 0)
        {
          return LENS034C_FAIL(false);
        }
      }
    }''')
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
