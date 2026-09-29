# twin.py <rv run> [--neg]: twin rule of the review oracle - loc == geo, nest == geon (same T); metrics compared:
# grade, error text, validity, solids/faces, volume/area (rel 1e-7), centre of mass in the local frame (abs 1e-6 * diag)
import sys, re, collections
def parse(p):
    d = collections.defaultdict(dict)
    for l in open(p):
        t = l.split()
        if len(t) < 7 or t[0] != 'RV' or t[1] == 'BUILD-FAILED' or 'BUILD-FAILED' in l: continue
        key = tuple(t[1:5]); var = t[5]; rest = [x for x in t[6:] if not x.startswith('li=')]
        r = {'grade': rest[0]}
        if rest[0] == 'ERR': r['err'] = rest[1]
        for x in rest[1:]:
            if '=' in x: k, v = x.split('=', 1); r[k] = v
        d[key][var] = r
    return d
def same(a, b):
    if a['grade'] != b['grade']: return False
    if a['grade'] == 'ERR': return a['err'] == b['err']
    for k in ('valid', 'ns', 'nf'):
        if a[k] != b[k]: return False
    for k in ('vol', 'area'):
        x, y = float(a[k]), float(b[k])
        if abs(x - y) > 1e-7 * max(abs(x), abs(y), 1): return False
    ca = [float(v) for v in a['cl'].split(',')]; cb = [float(v) for v in b['cl'].split(',')]
    tol = 1e-6 * max(float(a['diag']), 1)
    if float(a['vol']) > 1e50: return True  # unbounded result (stock), centre meaningless
    return all(abs(p - q) <= tol for p, q in zip(ca, cb))
d = parse(sys.argv[1])
if '--neg' in sys.argv:
    for k, vs in d.items():
        if vs.get('loc', {}).get('grade') == 'OK':
            vs['loc']['vol'] = repr(float(vs['loc']['vol']) * (1 + 1e-6)); print('NEG perturbed', k); break
cnt = collections.Counter()
for k, vs in sorted(d.items()):
    for v, t in (('loc', 'geo'), ('nest', 'geon')):
        ok = same(vs[v], vs[t]); cnt['EQ' if ok else 'DIFF'] += 1
        if not ok:
            print('DIFF', ' '.join(k), v, '%s/%s/valid=%s' % (vs[v]['grade'], vs[v].get('err', ''), vs[v].get('valid', '-')), 'vs', t, '%s/%s/valid=%s' % (vs[t]['grade'], vs[t].get('err', ''), vs[t].get('valid', '-')))
    g = vs['geo']; n = vs['none']
    cnt['frame(geo==none):' + ('EQ' if same(g, n) else 'DIFF')] += 1
print('SUMMARY', dict(cnt))
