import json,re
D='/home/user/gaia-skill-tree/docs/graph/'
g=json.load(open(D+'gaia.json'));n=json.load(open(D+'named/index.json'))
sk=g['skills'];idx={s['id']:i for i,s in enumerate(sk)}
gen=[[s['id'],s['name'],'f' if s['type']=='fusion' else 'b',[idx[p] for p in s.get('prerequisites',[]) if p in idx]] for s in sk]
allN=[x for v in n['buckets'].values() for x in v]+n['awaitingClassification']
def lv(x):
    m=re.sub(r'\D+','',str(x.get('level') or ''));return int(m) if m else 0
br={'unique':'u','suite':'s'}
named=[]
for x in allN:
    ref=x.get('genericSkillRef') or x['id']
    if ref not in idx: continue
    gr=x.get('overallTrustGrade') or '-'
    if gr=='ungraded': gr='-'
    named.append([x['id'],x.get('contributor') or x['id'].split('/')[0],idx[ref],lv(x),br.get(x.get('branch'),'x'),1 if x.get('origin') else 0,round(x.get('trustMagnitude') or 0,2),gr,x.get('title') or x.get('name') or ''])
out={'g':gen,'n':named}
json.dump(out,open('/tmp/claude-0/-home-user/850a0daa-1860-5fc6-932e-829ca9edd2b5/scratchpad/canvas/_blob/local-flow.json','w'),separators=(',',':'),ensure_ascii=False)
print(len(gen),len(named),sum(len(x[3]) for x in gen))
