"""mkrc.py <name> [lib/<file>=<replacement> ...]: hard-link run copy of the delivery C:/dev/FreeCAD-occt8-perf
into C:/dev/occt8-mig/vr6body/rc/<name>. Only bin/lib/Mod/Ext/data/share/doc are linked (never userdata or any
config, AGENT-RULES 27.09); __pycache__ files are real copies; each replaced file is delete-then-copy.
A fresh cfg dir rc/<name>-cfg is made from a COPY of the delivery user.cfg/system.cfg."""
import hashlib, os, shutil, sys

W = "C:/dev/FreeCAD-occt8-perf"
name = sys.argv[1]
dst = os.path.join("C:/dev/occt8-mig/vr6body/rc", name)
if os.path.exists(dst):
    sys.exit("exists: " + dst)
n = c = 0
for top in ("bin", "lib", "Mod", "Ext", "data", "share", "doc"):
    for root, dirs, files in os.walk(os.path.join(W, top)):
        rel = os.path.relpath(root, W)
        od = os.path.join(dst, rel)
        os.makedirs(od, exist_ok=True)
        pyc = "__pycache__" in rel.split(os.sep)
        for f in files:
            s, d = os.path.join(root, f), os.path.join(od, f)
            if pyc:
                shutil.copy2(s, d)
                c += 1
            else:
                os.link(s, d)
                n += 1
for rep in sys.argv[2:]:
    rel, src = rep.split("=", 1)
    d = os.path.join(dst, rel)
    os.remove(d)
    shutil.copy2(src, d)
    print("replaced", rel, hashlib.md5(open(d, "rb").read()).hexdigest())
cfg = dst + "-cfg"
os.makedirs(cfg, exist_ok=True)
for f in ("user.cfg", "system.cfg"):
    shutil.copyfile(os.path.join(W, "userdata", f), os.path.join(cfg, f))
print("links", n, "copies", c, "cfg", cfg)
