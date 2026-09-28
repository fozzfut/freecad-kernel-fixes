# idcmp.py <A> <B> : compare two identity result files (class/rv116/rvx: one line per case; corp: RES lines; b33: blocks)
# on the user-visible fields: done, err, exc, valid, grade, volume (4 decimals), faces/shells/solids.
import sys, re
KEYS = ("done", "err", "exc", "valid", "grade", "vol", "nf", "shells", "solids", "faces", "nsol")
def parse(fn):
    out = {}; cur = None
    for ln in open(fn, encoding="utf-8", errors="replace"):
        ln = ln.rstrip("\n")
        if ln.startswith("== "):
            cur = ln.split()[1]; continue
        if cur is not None and ln.startswith("STOCK"):
            out[cur] = ln; cur = None; continue
        f = ln.split()
        if len(f) < 3 or ln.startswith("IN ") or ln.startswith("done "): continue
        out[f[1] if f[0] == "RV" else f[0]] = ln
    return out
def sig(ln):
    kv = dict(m.group(1, 2) for m in re.finditer(r"(\w+)=(\S+)", ln))
    return tuple((k, kv.get(k)) for k in KEYS if k in kv)
a, b = parse(sys.argv[1]), parse(sys.argv[2])
same = diff = 0; miss = sorted(set(a) ^ set(b)); lines = []
for k in sorted(set(a) & set(b)):
    if sig(a[k]) == sig(b[k]): same += 1
    else:
        diff += 1; lines.append("   %s | %s | %s" % (k, " ".join("%s=%s" % x for x in sig(a[k])), " ".join("%s=%s" % x for x in sig(b[k]))))
print("compared %d same %d diff %d missing %d %s" % (same + diff, same, diff, len(miss), miss[:5]))
print("\n".join(lines))
