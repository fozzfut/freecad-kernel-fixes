"""summ.py <a-vs-b result file> [a] [b] : per family (tag prefix up to the digits) transition table base->new and
identity check: every case whose new verdict is not in {EXACT, EXACT?} (outside the class or not handled) must have
the SAME result fields as the base (err, grade, bop, nf, vol) - known stock nondeterminism (err code 1<->6, volume
of invalid shapes) is reported separately. Also lists regressions: base EXACT/EXACT? -> anything else, and any
ERROR -> WRONG."""
import collections
import re
import sys

fn = sys.argv[1]
A = sys.argv[2] if len(sys.argv) > 2 else 'a'
B = sys.argv[3] if len(sys.argv) > 3 else 'f'
rows = [l.split() for l in open(fn) if l.strip()]
tab = collections.defaultdict(dict)
for r in rows:
    tab[r[0]][r[1]] = ' '.join(r)


def fld(s, k):
    m = re.search(r'\b' + k + r'=(\S+)', s)
    return m.group(1) if m else '?'


def fam(tag):
    m = re.match(r'([a-z]+)', tag)
    return m.group(1)


trans = collections.defaultdict(collections.Counter)
regress, diffs, nondet = [], [], []
for t, v in sorted(tab.items()):
    if A not in v or B not in v:
        continue
    a, b = v[A].split()[3], v[B].split()[3]
    trans[fam(t)][(a, b)] += 1
    if a in ('EXACT', 'EXACT?') and b not in ('EXACT', 'EXACT?'):
        regress.append((t, a, b))
    if a == 'ERROR' and b == 'WRONG':
        regress.append((t, a, b))
    if b not in ('EXACT', 'EXACT?') or a in ('EXACT', 'EXACT?'):
        fa = [fld(v[A], k) for k in ('err', 'grade', 'bop', 'nf', 'vol')]
        fb = [fld(v[B], k) for k in ('err', 'grade', 'bop', 'nf', 'vol')]
        if fa != fb:
            if fa[1] == fb[1] == 'ERR' or (fa[1] == fb[1] == 'INV' and fa[3] == fb[3]):
                nondet.append((t, fa, fb))
            else:
                diffs.append((t, fa, fb))
for f, c in sorted(trans.items()):
    print(f, ' '.join('%s->%s:%d' % (k[0], k[1], n) for k, n in sorted(c.items())))
print('REGRESSIONS', len(regress), regress[:10])
print('IDENTITY-DIFFS (outside class)', len(diffs))
for d in diffs[:20]:
    print('  ', d)
print('NONDET (err code / invalid volume, both broken)', len(nondet))
for d in nondet[:10]:
    print('  ', d)
