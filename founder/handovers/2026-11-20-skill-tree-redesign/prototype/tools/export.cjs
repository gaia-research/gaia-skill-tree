// Export a compact snapshot of the live World Tree field layout for the HUD prototype.
// Runs the site's own deterministic layout (docs/js/world-tree-layout.js) over docs/graph/gaia.json.
const fs = require('fs');
const path = require('path');
const ROOT = '/home/user/gaia-skill-tree/docs';
const layoutApi = require(path.join(ROOT, 'js/world-tree-layout.js'));
const graph = JSON.parse(fs.readFileSync(path.join(ROOT, 'graph/gaia.json'), 'utf8'));
const named = JSON.parse(fs.readFileSync(path.join(ROOT, 'graph/named/index.json'), 'utf8'));
const holders = fs.readFileSync(path.join(__dirname, 'holders.txt'), 'utf8').trim().split('\n');

function stars(label) { const n = parseInt(label, 10); return Number.isFinite(n) ? n : 0; }
graph.skills.forEach((s) => { s.effectiveRank = stars(s.namedMaxLevel); });
const L = layoutApi.buildWorldTreeLayout(graph, { width: 760, height: 680 });
console.error('layout keys', Object.keys(L));

const ids = graph.skills.map((s) => s.id);
const idx = Object.fromEntries(ids.map((id, i) => [id, i]));
const r1 = (v) => Math.round(v * 10) / 10;
const short = (t, n) => { t = (t || '').replace(/\s+/g, ' ').trim(); if (t.length <= n) return t; const c = t.slice(0, n); return c.slice(0, c.lastIndexOf(' ')) + '…'; };

const nodes = graph.skills.map((s) => {
  const fp = L.fieldPose[s.id] || { x: 0, y: 0, z: 0, phase: 0 };
  const arr = named.buckets[s.id] || [];
  const origins = arr.filter((e) => e.origin);
  const o = origins[0] || null;
  const lv = o ? stars(o.level) : 0;
  const redacted = o && lv <= 1;
  const co = redacted ? [] : origins.map((e) => holders.indexOf(e.contributor)).filter((k) => k >= 0);
  const br = s.branch === 'suite' ? 1 : s.branch === 'unique' ? 2 : 0;
  return [
    s.id, s.name || s.id, s.type === 'fusion' ? 1 : 0, br, stars(s.namedMaxLevel),
    r1(fp.x), r1(fp.y), r1(fp.z || 0), Math.round((fp.phase || 0) * 100) / 100,
    o && !redacted ? holders.indexOf(o.contributor) : -1,
    o && !redacted ? (o.id.split('/')[1] || '') : '',
    o && o.title && !redacted ? o.title : '',
    short(s.summary || s.description, 150),
    arr.length,
    co,
  ];
});

const structural = new Set(L.structuralEdgeKeys || []);
const edges = (L.edges || []).map((e) => {
  const a = e.source, b = e.target;
  if (!(a in idx) || !(b in idx)) return null;
  return [idx[a], idx[b], structural.has(a + '\u0000' + b) ? 1 : 0];
}).filter(Boolean);

const ghostKeys = []; const gIdx = {};
const routes = {};
Object.entries(L.structuralRoutes || {}).forEach(([key, route]) => {
  const [a, b] = key.split('\u0000');
  routes[idx[a] + ':' + idx[b]] = route.map((w) => {
    if (w.kind === 'node') return idx[w.id];
    if (!(w.key in gIdx)) { gIdx[w.key] = ghostKeys.length; ghostKeys.push(w.key); }
    return -(gIdx[w.key] + 1);
  });
});
const ghosts = ghostKeys.map((k) => { const g = L.ghostPose[k]; return [r1(g.x), r1(g.y), r1(g.z || 0)]; });

const out = { v: 2, avCols: 8, avRows: Math.ceil(holders.length / 8), avCell: 64, source: 'docs/graph/gaia.json + docs/js/world-tree-layout.js (field pose)', counts: { skills: nodes.length, links: edges.length, unique: nodes.filter((n) => n[3] === 2).length, holders: holders.length }, holders, nodes, edges, ghosts, routes };
fs.writeFileSync(path.join(__dirname, 'field-data.json'), JSON.stringify(out));
console.error('nodes', nodes.length, 'edges', edges.length, 'structural', edges.filter((e) => e[2]).length, 'ghosts', ghosts.length, 'routes', Object.keys(routes).length, 'bytes', fs.statSync(path.join(__dirname, 'field-data.json')).size);
const xs = nodes.map((n) => n[5]), ys = nodes.map((n) => n[6]), zs = nodes.map((n) => n[7]);
console.error('x', Math.min(...xs), Math.max(...xs), 'y', Math.min(...ys), Math.max(...ys), 'z', Math.min(...zs), Math.max(...zs));
const byRank = {}; nodes.forEach((n) => { const k = ['std', 'suite', 'uniq'][n[3]] + n[4]; byRank[k] = (byRank[k] || 0) + 1; }); console.error(byRank);
