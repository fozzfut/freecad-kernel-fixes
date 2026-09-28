p = 'C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx'
s = open(p, encoding='utf-8', newline='').read()


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:90], s.count(old))
    s = s.replace(old, new)


helper = '''//! Pattern search for a folded point (factor < 0) from theStart, the grid
//! steps theDU x theDV halved down to 1/1024 (a narrow fold band between the
//! samples, e.g. a crest of a B-spline profile). Inside [U0,U1]x[V0,V1].
static bool foldNear034c(const Geom_Surface& theS,
                         const double        theDD,
                         const gp_Pnt2d&     theStart,
                         const double        theDU,
                         const double        theDV,
                         const double        theU0,
                         const double        theU1,
                         const double        theV0,
                         const double        theV1,
                         gp_Pnt2d&           theFound)
{
  static const int THE_DIRS[8][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
  double           aG, a1, a2;
  if (!foldFactor034c(theS, theStart.X(), theStart.Y(), theDD, aG, a1, a2))
  {
    return false;
  }
  gp_Pnt2d aP  = theStart;
  double   aHU = theDU, aHV = theDV;
  for (int anIt = 0; anIt < 128 && (aHU > theDU / 1024. || aHV > theDV / 1024.); ++anIt)
  {
    bool isMoved = false;
    for (int k = 0; k < 8; ++k)
    {
      const gp_Pnt2d aQ(std::min(std::max(aP.X() + THE_DIRS[k][0] * aHU, theU0), theU1),
                        std::min(std::max(aP.Y() + THE_DIRS[k][1] * aHV, theV0), theV1));
      double         aGq;
      if (!foldFactor034c(theS, aQ.X(), aQ.Y(), theDD, aGq, a1, a2))
      {
        continue;
      }
      if (aGq < aG)
      {
        aG      = aGq;
        aP      = aQ;
        isMoved = true;
      }
    }
    if (aG < 0.)
    {
      theFound = aP;
      return true;
    }
    if (!isMoved)
    {
      aHU *= 0.5;
      aHV *= 0.5;
    }
  }
  return false;
}

'''
anchor = '''//! Lenses of the offset of a face by theOffset (theOffset along the outward'''
rep(anchor, helper + anchor)

# lensCandidate: keep the lowest regular samples, search from them
rep('''      IntTools_FClass2d aCls(aF, Precision::PConfusion());
      bool              isFold = false, isReg = false;
      for (int i = 0; i <= 32 && !(isFold && isReg); ++i)
      {
        for (int j = 0; j <= 32 && !(isFold && isReg); ++j)
        {
          const gp_Pnt2d aP(aU0 + (aU1 - aU0) * i / 32, aV0 + (aV1 - aV0) * j / 32);
          double         aG, a1, a2;
          if (aCls.Perform(aP) == TopAbs_OUT || !foldFactor034c(*aS, aP.X(), aP.Y(), aDD, aG, a1, a2))
          {
            continue;
          }
          (aG < 0. ? isFold : isReg) = true;
        }
      }''', '''      IntTools_FClass2d aCls(aF, Precision::PConfusion());
      bool              isFold = false, isReg = false;
      std::vector<std::pair<double, gp_Pnt2d>> aLow; // the lowest regular samples
      for (int i = 0; i <= 32 && !(isFold && isReg); ++i)
      {
        for (int j = 0; j <= 32 && !(isFold && isReg); ++j)
        {
          const gp_Pnt2d aP(aU0 + (aU1 - aU0) * i / 32, aV0 + (aV1 - aV0) * j / 32);
          double         aG, a1, a2;
          if (aCls.Perform(aP) == TopAbs_OUT || !foldFactor034c(*aS, aP.X(), aP.Y(), aDD, aG, a1, a2))
          {
            continue;
          }
          (aG < 0. ? isFold : isReg) = true;
          if (aG >= 0. && aG < 0.75)
          {
            aLow.push_back(std::make_pair(aG, aP));
          }
        }
      }
      if (isReg && !isFold)
      {
        // a narrow fold between the samples
        std::sort(aLow.begin(), aLow.end(), [](const std::pair<double, gp_Pnt2d>& theA,
                                               const std::pair<double, gp_Pnt2d>& theB) { return theA.first < theB.first; });
        for (size_t k = 0; k < aLow.size() && k < 8 && !isFold; ++k)
        {
          gp_Pnt2d aFound;
          isFold = foldNear034c(*aS, aDD, aLow[k].second, (aU1 - aU0) / 32, (aV1 - aV0) / 32, aU0, aU1, aV0, aV1,
                                aFound)
                   && aCls.Perform(aFound) != TopAbs_OUT;
        }
      }''')

# findLenses: the same after the grid
rep('''  if (aNReg == 0)
  {
    return 0; // folds everywhere: a vanishing face (rounds 1-2 prove it)
  }
  if (aFold.IsEmpty())''', '''  if (aNReg == 0)
  {
    return 0; // folds everywhere: a vanishing face (rounds 1-2 prove it)
  }
  if (aFold.IsEmpty())
  {
    // a narrow fold between the samples: pattern search from the lowest ones
    std::vector<std::pair<double, gp_Pnt2d>> aLow;
    for (int i = 0; i < aNU; ++i)
    {
      for (int j = 0; j < aNV; ++j)
      {
        const gp_Pnt2d aP(aU0 + (aU1 - aU0) * (i + 0.5) / aNU, aV0 + (aV1 - aV0) * (j + 0.5) / aNV);
        double         aG, aEu, aEv;
        if (aDom.IsIn(aP) && foldFactor034c(*aS, aP.X(), aP.Y(), aDD, aG, aEu, aEv) && aG < 0.75)
        {
          aLow.push_back(std::make_pair(aG, aP));
        }
      }
    }
    std::sort(aLow.begin(), aLow.end(), [](const std::pair<double, gp_Pnt2d>& theA,
                                           const std::pair<double, gp_Pnt2d>& theB) { return theA.first < theB.first; });
    for (size_t k = 0; k < aLow.size() && k < 8; ++k)
    {
      gp_Pnt2d aFound;
      if (foldNear034c(*aS, aDD, aLow[k].second, (aU1 - aU0) / aNU, (aV1 - aV0) / aNV, aU0, aU1, aV0, aV1, aFound)
          && aDom.IsIn(aFound))
      {
        aFold.Append(aFound);
      }
    }
  }
  if (aFold.IsEmpty())''')
if '#include <algorithm>' not in s:
    s = s.replace('#include <memory>\n', '#include <memory>\n#include <algorithm>\n', 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
