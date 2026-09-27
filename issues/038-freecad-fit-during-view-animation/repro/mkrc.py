"""mkrc.py <name> [FreeCADGui.dll] -- lane vr6-unconf (copied from undovis): hard-link run copy of the DELIVERY C:/dev/FreeCAD-occt8-perf
(bin lib Mod Ext data share doc only; __pycache__ contents = real copies; userdata and _replaced NOT copied - configs are
never linked) into C:/dev/occt8-mig/vr6unconf/rc/<name>; optionally bin/FreeCADGui.dll replaced delete-then-copy."""
import hashlib, os, shutil, sys
D = os.environ.get("MKRC_SRC", r"C:/dev/FreeCAD-occt8-perf")
name = sys.argv[1]
dst = os.path.join(r"C:/dev/occt8-mig/vr6unconf/rc", name)
if os.path.exists(dst):
    sys.exit("exists: " + dst)
n = c = 0
for top in ("bin", "lib", "Mod", "Ext", "data", "share", "doc"):
    for root, dirs, files in os.walk(os.path.join(D, top)):
        rel = os.path.relpath(root, D)
        od = os.path.join(dst, rel)
        os.makedirs(od, exist_ok=True)
        pyc = "__pycache__" in rel.split(os.sep)
        for f in files:
            s, d = os.path.join(root, f), os.path.join(od, f)
            if pyc:
                shutil.copy2(s, d); c += 1
            else:
                os.link(s, d); n += 1
print("links", n, "copies", c)
# further args: <published relpath>=<file> (delete-then-copy, links are never written through); a bare path = bin/FreeCADGui.dll
for a in sys.argv[2:]:
    rel, _, src = a.rpartition("=") if "=" in a else ("bin/FreeCADGui.dll", "", a)
    d = os.path.join(dst, rel)
    os.remove(d)
    shutil.copy2(src, d)
for rel in ("bin/FreeCADGui.dll", "lib/PartGui.pyd"):
    print(rel, hashlib.md5(open(os.path.join(dst, rel), "rb").read()).hexdigest())
