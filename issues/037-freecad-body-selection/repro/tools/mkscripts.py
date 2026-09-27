"""Make one.bat (CommandBody.cpp only) / link.bat / link.rsp for the vr6body PartDesignGui build
from the chamfer lane's g263 scripts (the delivered PartDesignGui c3964619 pipeline).
Usage: mkscripts.py [srcroot]   srcroot default C:/dev/fc-vr6body"""
import sys
BS = chr(92)
S = "C:/dev/occt8-mig/chamfer/g263/"
D = "C:/dev/occt8-mig/vr6body/g263/"
src = sys.argv[1] if len(sys.argv) > 1 else "C:/dev/fc-vr6body"
srcname = src.rstrip("/").split("/")[-1]


def sub(t):
    pairs = [
        (BS + "dev" + BS + "fc-chamfer" + BS, BS + "dev" + BS + srcname + BS),
        ("C:/dev/fc-chamfer/", "C:/dev/" + srcname + "/"),
        ("occt8-mig" + BS + "chamfer" + BS + "g263", "occt8-mig" + BS + "vr6body" + BS + "g263"),
        ("occt8-mig/chamfer/g263", "occt8-mig/vr6body/g263"),
    ]
    for a, b in pairs:
        t = t.replace(a, b)
    return t


one = open(S + "one.bat").read().splitlines()[:4]
line = [l for l in open(S + "build.bat").read().splitlines() if "CommandBody.cpp" in l]
assert len(line) == 1, len(line)
open(D + "one.bat", "w", newline="\r\n").write("\n".join(one + [sub(line[0]) + " || exit /b 5", "echo CC-OK", ""]))
open(D + "link.rsp", "w", newline="\r\n").write(sub(open(S + "link.rsp").read()))
open(D + "link.bat", "w", newline="\r\n").write(sub(open(S + "link.bat").read()))
win = D.replace("/", BS)
for n in ("one", "link"):
    open(D + n + ".sh", "w", newline="\n").write(
        '#!/bin/bash\nexport MSYS2_ARG_CONV_EXCL="*"\ncmd.exe /c "' + win + n + '.bat"\n')
for n in ("one.bat", "link.bat", "link.rsp"):
    t = open(D + n).read()
    print(n, "chamfer refs:", t.count("chamfer"), "src refs:", t.count(srcname))
