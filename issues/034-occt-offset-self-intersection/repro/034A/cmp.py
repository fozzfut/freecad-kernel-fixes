"""cmp.py <a.txt> <b.txt> <aOutDir> <bOutDir> : per tag compare the RES fields that are results (done, err, exc,
grade, bop, nf, vol) exactly, and the canonical signature files (<tag>.sig from off034: counts, volume, area, centre
of mass, one line per face) with a relative tolerance RTOL (stock itself changes face order and last digits run to
run: heap-address map order). Timing (ms), peakMB and TRACE are ignored.
Prints one line per changed tag and a summary:  CMP same=<n> changed=<n> <a-grade>-><b-grade>:<count> ..."""
import collections
import os
import re
import sys

KEYS = ("done", "err", "exc", "grade", "bop", "nf", "vol")
RTOL = 1e-7


def load(p):
    d = collections.OrderedDict()
    for line in open(p, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        tag = line.split()[0]
        f = dict(re.findall(r"(\w+)=(\S+)", line.split("TRACE[")[0]))
        tr = line.split("TRACE[")[1].rstrip("]") if "TRACE[" in line else ""
        d[tag] = (f, tr)
    return d


def close(x, y):
    return abs(x - y) <= RTOL * max(1.0, abs(x), abs(y))


def sig(p):
    if not os.path.isfile(p):
        return None
    head, faces = None, []
    for line in open(p):
        w = line.split()
        if w[0] == "S":
            head = [int(v) for v in w[1:6]] + [float(v) for v in w[6:]]
        elif w[0] == "F":
            faces.append((w[1], [float(v) for v in w[2:6]], [int(v) for v in w[6:]]))
    return head, faces


def sig_equal(a, b):
    """None/None equal; else counts exact, volume/area/centre within RTOL, faces matched one to one"""
    if a is None or b is None:
        return a is None and b is None, "missing"
    ha, fa = a
    hb, fb = b
    if ha[:5] != hb[:5]:
        return False, "counts %s vs %s" % (ha[:5], hb[:5])
    if not all(close(x, y) for x, y in zip(ha[5:], hb[5:])):
        return False, "vol/area/cm %s vs %s" % (ha[5:], hb[5:])
    used = [False] * len(fb)
    for t, v, n in fa:
        hit = -1
        for j, (t2, v2, n2) in enumerate(fb):
            if not used[j] and t2 == t and n2 == n and all(close(x, y) for x, y in zip(v, v2)):
                hit = j
                break
        if hit < 0:
            return False, "face %s %s %s unmatched" % (t, v, n)
        used[hit] = True
    return True, ""


a, b = load(sys.argv[1]), load(sys.argv[2])
oa, ob = sys.argv[3], sys.argv[4]
same = 0
trans = collections.Counter()
for tag, (fa, _) in a.items():
    fb, tr = b.get(tag, ({}, ""))
    va = tuple(fa.get(k, "?") for k in KEYS)
    vb = tuple(fb.get(k, "?") for k in KEYS)
    ok, why = sig_equal(sig(os.path.join(oa, tag + ".sig")), sig(os.path.join(ob, tag + ".sig")))
    if va == vb and ok:
        same += 1
        continue
    trans[fa.get("grade", "?") + "->" + fb.get("grade", "?")] += 1
    print("CHANGED %s a[%s] b[%s] %s %s" % (
        tag, " ".join("%s=%s" % kv for kv in zip(KEYS, va)), " ".join("%s=%s" % kv for kv in zip(KEYS, vb)),
        ("sig: " + why) if (va == vb and not ok) else "", ("TRACE " + tr) if tr else ""))
print("CMP same=%d changed=%d %s" % (same, sum(trans.values()), " ".join("%s:%d" % kv for kv in sorted(trans.items()))))
