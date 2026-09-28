p = 'C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx'
s = open(p, encoding='utf-8', newline='').read()
BS = chr(92)


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:90], s.count(old))
    s = s.replace(old, new)


# ProlongRimSections: exact corners
rep('''  const double* aM1   = THE_VANISH_034B->RimMargin.Seek(theF1);
  const double* aM2   = THE_VANISH_034B->RimMargin.Seek(theF2);
  const double  aReach = std::max(aM1 ? *aM1 : 0., aM2 ? *aM2 : 0.);
  TopoDS_Vertex aVa, aVb;
  TopExp::Vertices(TopoDS::Edge(theE), aVa, aVb);
  const bool isA = THE_VANISH_034B->SetVertices.Contains(aVa);
  const bool isB = THE_VANISH_034B->SetVertices.Contains(aVb);
  if (!(aReach > 0.) || (!isA && !isB) || aVa.IsNull() || aVb.IsNull())
  {
    return;
  }''', '''  // the corners: the surfaces the section meets across the set (the removed
  // faces, the offsets of the other rim faces), the two faces themselves out
  NCollection_List<RimTarget034b> aTargets;
  for (const TopoDS_Shape* aF : {&theF1, &theF2})
  {
    if (const NCollection_List<RimTarget034b>* aTg = THE_VANISH_034B->RimTargets.Seek(*aF))
    {
      for (NCollection_List<RimTarget034b>::Iterator anItT(*aTg); anItT.More(); anItT.Next())
      {
        if (!anItT.Value().Face.IsSame(theF1) && !anItT.Value().Face.IsSame(theF2))
        {
          aTargets.Append(anItT.Value());
        }
      }
    }
  }
  TopoDS_Vertex aVa, aVb;
  TopExp::Vertices(TopoDS::Edge(theE), aVa, aVb);
  const bool isA = THE_VANISH_034B->SetVertices.Contains(aVa);
  const bool isB = THE_VANISH_034B->SetVertices.Contains(aVb);
  if (aTargets.IsEmpty() || (!isA && !isB) || aVa.IsNull() || aVb.IsNull())
  {
    return;
  }''')
rep('''    const TopoDS_Edge aProl = prolongedSection034b(aSE,
                                                   isSwap ? isB : isA,
                                                   isSwap ? isA : isB,
                                                   aReach + 10. * BRep_Tool::Tolerance(aSE));''', '''    const TopoDS_Edge aProl = prolongedSection034b(
      aSE,
      isSwap ? isB : isA,
      isSwap ? isA : isB,
      aTargets,
      10. * BRep_Tool::Tolerance(aSE) + 1.e-3 * std::abs(THE_VANISH_034B->Offset));''')
# ToContext hook
rep('''            // Issue 034 lane B2: the section of a rim face with a removed
            // face ends where a vanished face began; the rim face meets the
            // other rim faces on it (rim lemma) and other removed faces
            // across the set, beyond that end: the section is prolonged there
            // by the reach of the set, its other end is kept.
            const double* aReach = THE_VANISH_034B->RimMargin.Seek(S);''', '''            // Issue 034 lane B2: the section of a rim face with a removed
            // face ends where a vanished face began; the rim face meets the
            // other rim faces on it (rim lemma) and other removed faces
            // across the set, beyond that end: the section is prolonged to
            // that corner (round 3: computed), its other end is kept.
            const NCollection_List<RimTarget034b>* aTg = THE_VANISH_034B->RimTargets.Seek(S);
            NCollection_List<RimTarget034b>        aTargets;
            if (aTg != nullptr)
            {
              for (NCollection_List<RimTarget034b>::Iterator anItT(*aTg); anItT.More(); anItT.Next())
              {
                if (!anItT.Value().Face.IsSame(*aCapOE))
                {
                  aTargets.Append(anItT.Value());
                }
              }
            }
''')
rep('''            if (aReach != nullptr && (isA || isB))''', '''            if (!aTargets.IsEmpty() && (isA || isB))''')
rep('''                const TopoDS_Edge aProl =
                  prolongedSection034b(aNE0, isAtFirst, isAtLast, *aReach + 10. * myTol);''', '''                const TopoDS_Edge aProl = prolongedSection034b(aNE0,
                                                               isAtFirst,
                                                               isAtLast,
                                                               aTargets,
                                                               10. * myTol + 1.e-3 * std::abs(myOffset));''')
# record offset
rep('''  theRec.RimMargin.Clear();''', '''  theRec.RimMargin.Clear();
  theRec.RimTargets.Clear();
  theRec.Offset = theOffset;''')
# extrusion / revolution: convert the trimmed surface (infinite in v otherwise)
rep('''    try
    {
      OCC_CATCH_SIGNALS
      aBS = GeomConvert::SurfaceToBSplineSurface(aS);
    }''', '''    try
    {
      OCC_CATCH_SIGNALS
      double aSU0, aSU1, aSV0, aSV1;
      aS->Bounds(aSU0, aSU1, aSV0, aSV1);
      // the face range (inside the bounds; the conversion needs a bounded surface)
      const double aTU0 = aS->IsUPeriodic() ? theU0 : std::max(theU0, aSU0);
      const double aTU1 = aS->IsUPeriodic() ? theU1 : std::min(theU1, aSU1);
      const double aTV0 = aS->IsVPeriodic() ? theV0 : std::max(theV0, aSV0);
      const double aTV1 = aS->IsVPeriodic() ? theV1 : std::min(theV1, aSV1);
      if (!(aTU1 > aTU0) || !(aTV1 > aTV0))
      {
        return false;
      }
      aBS = GeomConvert::SurfaceToBSplineSurface(new Geom_RectangularTrimmedSurface(aS, aTU0, aTU1, aTV0, aTV1));
    }''')
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
