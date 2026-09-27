# gen.py: synthetic variants of the owner's part (plate + upper block, chamfer on the ledge's concave edges, then
# fillet on one vertical block edge + the chamfer miter edge at its foot). Writes out/syn_<name>_chamfer.brep and
# out/syn_<name>.edges (1-based edge indices to fillet, radius). FreeCADCmd; env FC_OUT = log.
import os, math, FreeCAD as App, Part
V=App.Vector
OUT=os.environ["FC_OUT"]; o=open(OUT,"w")
def say(*a): o.write(" ".join(str(x) for x in a)+"\n"); o.flush()
D="C:/dev/occt8-mig/fillet-corner/out/"
def build(name, poly, h_plate, h_block, pad, ch_x, ch_y, r, corner):
    """poly: block footprint (list of V, CCW); plate = footprint offset by pad (box around it).
    ch_x / ch_y: chamfer distance on the ledge edges; ch_y is used for edges whose direction is mostly along x.
    corner: index of the footprint vertex whose vertical edge is filleted."""
    xs=[p.x for p in poly]; ys=[p.y for p in poly]
    plate=Part.makeBox(max(xs)-min(xs)+2*pad, max(ys)-min(ys)+2*pad, h_plate, V(min(xs)-pad, min(ys)-pad, 0))
    w=Part.makePolygon([V(p.x,p.y,h_plate) for p in poly]+[V(poly[0].x,poly[0].y,h_plate)])
    block=Part.Face(w).extrude(V(0,0,h_block))
    s=plate.fuse(block).removeSplitter()
    s=Part.Solid(s.Shells[0]) if s.ShapeType!="Solid" else s
    # concave ledge edges: edges at z=h_plate lying on the block footprint
    ch_edges=[]
    for i,e in enumerate(s.Edges):
        if abs(e.BoundBox.ZMin-h_plate)<1e-7 and abs(e.BoundBox.ZMax-h_plate)<1e-7:
            m=e.CenterOfMass
            onblock=any(abs((m-V(a.x,a.y,h_plate)).cross(V(b.x,b.y,h_plate)-V(a.x,a.y,h_plate)).Length)<1e-6 for a,b in zip(poly,poly[1:]+poly[:1]))
            if onblock: ch_edges.append(e)
    c=s.makeChamfer(ch_x, ch_edges) if ch_x==ch_y else None
    if c is None:
        # per-edge distances: y-size for edges mostly along x
        import Part as P
        c=s
        # FreeCAD makeChamfer takes one list; build with two different distances via two lists is not possible in
        # one call from Python -> use the (edge, d1, d2) form
        c=s.makeChamfer([ (e, (ch_y if abs(e.tangentAt(e.FirstParameter).x)>0.7 else ch_x), (ch_y if abs(e.tangentAt(e.FirstParameter).x)>0.7 else ch_x)) for e in ch_edges]) if False else s.makeChamfer(ch_x, ch_edges)
    cp=V(poly[corner].x, poly[corner].y, 0)
    ids=[]
    for i,e in enumerate(c.Edges):
        bb=e.BoundBox
        if type(e.Curve).__name__!="Line": continue
        a,b=e.Vertexes[0].Point,e.Vertexes[-1].Point
        # vertical block edge at the corner
        if abs(a.x-cp.x)<1e-6 and abs(a.y-cp.y)<1e-6 and abs(b.x-cp.x)<1e-6 and abs(b.y-cp.y)<1e-6 and bb.ZLength>1: ids.append(i+1)
    # miter edge: shares the vertex at the foot of the vertical edge, not horizontal, not vertical
    ve=c.Edges[ids[0]-1]; foot=min(ve.Vertexes,key=lambda v:v.Point.z)
    for i,e in enumerate(c.Edges):
        if type(e.Curve).__name__!="Line" or i+1 in ids: continue
        if any(v.isSame(foot) for v in e.Vertexes):
            d=(e.Vertexes[-1].Point-e.Vertexes[0].Point); d.normalize()
            if abs(d.z)>0.1 and abs(d.z)<0.99: ids.append(i+1)
    c.exportBrep(D+"syn_%s_chamfer.brep"%name)
    open(D+"syn_%s.edges"%name,"w").write("%g %s\n"%(r," ".join(map(str,ids))))
    say("CASE",name,"faces",len(c.Faces),"valid",c.isValid(),"edges",ids,"r",r,"foot",foot.Point)
sq=[V(-29.5239,-29.7568,0),V(29.5239,-29.7568,0),V(29.5239,29.7568,0),V(-29.5239,29.7568,0)]
build("sq_c15_r1", sq, 3, 18, 2, 1.5, 1.5, 1.0, 2)
build("sq_c08_r15", sq, 3, 18, 2, 0.8, 0.8, 1.5, 2)
hexa=[V(20*math.cos(math.radians(60*k)),20*math.sin(math.radians(60*k)),0) for k in range(6)]
build("hex_c1_r1", hexa, 3, 18, 3, 1.0, 1.0, 1.0, 1)
obl=[V(-20,-20,0),V(20,-20,0),V(12,20,0),V(-20,20,0)]   # oblique corner (vertex 2: 101.3 deg interior)
build("obl_c1_r1", obl, 3, 18, 3, 1.0, 1.0, 1.0, 2)
o.close()
