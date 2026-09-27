"""mkrc034.py <name> [TKOffset.dll] -- hard-link run copy of the DELIVERY C:/dev/FreeCAD-occt8-perf into
C:/dev/occt8-mig/fcD/rc/<name> (fcD/tools/fcrun.sh runs only from there). Every file is a hard link except
__pycache__ contents and the user-writable userdata tree (real copies), and bin/TKOffset.dll when given
(delete-then-copy, so the delivery file is never written). Prints the md5 of bin/TKOffset.dll in the copy."""
import hashlib
import os
import shutil
import sys

SRC = r"C:/dev/FreeCAD-occt8-perf"
name = sys.argv[1]
dst = os.path.join(r"C:/dev/occt8-mig/fcD/rc", name)
if os.path.exists(dst):
    sys.exit("exists: " + dst)
n = c = 0
for root, dirs, files in os.walk(SRC):
    rel = os.path.relpath(root, SRC)
    od = os.path.join(dst, rel)
    os.makedirs(od, exist_ok=True)
    parts = rel.replace("\\", "/").split("/")
    real = "__pycache__" in parts or parts[0] in ("userdata", "_replaced")
    for f in files:
        s, d = os.path.join(root, f), os.path.join(od, f)
        if real:
            shutil.copy2(s, d)
            c += 1
        else:
            os.link(s, d)
            n += 1
print("links", n, "copies", c)
if len(sys.argv) == 3:
    d = os.path.join(dst, "bin", "TKOffset.dll")
    os.remove(d)
    shutil.copy2(sys.argv[2], d)
print("TKOffset.dll", hashlib.md5(open(os.path.join(dst, "bin", "TKOffset.dll"), "rb").read()).hexdigest())
