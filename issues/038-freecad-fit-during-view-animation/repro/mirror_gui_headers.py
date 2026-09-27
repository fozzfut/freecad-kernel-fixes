"""mirror_gui_headers.py <commit> <overlay root> -- round 3: an overlay that changes a header included RELATIVELY by other
Gui headers (View3DInventorViewer.h via Selection/SoFCUnifiedSelection.h, Quarter/SoQTQuarterAdaptor.h) must carry the
whole src/Gui header tree, or MSVC resolves a relative include to fcD/src's copy of the same header (pragma once is per
path -> class redefinition). Writes every src/Gui header of <commit> into <ovl>/Gui (git blob bytes) and, for every
overlay .cpp that includes its own moc_X.cpp, a copy of bld144's moc_X.cpp whose single header include points at the
overlay header (moc output does not depend on the header path; the Q_OBJECT content of X.h is unchanged)."""
import os, re, subprocess, sys
commit, ovl = sys.argv[1], sys.argv[2]
SRC = "C:/dev/occt8-mig/fcD/src"
AUTO = "C:/dev/occt8-mig/fcD/bld144/src/Gui/FreeCADGui_autogen/include"
names = subprocess.check_output(["git", "-C", SRC, "ls-tree", "-r", "--name-only", commit, "src/Gui"], text=True).split()
n = 0
for p in names:
    if not re.search(r"\.(h|hpp|hxx|inl|ipp)$", p):
        continue
    dst = os.path.join(ovl, p[len("src/"):])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    data = subprocess.check_output(["git", "-C", SRC, "show", commit + ":" + p])
    if os.path.exists(dst) and open(dst, "rb").read() != data:
        sys.exit("overlay header differs from the commit: " + dst)
    open(dst, "wb").write(data); n += 1
m = 0
for root, _, files in os.walk(os.path.join(ovl, "Gui")):
    for f in files:
        if not f.endswith(".cpp") or f.startswith("moc_"):
            continue
        for inc in re.findall(rb'#include "(moc_[^"]+\.cpp)"', open(os.path.join(root, f), "rb").read()):
            moc = open(os.path.join(AUTO, inc.decode()), "rb").read()
            hs = re.findall(rb'#include "(\.\./[^"]*/src/src/Gui/([^"]+))"', moc)
            if len(hs) != 1:
                sys.exit("moc header includes %r in %s" % (hs, inc))
            full, rel = hs[0]
            target = os.path.relpath(os.path.join(ovl, "Gui", rel.decode()), root).replace(os.sep, "/")
            moc = moc.replace(b'#include "' + full + b'"', b'#include "' + target.encode() + b'"')
            open(os.path.join(root, inc.decode()), "wb").write(moc); m += 1
            print("moc", os.path.join(root, inc.decode()), "->", target)
print("headers", n, "mocs", m)
