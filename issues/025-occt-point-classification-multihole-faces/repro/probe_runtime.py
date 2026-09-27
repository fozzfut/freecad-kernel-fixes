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
