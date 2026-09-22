"""Plain Python (no FreeCAD): copy a headless-made .FCStd and add a minimal GuiDocument.xml in which every object's
view provider has Visibility = true. All other view-provider properties are left out, so FreeCAD gives them the
defaults of the cfg it runs with (the owner's copy in a bench run: AngularDeflection 6.4 deg, Deviation 0.5 %, as in
runs/make-visible-synthetic_1000_copies_vis/make_visible.json).

Why not tools/make_visible.sh: showing the 5000 parts of synthetic_5000_copies.FCStd one by one in the GUI did not
finish in 580 s (runs/make-visible-synthetic_5000_copies_vis/progress.log: the "show" step never ended, twice),
while the 1000-part file took seconds. With this file the parts are shown at restore, as in a GUI-saved file.

    python add_gui_visibility.py <src.FCStd> <dst.FCStd>
"""
import os
import re
import sys
import zipfile


def main(src, dst):
    zin = zipfile.ZipFile(src)
    if "GuiDocument.xml" in zin.namelist():
        sys.exit("%s already has a GuiDocument.xml" % src)
    doc = zin.read("Document.xml").decode("utf-8")
    names = re.findall(r'<Object type="[^"]+" name="([^"]+)"', doc)
    vps = "".join(
        '        <ViewProvider name="%s" expanded="0">\n'
        '            <Properties Count="1" TransientCount="0">\n'
        '                <Property name="Visibility" type="App::PropertyBool" status="1">\n'
        '                    <Bool value="true"/>\n'
        '                </Property>\n'
        '            </Properties>\n'
        '        </ViewProvider>\n' % n for n in names)
    # header as FreeCAD 1.1.1 writes it (files/synthetic_1000_copies_vis.FCStd): with the HasExpansion attribute the
    # reader expects an <Expand/> element first; HasExpansion="0" without it gave "Reading failed from embedded file:
    # GuiDocument.xml" and every part stayed hidden (runs/t4-s5000vis-open, first try)
    gui = ("<?xml version='1.0' encoding='utf-8'?>\n<Document SchemaVersion=\"1\" HasExpansion=\"1\">\n"
           "    <Expand />\n    <ViewProviderData Count=\"%d\">\n%s    </ViewProviderData>\n"
           "    <Camera settings=\"\"/>\n</Document>\n" % (len(names), vps))
    tmp = dst + ".writing"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zout.writestr(info, zin.read(info.filename))
        zout.writestr("GuiDocument.xml", gui)
    os.replace(tmp, dst)
    print("%s: %d view providers visible" % (dst, len(names)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
