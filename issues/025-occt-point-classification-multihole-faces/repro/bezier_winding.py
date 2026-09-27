"""Research spike: oriented rational-Bezier winding, no ray/curve intersections.
Positive weights + convex hull give a homotopy-preserving chord substitution.
Not a production classifier: floating-point bounds and OCCT tolerance equivalence
are NOT certified. Only planar, nearly closed, supported pcurves are attempted.
"""
import probe_runtime  # 1 GiB Job Object, RAM/commit gate before OCCT imports
import json, math, random, time
from collections import Counter
from pathlib import Path
from OCC.Core.BRep import BRep_Builder, BRep_Tool
from OCC.Core.BRepTools import breptools, BRepTools_WireExplorer
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepTopAdaptor import BRepTopAdaptor_FClass2d
from OCC.Core.TopoDS import TopoDS_Shape, topods
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE, TopAbs_FORWARD, TopAbs_REVERSED
from OCC.Core.GeomAbs import GeomAbs_Plane
from OCC.Core.Geom2d import Geom2d_TrimmedCurve
from OCC.Core.Geom2dConvert import geom2dconvert, Geom2dConvert_BSplineCurveToBezierCurve
from OCC.Core.gp import gp_Pnt2d
ROOT=Path('C:/dev/freecad-kernel-fixes')
ISSUE=ROOT/'issues/025-occt-point-classification-multihole-faces'
TOL=1e-7
class Uncertain(Exception): pass

def bbox(points):
    return (min(p[0] for p in points),max(p[0] for p in points),min(p[1] for p in points),max(p[1] for p in points))
def merge(boxes):
    return (min(b[0] for b in boxes),max(b[1] for b in boxes),min(b[2] for b in boxes),max(b[3] for b in boxes))
def contains(b,p,pad):
    return b[0]-pad<=p[0]<=b[1]+pad and b[2]-pad<=p[1]<=b[3]+pad
class Arc:
    def __init__(self,h):
        self.h=h
        self.p=[(x/w,y/w) for x,y,w in h]
        self.box=bbox(self.p)
        self.children=None
    def split(self):
        if self.children is None:
            row=self.h;left=[row[0]];right=[row[-1]]
            while len(row)>1:
                row=[tuple((a+b)*.5 for a,b in zip(u,v)) for u,v in zip(row,row[1:])]
                left.append(row[0]);right.append(row[-1])
            self.children=(Arc(left),Arc(right[::-1]))
        return self.children
    def angle(self,q,pad,stats,depth=0):
        stats['arc_nodes']+=1
        if contains(self.box,q,pad):
            if len(self.h)==2:
                a,b=self.p;dx=b[0]-a[0];dy=b[1]-a[1]
                den=dx*dx+dy*dy
                t=max(0.,min(1.,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/den)) if den else 0.
                if math.hypot(q[0]-a[0]-t*dx,q[1]-a[1]-t*dy)<=pad:raise Uncertain('boundary')
            else:
                if depth>=32 or max(self.box[1]-self.box[0],self.box[3]-self.box[2])<=2*pad:
                    raise Uncertain('boundary_or_depth')
                a,b=self.split()
                return a.angle(q,pad,stats,depth+1)+b.angle(q,pad,stats,depth+1)
        a,b=self.p[0],self.p[-1]
        ax=a[0]-q[0];ay=a[1]-q[1];bx=b[0]-q[0];by=b[1]-q[1]
        stats['angles']+=1
        return math.atan2(ax*by-ay*bx,ax*bx+ay*by)
class Wire:
    def __init__(self,arcs):
        self.arcs=arcs;self.box=merge([a.box for a in arcs])
class Index:
    def __init__(self,wires):
        self.box=merge([w.box for w in wires]);self.items=None;self.children=None
        if len(wires)<=2:self.items=wires
        else:
            axis=0 if self.box[1]-self.box[0]>self.box[3]-self.box[2] else 2
            wires=sorted(wires,key=lambda w:w.box[axis]+w.box[axis+1]);m=len(wires)//2
            self.children=(Index(wires[:m]),Index(wires[m:]))
    def candidates(self,q,pad,stats):
        stats['index_nodes']+=1
        if not contains(self.box,q,pad):return
        if self.items:
            for wire in self.items:
                if contains(wire.box,q,pad):yield wire
        else:
            for child in self.children:yield from child.candidates(q,pad,stats)

