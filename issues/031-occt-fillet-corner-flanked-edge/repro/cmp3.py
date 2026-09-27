# cmp3.py <stock d3.txt> <new d3.txt> [--list] : classify every downstream operation of filsweep3 (round 3).
# Status of one check: OK | BOP (valid, BOP faults) | INV (invalid) | ERR (error/not done) | NA | HANG.
# BOP and INV are SILENT (a result returned without an error that is broken).
# Per check (stock -> new):
#   same          equal status (both silent counts as same: "same-silent")
#   improved      new OK where stock not OK, or new ERR where stock silent
#   err-where-ok  stock OK, new ERR
#   SILENT        new silent where stock was OK or ERR (or INV where stock BOP)
#   HANG          new > 30 s where stock < 5 s (or a watchdog HANG line)
#   slow          new > 10x stock and > 2 s (reported, not a hang)
# fil2/fil3 singles (f2s*, f2m*, f2b*, f3s*) are compared as multisets per family because the edges differ
# between builds; the self fillet (self=) is compared like a check.
import sys, re
from collections import Counter, defaultdict

def load(f):
    d, hang = {}, {}
    for l in open(f, errors="replace"):
        l = l.rstrip("\n")
        if l.startswith("HANG "):
            w = l.split()
            if w[1] == "CASE":
                key = " ".join(w[1:-2]) if w[3].startswith("@") else " ".join(w[1:3])
            else:
                key = " ".join(w[1:6])
            hang[key] = w[-2]
            continue
        if l.startswith("FS3-DONE") or l.startswith("DRIVE") or not l.strip():
            continue
        if l.startswith("CASE"):
            head, _, down = l.partition(" |")
            w = head.split()
            key = " ".join(w[:3]) if len(w) > 2 and w[2].startswith("@") else " ".join(w[:2])
        else:
            head, _, down = l.partition(" |")
            w = head.split()
            key = " ".join(w[:5])
        m = {}
        for k, st, ms in re.findall(r"(\S+?)=(OK|BOP|INV|ERR|NA):(\d+)", head + " " + down):
            m[k] = (st, int(ms))
        d[key] = m
    return d, hang

SIL = ("BOP", "INV")
RANK = {"OK": 3, "ERR": 2, "BOP": 1, "INV": 0, "NA": -1}

def cls(a, b, ta=0, tb=0):
    if b == "HANG":
        return "HANG"
    if tb > 30000 and ta < 5000:
        return "HANG"
    if a == b:
        return "same"
    if b in SIL and (a not in SIL or (a == "BOP" and b == "INV")):
        return "SILENT"
    if a == "OK" and b == "ERR":
        return "err-where-ok"
    if a == "NA" or b == "NA":
        return "na-diff"
    return "improved"

def family(k):
    m = re.match(r"(f2s|f2m|f2b|f3s)\d+$", k)
    return m.group(1) if m else None

a, ha = load(sys.argv[1])
b, hb = load(sys.argv[2])
lst = "--list" in sys.argv
keys = [k for k in a if k in b or k in hb]
tot = defaultdict(Counter)
bad = []
slow = []
for k in keys:
    A = a[k]
    if k in hb and k not in b:
        tot["(op)"]["HANG"] += 1
        bad.append((k, "(watchdog)", "-", "HANG " + hb[k], "HANG"))
        continue
    B = b[k]
    if k in hb:
        bad.append((k, "(watchdog)", "-", "HANG " + hb[k], "HANG"))
        tot["(op)"]["HANG"] += 1
    fams = defaultdict(lambda: [Counter(), Counter()])
    for c in set(A) | set(B):
        f = family(c)
        if f:
            if c in A: fams[f][0][A[c][0]] += 1
            if c in B: fams[f][1][B[c][0]] += 1
            for side, M in ((0, A), (1, B)):
                if c in M and M[c][1] > 30000 and side == 1:
                    tot[f]["HANG?"] += 0
            continue
        sa, ta = A.get(c, ("NA", 0))
        sb, tb = B.get(c, ("NA", 0))
        if c not in B and k in hb:
            continue
        r = cls(sa, sb, ta, tb)
        if sb != "HANG" and tb > 2000 and tb > 10 * max(ta, 1):
            slow.append((k, c, ta, tb))
        tot[c if not c.startswith("self") else "self"][r] += 1
        if r in ("SILENT", "HANG", "err-where-ok"):
            bad.append((k, c, "%s:%d" % (sa, ta), "%s:%d" % (sb, tb), r))
    for f, (ca, cb) in fams.items():
        # multiset: more silent in new -> SILENT; fewer OK -> err-where-ok; more OK / fewer silent -> improved
        sa_, sb_ = ca["BOP"] + ca["INV"], cb["BOP"] + cb["INV"]
        if sb_ > sa_:
            r = "SILENT"
        elif cb["OK"] < ca["OK"]:
            r = "err-where-ok"
        elif cb["OK"] > ca["OK"] or sb_ < sa_:
            r = "improved"
        else:
            r = "same"
        tot[f][r] += 1
        if r in ("SILENT", "err-where-ok"):
            bad.append((k, f, dict(ca), dict(cb), r))
        # slow singles
    for c in B:
        if family(c) and B[c][1] > 30000:
            bad.append((k, c, "-", "HANG-ish %d ms" % B[c][1], "HANG"))
            tot[family(c)]["HANG"] += 1
print("ops compared %d (stock %d, new %d, new hangs %d)" % (len(keys), len(a), len(b), len(hb)))
order = ["self", "thk-0.3", "thk-0.1", "thk+0.1", "thk+0.3", "cutT", "cut06", "cut15", "fuse06", "f2s", "f2m", "f2b",
         "f2all", "f3s", "f3all", "step", "(op)"]
for c in order + sorted(set(tot) - set(order)):
    if c in tot:
        print("  %-8s %s" % (c, dict(tot[c])))
T = Counter()
for c in tot:
    T.update(tot[c])
print("TOTAL", dict(T))
C = Counter(x[4] for x in bad)
print("BAD %d (SILENT %d, HANG %d, err-where-ok %d)" % (len(bad), C["SILENT"], C["HANG"], C["err-where-ok"]))
if slow:
    print("SLOW (>10x and >2 s):", len(slow))
    for s in slow[:20]:
        print("   ", s[0].split("/")[-1], s[1], s[2], "->", s[3])
if lst:
    for x in bad:
        print("  ", x[0].split("/")[-1], x[1], x[2], "->", x[3])
