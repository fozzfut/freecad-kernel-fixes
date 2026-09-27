"""Lane undo-visibility: FreeCADGui.dll of fcD/bld144 with View3DPy/View3DViewerPy (033) + CommandView/Tree taken from a folder (copy of sechang/fc/mkgui.py).

    python mkgui.py <variant: ctl|fix> <source dir holding View3DPy.cpp and View3DViewerPy.cpp>

Compile lines = bld144/compile_commands.json verbatim except the source path, /Fo and /Fd; the link
= bld144/build.ninja's FreeCADGui.dll block (same objects in the same order, the two replaced; same
LINK_PATH, LINK_LIBRARIES, flags) through cmake -E vs_link_dll like ninja does. Nothing in bld144
or fcD/src is written: objects, rsp, dll, lib, pdb go to sechang/fc/{obj,out}-<variant>.
Run inside the MSVC 14.44 environment (build.bat).
"""
import json
import os
import shlex
import subprocess
import sys

BLD = "C:/dev/occt8-mig/fcD/bld144"
HERE = "C:/dev/occt8-mig/undovis/build"
FILES = ("View3DPy.cpp", "View3DViewerPy.cpp", "CommandView.cpp", "Tree.cpp")

variant, srcdir = sys.argv[1], sys.argv[2]
obj = os.path.join(HERE, "obj-" + variant)
out = os.path.join(HERE, "out-" + variant)
os.makedirs(obj, exist_ok=True)
os.makedirs(out, exist_ok=True)
log = open(os.path.join(out, "build.log"), "w")

cc = json.load(open(BLD + "/compile_commands.json"))
replaced = {}
for entry in cc:
    path = entry["file"].replace("\\", "/")
    for name in FILES:
        if path.endswith("src/Gui/" + name):
            args = entry["command"].split(" ")
            new = []
            for a in args:
                if a.startswith("/Fo"):
                    new.append("/Fo" + os.path.join(obj, name + ".obj").replace("/", "\\"))
                    replaced[a[3:]] = os.path.join(obj, name + ".obj").replace("/", "\\")
                elif a.startswith("/Fd"):
                    new.append("/Fd" + obj.replace("/", "\\") + "\\")
                elif a.replace("\\", "/").endswith("src/Gui/" + name):
                    new.append(os.path.join(srcdir, name).replace("/", "\\"))
                else:
                    new.append(a)
            line = " ".join(new)
            log.write("COMPILE " + line + "\n")
            log.flush()
            rc = subprocess.call(line, cwd=BLD, stdout=log, stderr=subprocess.STDOUT, shell=True)
            print("compile", name, "rc", rc)
            if rc:
                sys.exit(rc)
if len(replaced) != len(FILES):
    sys.exit("compile lines found: %d" % len(replaced))

# the link block
text = open(BLD + "/build.ninja", encoding="utf-8").read().split("\n")
start = next(i for i, l in enumerate(text) if l.startswith("build bin\\FreeCADGui.dll "))
head = text[start]
inputs = head.split(": CXX_SHARED_LIBRARY_LINKER__FreeCADGui_Release ", 1)[1]
inputs = inputs.split(" | ")[0].split(" || ")[0].split()
vars_ = {}
for l in text[start + 1:]:
    if not l.startswith("  "):
        break
    k, _, v = l.strip().partition(" = ")
    vars_[k] = v
objs = []
swapped = 0
for i in inputs:
    if i in replaced:
        objs.append(replaced[i])
        swapped += 1
    else:
        objs.append(i)
if swapped != len(FILES):
    sys.exit("objects swapped: %d" % swapped)
rsp = os.path.join(obj, "FreeCADGui.rsp")
with open(rsp, "w") as h:
    h.write("\n".join(objs) + " " + vars_.get("LINK_PATH", "") + " " + vars_.get("LINK_LIBRARIES", ""))
rule = [l for l in open(BLD + "/CMakeFiles/rules.ninja", encoding="utf-8").read().split("\n")]
ri = rule.index("rule CXX_SHARED_LIBRARY_LINKER__FreeCADGui_Release")
command = rule[ri + 1].strip()[len("command = "):]
dll = os.path.join(out, "FreeCADGui.dll").replace("/", "\\")
subst = {"$PRE_LINK": vars_.get("PRE_LINK", "cd ."), "$POST_BUILD": vars_.get("POST_BUILD", "cd ."),
         "$OBJECT_DIR": obj.replace("/", "\\"), "$MANIFESTS": vars_.get("MANIFESTS", ""),
         "$RSP_FILE": rsp.replace("/", "\\"), "$TARGET_FILE": dll,
         "$TARGET_IMPLIB": os.path.join(out, "FreeCADGui.lib").replace("/", "\\"),
         "$TARGET_PDB": os.path.join(out, "FreeCADGui.pdb").replace("/", "\\"),
         "$LINK_FLAGS": vars_.get("LINK_FLAGS", "")}
for k in sorted(subst, key=len, reverse=True):
    command = command.replace(k, subst[k])
log.write("LINK " + command + "\n")
log.flush()
rc = subprocess.call(command, cwd=BLD, stdout=log, stderr=subprocess.STDOUT, shell=True)
print("link rc", rc, dll)
sys.exit(rc)
