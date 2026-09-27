"""Generate private diagnostic/prototype classes from OCCT 7.8.1; never edits OCCT.
The prepared variant reuses FaceExplorer UV bounds and lazy wire adjacency maps.
No geometric check, ray, edge, tolerance or iteration order is changed.
"""
from pathlib import Path
import hashlib, json, zipfile
ROOT=Path('C:/dev/freecad-kernel-fixes')
SRC=ROOT/'occt/src'
OUT=ROOT/'build/025/probe'
OUT.mkdir(parents=True, exist_ok=True)
def write(name,s): (OUT/name).write_text(s,encoding='utf-8',newline='\n')
def read(pkg,name): return (SRC/pkg/name).read_text(encoding='utf-8')
def change(s,a,b,n=1):
    assert s.count(a)==n,(a,s.count(a),n)
    return s.replace(a,b)
h=read('BRepClass','BRepClass_FaceExplorer.hxx').replace('BRepClass_FaceExplorer','PreparedExplorer').replace('Standard_EXPORT ','')
h=h.replace('#include <Standard.hxx>','#include <Standard.hxx>\n#include <NCollection_DataMap.hxx>\n#include <TopTools_ShapeMapHasher.hxx>\n#include <memory>')
h=change(h,'  TopoDS_Face myFace;', '''  typedef TopTools_IndexedDataMapOfShapeListOfShape WireMap;
  NCollection_DataMap<TopoDS_Shape, std::shared_ptr<WireMap>> myWireMaps;
  const WireMap* myCurrentMap = nullptr;
  TopoDS_Face myFace;''')
write('PreparedExplorer.hxx',h)
write('PreparedExplorer.lxx',read('BRepClass','BRepClass_FaceExplorer.lxx').replace('BRepClass_FaceExplorer','PreparedExplorer'))
c=read('BRepClass','BRepClass_FaceExplorer.cxx').replace('BRepClass_FaceExplorer','PreparedExplorer')
c=change(c,'  myMapVE.Clear();\n  TopExp::MapShapesAndAncestors(myWExplorer.Current(), TopAbs_VERTEX, TopAbs_EDGE, myMapVE);','''  const std::shared_ptr<WireMap>* cached = myWireMaps.Seek(myWExplorer.Current());
  if (!cached) {
    std::shared_ptr<WireMap> fresh(new WireMap);
    TopExp::MapShapesAndAncestors(myWExplorer.Current(), TopAbs_VERTEX, TopAbs_EDGE, *fresh);
    myWireMaps.Bind(myWExplorer.Current(), fresh);
    myCurrentMap = fresh.get();
  } else { myCurrentMap = cached->get(); }''')
c=change(c,'E.SetNextEdge(myMapVE);','E.SetNextEdge(*myCurrentMap);')
write('PreparedExplorer.cxx',c)
for suffix in ['hxx','_0.cxx']:
    name='BRepClass_FClassifier'+('.hxx' if suffix=='hxx' else '_0.cxx')
    txt=read('BRepClass',name).replace('BRepClass_FClassifier','PreparedClassifier').replace('BRepClass_FaceExplorer','PreparedExplorer').replace('Standard_EXPORT ','')
    write('PreparedClassifier'+('.hxx' if suffix=='hxx' else '.cxx'),txt)
for kind in ['Diagnostic','Prepared']:
    cls=kind+'FClass2d'
    h=read('BRepTopAdaptor','BRepTopAdaptor_FClass2d.hxx').replace('BRepTopAdaptor_FClass2d',cls).replace('Standard_EXPORT ','')
    extra='''\n  mutable unsigned long long queries=0, wireTests=0, ambiguous=0, badWire=0;
  int polygons() const { return TabClass.Length(); }
  int firstOrientation() const { return TabOrien.IsEmpty() ? -99 : TabOrien(1); }
'''
    if kind=='Prepared':
        h=h.replace('#include <Standard.hxx>','#include <Standard.hxx>\n#include <memory>\n#include <PreparedExplorer.hxx>')
        extra+='  mutable std::unique_ptr<PreparedExplorer> preparedExplorer;\n'
    h=change(h,'  DEFINE_STANDARD_ALLOC','  DEFINE_STANDARD_ALLOC'+extra)
    write(cls+'.hxx',h)
    c=read('BRepTopAdaptor','BRepTopAdaptor_FClass2d.cxx').replace('BRepTopAdaptor_FClass2d',cls)
    c=change(c,'  Standard_Integer nbtabclass = TabClass.Length();\n  \n  if(nbtabclass==0)', '  ++queries;\n  Standard_Integer nbtabclass = TabClass.Length();\n  \n  if(nbtabclass==0)',2)
    c=change(c,'Standard_Integer cur = ((CSLib_Class2d *)TabClass(n))->SiDans(Puv);','++wireTests;\n\t  Standard_Integer cur = ((CSLib_Class2d *)TabClass(n))->SiDans(Puv);')
    c=change(c,'if(dedans==0) { \n\t  BRepClass_FaceClassifier','if(dedans==0) { \n          ++ambiguous;\n\t  BRepClass_FaceClassifier')
    c=change(c,'else {  //-- TabOrien(1)=-1    False Wire\n\tBRepClass_FaceClassifier','else {  //-- TabOrien(1)=-1    False Wire\n        ++badWire;\n\tBRepClass_FaceClassifier',2)
    if kind=='Prepared':
        c=c.replace('#include <BRepClass_FaceClassifier.hxx>','#include <PreparedClassifier.hxx>')
        c=c.replace('BRepClass_FaceClassifier aClassifier;', 'if (!preparedExplorer) preparedExplorer.reset(new PreparedExplorer(Face));\n        PreparedClassifier aClassifier;')
        c=c.replace('aClassifier.Perform(Face,Puv,','aClassifier.Perform(*preparedExplorer,Puv,')
    write(cls+'.cxx',c)
with zipfile.ZipFile('C:/dev/fillet-perf/parts/Top.FCStd') as z:
    names=[n for n in z.namelist() if n.endswith('.brp')]
    assert len(names)==1,names
    (OUT/'Top.brep').write_bytes(z.read(names[0]))
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*') if p.suffix in ('.hxx','.cxx','.lxx','.brep')}
write('generated.sha256.json',json.dumps(manifest,indent=2))
print('GENERATED',len(manifest),'files')
