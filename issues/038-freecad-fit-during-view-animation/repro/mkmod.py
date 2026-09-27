"""Lane vr6-unconf: FreeCADGui.dll or PartGui.pyd of fcD/bld144 with some sources taken from an overlay folder
(generalised copy of undovis/tools/mkgui.py).

    python mkmod.py <gui|part> <variant> <overlay root>

The overlay mirrors src/ (e.g. <ovl>/Gui/Navigation/NavigationStyle.cpp). Compile lines = bld144/compile_commands.json
verbatim except the source path, /Fo, /Fd and two include dirs put FIRST: <ovl> and <ovl>/Gui, so the overlay's headers
(e.g. Navigation/NavigationStyle.h) win over fcD/src's in the compiled units; /showIncludes goes to the build log so the
resolution can be checked. The link = bld144/build.ninja's block for the target (same objects in the same order, the
compiled ones replaced; same LINK_PATH, LINK_LIBRARIES, flags) through the rule's command, as ninja runs it. Nothing in
bld144 or fcD/src is written: objects, rsp and outputs go to vr6unconf/build/{obj,out}-<target>-<variant>.
Run inside the MSVC 14.44 environment (build.bat)."""
import json
import os
import subprocess
import sys

BLD = "C:/dev/occt8-mig/fcD/bld144"
HERE = "C:/dev/occt8-mig/vr6unconf/build"
TARGETS = {
    "gui": ("bin\\FreeCADGui.dll", "FreeCADGui", ["Gui/View3DInventorViewer.cpp", "Gui/Navigation/NavigationStyle.cpp",
            "Gui/Navigation/NavigationAnimator.cpp", "Gui/View3DPy.cpp", "Gui/View3DViewerPy.cpp",
            "Gui/CommandView.cpp", "Gui/Tree.cpp"], "FreeCADGui.dll", "FreeCADGui.lib"),
    # round 2: on mig/undo-vis-pe 3eccec5 (delivered 7af65a21) = the undo-vis sources + propertyeditor/PropertyItem.cpp
    "gui2": ("bin\\FreeCADGui.dll", "FreeCADGui", ["Gui/View3DInventorViewer.cpp", "Gui/Navigation/NavigationStyle.cpp",
             "Gui/Navigation/NavigationAnimator.cpp", "Gui/View3DPy.cpp", "Gui/View3DViewerPy.cpp",
             "Gui/CommandView.cpp", "Gui/Tree.cpp", "Gui/propertyeditor/PropertyItem.cpp"], "FreeCADGui.dll", "FreeCADGui.lib"),
    # round 2 D0: only the five sources the delivered 035-PE build (7af65a21) swapped, from a folder whose path has the
    # length of that build's mirror (C:\dev\occt8-mig\uvp\fix\src = C:\dev\occt8-mig\vr6unconf\d), so __FILE__ strings keep their size
    "gui2d0": ("bin\\FreeCADGui.dll", "FreeCADGui", ["Gui/View3DPy.cpp", "Gui/View3DViewerPy.cpp", "Gui/CommandView.cpp",
               "Gui/Tree.cpp", "Gui/propertyeditor/PropertyItem.cpp"], "FreeCADGui.dll", "FreeCADGui.lib"),
    "part": ("Mod\\Part\\PartGui.pyd", "PartGui", ["Mod/Part/Gui/SoBrepFaceSet.cpp"], "PartGui.pyd", "PartGui.lib"),
}

target, variant, ovl = sys.argv[1], sys.argv[2], os.path.abspath(sys.argv[3])
# MKMOD_FLAT=<dir>: D0 mode - sources taken as <dir>/<basename> (a flat folder as undovis/mkgui.py used), compile line
# exactly as mkgui.py (no overlay include dirs, no /showIncludes), so the delivered DLL can be reproduced byte for byte.
FLAT = os.environ.get("MKMOD_FLAT")
if FLAT:
    TARGETS["gui0"] = ("bin\\FreeCADGui.dll", "FreeCADGui", ["Gui/View3DPy.cpp", "Gui/View3DViewerPy.cpp",
                       "Gui/CommandView.cpp", "Gui/Tree.cpp"], "FreeCADGui.dll", "FreeCADGui.lib")
