# copied from C:/dev/hybriddesign-perf/scripts/cfg_sandbox.py (2026-09-15): marks CAM migration as offered so no modal dialog blocks an offscreen FreeCAD
import sys, shutil, os
import xml.etree.ElementTree as ET
src, dst_dir = sys.argv[1], sys.argv[2]
os.makedirs(dst_dir, exist_ok=True)
tree = ET.parse(src)
root = tree.getroot()
node = root
for name in ["Root", "BaseApp", "Preferences", "Mod", "CAM", "Migration"]:
    child = None
    for c in node.findall("FCParamGroup"):
        if c.get("Name") == name:
            child = c
            break
    if child is None:
        child = ET.SubElement(node, "FCParamGroup", {"Name": name})
        print("created group", name)
    node = child
cur = None
for t in node.findall("FCText"):
    if t.get("Name") == "OfferedToMigrateCAMAssets":
        cur = t
print("existing OfferedToMigrateCAMAssets:", None if cur is None else cur.text)
if cur is None:
    cur = ET.SubElement(node, "FCText", {"Name": "OfferedToMigrateCAMAssets"})
vals = set((cur.text or "").split(",")) - {""}
vals.update({"v1-1", "1-1", "1.1"})
cur.text = ",".join(sorted(vals))
tree.write(os.path.join(dst_dir, "user.cfg"), encoding="UTF-8", xml_declaration=True)
shutil.copy(sys.argv[3], os.path.join(dst_dir, "system.cfg"))
print("written", dst_dir, cur.text)
