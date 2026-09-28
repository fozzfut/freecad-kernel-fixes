p = 'C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx'
s = open(p, encoding='utf-8', newline='').read()
BS = chr(92)


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:90], s.count(old))
    s = s.replace(old, new)


# 1. the patch test also proves "no fold" (both factors above the limit)
rep('''  return (aC1.Hi < -aM1 || aC2.Hi < -aM2) ? 1 : 0;''',
    '''  if (aC1.Hi < -aM1 || aC2.Hi < -aM2)
  {
    return 1;
  }
  // round 3: both factors above the limit on the whole patch (the trace and
  // the determinant of sigma I - dW positive): proven regular
  return (aC1.Lo > aM1 && aC2.Lo > aM2) ? 2 : 0;''')
rep('''//! Test of one patch: 1 proven vanishing, 0 not proven, -1 no bound (a
//! weight or the normal may vanish on the patch).''',
    '''//! Test of one patch: 1 proven vanishing, 2 proven regular (round 3: both
//! factors above the limit), 0 not proven, -1 no bound (a weight or the
//! normal may vanish on the patch).''')
# includes
rep('#include <GeomConvert_BSplineSurfaceToBezierSurface.hxx>',
    '#include <GeomConvert_BSplineSurfaceToBezierSurface.hxx>\n#include <GeomConvert.hxx>')
# 2. certificate block before findLenses034c
anchor = '''//! Parameters of the points of a lens (length along the traced curve in the'''
cert = open('C:/dev/occt8-mig/offset-034b2/r3c/src/cert_block.cxx', encoding='utf-8').read()
rep(anchor, cert + anchor)
# 3. no fold sample: the face must be proven regular (a fold between the samples
#    would otherwise stay in the result of the lens pass)
rep('''  if (aFold.IsEmpty() || aNReg == 0)
  {
    return 0;
  }''', '''  if (aNReg == 0)
  {
    return 0; // folds everywhere: a vanishing face (rounds 1-2 prove it)
  }
  if (aFold.IsEmpty())
  {
    LensCert034c aNoLens;
    aNoLens.UPer = aDom.UPer();
    aNoLens.VPer = aDom.VPer();
    return certifyLenses034c(theF, aS, aDD, aNoLens) ? 0 : LENS034C_FAIL(-1);
  }''')
# 4. certificate of the lenses at the end of findLenses034c
rep('''          if (segCross034c(aA1, aA2, aB1, aB2))
          {
            return LENS034C_FAIL(-1);
          }
        }
      }
    }
  }
  return 1;
}
} // namespace''', '''          if (segCross034c(aA1, aA2, aB1, aB2))
          {
            return LENS034C_FAIL(-1);
          }
        }
      }
    }
  }
  // the certificate: every point of the face outside the lenses is regular
  LensCert034c aCert;
  aCert.UPer = aDom.UPer();
  aCert.VPer = aDom.VPer();
  for (int l = 1; l <= theLenses.Length(); ++l)
  {
    const Lens034c& aL = theLenses.Value(l);
    aCert.Polys.Append(aL.Poly);
    for (int anEnd = 0; anEnd < 2; ++anEnd)
    {
      const XPt034c& anE = anEnd == 0 ? aL.Pts.First() : aL.Pts.Last();
      if (aL.Miter[anEnd])
      {
        aCert.Miters.Append(anE.P);
      }
      else if (aL.Exit[anEnd].Both)
      {
        aCert.Exits.Append(std::make_pair(anE.P, anE.Q));
      }
    }
    // chords of the polygon against the interpolated sides
    occ::handle<Geom2d_Curve> aC1, aC2;
    NCollection_Sequence<XPt034c> aPts = aL.Pts;
    if (!lensParams034c(aTr, aPts, aC1, aC2))
    {
      return LENS034C_FAIL(-1);
    }
    for (int i = 1; i < aPts.Length(); ++i)
    {
      const double aLm = 0.5 * (aPts.Value(i).L + aPts.Value(i + 1).L);
      const gp_Pnt2d aM1(0.5 * (aPts.Value(i).P.X() + aPts.Value(i + 1).P.X()),
                         0.5 * (aPts.Value(i).P.Y() + aPts.Value(i + 1).P.Y()));
      const gp_Pnt2d aM2(0.5 * (aPts.Value(i).Q.X() + aPts.Value(i + 1).Q.X()),
                         0.5 * (aPts.Value(i).Q.Y() + aPts.Value(i + 1).Q.Y()));
      aCert.Margin = std::max({aCert.Margin, aC1->Value(aLm).Distance(aM1), aC2->Value(aLm).Distance(aM2)});
    }
  }
  aCert.Margin = 2. * aCert.Margin + Precision::PConfusion();
  if (!certifyLenses034c(theF, aS, aDD, aCert))
  {
    return LENS034C_FAIL(-1);
  }
  return 1;
}
} // namespace''')
# 5. refinement near a miter point: a looser corrector, then the interval is
#    accepted when the deviation is within 20 x the tolerance (the X edge then
#    carries it as its tolerance)
rep('''        int anIt = 0;
        if (!theTr.Correct(aX, aT, aYp, anIt, 1.e-3 * theTol) || !(aX[3] > 0.))
        {''', '''        int    anIt = 0;
        double aX0[4];
        for (int k = 0; k < 4; ++k)
        {
          aX0[k] = aX[k];
        }
        bool isCorr = theTr.Correct(aX, aT, aYp, anIt, 1.e-3 * theTol) && aX[3] > 0.;
        if (!isCorr)
        {
          for (int k = 0; k < 4; ++k)
          {
            aX[k] = aX0[k];
          }
          isCorr = theTr.Correct(aX, aT, aYp, anIt, theTol) && aX[3] > 0.;
        }
        if (!isCorr && (aA.C[3] == 0. || aB.C[3] == 0.) && aDev <= 20. * theTol)
        {
          // the interval at a miter point, where the system is singular:
          // kept as interpolated (the deviation stays in the edge tolerance)
          aNew.Append(aB);
          continue;
        }
        if (!isCorr)
        {''')
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
