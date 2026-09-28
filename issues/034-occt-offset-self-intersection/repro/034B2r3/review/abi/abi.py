# abi.py: exports vs weekly, imports vs delivery, every new import resolved by the delivery bin (+ fake-symbol negative control)
import pefile, os, sys
W = r"C:\dev\FreeCAD-occt8\FreeCAD_weekly-2026.09.23-Windows-x86_64-experimental\bin"
D = r"C:\dev\FreeCAD-occt8-perf\bin"
NEW = r"C:\dev\freecad-kernel-fixes\build\variants801\034B2r3\TKOffset.dll"
def exps(p):
    pe = pefile.PE(p, fast_load=True); pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
    return set(e.name.decode() for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name) if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT') else set()
def imps(p):
    pe = pefile.PE(p, fast_load=True); pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    r = set()
    for d in pe.DIRECTORY_ENTRY_IMPORT:
        for i in d.imports:
            r.add((d.dll.decode().lower(), i.name.decode() if i.name else '#%d' % i.ordinal))
    return r
en, ew = exps(NEW), exps(os.path.join(W, "TKOffset.dll"))
print("exports new %d weekly %d diff %d" % (len(en), len(ew), len(en ^ ew)))
inew, idlv = imps(NEW), imps(os.path.join(D, "TKOffset.dll"))
print("import dlls new", sorted(set(a for a, b in inew) - set(a for a, b in idlv)), "gone", sorted(set(a for a, b in idlv) - set(a for a, b in inew)))
added = sorted(inew - idlv); print("imports +%d -%d" % (len(added), len(idlv - inew)))
cache = {}
def resolves(dll, name):
    if dll not in cache:
        for base in (D, r"C:\Windows\System32"):
            p = os.path.join(base, dll)
            if os.path.exists(p):
                cache[dll] = exps(p); break
        else:
            cache[dll] = set()
    return name in cache[dll]
bad = [x for x in added if not resolves(*x)]
for x in added: print("  +", x[0], x[1][:90], "OK" if x not in bad else "UNRESOLVED")
print("unresolved", len(bad))
print("NEG fake symbol resolves:", resolves("tkg3d.dll", "?FakeSymbol034b2@@YAXXZ"))
