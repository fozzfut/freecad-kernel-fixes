# summarize.py <eval-db.txt> <eval-su.txt> <eval-eu.txt> -> one line per case: stock / deblend / self-union / union
# categories: EXACT = valid + BOP-clean + every face on S / at |t| / on a removed-face wall (oracle MIX=0);
# GEOM = oracle MIX=0 but BOP faults; WRONG = oracle MIX>0 or BRepCheck-invalid or no solid; ERR = no result;
# HANG / CRASH / NOSHELL (self-union needs a stock shell)
import re, sys

def cat(line):
    if not line:
        return '-'
    g = re.search(r'grade=(\w+)', line).group(1)
    mix = int(re.search(r'MIX=(\d+)', line).group(1)) if 'MIX=' in line else 0
    ms = re.search(r'ms=(\d+)', line)
    ms = ms.group(1) if ms else '?'
    if g in ('ERR', 'EXC'):
        return 'ERR'
    off = int(re.search(r'OFF=(\d+)', line).group(1)) if 'OFF=' in line else 1
    if g in ('INV', 'NOSOLID') or mix > 0 or off == 0:
        return 'WRONG'
    if g == 'BOP':
        return 'GEOM'
    return 'EXACT'

def parse(path, resultTag):
    res = {}
    if not path:
        return res
    cur = None
    for l in open(path, encoding='utf-8', errors='replace'):
        l = l.rstrip('\n')
        m = re.match(r'== (\S+) (\S+) rc=(\d+)\s*(\S*)\s*wall=(\d+)s', l)
        if m:
            cur = m.group(1)
            res[cur] = {'rc': m.group(3), 'k': m.group(4), 'wall': m.group(5), 'stock': None, 'res': None, 'extra': ''}
            continue
        if cur is None:
            continue
        if l.startswith('STOCK'):
            res[cur]['stock'] = l
        elif l.startswith(resultTag):
            res[cur]['res'] = l
        elif l.startswith('NO-RAW'):
            res[cur]['extra'] = 'NOSHELL'
    return res

db = parse(sys.argv[1], 'DEBLEND')
su = parse(sys.argv[2] if len(sys.argv) > 2 else None, 'RESULT')
eu = parse(sys.argv[3] if len(sys.argv) > 3 else None, 'RESULT')
tags = list(db.keys())
print('%-22s %-7s %-14s %-14s %-14s' % ('case', 'stock', 'deblend', 'self-union', 'elem-union'))
tot = {}
for t in tags:
    def show(d):
        if t not in d:
            return '-'
        r = d[t]
        if r['k']:
            return r['k']
        if r['extra'] == 'NOSHELL':
            return 'NOSHELL'
        c = cat(r['res'])
        return '%s %ss' % (c, r['wall'])
    st = cat(db[t]['stock']) if t in db else '-'
    row = [st, show(db), show(su), show(eu)]
    for k, v in zip(['stock', 'db', 'su', 'eu'], row):
        tot.setdefault(k, {}).setdefault(v.split()[0], 0)
        tot[k][v.split()[0]] += 1
    print('%-22s %-7s %-14s %-14s %-14s' % (t, *row))
print()
for k, v in tot.items():
    print(k, dict(sorted(v.items())))
