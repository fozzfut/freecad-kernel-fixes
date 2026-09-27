# cmpdown.py <stock swd.txt> <new swd.txt>: compare the downstream checks (filsweep FILSWEEP_DOWN) per operation.
# A check "works" when its result is a valid solid (OK or BOP: BRepCheck valid; BOP = BRepAlgoAPI_Check also
# finds faults). fil2 / fil3: number of single second fillets that work. WORSE = stock works and new does not
# (or fewer second fillets work); BETTER = the other way round.
import sys, re
from collections import Counter

def load(f):
    d = {}
    for l in open(f, errors="replace"):
        if l.startswith("SWEEP") or " | " not in l:
            continue
        head, down = l.rstrip("\n").split(" | ", 1)
        w = head.split()
        key = " ".join(w[:4] + [w[5]])
        m = dict(re.findall(r"(\w+[-+]?)=(\S+)", down))
        d[key] = m
    return d

def works(v):
    return v is not None and (v.startswith("OK") or v.startswith("BOP"))

def nok(v):
    if v is None or v == "NA":
        return None
    m = re.match(r"(\d+)/(\d+)", v)
    return int(m.group(1)) if m else 0

a, b = load(sys.argv[1]), load(sys.argv[2])
keys = [k for k in a if k in b]
tot = {c: Counter() for c in ("self", "thk-", "thk+", "cut", "fil2", "fil3", "step")}
worse = []
for k in keys:
    for c in tot:
        va, vb = a[k].get(c), b[k].get(c)
        if c in ("fil2", "fil3"):
            x, y = nok(va), nok(vb)
            if x is None and y is None:
                r = "na"
            elif (y or 0) < (x or 0):
                r = "worse"
            elif (y or 0) > (x or 0):
                r = "better"
            else:
                r = "same"
        else:
            if works(va) and not works(vb):
                r = "worse"
            elif works(vb) and not works(va):
                r = "better"
            else:
                r = "same"
        tot[c][r] += 1
        if r == "worse":
            worse.append((k, c, va, vb))
print("ops compared", len(keys), "(stock %d, new %d)" % (len(a), len(b)))
for c, cnt in tot.items():
    print("  %-5s %s" % (c, dict(cnt)))
print("WORSE", len(worse))
for w in worse:
    print("  ", w[0].split("/")[-1], w[1], w[2], "->", w[3])
