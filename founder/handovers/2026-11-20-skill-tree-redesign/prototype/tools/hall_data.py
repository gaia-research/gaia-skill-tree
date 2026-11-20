"""Collect Hall of Heroes plates (4★+) and every contributor handle the prototype shows; download avatars."""
import json, re, sys, os, subprocess
from PIL import Image
R = '/home/user/gaia-skill-tree/docs'
S = sys.argv[1]
n = json.load(open(R + '/graph/named/index.json'))
L = json.load(open(R + '/graph/ledger/data.json'))
tm = {r['skillId']: r for r in L['rows']}
gen = {s['id']: s for s in json.load(open(R + '/graph/gaia.json'))['skills']}
named = [(g, s) for g, lst in n['buckets'].items() for s in lst]
count = {}
for g, s in named:
    count[s['contributor']] = count.get(s['contributor'], 0) + 1

def lv(s):
    m = re.match(r'(\d)', s.get('level') or '0'); return int(m.group(1)) if m else 0

plates = []
for g, s in named:
    if lv(s) < 4:
        continue
    r = tm.get(s['id'], {})
    br = r.get('branch') or ('suite' if gen.get(g, {}).get('branch') == 'suite' else 'unique')
    fb = s.get('fusionBreakdown') or {}
    plates.append({'id': s['id'], 'slug': s['id'].split('/', 1)[1], 'title': s.get('title') or '', 'c': s['contributor'], 'lv': lv(s), 'br': br,
                   'tm': r.get('tm'), 'gr': r.get('grade') or '-', 'o': bool(s.get('origin')), 'nNamed': count[s['contributor']],
                   'fs': s.get('fusionScore'), 'fsDirect': fb.get('directCount'), 'fsTrans': fb.get('transitiveCount'), 'fsNested': fb.get('nestedSuiteCount'),
                   'g': g, 'gName': gen.get(g, {}).get('name', g)})
# order like the live page: 5★ unique, 5★ suite, then 4★ unique, 4★ suite, by TM
order = {('unique', 5): 0, ('suite', 5): 1, ('unique', 4): 2, ('suite', 4): 3}
plates.sort(key=lambda p: (order.get((p['br'], p['lv']), 9), -(p['tm'] or 0)))
fx = json.load(open(S + '/assets/atlas-fixtures.json'))
handles = set(p['c'] for p in plates)
handles |= set(x['c'] for x in fx['skills'])
handles |= set(h['c'] for h in fx['hall'])
handles |= set(x['id'].split('/')[0] for x in fx['ledger'])
handles |= {'mattpocock', 'mbtiongson1'}
os.makedirs(S + '/avatars', exist_ok=True)
ok, fail = [], []
for h in sorted(handles):
    dst = S + '/avatars/' + h + '.webp'
    if os.path.exists(dst):
        ok.append(h); continue
    tmp = S + '/avatars/' + h + '.src'
    code = subprocess.run(['curl', '-sS', '-m', '20', '-L', '-o', tmp, '-w', '%{http_code}', 'https://avatars.githubusercontent.com/' + h + '?s=240'], capture_output=True, text=True).stdout
    try:
        im = Image.open(tmp).convert('RGB'); im = im.resize((240, 240)); im.save(dst, 'WEBP', quality=80); ok.append(h)
    except Exception as e:
        fail.append((h, code))
    if os.path.exists(tmp):
        os.remove(tmp)
json.dump(plates, open(S + '/assets/hall-plates.json', 'w'), separators=(',', ':'))
print('plates', len(plates), 'handles', len(handles), 'ok', len(ok), 'fail', fail)
print([(p['slug'], p['br'], p['lv'], p['fs']) for p in plates[:6]])
