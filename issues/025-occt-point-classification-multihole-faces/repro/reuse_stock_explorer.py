"""Native OCCT calls through existing pythonOCC, independent of C++ build queue.
Tests ONLY reuse of stock FaceExplorer; no custom compiled implementation.
Run with FreeCAD's bin/python.exe -B; never imports FreeCAD or writes into its installation.
"""
import ctypes as C, json, os, sys, time, random
from pathlib import Path
class Memory(C.Structure):
    _fields_=[('length',C.c_ulong),('load',C.c_ulong)]+[(n,C.c_ulonglong) for n in ('totalphys','availphys','totalpage','availpage','totalvirt','availvirt','extended')]
class Basic(C.Structure):
    _fields_=[('process_time',C.c_longlong),('job_time',C.c_longlong),('flags',C.c_ulong),('minws',C.c_size_t),('maxws',C.c_size_t),('active',C.c_ulong),('affinity',C.c_size_t),('priority',C.c_ulong),('scheduling',C.c_ulong)]
class IO(C.Structure): _fields_=[(n,C.c_ulonglong) for n in ('ro','wo','oo','rt','wt','ot')]
class Limits(C.Structure):
    _fields_=[('basic',Basic),('io',IO),('process',C.c_size_t),('job',C.c_size_t),('peakprocess',C.c_size_t),('peakjob',C.c_size_t)]
k=C.WinDLL('kernel32',use_last_error=True)
k.CreateJobObjectW.restype=C.c_void_p;k.CreateJobObjectW.argtypes=[C.c_void_p,C.c_wchar_p]
k.GetCurrentProcess.restype=C.c_void_p
k.SetInformationJobObject.argtypes=[C.c_void_p,C.c_int,C.c_void_p,C.c_ulong]
k.AssignProcessToJobObject.argtypes=[C.c_void_p,C.c_void_p]
job=k.CreateJobObjectW(None,None);limits=Limits();limits.basic.flags=0x100;limits.process=1024**3
assert job and k.SetInformationJobObject(job,9,C.byref(limits),C.sizeof(limits)) and k.AssignProcessToJobObject(job,k.GetCurrentProcess()),('cap failed',C.get_last_error())
m=Memory();m.length=C.sizeof(m);k.GlobalMemoryStatusEx(C.byref(m))
start_gate=time.monotonic()
while m.availphys<1024**3 or m.availpage<4*1024**3:
    print('MEMORY_GATE',m.availphys,m.availpage,flush=True)
    if time.monotonic()-start_gate>=600:sys.exit(77)
    time.sleep(15)
    k.GlobalMemoryStatusEx(C.byref(m))
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepTools import breptools
from OCC.Core.BRepClass import BRepClass_FaceClassifier,BRepClass_FClassifier,BRepClass_FaceExplorer
from OCC.Core.TopoDS import TopoDS_Shape,topods
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE,TopAbs_WIRE
from OCC.Core.gp import gp_Pnt2d
root=Path('C:/dev/freecad-kernel-fixes')
rows=[]
def query(c,exp,p):
    try:
        if exp is None:c.Perform(face,p,1e-7)
        else:c.Perform(exp,p,1e-7)
        return int(c.State())
    except Exception as e:return type(e).__name__+':'+str(e)
for path in (root/'build/025/probe/list.txt').read_text().splitlines():
    shape=TopoDS_Shape();assert breptools.Read(shape,path,BRep_Builder())
    faces=[];it=TopExp_Explorer(shape,TopAbs_FACE);idx=0
    while it.More():
        idx+=1;f=topods.Face(it.Current());w=TopExp_Explorer(f,TopAbs_WIRE);nw=0
        while w.More():nw+=1;w.Next()
        if nw>1:faces.append((idx,nw,f))
        it.Next()
    if not faces:continue
    idx,nw,face=max(faces,key=lambda x:x[1]);u0,u1,v0,v1=breptools.UVBounds(face)
    rng=random.Random(25);points=[gp_Pnt2d(u0+(u1-u0)*rng.random(),v0+(v1-v0)*rng.random()) for _ in range(128)]
    # Same native algorithm; one path resets the FaceExplorer for every query.
    ref=[];times={};mismatch=0
    for rep,mode in enumerate(('fresh','reuse','reuse','fresh')):
        exp=None if mode=='fresh' else BRepClass_FaceExplorer(face)
        t=time.perf_counter();answers=[]
        for p in points:
            c=BRepClass_FaceClassifier() if exp is None else BRepClass_FClassifier()
            answers.append(query(c,exp,p))
        dt=time.perf_counter()-t;times.setdefault(mode,[]).append(dt)
        if not ref:ref=answers
        else:mismatch+=sum(a!=b for a,b in zip(ref,answers))
    row=dict(file=path,face=idx,wires=nw,points=len(points),timings=times,mismatches=mismatch,states={str(s):ref.count(s) for s in set(ref)})
    rows.append(row);print(json.dumps(row),flush=True)
    (root/'issues/025-occt-point-classification-multihole-faces/measurements/reuse-stock-explorer.json').write_text(json.dumps(rows,indent=2))
print('VERDICT mismatches='+str(sum(x['mismatches'] for x in rows)),flush=True)
sys.exit(1 if any(x['mismatches'] for x in rows) else 0)
