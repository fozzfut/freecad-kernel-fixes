p = 'C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx'
s = open(p, encoding='utf-8', newline='').read()


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:90], s.count(old))
    s = s.replace(old, new)


rep('#include <GCPnts_AbscissaPoint.hxx>', '#include <GCPnts_AbscissaPoint.hxx>\n#include <GeomAPI_IntCS.hxx>')

# 1. target surfaces instead of the arc-length reach
rep('''//! Copy of the section edge theNE (a rim offset face on a removed face)
//! prolonged along its curve by the arc length theLen at its first and/or last
//! end; the other end keeps its vertex (it is shared with the section of the
//! face that does not vanish there: a tube, a surviving blend, another removed
//! face). The prolongation stays inside the parameter bounds of the 3D curve
//! and of the pcurves. Null if no end can be prolonged.
static TopoDS_Edge prolongedSection034b(const TopoDS_Edge& theNE,
                                        const bool         theAtFirst,
                                        const bool         theAtLast,
                                        const double       theLen)
{''', '''//! A surface the section of a rim face must reach across a vanished set: a
//! removed face (not offset) or the offset of another rim face of the set.
struct RimTarget034b
{
  TopoDS_Shape              Face;    //!< the initial face (for exclusions)
  occ::handle<Geom_Surface> Surface; //!< its surface (removed face) or offset surface, in world coordinates
};

//! Copy of the section edge theNE (a rim offset face on a removed face, or
//! two rim offsets across a sharp edge) prolonged along its curve at its
//! first and/or last end up to the corner where it meets the nearest of the
//! surfaces theTargets beyond that end (issue 034 B2 round 3: the corner is
//! computed, GeomAPI_IntCS on the curve that carries the section, instead of
//! an estimated reach), plus theMargin of arc length so that the corner is
//! an intersection inside the edge for the 2D intersections. The other end
//! keeps its vertex (it is shared with the section of the face that does not
//! vanish there: a tube, a surviving blend, another removed face). The
//! prolongation stays inside the parameter bounds of the 3D curve and of the
//! pcurves; an end whose curve meets no target there is not prolonged (the
//! loops then stay open: an error). Null if no end is prolonged.
static TopoDS_Edge prolongedSection034b(const TopoDS_Edge&                      theNE,
                                        const bool                              theAtFirst,
                                        const bool                              theAtLast,
                                        const NCollection_List<RimTarget034b>& theTargets,
                                        const double                            theMargin)
{''')
rep('''  // parameter at the arc length theLen from the end (at most the bound)
  const GeomAdaptor_Curve aGC(aC);
  auto                    aReach = [&](const double theEnd, const double theBound) {
    if (std::abs(theBound - theEnd) <= Precision::PConfusion())
    {
      return theEnd;
    }
    try
    {
      OCC_CATCH_SIGNALS
      GCPnts_AbscissaPoint anAP(aGC, theBound > theEnd ? theLen : -theLen, theEnd);
      if (anAP.IsDone())
      {
        const double aP = anAP.Parameter();
        return theBound > theEnd ? std::min(std::max(aP, theEnd), theBound)
                                 : std::max(std::min(aP, theEnd), theBound);
      }
    }
    catch (Standard_Failure const&)
    {
    }
    return theEnd;
  };''', '''  // parameter of the nearest corner beyond the end (a target met by the
  // curve between the end and the bound), moved on by the margin
  const GeomAdaptor_Curve       aGC(aC);
  const occ::handle<Geom_Curve> aCW =
    aLoc.IsIdentity() ? aC : occ::down_cast<Geom_Curve>(aC->Transformed(aLoc.Transformation()));
  auto aReach = [&](const double theEnd, const double theBound) {
    if (std::abs(theBound - theEnd) <= Precision::PConfusion())
    {
      return theEnd;
    }
    const bool isFwd   = theBound > theEnd;
    double     aCorner = theBound;
    bool       isFound = false;
    for (NCollection_List<RimTarget034b>::Iterator anIt(theTargets); anIt.More(); anIt.Next())
    {
      try
      {
        OCC_CATCH_SIGNALS
        GeomAPI_IntCS anInt(aCW, anIt.Value().Surface);
        if (!anInt.IsDone())
        {
          continue;
        }
        for (int i = 1; i <= anInt.NbPoints(); ++i)
        {
          double aU, aV, aW;
          anInt.Parameters(i, aU, aV, aW);
          const bool isBeyond = isFwd ? (aW > theEnd + Precision::PConfusion() && aW <= theBound)
                                      : (aW < theEnd - Precision::PConfusion() && aW >= theBound);
          if (isBeyond && (!isFound || (isFwd ? aW < aCorner : aW > aCorner)))
          {
            aCorner = aW;
            isFound = true;
          }
        }
      }
      catch (Standard_Failure const&)
      {
      }
    }
    if (!isFound)
    {
      return theEnd;
    }
    try
    {
      OCC_CATCH_SIGNALS
      GCPnts_AbscissaPoint anAP(aGC, isFwd ? theMargin : -theMargin, aCorner);
      if (anAP.IsDone())
      {
        const double aP = anAP.Parameter();
        return isFwd ? std::min(std::max(aP, aCorner), theBound) : std::max(std::min(aP, aCorner), theBound);
      }
    }
    catch (Standard_Failure const&)
    {
    }
    return aCorner;
  };''')
