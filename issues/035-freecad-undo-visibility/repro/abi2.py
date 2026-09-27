"""Raw import/export table reader (pefile truncates long import lists): imports read from each descriptor's
OriginalFirstThunk array until the 0 terminator; exports = name table."""
import sys, struct, pefile
def info(p):
    pe = pefile.PE(p, fast_load=True)
    data = pe.get_memory_mapped_image()
    imp_rva = pe.OPTIONAL_HEADER.DATA_DIRECTORY[1].VirtualAddress
    im = set(); off = imp_rva
    while True:
        oft, ts, fc, name, ft = struct.unpack_from('<IIIII', data, off)
        if oft == 0 and name == 0 and ft == 0: break
        dll = data[name:name+260].split(b'\0')[0].decode().lower()
        t = oft or ft
        while True:
            e = struct.unpack_from('<Q', data, t)[0]
            if e == 0: break
            if e >> 63: im.add((dll, 'ord%d' % (e & 0xffff)))
            else: im.add((dll, data[(e & 0x7fffffff) + 2:(e & 0x7fffffff) + 1024].split(b'\0')[0].decode()))
            t += 8
        off += 20
    exp_rva = pe.OPTIONAL_HEADER.DATA_DIRECTORY[0].VirtualAddress
    ch, ts, mj, mn, nm, ob, nf, nn, af, an, ao = struct.unpack_from('<IIHHIIIIIII', data, exp_rva)
    ex = set(data[struct.unpack_from('<I', data, an + 4*i)[0]:][:2048].split(b'\0')[0] for i in range(nn))
    return ex, im, nf
if __name__ == '__main__':
    a, b = info(sys.argv[1]), info(sys.argv[2])
    print('exports(named)', len(a[0]), len(b[0]), 'functions', a[2], b[2], '+%d -%d' % (len(b[0]-a[0]), len(a[0]-b[0])))
    print('imports', len(a[1]), len(b[1]), '+%d -%d' % (len(b[1]-a[1]), len(a[1]-b[1])))
    for x in sorted(b[1]-a[1]): print('  +', x)
    for x in sorted(a[1]-b[1]): print('  -', x)
