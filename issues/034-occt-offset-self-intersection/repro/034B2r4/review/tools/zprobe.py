import FreeCAD as App, Part, os
V=App.Vector
O=open(os.environ["FC_OUT"]+"/zprobe.txt","w")
for n,zs in (("sx_a_off-1.5_ctl",(1.6,3,10,17,18.4)),("sx_a_off-3",(3.1,5,10,15,16.9)),("oq_a_off-3",(3.1,4,5,6,6.9))):
    r=Part.read("C:/dev/occt8-mig/offset-034b2/rv4/out/o034b2rv4-new/%s.brep"%n)
    bb=r.BoundBox
    O.write("%s vol %.6f bb z %.6f %.6f faces %s\n"%(n,r.Volume,bb.ZMin,bb.ZMax,[type(f.Surface).__name__ for f in r.Faces]))
    for z in zs:
        a=sum(Part.Face(w).Area for w in r.slice(V(0,0,1),z) if w.isClosed())
        O.write("  z=%.2f area %.6f\n"%(z,a))
O.close()
