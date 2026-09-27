# regenerate the traced copy of the branch MakeOffset.cxx (stage face counts, dump after MakeShells, rim pairs)
import re
src='C:/dev/occt-801-034-b2/src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx'
s=open(src,encoding='utf-8',newline='').read()
BS=chr(92)
def nf(expr): return '{int n_=0; for (TopExp_Explorer e_('+expr+', TopAbs_FACE); e_.More(); e_.Next()) n_++; fprintf(stderr, "T034 %d faces=%d err=%d'+BS+'n", __LINE__, n_, (int)myError);}'
def after(anchor, add, start=0):
    global s
    i=s.find(anchor, start); assert i>=0, anchor
    j=i+len(anchor); s=s[:j]+add+s[j:]; return j
k=s.find('void BRepOffset_MakeOffset::MakeOffsetShape(')
after('BuildOffsetByInter(aPS.Next(aSteps(PIOperation_BuildOffsetBy)));\n  }', '\n  '+nf('myFaceComp'), k)
after('MakeShells(aPS.Next(aSteps(PIOperation_MakeShells)));', '\n  '+nf('myOffsetShape')+'\n  if (getenv("T034_DUMP")) BRepTools::Write(myOffsetShape, getenv("T034_DUMP"));', k)
after('  SelectShells();', '\n  '+nf('myOffsetShape'), k)
a='        if (!aL1.IsEmpty())\n        {\n          Inter.TouchedFaces().Add(aF1);'
i=s.find(a); assert i>0
s=s[:i]+'        fprintf(stderr, "T034 rim pair cap=%d margin=%g n1=%d n2=%d'+BS+'n", (int)aPair.IsCapA, aPair.Margin, aL1.Extent(), aL2.Extent());\n'+s[i:]
s=s.replace('#include <cstdio>','#include <cstdio>\n#include <cstdlib>',1)
open('C:/dev/occt8-mig/offset-034b2/r1c/trc/BRepOffset_MakeOffset.cxx','w',encoding='utf-8',newline='').write(s)
print('ok', s.count('T034'))
# dump per touched face: the face + its descendant edges in AsDes, after Intersection3D
s=open('C:/dev/occt8-mig/offset-034b2/r1c/trc/BRepOffset_MakeOffset.cxx',encoding='utf-8',newline='').read()
a='  Intersection3D(Inter, aPSInter.Next(90));\n'
assert s.count(a)==1
dump='''  if (getenv("T034_ASDES"))
  {
    BRep_Builder aBBd; TopoDS_Compound aCd; aBBd.MakeCompound(aCd);
    for (int iF = 1; iF <= Inter.TouchedFaces().Extent(); ++iF)
    {
      const TopoDS_Shape& aFd = Inter.TouchedFaces()(iF);
      TopoDS_Compound aCf; aBBd.MakeCompound(aCf); aBBd.Add(aCf, aFd);
      if (myAsDes->HasDescendant(aFd))
        for (NCollection_List<TopoDS_Shape>::Iterator itD(myAsDes->Descendant(aFd)); itD.More(); itD.Next()) aBBd.Add(aCf, itD.Value());
      aBBd.Add(aCd, aCf);
    }
    BRepTools::Write(aCd, getenv("T034_ASDES"));
  }
'''
s=s.replace(a,a+dump)
open('C:/dev/occt8-mig/offset-034b2/r1c/trc/BRepOffset_MakeOffset.cxx','w',encoding='utf-8',newline='').write(s)
print('asdes ok')
