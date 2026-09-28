# locsum.py <run.txt> : per case, compare variants geo/loc/subloc/nest with "none" (unlocated).
# EQ = same grade + nf/ns/nsh equal + volume/area rel 1e-7 + centroid/bbox abs 1e-6*size
import sys, re, collections
def parse(p):
    d = collections.OrderedDict()
    for ln in open(p):
        t = ln.split()
        if len(t) < 3 or t[0] != 'LOC': continue
        if t[2].startswith('CRASH') or t[2] in ('BUILD-FAILED', 'NO-SUCH-CASE'):
            d.setdefault(t[1], {})['*'] = {'grade': t[2]}; continue
        kv = dict(x.split('=', 1) for x in t[3:] if '=' in x)
        d.setdefault(t[1], {})[t[2]] = kv
    return d
def same(a, b):
    if a.get('grade') != b.get('grade'): return False
    if a.get('grade') == 'ERR': return a.get('err') == b.get('err')
    for k in ('nf', 'ns', 'nsh', 'valid', 'bop'):
        if a.get(k) != b.get(k): return False
    for k in ('vol', 'area'):
        x, y = float(a[k]), float(b[k])
        if abs(x - y) > 1e-7 * max(1, abs(x), abs(y)): return False
    ca = [float(v) for v in a['c'].split(',') + a['bb'].split(',')]
    cb = [float(v) for v in b['c'].split(',') + b['bb'].split(',')]
    sz = max(1.0, max(abs(v) for v in ca))
    return all(abs(x - y) <= 1e-6 * sz for x, y in zip(ca, cb))
if __name__ == '__main__':
    d = parse(sys.argv[1])
    cnt = collections.Counter()
    for c, vs in d.items():
        if '*' in vs: print(c, vs['*']['grade']); cnt['broken'] += 1; continue
        n = vs.get('none')
        row = []
        for v in ('geo', 'loc', 'subloc', 'nest', 'geon'):
            if v not in vs: row.append(v + ':missing'); continue
            ok = same(n, vs[v]); cnt[v + (':EQ' if ok else ':DIFF')] += 1
            if not ok: row.append('%s:%s/%s' % (v, vs[v]['grade'], vs[v].get('err')))
        print('%-28s none=%s/%s %s' % (c, n['grade'], n.get('err'), ' '.join(row) if row else 'ALL-EQ'))
    print('SUMMARY', dict(sorted(cnt.items())))
