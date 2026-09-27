# geo.py: analysis helpers (FreeCAD Part). Import from probes.
import math, FreeCAD as App, Part
V=App.Vector
def fdesc(f):
    s=f.Surface; t=type(s).__name__
    extra=""
    if t=="BSplineSurface": extra=" deg=%d,%d poles=%dx%d"%(s.UDegree,s.VDegree,s.NbUPoles,s.NbVPoles)
    elif t=="Cylinder": extra=" R=%.4f ax=(%.3f,%.3f,%.3f)"%(s.Radius,s.Axis.x,s.Axis.y,s.Axis.z)
    elif t=="Plane": n=s.Axis; extra=" n=(%.4f,%.4f,%.4f)"%(n.x,n.y,n.z)
    elif t in("Toroid","Sphere"): extra=" R=%.4f"%s.Radius + ((" r=%.4f"%s.MinorRadius) if t=="Toroid" else "")
    return t+extra
def bb(s):
    b=s.BoundBox; return "[%.3f,%.3f]x[%.3f,%.3f]x[%.3f,%.3f]"%(b.XMin,b.XMax,b.YMin,b.YMax,b.ZMin,b.ZMax)
def edge_faces(sh):
    m={}
    for i,f in enumerate(sh.Faces):
        for e in f.Edges:
            for j,E in enumerate(sh.Edges):
                if E.isSame(e): m.setdefault(j,[]).append(i); break
    return m
def normal_at_edge(f,e,t):
    p=e.valueAt(t)
    u,v=f.Surface.parameter(p)
    n=f.normalAt(u,v)
    return n,p
def edge_angles(sh,j,fi,n=9):
    e=sh.Edges[j]; f1=sh.Faces[fi[0]]; f2=sh.Faces[fi[1]]
    a,b=e.ParameterRange; out=[]
    for k in range(n):
        t=a+(b-a)*(k+0.5)/n
        n1,p=normal_at_edge(f1,e,t); n2,_=normal_at_edge(f2,e,t)
        c=max(-1,min(1,n1.dot(n2))); out.append(math.degrees(math.acos(c)))
    return out
def check(sh):
    try:
        sh.check(True); return "OK"
    except Exception as ex: return "FAIL "+str(ex).replace("\n"," | ")[:600]
def report(sh,say,tag,focus_box=None,min_area=None):
    say("==",tag,"faces",len(sh.Faces),"edges",len(sh.Edges),"vol %.6f"%sh.Volume,"area %.6f"%sh.Area,"valid",sh.isValid(),"check",check(sh))
    ef=edge_faces(sh)
    for i,f in enumerate(sh.Faces):
        fb=f.BoundBox
        if focus_box and not focus_box.intersect(fb): continue
        say("F%d"%(i+1),fdesc(f),"area %.6f"%f.Area,"bb",bb(f),"nedges",len(f.Edges),"valid",f.isValid(),"orient",f.Orientation)
    for j,e in ef.items():
        E=sh.Edges[j]
        if focus_box and not focus_box.intersect(E.BoundBox): continue
        if len(e)!=2: say("E%d"%(j+1),"faces",e,"NONMANIFOLD"); continue
        try: ang=edge_angles(sh,j,e)
        except Exception as ex: ang=["ERR "+str(ex)]
        c=E.Curve; ct=type(c).__name__
        say("E%d"%(j+1),ct,"len %.6f"%E.Length,"F%d|F%d"%(e[0]+1,e[1]+1),"deg",E.isDegenerated() if hasattr(E,"isDegenerated") else "", "tol %.2e"%E.Tolerance,"angles",
            " ".join("%.4f"%a if isinstance(a,float) else a for a in ang), "bb", bb(E))
