# render.py: Coin offscreen images of the corner (lane fillet-corner). FreeCADCmd (no GUI): the shape is
# tessellated, put into a Coin scene (planes grey, analytic blends blue, the corner patch = BSpline faces orange,
# edges black), rendered with SoOffscreenRenderer, written as PNG by hand (the build has no simage).
# env FC_RENDER = lines "<png> <brep> <view>", FC_OUT = log.
import os, zlib, struct
import FreeCAD as App, Part
from pivy import coin
o = open(os.environ["FC_OUT"], "w")
def say(*a): o.write(" ".join(str(x) for x in a) + "\n"); o.flush()
V = App.Vector
CEN = V(29.2, 29.4, 4.0)
W = H = 900
FLIP = os.environ.get('FC_FLIP', '0') == '1'


def face_node(f):
    t = type(f.Surface).__name__
    pts, tris = f.tessellate(0.002 if t != "Plane" else 0.05)
    if not tris:
        return None
    sep = coin.SoSeparator()
    mat = coin.SoMaterial()
    mat.diffuseColor = {"BSplineSurface": (0.95, 0.35, 0.15), "Plane": (0.62, 0.66, 0.72)}.get(t, (0.35, 0.60, 0.90))
    mat.specularColor = (0.3, 0.3, 0.3)
    mat.shininess = 0.4
    sep.addChild(mat)
    sh = coin.SoShapeHints()
    sh.vertexOrdering = coin.SoShapeHints.UNKNOWN_ORDERING
    sep.addChild(sh)
    if t == "Plane":
        u0, u1, v0, v1 = f.ParameterRange
        n0 = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        nrm = [(n0.x, n0.y, n0.z)] * len(pts)
    else:
        nrm = []
        for p in pts:
            try:
                u, v = f.Surface.parameter(p)
                n = f.normalAt(u, v)
            except Exception:
                n = V(0, 0, 1)
            nrm.append((n.x, n.y, n.z))
    nb = coin.SoNormal()
    nb.vector.setValues(0, len(nrm), nrm)
    sep.addChild(nb)
    nbind = coin.SoNormalBinding()
    nbind.value = coin.SoNormalBinding.PER_VERTEX_INDEXED
    sep.addChild(nbind)
    c = coin.SoCoordinate3()
    c.point.setValues(0, len(pts), [(p.x, p.y, p.z) for p in pts])
    sep.addChild(c)
    fs = coin.SoIndexedFaceSet()
    idx = []
    for a, b, d in tris:
        idx += [a, b, d, -1]
    fs.coordIndex.setValues(0, len(idx), idx)
    fs.normalIndex.setValues(0, len(idx), idx)
    sep.addChild(fs)
    return sep


def scene(shape, view):
    root = coin.SoSeparator()
    cam = coin.SoOrthographicCamera()
    root.addChild(cam)
    d = {"iso": V(1, 1, 0.8), "low": V(1, 1, -0.15), "side": V(1, 0.25, 0.35)}[view]
    d.normalize()
    li = coin.SoDirectionalLight(); li.direction = (-d.x, -d.y, -d.z); root.addChild(li)
    li2 = coin.SoDirectionalLight(); li2.direction = (-0.3, 0.2, -1.0); li2.intensity = 0.4; root.addChild(li2)
    box = App.BoundBox(CEN.x - 3, CEN.y - 3, CEN.z - 3, CEN.x + 3, CEN.y + 3, CEN.z + 3)
    for f in shape.Faces:
        if box.intersect(f.BoundBox):
            n = face_node(f)
            if n is not None:
                root.addChild(n)
    es = coin.SoSeparator()
    lmb = coin.SoLightModel()
    lmb.model = coin.SoLightModel.BASE_COLOR
    es.addChild(lmb)
    em = coin.SoBaseColor()
    em.rgb = (0, 0, 0)
    es.addChild(em)
    ds = coin.SoDrawStyle()
    ds.lineWidth = 2
    es.addChild(ds)
    for e in shape.Edges:
        if not box.intersect(e.BoundBox):
            continue
        pl = e.discretize(Deflection=0.001)
        c = coin.SoCoordinate3()
        c.point.setValues(0, len(pl), [(p.x, p.y, p.z) for p in pl])
        es.addChild(c)
        ls = coin.SoLineSet()
        ls.numVertices.setValue(len(pl))
        es.addChild(ls)
    root.addChild(es)
    pos = CEN + d * 20
    cam.position.setValue(pos.x, pos.y, pos.z)
    cam.pointAt(coin.SbVec3f(CEN.x, CEN.y, CEN.z), coin.SbVec3f(0, 0, 1))
    cam.height = 3.2
    cam.nearDistance = 1
    cam.farDistance = 60
    return root


def write_png(path, buf):
    rows = []
    for y in range(H):
        rows.append(bytes([0]) + bytes(buf[(H - 1 - y) * W * 3:(H - y) * W * 3]) if FLIP else bytes([0]) + bytes(buf[y * W * 3:(y + 1) * W * 3]))
    raw = b"".join(rows)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    sig = bytes([137, 80, 78, 71, 13, 10, 26, 10])
    with open(path, "wb") as fh:
        fh.write(sig + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


for line in open(os.environ["FC_RENDER"]):
    if not line.strip():
        continue
    png, brep, view = line.split()
    s = Part.Shape()
    s.read(brep)
    root = scene(s, view)
    r = coin.SoOffscreenRenderer(coin.SbViewportRegion(W, H))
    r.setBackgroundColor(coin.SbColor(1, 1, 1))
    ok = r.render(root)
    if ok:
        write_png(png, r.getBuffer())
    say("RENDER", png, "ok", ok, os.path.exists(png) and os.path.getsize(png))
o.close()
