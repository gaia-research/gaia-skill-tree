import json,re
D='/home/user/gaia-skill-tree/docs/graph/'
g=json.load(open(D+'gaia.json')); n=json.load(open(D+'named/index.json'))
byid={s['id']:s for s in g['skills']}
skills=[]; sidx={}; hand=[]; hidx={}; ev=[]
def S(id,name,typ,named):
    if id not in sidx: sidx[id]=len(skills); skills.append([id,name,typ,1 if named else 0])
    return sidx[id]
def H(h):
    if not h or h=='unknown': return -1
    if h not in hidx: hidx[h]=len(hand); hand.append(h)
    return hidx[h]
ARR=re.compile(r'(\d)★\s*(?:to|→)\s*(\d)★')
def classify(t):
    a=t['action']; d=(t.get('details') or '').strip()
    d=re.sub(r'\s*\((?:gaia dev [^)]*)\)\s*$','',d).replace('->','→')
    if a in('demote','rank_up'):
        m=ARR.search(d)
        if m:
            x,y=int(m[1]),int(m[2])
            if y>x: return 'promoted','Promoted %d★ to %d★'%(x,y),d
            if y<x: return 'demoted','Demoted %d★ to %d★'%(x,y),d
        m=re.search(r'from None to (\d)★',d)
        if m: return 'promoted','Level set to %s★'%m[1],d
        if 'Origin status set to true' in d: return 'origin','Origin gained',d
        if a=='demote': return 'demoted','Demoted',d
        return 'promoted','Rank updated',d
    M={'propose':('added','Proposed'),'add':('added','Added'),'name':('named','Named'),
     'evidence_added':('evidence','Evidence added'),'evidence_graded':('evidence','Evidence re-graded'),'evidence_removed':('evidence','Evidence removed'),
     'fuse':('fused','Fused'),'suite_ref_set':('fused','Suite linked'),'merge':('other','Merged'),
     'recalibrate_trust_magnitude':('trust','Trust recalibrated'),'migrate_trust_magnitude':('trust','Trust migrated'),
     'upstream_synced':('upstream','Upstream synced'),'upstream_deprecated':('upstream','Upstream deprecated'),
     'type_change':('other','Reclassified'),'rename':('other','Renamed'),'note':('other','Note'),'installation_updated':('other','Install updated'),'verified':('other','Verified')}
    f,v=M.get(a,('other',a.replace('_',' ').capitalize()))
    d=re.sub(r'\s+from (?:/|generated-output/|~/)\S*','',d) if a=='installation_updated' else d
    d=re.sub(r'(?<![\w.])(?:/(?:tmp|data|home|Users|var)/\S+|generated-output/\S+)','[local path]',d)
    return f,v,d
def push(sid,typ,t):
    ts=t.get('timestamp') or t.get('date')
    if not ts: return
    f,v,d=classify(t)
    ev.append([ts[:19].replace('T',' ') if 'T' in ts else ts+' 00:00:00',sid,f,t['action'],H(t.get('contributor')),v,d[:240],typ])
for s in g['skills']:
    i=S(s['id'],s['name'],s.get('type','basic'),False)
    for t in s.get('timeline',[]): push(i,s.get('type','basic'),t)
for sk,lst in n['buckets'].items():
    for x in lst:
        c=byid.get(x.get('genericSkillRef') or sk); typ=(c or {}).get('type') or x.get('type') or 'basic'
        i=S(x['id'],x['id'],typ,True)
        for t in x.get('timeline',[]): push(i,typ,t)
ev.sort(key=lambda e:e[0],reverse=True)
out={'gen':g.get('generatedAt'),'skills':skills,'hand':hand,'ev':ev}
json.dump(out,open('canvas/_blob/local-changelog.json','w'),ensure_ascii=False,separators=(',',':'))
import collections
print(len(ev),len(skills),ev[-1][0],ev[0][0],collections.Counter(e[2] for e in ev))
