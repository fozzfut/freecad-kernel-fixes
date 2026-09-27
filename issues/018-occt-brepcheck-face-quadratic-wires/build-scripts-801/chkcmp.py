"""chkcmp.py <runs/tag> <variantA> <variantB>: compare two chkrun.sh outputs shape by shape (digest of the full status
dump, validity, outcome); on a digest difference, diff the dumps and print the first lines. Exit 1 on any difference."""
import os
import sys

d, a, b = sys.argv[1:4]


def load(v):
    r = {}
    for line in open(os.path.join(d, v + ".tsv"), encoding="utf-8", errors="replace"):
        f = line.rstrip("\n").split("\t")
        if f[0] == "BEGIN":
            r.setdefault(int(f[1]), ("CRASH", f[2], None))
            continue
        i = int(f[0])
        if f[2] == "OK":
            r[i] = ("OK", f[1], (f[4], f[5], f[6]))
        else:
            r[i] = ("FAIL", f[1], tuple(f[3:]))
    return r


ra, rb = load(a), load(b)
same = diff = 0
for i in sorted(set(ra) | set(rb)):
    x, y = ra.get(i), rb.get(i)
    if x is not None and y is not None and x[0] == y[0] and x[2] == y[2]:
        same += 1
        continue
    diff += 1
    print("DIFF", i, x, y)
    if x and y and x[0] == "OK" and y[0] == "OK":
        def dump(v):
            import glob
            p = os.path.join(d, v + ".d", "%d_%s.txt" % (i, os.path.basename(x[1])))
            if not os.path.isfile(p):  # chkrun.sh before the fix named the dump of shape 0 "1_<name>"
                p = glob.glob(os.path.join(d, v + ".d", "*_%s.txt" % os.path.basename(x[1])))[0]
            return open(p, encoding="utf-8").read().splitlines()
        la, lb = dump(a), dump(b)
        k = 0
        for p, q in zip(la, lb):
            if p != q:
                print("   ", a, p, "|", b, q)
                k += 1
                if k >= 5:
                    break
print("COMPARE %s vs %s: shapes %d same %d different %d" % (a, b, same + diff, same, diff))
sys.exit(1 if diff else 0)
