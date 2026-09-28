# locsum2.py <run.txt> [--neg] : class verdict of lane R-034-loc round 2.
# Twin rule: loc/subloc/floc must equal geo (geometry-transformed copy by T); nest must equal geon (same composed
# matrix baked into the geometry). Also reports equality with "none" (unlocated, base frame) for information.
# --neg: negative control - perturb the volume of the first located OK line by 1e-5 relative; must be caught.
import sys, collections
from locsum import parse, same
TW = {'loc': 'geo', 'subloc': 'geo', 'floc': 'geo', 'nest': 'geon'}
d = parse(sys.argv[1])
if '--neg' in sys.argv:
    for c, vs in d.items():
        v = vs.get('loc')
        if v and v.get('grade') != 'ERR' and 'vol' in v:
            v['vol'] = repr(float(v['vol']) * (1 + 1e-5)); print('NEG perturbed', c, 'loc'); break
cnt = collections.Counter(); bad = []
for c, vs in d.items():
    if '*' in vs: cnt['broken'] += 1; bad.append((c, 'broken')); continue
    for v, t in TW.items():
        if v not in vs or t not in vs: cnt['missing'] += 1; continue
        ok = same(vs[t], vs[v]); cnt['twin:' + ('EQ' if ok else 'DIFF')] += 1
        if not ok: bad.append((c, '%s:%s/%s vs %s:%s/%s' % (v, vs[v]['grade'], vs[v].get('err'), t, vs[t]['grade'], vs[t].get('err'))))
        if 'none' in vs: cnt['none:' + ('EQ' if same(vs['none'], vs[v]) else 'DIFF')] += 1
for b in bad: print('DIFF', *b)
print('SUMMARY', dict(sorted(cnt.items())))
