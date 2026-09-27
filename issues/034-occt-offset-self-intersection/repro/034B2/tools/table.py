"""table.py <result file> <variant> : class coverage per family: group = family x (plain|thick) x (analytic a | NURBS n |
NURBS split m) x member (|d| >= r: in the class; |d| < r: control outside the class); counts of verdicts.
Twin rule: a 'WRONG' of a thick NURBS member whose only oracle fault is one MIX face (the removed-face wall on a bounded
B-spline surface, which the oracle cannot project on) counts EXACT-twin when its volume equals the analytic twin's to
1e-7 relative and mc shows 0 disagreements."""
import collections
import re
import sys

fn, V = sys.argv[1], sys.argv[2]
rows = {}
for l in open(fn):
    w = l.split()
    if len(w) > 3 and w[1] == V:
        rows[w[0]] = l
def f(s, k):
    m = re.search(r'\b' + k + r'=(\S+)', s)
    return m.group(1) if m else None
tab = collections.defaultdict(collections.Counter)
for tag, l in rows.items():
    m = re.match(r'([a-z]+)([0-9.]+)([anm])p([012])_(thk)?([+-][0-9.]+)', tag)
    if not m:
        continue
    fam, r, var, p, thk, d = m.groups()
    r = float(r); d = abs(float(d))
    member = 'class' if d >= r - 1e-12 else 'ctrl'
    verdict = l.split()[3]
    if verdict == 'EXACT?':
        verdict = 'EXACT'
    if verdict == 'WRONG' and var in 'nm' and f(l, 'grade') == 'OK' and f(l, 'MIX') == '1' and (f(l, 'mc') or '').startswith('0/'):
        twin = rows.get(tag.replace(var + 'p', 'ap'))
        if twin and twin.split()[3].startswith('EXACT'):
            va, vb = float(f(l, 'vol')), float(f(twin, 'vol'))
            if abs(va - vb) <= 1e-7 * abs(vb):
                verdict = 'EXACT-twin'
    if member == 'class' and d == r:
        member = 'class d=r'
    tab[(fam, 'thick' if thk else 'plain', var, member)][verdict] += 1
for k in sorted(tab):
    print('%-6s %-5s %s %-9s %s' % (k + (' '.join('%s:%d' % x for x in sorted(tab[k].items())),)))
