# cmp.py <base.txt> <new.txt> [variant-base] [variant-new]: per tag grade/vol/sd; prints differing rows + summary
import sys, re
def load(p, v):
    d = {}
    for l in open(p, encoding='utf-8', errors='replace'):
        f = l.split()
        if len(f) < 4 or f[2] != 'R': continue
        if v and f[1] != v: continue
        g = f[3]; kv = dict(x.split('=', 1) for x in f if '=' in x and not x.startswith('rem'))
        d[f[0]] = (g, kv.get('vol', '?'), kv.get('sd', '?'), kv.get('err', '?'), kv.get('ms', '?'))
    return d
a = load(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else None)
b = load(sys.argv[2], sys.argv[4] if len(sys.argv) > 4 else None)
same = 0; diff = []
for k in a:
    if k not in b: continue
    x, y = a[k], b[k]
    gx = x[0].rstrip('?'); gy = y[0].rstrip('?')
    sdok = x[2] == y[2] or '-1' in (x[2], y[2])
    if gx == gy and (gx != 'EXACT' or abs(float(x[1]) - float(y[1])) <= 1e-6 * max(1, abs(float(x[1])))) and sdok:
        same += 1
    else:
        diff.append((k, x, y))
for k, x, y in diff: print("DIFF %-28s %s -> %s" % (k, x, y))
print("compared", len([k for k in a if k in b]), "same", same, "diff", len(diff))
