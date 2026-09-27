"""Compare two COFF .obj files section by section (bigobj aware): multiset of (name, size, md5(raw))
Usage: coffcmp.py a.obj b.obj  -> prints sections present only in one (grouped by name)."""
import sys, struct, hashlib, collections


def secs(p):
    d = open(p, "rb").read()
    if d[:4] == b"\x00\x00\xff\xff":  # bigobj
        nsec, = struct.unpack_from("<I", d, 44)
        symptr, nsym = struct.unpack_from("<II", d, 48)
        off = 56
        symsz = 20
    else:
        nsec, = struct.unpack_from("<H", d, 2)
        symptr, nsym = struct.unpack_from("<II", d, 8)
        off = 20 + struct.unpack_from("<H", d, 16)[0]
        symsz = 18
    strtab = symptr + nsym * symsz
    out = []
    for i in range(nsec):
        h = d[off + 40 * i: off + 40 * i + 40]
        name = h[:8].rstrip(b"\0")
        if name.startswith(b"/"):
            o = int(name[1:]); name = d[strtab + o: d.index(b"\0", strtab + o)]
        size, ptr = struct.unpack_from("<II", h, 16)
        raw = d[ptr: ptr + size] if ptr else b""
        out.append((name.decode(errors="replace"), size, hashlib.md5(raw).hexdigest()))
    return out


a, b = secs(sys.argv[1]), secs(sys.argv[2])
ca, cb = collections.Counter(a), collections.Counter(b)
oa, ob = ca - cb, cb - ca
print("sections", len(a), len(b), "identical", sum((ca & cb).values()))
ga = collections.Counter(n for (n, s, h) in oa.elements()); gb = collections.Counter(n for (n, s, h) in ob.elements())
print("differ only-a:", dict(ga)); print("differ only-b:", dict(gb))
