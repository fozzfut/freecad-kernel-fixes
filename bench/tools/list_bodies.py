"""FreeCADCmd: list Part::Feature bodies of a file with face counts, largest first (choose BENCH_CUT_BASE).
The file comes from env BENCH_LIST_FILE: FreeCADCmd opens every .FCStd on its own command line itself."""
import os
import FreeCAD as App
doc = App.openDocument(os.environ["BENCH_LIST_FILE"])
rows = sorted(((len(o.Shape.Faces), o.Name, o.Label) for o in doc.Objects
               if o.TypeId == "Part::Feature" and not o.Shape.isNull()), reverse=True)
for r in rows[:15]:
    print("%5d  %-22s %s" % r)
