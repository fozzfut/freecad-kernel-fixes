"""Small differential and negative controls for the algorithm-replacement spike."""
from bezier_winding_boundary import *
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
from OCC.Core.Geom import Geom_BezierCurve
from OCC.Core.TColgp import TColgp_Array1OfPnt
from OCC.Core.TColStd import TColStd_Array1OfReal
from OCC.Core.gp import gp_Pnt, gp_Vec2d

def classify(wires,index,pad,q,stock,stats):
    try:
        value=math.fsum(a.angle(q,pad,stats) for w in index.candidates(q,pad,stats) for a in w.arcs)/(2*math.pi)
        if abs(value-round(value))>1e-7:raise Uncertain('noninteger')
        stats['new']+=1
        return 0 if round(value)!=0 else 1
    except OnBoundary:stats['new_on']+=1;return 2
    except Uncertain:
        stats['fallback']+=1
        return int(stock.Perform(gp_Pnt2d(*q)))

def fixture(rational):
    p=TColgp_Array1OfPnt(1,4);w=TColStd_Array1OfReal(1,4)
    for i,(x,y,weight) in enumerate(((0,0,1),(0,2,.7),(2,2,1.4),(2,0,1)),1):
        p.SetValue(i,gp_Pnt(x,y,0));w.SetValue(i,weight)
    curve=Geom_BezierCurve(p,w) if rational else Geom_BezierCurve(p)
    a=BRepBuilderAPI_MakeEdge(curve).Edge()
    b=BRepBuilderAPI_MakeEdge(gp_Pnt(2,0,0),gp_Pnt(0,0,0)).Edge()
    wire=BRepBuilderAPI_MakeWire(a,b).Wire();wire.Reverse()
    return BRepBuilderAPI_MakeFace(wire,True).Face()

shape=TopoDS_Shape();assert breptools.Read(shape,str(ROOT/'build/025/probe/Top.brep'),BRep_Builder())
it=TopExp_Explorer(shape,TopAbs_FACE)
for _ in range(4):it.Next()
faces=[('TopFace5',topods.Face(it.Current())),('cubic',fixture(False)),('rational_cubic',fixture(True))]
rows=[]
for name,face in faces:
    face.Orientation(TopAbs_FORWARD)
    wires,types,gap,_,pad=extract(face);index=Index(wires);stock=BRepTopAdaptor_FClass2d(face,TOL)
    points=[];it=TopExp_Explorer(face,TopAbs_EDGE)
    while it.More():
        c,f,l=BRep_Tool.CurveOnSurface(topods.Edge(it.Current()),face)
        p=gp_Pnt2d();d=gp_Vec2d();c.D1(f+(l-f)*.43213918,p,d)
        length=d.Magnitude()
        if length:
            for factor in (-100,-10,-2,-1.01,-1,-.99,-.5,0,.5,.99,1,1.01,2,10,100):
                off=TOL*factor;points.append((p.X()-d.Y()/length*off,p.Y()+d.X()/length*off))
        it.Next()
    u0,u1,v0,v1=breptools.UVBounds(face);rng=random.Random(25)
    points.extend((u0+(u1-u0)*rng.random(),v0+(v1-v0)*rng.random()) for _ in range(128))
    stats=Counter();bad=[];mutant=0
    outer=max(wires,key=lambda w:(w.box[1]-w.box[0])*(w.box[3]-w.box[2]));outer_index=Index([outer])
    for i,q in enumerate(points):
        ref=int(stock.Perform(gp_Pnt2d(*q)));answer=classify(wires,index,pad,q,stock,stats)
        if answer!=ref:bad.append(dict(i=i,p=q,stock=ref,new=answer))
    # Negative control: omission of holes must be detected, away from tolerances.
    for wire in wires:
        if wire is outer:continue
        q=((wire.box[0]+wire.box[1])*.5,(wire.box[2]+wire.box[3])*.5)
        if classify([outer],outer_index,pad,q,stock,Counter())!=int(stock.Perform(gp_Pnt2d(*q))):mutant+=1
    # Negative control: replacing all curved arcs by chords loses the bulge.
    chords=[Wire([Arc([a.h[0],a.h[-1]]) for a in w.arcs]) for w in wires]
    chord_index=Index(chords);chord_bad=0
    for q in points[-128:]:
        if classify(chords,chord_index,pad,q,stock,Counter())!=int(stock.Perform(gp_Pnt2d(*q))):chord_bad+=1
    row=dict(name=name,points=len(points),pcurve_types=dict(types),stats=dict(stats),mismatch_count=len(bad),mismatches=bad[:20],mutant_omit_holes_mismatches=mutant,mutant_chords_mismatches=chord_bad)
    rows.append(row);print(json.dumps(row),flush=True)
(ISSUE/'measurements/winding-regression.json').write_text(json.dumps(rows,indent=2))
passed=sum(r['mismatch_count'] for r in rows)==0 and rows[0]['mutant_omit_holes_mismatches']>0 and all(r['mutant_chords_mismatches']>0 for r in rows[1:])
print('VERDICT differential_mismatches='+str(sum(r['mismatch_count'] for r in rows))+' negative_controls='+str(passed),flush=True)
raise SystemExit(0 if passed else 1)