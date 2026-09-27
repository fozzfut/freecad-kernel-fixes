# idcmp.py <a.txt> <b.txt> : per-line key = first token (or 2nd for RV lines); compare done/err/valid/vol fields
import sys,re
def load(p):
    d={}; cur=None
    for l in open(p,encoding='utf-8',errors='replace'):
        l=l.strip()
        if not l: continue
        if l.startswith('== '): cur=l.split()[1]; d[cur]=''; continue
        f=l.split()
        key=f[1] if f[0] in ('RV',) else (cur if cur and l.startswith(('IN','STOCK')) else f[0])
        kv=dict(x.split('=',1) for x in f if '=' in x)
        sig=' '.join('%s=%s'%(k,kv[k]) for k in ('done','err','valid','grade','vol','shells','solids','faces','nf') if k in kv)
        if f[0].startswith('STOCK') or f[0]=='IN': d[key]=d.get(key,'')+' '+f[0]+':'+sig
        else: d[key]=sig
    return d
a=load(sys.argv[1]); b=load(sys.argv[2]); same=0; diff=[]
for k in a:
    if k not in b: continue
    if a[k]==b[k]: same+=1
    else: diff.append(k)
print("compared",len([k for k in a if k in b]),"same",same,"diff",len(diff),"missing",len([k for k in a if k not in b]))
for k in diff: print("  ",k,"|",a[k][:150],"|",b[k][:150])