def extract(face):
    if BRepAdaptor_Surface(face).GetType()!=GeomAbs_Plane:raise Uncertain('nonplanar')
    wires=[];types=Counter();maxgap=0.;boundary=[]
    wi=TopExp_Explorer(face,TopAbs_WIRE)
    while wi.More():
        wire=topods.Wire(wi.Current());ex=BRepTools_WireExplorer(wire,face);arcs=[];visited=0
        while ex.More():
            edge=ex.Current();visited+=1
            curve,first,last=BRep_Tool.CurveOnSurface(edge,face)
            types[curve.DynamicType().Name()]+=1
            if 'Offset' in curve.DynamicType().Name():raise Uncertain('offset_conversion')
            spline=geom2dconvert.CurveToBSplineCurve(Geom2d_TrimmedCurve(curve,first,last))
            conv=Geom2dConvert_BSplineCurveToBezierCurve(spline)
            edgearcs=[]
            for i in range(1,conv.NbArcs()+1):
                b=conv.Arc(i);h=[]
                for j in range(1,b.NbPoles()+1):
                    p=b.Pole(j);w=b.Weight(j)
                    if w<=0:raise Uncertain('nonpositive_weight')
                    h.append((p.X()*w,p.Y()*w,w))
                edgearcs.append(Arc(h))
            if edge.Orientation()==TopAbs_REVERSED:
                edgearcs=[Arc(a.h[::-1]) for a in edgearcs[::-1]]
            elif edge.Orientation()!=TopAbs_FORWARD:raise Uncertain('edge_orientation')
            arcs.extend(edgearcs)
            for fraction in (.0,.43213918):
                t=first+(last-first)*fraction;p=curve.Value(t)
                boundary.append((p.X(),p.Y()))
            ex.Next()
        count=0;all_edges=TopExp_Explorer(wire,TopAbs_EDGE)
        while all_edges.More():count+=1;all_edges.Next()
        if count!=visited or not arcs:raise Uncertain('wire_traversal')
        for a,b in zip(arcs,arcs[1:]+arcs[:1]):
            maxgap=max(maxgap,math.dist(a.p[-1],b.p[0]))
        wires.append(Wire(arcs));wi.Next()
    scale=max(1.,*(abs(v) for w in wires for v in w.box))
    if maxgap>scale*1e-12:raise Uncertain('open_wire')
    return wires,types,maxgap,boundary,max(4*TOL,scale*1e-13)

def run():
    rows=[];failures=0
    for path in (ROOT/'build/025/probe/list.txt').read_text().splitlines():
        shape=TopoDS_Shape();assert breptools.Read(shape,path,BRep_Builder())
        faces=[];it=TopExp_Explorer(shape,TopAbs_FACE);idx=0
        while it.More():
            idx+=1;face=topods.Face(it.Current());w=TopExp_Explorer(face,TopAbs_WIRE);n=0
            while w.More():n+=1;w.Next()
            if n>1:faces.append((idx,n,face))
            it.Next()
        # One worst face per input, to keep this a bounded feasibility probe.
        idx,n,face=max(faces,key=lambda x:x[1]);face.Orientation(TopAbs_FORWARD)
        start=time.perf_counter()
        try:wires,types,gap,boundary,pad=extract(face)
        except Exception as e:
            failures+=1;print('EXTRACT_FAILED',path,type(e).__name__,str(e),flush=True);continue
        index=Index(wires);setup=time.perf_counter()-start
        u0,u1,v0,v1=breptools.UVBounds(face);rng=random.Random(252025)
        points=[(u0+(u1-u0)*rng.uniform(-.05,1.05),v0+(v1-v0)*rng.uniform(-.05,1.05)) for _ in range(256)]
        near=[]
        for p in boundary[::max(1,len(boundary)//128)]:
            near.extend((p,(p[0]+1e-6,p[1]-1e-6),(p[0]-1e-6,p[1]+1e-6)))
        stock=BRepTopAdaptor_FClass2d(face,TOL)
        def old(p):return int(stock.Perform(gp_Pnt2d(*p)))
        for label,queries in [('random',points),('boundary',near)]:
            start=time.perf_counter();ref=[old(q) for q in queries];stock_s=time.perf_counter()-start
            for mode in ('winding_all','winding_index'):
                stats=Counter();mismatches=[];start=time.perf_counter()
                for i,q in enumerate(queries):
                    candidates=wires if mode=='winding_all' else index.candidates(q,pad,stats)
                    try:
                        angles=[]
                        for wire in candidates:
                            stats['wire_visits']+=1
                            angles.extend(a.angle(q,pad,stats) for a in wire.arcs)
                        wn=math.fsum(angles)/(2*math.pi)
                        if abs(wn-round(wn))>1e-7:raise Uncertain('noninteger')
                        answer=0 if round(wn)!=0 else 1
                        stats['new_answers']+=1
                    except Uncertain as e:
                        stats['fallback']+=1;stats[str(e)]+=1;answer=old(q)
                    if answer!=ref[i]:mismatches.append(dict(i=i,p=q,stock=ref[i],new=answer))
                row=dict(file=path,face=idx,wires=n,mode=mode,queries=label,points=len(queries),setup_s=setup,stock_s=stock_s,new_s=time.perf_counter()-start,stats=dict(stats),mismatches=mismatches[:12],mismatch_count=len(mismatches),pcurve_types=dict(types),max_closure_gap=gap,pad=pad)
                rows.append(row);print(json.dumps(row),flush=True)
                (ISSUE/'measurements/bezier-winding.json').write_text(json.dumps(rows,indent=2))
    print('VERDICT rows='+str(len(rows))+' mismatches='+str(sum(r['mismatch_count'] for r in rows))+' extraction_failures='+str(failures),flush=True)
    return bool(failures or any(r['mismatch_count'] for r in rows))
if __name__=='__main__':raise SystemExit(run())