import re,collections,sys
c=collections.Counter()
for l in open(sys.argv[1]):
    f=dict(re.findall(r'(\w+)=(\S+)',l)); tag=l.split()[0]
    if f.get('done')=='1':
        k='done valid=%s bop=%s sh=%s'%(f['valid'],f['bop'],re.sub(r'\d+:f\d+/','',f['shells']))
        if len(sys.argv)>2 and (f['valid']=='0' or f['bop']!='clean'): print(' ',tag, f['shells'], f['check'], 'vol0=',f['vol0'],'vol=',f['vol'])
    else: k='notdone err=%s'%f.get('err')
    c[k]+=1
for k,v in c.most_common(): print(v,k)
