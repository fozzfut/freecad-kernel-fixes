import sys; sys.argv = ["cmp3.py", "x", "0"]
exec(open("C:/dev/occt8-mig/offset-034b2/rv3/cmp3.py").read().split("if len(sys.argv) > 3")[0])
import random
from shapely.prepared import prep
for d in (2., 3.):
    mine = ero(P_REV, d); sh = P_REV.buffer(-d, quad_segs=QS); B = LinearRing(np.array(P_REV.exterior.coords))
    diff = mine.symmetric_difference(sh); pd_, pm, ps, pP = prep(diff), prep(mine), prep(sh), prep(P_REV)
    print("d", d, "diff area", diff.area, "bounds", diff.bounds)
    rnd = random.Random(1); okm = oks = n = 0
    minx, miny, maxx, maxy = diff.bounds
    while n < 300:
        p = Point(rnd.uniform(minx, maxx), rnd.uniform(miny, maxy))
        if not pd_.contains(p): continue
        n += 1; truth = pP.contains(p) and B.distance(p) > d
        okm += (pm.contains(p) == truth); oks += (ps.contains(p) == truth)
    print("  points in the difference: mine right %d/%d, shapely right %d/%d" % (okm, n, oks, n))
