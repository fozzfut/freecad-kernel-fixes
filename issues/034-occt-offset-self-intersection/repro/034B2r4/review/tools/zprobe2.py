import FreeCAD as App, Part, Mesh, os
O=open(os.environ["FC_OUT"]+"/zprobe2.txt","w")
for n in ("sx_a_off-1.5_ctl","sx_a_off-3","oq_a_off-3","oq_w_off-3","oq_n_off-3"):
    r=Part.read("C:/dev/occt8-mig/offset-034b2/rv4/out/o034b2rv4-new/%s.brep"%n)
    for tol in (0.02,0.008):
        m=Mesh.Mesh(r.tessellate(tol)); O.write("%s tess %.3f meshvol %.6f solid %s gprop %.6f\n"%(n,tol,m.Volume,m.isSolid(),r.Volume))
O.close()
