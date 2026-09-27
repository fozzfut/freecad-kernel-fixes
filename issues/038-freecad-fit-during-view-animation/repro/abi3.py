"""abi3.py - lane vr6-unconf round 3: D0 byte diffs and export/import name tables (pefile, symbol limits raised)."""
import sys, pefile
pefile.MAX_SYMBOL_EXPORT_COUNT = 1 << 20
pefile.MAX_IMPORT_SYMBOLS = 1 << 20
pefile.MAX_DLL_LENGTH = 1 << 16
B = "C:/dev/occt8-mig/vr6unconf/build/"
DLV = "C:/dev/FreeCAD-occt8-perf/bin/FreeCADGui.dll"
R2 = B + "out-gui2-fix/FreeCADGui.dll"
R2C = B + "out-gui2-ctl/FreeCADGui.dll"
C3 = B + "out-gui3-ctl/FreeCADGui.dll"
F3 = B + "out-gui3-fix/FreeCADGui.dll"
NEG = "C:/Program Files/FreeCAD 1.1/bin/FreeCADGui.dll"

def abi(p):
    pe = pefile.PE(p, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT'],
                                           pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    ex = set(e.name for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name)
    im = set((d.dll.decode().lower(), (i.name or b'#%d' % i.ordinal)) for d in pe.DIRECTORY_ENTRY_IMPORT for i in d.imports)
    return ex, im

def bd(a, b):
    A, B_ = open(a, 'rb').read(), open(b, 'rb').read()
    diff = [i for i, (x, y) in enumerate(zip(A, B_)) if x != y]
    return len(A), len(B_), len(diff) + abs(len(A) - len(B_)), [hex(i) for i in diff[:12]]

print("D0 gui3-ctl vs gui2-ctl (same 3eccec5 sources, same-length overlay path):", bd(C3, R2C))
print("D0 gui3-ctl vs delivered 7af65a21:", bd(C3, DLV)[:3])
for lab, a, b in (("delivered -> fix3", DLV, F3), ("r2 fix2 -> fix3", R2, F3), ("gui3-ctl -> delivered", C3, DLV),
                  ("NEG 1.1.1 -> fix3", NEG, F3)):
    x, y = abi(a), abi(b)
    print("== %s: exports %d -> %d +%d -%d | imports %d -> %d +%d -%d" % (lab, len(x[0]), len(y[0]), len(y[0] - x[0]),
          len(x[0] - y[0]), len(x[1]), len(y[1]), len(y[1] - x[1]), len(x[1] - y[1])))
    if not lab.startswith("NEG"):
        for n in sorted(y[0] - x[0]): print("  +E", n.decode())
        for n in sorted(x[0] - y[0]): print("  -E", n.decode())
        for n in sorted(y[1] - x[1]): print("  +I", n)
        for n in sorted(x[1] - y[1]): print("  -I", n)
