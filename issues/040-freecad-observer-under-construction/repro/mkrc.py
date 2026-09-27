"""mkrc.py <name> [FreeCADGui.dll] -- lane vr6-asm: hard-link run copy of the DELIVERY C:/dev/FreeCAD-occt8-perf
(bin lib Mod Ext data share doc only; __pycache__ contents = real copies; userdata and _replaced NOT copied - configs are
never linked) into C:/dev/occt8-mig/vr6asm/rc/<name>; optionally bin/FreeCADGui.dll replaced delete-then-copy."""
import hashlib, os, shutil, sys
D = r"C:/dev/FreeCAD-occt8-perf"
name = sys.argv[1]
dst = os.path.join(r"C:/dev/occt8-mig/vr6asm/rc", name)
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
if len(sys.argv) > 2:
    d = os.path.join(dst, "bin/FreeCADGui.dll")
    os.remove(d)
    shutil.copy2(sys.argv[2], d)
print("bin/FreeCADGui.dll", hashlib.md5(open(os.path.join(dst, "bin/FreeCADGui.dll"), "rb").read()).hexdigest())
