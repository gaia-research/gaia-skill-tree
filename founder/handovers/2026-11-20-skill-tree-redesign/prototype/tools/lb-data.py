import json
d=json.load(open('/home/user/gaia-skill-tree/docs/api/v1/leaderboard.json'))
rows=[]
for r in d['rows']:
    if r['grade'] not in 'SABC' or r['grade']=='ungraded': continue
    bd={k:round(v,1) for k,v in (r.get('typeBreakdown') or {}).items() if v}
    rows.append([r['id'],round(r['trustMagnitude'],2),r['grade'],int(r['level'][0]),1 if r['origin'] else 0,{'standard':'s','unique':'u','suite':'S'}[r['branch']],bd])
out={'at':d['generatedAt'][:10],'dist':{k:d['distribution'][k] for k in 'SABC'},'rows':rows}
open('lb-data.json','w').write(json.dumps(out,separators=(',',':')))
print(len(rows),len(json.dumps(out,separators=(',',':'))))
