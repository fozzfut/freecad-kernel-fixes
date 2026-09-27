"""r2: make one3.bat compiling CommandBody.cpp, Utils.cpp, ViewProviderBody.cpp (lines from the chamfer
lane's g263 build.bat = delivered PartDesignGui c3964619 pipeline) into vr6body/g263/mod."""
import sys
BS = chr(92)
S = "C:/dev/occt8-mig/chamfer/g263/"
D = "C:/dev/occt8-mig/vr6body/g263/"
src = sys.argv[1] if len(sys.argv) > 1 else "C:/dev/fc-vr6body"
srcname = src.rstrip("/").split("/")[-1]
FILES = ["CommandBody.cpp", "Utils.cpp", "ViewProviderBody.cpp"]


def sub(t):
    for a, b in [(BS + "dev" + BS + "fc-chamfer" + BS, BS + "dev" + BS + srcname + BS),
                 ("C:/dev/fc-chamfer/", "C:/dev/" + srcname + "/"),
                 ("occt8-mig" + BS + "chamfer" + BS + "g263", "occt8-mig" + BS + "vr6body" + BS + "g263"),
                 ("occt8-mig/chamfer/g263", "occt8-mig/vr6body/g263")]:
        t = t.replace(a, b)
    return t


one = open(S + "one.bat").read().splitlines()[:4]
bl = open(S + "build.bat").read().splitlines()
out = list(one)
for f in FILES:
    line = [l for l in bl if ("PartDesign" + BS + "Gui" + BS + f) in l or ("PartDesign/Gui/" + f) in l]
    assert len(line) == 1, (f, len(line))
    out += [sub(line[0]) + " || exit /b 5", "echo CC-OK " + f]
open(D + "one3.bat", "w", newline="\r\n").write("\n".join(out + [""]))
open(D + "one3.sh", "w", newline="\n").write(
    '#!/bin/bash\nexport MSYS2_ARG_CONV_EXCL="*"\ncmd.exe /c "' + D.replace("/", BS) + 'one3.bat"\n')
t = open(D + "one3.bat").read()
print("chamfer refs:", t.count("chamfer"), "src refs:", t.count(srcname))