rep('''  if (aC.IsNull() || aTE.IsNull() || !(aL > aF) || !(theLen > 0.))
  {
    return TopoDS_Edge();
  }''', '''  if (aC.IsNull() || aTE.IsNull() || !(aL > aF) || theTargets.IsEmpty())
  {
    return TopoDS_Edge();
  }''')
# 2. record: targets of the rim faces, offset value
rep('''  NCollection_DataMap<TopoDS_Shape, double, TopTools_ShapeMapHasher> RimMargin;
  //! vertices of the vanishing faces''', '''  NCollection_DataMap<TopoDS_Shape, double, TopTools_ShapeMapHasher> RimMargin;
  //! round 3: rim faces of sets that reach a removed face -> the surfaces
  //! their sections meet across the set (the removed faces of the set, the
  //! offsets of the other rim faces), the corners the sections are prolonged to
  NCollection_DataMap<TopoDS_Shape, NCollection_List<RimTarget034b>, TopTools_ShapeMapHasher> RimTargets;
  double                                                                                        Offset = 0.;
  //! vertices of the vanishing faces''')
# 3. fill the targets in findVanishing034b (where the margins are bound)
rep('''      if (aMargin > 0.)
      {
        double* aRM = theRec.RimMargin.ChangeSeek(aRim(i));
        if (aRM == nullptr)
        {
          theRec.RimMargin.Bind(aRim(i), aMargin);
        }
        else
        {
          *aRM = std::max(*aRM, aMargin);
        }
      }''', '''      if (aMargin > 0.)
      {
        double* aRM = theRec.RimMargin.ChangeSeek(aRim(i));
        if (aRM == nullptr)
        {
          theRec.RimMargin.Bind(aRim(i), aMargin);
        }
        else
        {
          *aRM = std::max(*aRM, aMargin);
        }
        if (!theRec.RimTargets.IsBound(aRim(i)))
        {
          theRec.RimTargets.Bind(aRim(i), NCollection_List<RimTarget034b>());
        }
        NCollection_List<RimTarget034b>& aTg = theRec.RimTargets.ChangeFind(aRim(i));
        for (int c = 1; c <= aRimCaps.Extent(); ++c)
        {
          const TopoDS_Face& aCapF = TopoDS::Face(aRimCaps(c));
          aTg.Append(RimTarget034b{aCapF, BRep_Tool::Surface(aCapF)});
        }
        for (int j = 1; j <= aRim.Extent(); ++j)
        {
          const BRepOffset_Offset* anOFj = theMapSF.Seek(aRim(j));
          if (j != i && anOFj != nullptr && !anOFj->Face().IsNull())
          {
            aTg.Append(RimTarget034b{aRim(j), BRep_Tool::Surface(TopoDS::Face(anOFj->Face()))});
          }
        }
      }''')
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
