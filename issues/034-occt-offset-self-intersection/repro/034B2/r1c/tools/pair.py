"""pair.py <k.sh output> [va] [vb] : per tag verdict pair a->b; prints counts and every tag whose pair is not
ERROR->EXACT / EXACT->EXACT(same vol), plus EXACT results with a reference that is not sd=0."""
import re, sys, collections
f = sys.argv[1]; va = sys.argv[2] if len(sys.argv) > 2 else 'a2'; vb = sys.argv[3] if len(sys.argv) > 3 else 'x'
rows = collections.OrderedDict()
for l in open(f):
    p = l.split()
    if len(p) < 4 or p[2] != 'R': continue
    d = dict(re.findall(r'(\w+)=(\S+)', l)); d['V'] = p[3]
    rows.setdefault(p[0], {})[p[1]] = d
c = collections.Counter(); odd = []
for t, v in rows.items():
    if va not in v or vb not in v: continue
    a, b = v[va], v[vb]
    k = (a['V'], b['V']); c[k] += 1
    same = a['V'] == b['V'] and a.get('vol') == b.get('vol') and a.get('nf') == b.get('nf')
    if not (k == ('ERROR', 'EXACT') or same):
        odd.append(f"{t}: {a['V']}(vol={a.get('vol')} nf={a.get('nf')} err={a.get('err')}) -> {b['V']}(vol={b.get('vol')} nf={b.get('nf')} err={b.get('err')} mc={b.get('mc')} MIX={b.get('MIX')} sd={b.get('sd')})")
    if b['V'] == 'EXACT' and b.get('sd') not in ('-1', '0'):
        odd.append(f"{t}: {vb} EXACT but sd={b.get('sd')}")
print(dict(c))
print('\n'.join(odd))