ninja_out, cmake_name, files, out_name, lib_name = TARGETS[target]
obj = os.path.join(HERE, "obj-%s-%s" % (target, variant))
out = os.path.join(HERE, "out-%s-%s" % (target, variant))
os.makedirs(obj, exist_ok=True)
os.makedirs(out, exist_ok=True)
log = open(os.path.join(out, "build.log"), "w")
inc = ["/I" + ovl.replace("/", "\\"), "/I" + os.path.join(ovl, "Gui").replace("/", "\\")]

cc = json.load(open(BLD + "/compile_commands.json"))
replaced = {}
for entry in cc:
    path = entry["file"].replace("\\", "/")
    for rel in files:
        if not path.endswith("/src/src/" + rel):
            continue
        src = (os.path.join(FLAT, os.path.basename(rel)) if FLAT else os.path.join(ovl, rel)).replace("/", "\\")
        if not os.path.isfile(src):
            sys.exit("missing overlay source " + src)
        oname = rel.replace("/", "_") + ".obj"
        args = entry["command"].split(" ")
        new = []
        for a in args:
            if a.startswith("/Fo"):
                new.append("/Fo" + os.path.join(obj, oname).replace("/", "\\"))
                replaced[a[3:]] = os.path.join(obj, oname).replace("/", "\\")
            elif a.startswith("/Fd"):
                new.append("/Fd" + obj.replace("/", "\\") + "\\")
            elif a.replace("\\", "/").endswith("/src/src/" + rel):
                new.append(src)
            else:
                new.append(a)
            if a == "/TP" and not FLAT:
                new.extend(inc)
        if not FLAT:
            # the unit's own source folder in fcD/src, searched LAST (a unit normally sees it first as its own dir)
            new.append("-I" + os.path.dirname(entry["file"]))
            new.append("/showIncludes")
        line = " ".join(new)
        log.write("COMPILE " + line + "\n")
        log.flush()
        rc = subprocess.call(line, cwd=BLD, stdout=log, stderr=subprocess.STDOUT, shell=True)
        print("compile", rel, "rc", rc)
        if rc:
            sys.exit(rc)
if len(replaced) != len(files):
    sys.exit("compile lines found: %d of %d" % (len(replaced), len(files)))

text = open(BLD + "/build.ninja", encoding="utf-8").read().split("\n")
start = next(i for i, l in enumerate(text) if l.startswith("build " + ninja_out + " "))
rulename = "CXX_SHARED_LIBRARY_LINKER__%s_Release" % cmake_name
inputs = text[start].split(": " + rulename + " ", 1)[1]
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
if swapped != len(files):
    sys.exit("objects swapped: %d of %d" % (swapped, len(files)))
rsp = os.path.join(obj, cmake_name + ".rsp")
with open(rsp, "w") as h:
    h.write("\n".join(objs) + " " + vars_.get("LINK_PATH", "") + " " + vars_.get("LINK_LIBRARIES", ""))
rule = open(BLD + "/CMakeFiles/rules.ninja", encoding="utf-8").read().split("\n")
ri = rule.index("rule " + rulename)
command = rule[ri + 1].strip()[len("command = "):]
dll = os.path.join(out, out_name).replace("/", "\\")
subst = {"$PRE_LINK": vars_.get("PRE_LINK", "cd ."), "$POST_BUILD": vars_.get("POST_BUILD", "cd ."),
         "$OBJECT_DIR": obj.replace("/", "\\"), "$MANIFESTS": vars_.get("MANIFESTS", ""),
         "$RSP_FILE": rsp.replace("/", "\\"), "$TARGET_FILE": dll,
         "$TARGET_IMPLIB": os.path.join(out, lib_name).replace("/", "\\"),
         "$TARGET_PDB": os.path.join(out, cmake_name + ".pdb").replace("/", "\\"),
         "$LINK_FLAGS": vars_.get("LINK_FLAGS", "")}
for k in sorted(subst, key=len, reverse=True):
    command = command.replace(k, subst[k])
log.write("LINK " + command + "\n")
log.flush()
rc = subprocess.call(command, cwd=BLD, stdout=log, stderr=subprocess.STDOUT, shell=True)
print("link rc", rc, dll)
sys.exit(rc)
