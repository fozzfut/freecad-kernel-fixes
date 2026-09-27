import os,sys; sys.path.insert(0,"C:/dev/occt8-mig/fillet-corner/probe")
import FreeCAD as App, Part, geo
OUT=os.environ["FC_OUT"]; ST=os.environ.get("FC_STACK","x"); o=open(OUT,"w")
def say(*a): o.write(" ".join(str(x) for x in a)+"\n"); o.flush()
say("VERSION", App.Version()[:4], "OCC", Part.OCC_VERSION)
ch=Part.Shape(); ch.read("C:/dev/occt8-mig/fillet-corner/out/saved_Chamfer.brep")
names=['Edge27','Edge10','Edge25','Edge8','Edge28','Edge18','Edge31','Edge17','Edge39']
edges=[ch.getElement(n) for n in names]
FB=App.BoundBox(27.5,27.7,1.5,32,32.3,5.5)
def run(tag, base, eds):
    try:
        r=base.makeFillet(1.0, eds)
    except Exception as ex:
        say("==",tag,"FAIL",ex); return None
    geo.report(r,say,tag,focus_box=FB)
    return r
r=run("all9", ch, edges)
if r: r.exportBrep("C:/dev/occt8-mig/fillet-corner/out/raw_all9_%s.brep"%ST)
run("vert_only", ch, [edges[-1]])
run("miter_only", ch, edges[:-1])
run("vert+cornermiter", ch, [edges[-1], edges[6]])
m=ch.makeFillet(1.0, edges[:-1])
# second op: vertical edge on the miter-filleted result (find by geometry)
ve=[e for e in m.Edges if abs(e.BoundBox.XMin-29.524)<2e-3 and abs(e.BoundBox.YMin-29.757)<2e-3 and e.BoundBox.ZLength>10]
say("seq vert edge found",len(ve))
r2=run("seq_miter_then_vert", m, ve)
v=ch.makeFillet(1.0,[edges[-1]])
me=[]
for e0 in edges[:-1]:
    for e in v.Edges:
        if e.Curve.__class__.__name__=="Line" and (e.CenterOfMass-e0.CenterOfMass).Length<1e-6: me.append(e)
say("seq miter found",len(me))
run("seq_vert_then_miter", v, me)
o.close()
