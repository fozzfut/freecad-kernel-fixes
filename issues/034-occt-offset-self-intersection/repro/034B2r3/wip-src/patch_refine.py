p = 'C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx'
s = open(p, encoding='utf-8', newline='').read()


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)


rep('''struct XPt034c
{
  double   C[4]; //!< cu, cv, th, s
  gp_Pnt2d P, Q; //!< preimages (unwrapped UV)
  gp_Pnt   O;    //!< the point of X
};''', '''struct XPt034c
{
  double   C[4];   //!< cu, cv, th, s
  gp_Pnt2d P, Q;   //!< preimages (unwrapped UV)
  gp_Pnt   O;      //!< the point of X
  double   L = 0.; //!< parameter of the edge X (length along the traced curve, scaled variables)
};''')
rep('''  //! Newton on (alpha, th, s) with c = theC0 + alpha * (theEu, theEv)''', '''  //! scale of the variable k (cu, cv, th, s) in the tracing metric
  double Scale(const int theK) const { return mySc[theK]; }

  //! the variables (c, th, s) of the preimage pair (theP, theQ): c the middle,
  //! s w(th) the half difference, th the branch nearest to theThNear, s > 0
  bool FrameCoords(const gp_Pnt2d& theP, const gp_Pnt2d& theQ, const double theThNear, double theC[4]) const
  {
    const double aHu = 0.5 * (theP.X() - theQ.X()), aHv = 0.5 * (theP.Y() - theQ.Y());
    const double aDet = myAu * myBv - myAv * myBu;
    if (!(std::abs(aDet) > 1.e-300))
    {
      return false;
    }
    const double aX = (aHu * myBv - aHv * myBu) / aDet, aY = (myAu * aHv - myAv * aHu) / aDet;
    theC[0]         = 0.5 * (theP.X() + theQ.X());
    theC[1]         = 0.5 * (theP.Y() + theQ.Y());
    theC[3]         = std::sqrt(aX * aX + aY * aY);
    double aTh      = std::atan2(aY, aX);
    aTh += 2. * M_PI * std::round((theThNear - aTh) / (2. * M_PI));
    theC[2] = aTh;
    return theC[3] > 0.;
  }

  //! Newton on (alpha, th, s) with c = theC0 + alpha * (theEu, theEv)''')
rep('''      anX.C[0] = 0.5 * (anX.P.X() + anX.Q.X());
      anX.C[1] = 0.5 * (anX.P.Y() + anX.Q.Y());
      anX.C[3] = -1.; // not used''', '''      if (!aTr.FrameCoords(anX.P, anX.Q, aA.C[2], anX.C))
      {
        return LENS034C_FAIL(-1);
      }''')
rep('''    // boundary polygon: C1 forward, C2 backward (the chords close the exits)''', '''    // the two preimage curves are interpolated with one parameter (the edge
    // X has one parameter on both sides): points are added until the offsets
    // of the two interpolants coincide within the tolerance between the
    // traced points too
    if (!refineLens034c(aTr, *aS, aDD, aLens.Pts, 1.e-9 * std::max(1., aSize)))
    {
      return LENS034C_FAIL(-1);
    }
    // boundary polygon: C1 forward, C2 backward (the chords close the exits)''')
rep('''      NCollection_Sequence<double> aT;
      aT.Append(0.);
      for (int i = 2; i <= aL.Pts.Length(); ++i)
      {
        const double aD = aL.Pts.Value(i).O.Distance(aL.Pts.Value(i - 1).O);
        if (!(aD > 0.))
        {
          return LENS034C_FAIL(false);
        }
        aT.Append(aT.Last() + aD);
      }''', '''      NCollection_Sequence<double> aT;
      for (int i = 1; i <= aL.Pts.Length(); ++i)
      {
        aT.Append(aL.Pts.Value(i).L);
      }''')
anchor = '''//! Lenses of the offset of a face by theOffset (theOffset along the outward'''
func = open('C:/dev/occt8-mig/offset-034b2/r3c/src/refine_block.cxx', encoding='utf-8').read()
rep(anchor, func + anchor)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
