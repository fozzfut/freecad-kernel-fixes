"""expnames.py - full export NAME table of a PE (manual parse; pefile stops at 8192)."""
import struct, sys, pefile
def names(p):
    pe = pefile.PE(p, fast_load=True)
    d = pe.OPTIONAL_HEADER.DATA_DIRECTORY[0]
    data = pe.get_memory_mapped_image()
    (ch, ts, ma, mi, nm, base, nf, nn, af, an, ao) = struct.unpack_from("<IIHHIIIIIII", data, d.VirtualAddress)
    out = set()
    for i in range(nn):
        rva = struct.unpack_from("<I", data, an + 4 * i)[0]
        out.add(data[rva:data.index(b"\0", rva)])
    return out
B = "C:/dev/occt8-mig/vr6unconf/build/"
DLV = "C:/dev/FreeCAD-occt8-perf/bin/FreeCADGui.dll"
pairs = [("delivered 7af65a21 -> fix3", DLV, B + "out-gui3-fix/FreeCADGui.dll"),
         ("r2 fix2 39a66e0c -> fix3", B + "out-gui2-fix/FreeCADGui.dll", B + "out-gui3-fix/FreeCADGui.dll"),
         ("gui3-ctl -> delivered", B + "out-gui3-ctl/FreeCADGui.dll", DLV),
         ("NEG 1.1.1 -> fix3", "C:/Program Files/FreeCAD 1.1/bin/FreeCADGui.dll", B + "out-gui3-fix/FreeCADGui.dll")]
for lab, a, b in pairs:
    x, y = names(a), names(b)
    print("== %s: export names %d -> %d +%d -%d" % (lab, len(x), len(y), len(y - x), len(x - y)))
    if not lab.startswith("NEG"):
        for n in sorted(y - x): print("  +", n.decode())
        for n in sorted(x - y): print("  -", n.decode())
