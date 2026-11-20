// Adds two shapes and two Unique placements to field-data.json for the 3D explorer.
//   live  : the site's world-tree-layout.js field pose (already in the file)
//   hero  : the prototype hero's networking (Scene.dc.html): Basic roots by cluster, fusions up the
//           crown by depth along their deepest prerequisite
//   Unique placement per shape: "layout" (live: spread disc around the outside anchor; hero: where the
//   hero formula puts it) and "fruit" (hung under a bough of the crown it belongs to).
// Output positions are explorer world coordinates: X right, Y up, Z depth.
const fs = require('fs');
const path = require('path');
const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'field-data.json'), 'utf8'));
const graph = JSON.parse(fs.readFileSync('/home/user/gaia-skill-tree/docs/graph/gaia.json', 'utf8'));
const cluster = graph.skills.map((s) => s.cluster || 0);
const nodes = D.nodes, N = nodes.length;
const parents = nodes.map(() => []), children = nodes.map(() => []);
D.edges.forEach((e) => { parents[e[1]].push(e[0]); children[e[0]].push(e[1]); });
const isU = nodes.map((n) => n[3] === 2 && n[4] >= 4);
const type = nodes.map((n) => n[2]), rank = nodes.map((n) => n[4]);

function hash01(s, salt) { let h = 2166136261 ^ (salt || 0); for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return ((h >>> 0) % 100000) / 100000; }
const r1 = (v) => Math.round(v * 10) / 10;

/* ── live shape: layout coordinates to world (Y up); Uniques spread on a golden-angle disc ── */
const liveD = new Float64Array(N * 3);
nodes.forEach((n, i) => { liveD[i * 3] = n[5]; liveD[i * 3 + 1] = -n[6]; liveD[i * 3 + 2] = n[7]; });
const groups = {};
nodes.forEach((n, i) => { if (isU[i]) { const k = n[5] + ',' + n[6] + ',' + n[7]; (groups[k] = groups[k] || []).push(i); } });
Object.values(groups).forEach((g) => {
  g.sort((a, b) => rank[b] - rank[a] || (nodes[a][0] < nodes[b][0] ? -1 : 1));
  g.forEach((i, j) => { if (!j) return; const a = j * 2.39996323, r = 23 * Math.sqrt(j); liveD[i * 3] += Math.cos(a) * r; liveD[i * 3 + 2] += Math.sin(a) * r; liveD[i * 3 + 1] += ((j % 3) - 1) * 6; });
});

/* ── hero shape: the Scene formulas, unit space, then scaled ── */
const S = 300;
const depth = new Array(N).fill(-1);
function dep(i, seen) { if (depth[i] >= 0) return depth[i]; if (!type[i]) { depth[i] = 0; return 0; } if (seen[i]) return 1; seen[i] = 1; let m = 0; parents[i].forEach((p) => { m = Math.max(m, dep(p, seen)); }); seen[i] = 0; depth[i] = m + 1; return depth[i]; }
for (let i = 0; i < N; i++) dep(i, {});
const deriv = children.map((c) => c.length);
const angC = (c) => (c / 8) * Math.PI * 2 + 0.35;
const hu = new Array(N), ang = new Array(N).fill(0), hParent = new Array(N).fill(-1);
const byCl = {};
nodes.forEach((n, i) => { if (!type[i]) (byCl[cluster[i]] = byCl[cluster[i]] || []).push(i); });
Object.keys(byCl).forEach((c) => {
  const arr = byCl[c].sort((a, b) => deriv[b] - deriv[a] || (nodes[a][0] < nodes[b][0] ? -1 : 1));
  arr.forEach((i, k) => {
    const t = (k + 1) / (arr.length + 1);
    const a = angC(+c) + (hash01(nodes[i][0], 1) - 0.5) * 1.0 * Math.sqrt(t);
    const r = 0.10 + 0.80 * Math.pow(t, 0.72);
    const y = -0.06 - 0.36 * Math.pow(t, 1.3) - hash01(nodes[i][0], 2) * 0.07;
    ang[i] = a; hu[i] = [Math.cos(a) * r, y, Math.sin(a) * r * 0.7];
  });
});
const crownR = [0, 0.66, 0.74, 0.60, 0.42, 0.22];
const fus = []; for (let i = 0; i < N; i++) if (type[i]) fus.push(i);
fus.sort((a, b) => depth[a] - depth[b]);
fus.forEach((i) => {
  let p = -1;
  parents[i].forEach((q) => { if (p < 0 || depth[q] > depth[p] || (depth[q] === depth[p] && rank[q] > rank[p])) p = q; });
  hParent[i] = p;
  const h1 = hash01(nodes[i][0], 3), h2 = hash01(nodes[i][0], 4), h3 = hash01(nodes[i][0], 5);
  const d = Math.min(depth[i], 5);
  const a = p >= 0 ? ang[p] + (h1 - 0.5) * (type[p] ? 0.8 : 1.5) : angC(cluster[i]);
  ang[i] = a;
  const y = 0.48 + (d - 1) * 0.2 + (h2 - 0.5) * 0.15;
  const r = crownR[d] * (0.5 + 0.5 * h3) + 0.05;
  hu[i] = [Math.cos(a) * r, y, Math.sin(a) * r * 0.7];
});
const heroD = new Float64Array(N * 3);
hu.forEach((p, i) => { heroD[i * 3] = p[0] * S; heroD[i * 3 + 1] = p[1] * S; heroD[i * 3 + 2] = p[2] * S; });

/* ── fruit: hang each Unique under a bough it belongs to ── */
function fruit(P, inCrown, axis) {
  const F = Float64Array.from(P), anchor = new Array(N).fill(-1);
  const crown = []; for (let i = 0; i < N; i++) if (!isU[i] && inCrown(i)) crown.push(i);
  const score = (i) => rank[i] * 100 + P[i * 3 + 1] * 0.1;
  /* candidates: crown prerequisites, then crown unlocks, then the same cluster, then any proven bough;
     at most three fruit hang from one bough */
  const load = {}, order = [];
  for (let u = 0; u < N; u++) if (isU[u]) order.push(u);
  order.sort((a, b) => rank[b] - rank[a] || (nodes[a][0] < nodes[b][0] ? -1 : 1));
  order.forEach((u) => {
    const byScore = (arr) => arr.slice().sort((a, b) => score(b) - score(a));
    const byHash = (arr) => arr.slice().sort((a, b) => hash01(nodes[u][0] + nodes[a][0], 7) - hash01(nodes[u][0] + nodes[b][0], 7));
    const c = [].concat(
      byScore(parents[u].filter((p) => !isU[p] && inCrown(p))),
      byScore(children[u].filter((p) => !isU[p] && inCrown(p))),
      byHash(crown.filter((p) => cluster[p] === cluster[u] && rank[p] >= 2)),
      byHash(crown.filter((p) => rank[p] >= 2)));
    const pick = c.find((p) => (load[p] || 0) < 3);
    anchor[u] = pick != null ? pick : c[0];
    load[anchor[u]] = (load[anchor[u]] || 0) + 1;
  });
  const by = {};
  for (let u = 0; u < N; u++) if (anchor[u] >= 0) (by[anchor[u]] = by[anchor[u]] || []).push(u);
  Object.keys(by).forEach((a) => {
    a = +a; const list = by[a].sort((x, y) => rank[y] - rank[x] || (nodes[x][0] < nodes[y][0] ? -1 : 1));
    const ax = P[a * 3], ay = P[a * 3 + 1], az = P[a * 3 + 2];
    let ox = ax - axis[0], oz = az - axis[2]; const ol = Math.hypot(ox, oz);
    if (ol < 8) { const t = hash01(nodes[a][0], 11) * Math.PI * 2; ox = Math.cos(t); oz = Math.sin(t); } else { ox /= ol; oz /= ol; }
    list.forEach((u, k) => {
      const turn = (k - (list.length - 1) / 2) * 0.95, cx = Math.cos(turn), sx = Math.sin(turn);
      const dx = ox * cx - oz * sx, dz = ox * sx + oz * cx;
      const out = 9 + 5 * k, drop = 24 + 7 * (k % 2) + hash01(nodes[u][0], 13) * 6;
      F[u * 3] = ax + dx * out; F[u * 3 + 1] = ay - drop; F[u * 3 + 2] = az + dz * out;
    });
  });
  /* relax: fruit keep 22 apart from each other and 11 from any other skill */
  const us = []; for (let u = 0; u < N; u++) if (anchor[u] >= 0) us.push(u);
  for (let it = 0; it < 60; it++) {
    us.forEach((u) => {
      for (let j = 0; j < N; j++) {
        if (j === u) continue;
        const min = isU[j] ? 22 : 11;
        const dx = F[u * 3] - F[j * 3], dy = F[u * 3 + 1] - F[j * 3 + 1], dz = F[u * 3 + 2] - F[j * 3 + 2], d = Math.hypot(dx, dy, dz);
        if (d >= min || d === 0) continue;
        const push = (min - d) * (isU[j] ? 0.5 : 1), hl = Math.hypot(dx, dz) || 1;
        F[u * 3] += dx / hl * push * 0.8; F[u * 3 + 2] += dz / hl * push * 0.8; F[u * 3 + 1] -= push * 0.35;
      }
    });
  }
  return { F, anchor };
}
const liveCenter = [0, 0, 0];
const liveF = fruit(liveD, (i) => nodes[i][6] < 100, liveCenter);
const heroF = fruit(heroD, (i) => type[i] === 1, [0, 0, 0]);

const flat = (a) => Array.from(a, r1);
const anchors = (f) => { const o = {}; f.anchor.forEach((a, u) => { if (a >= 0) o[u] = a; }); return o; };
D.v = 3;
D.shapes = {
  live: { layout: flat(liveD), fruit: flat(liveF.F), anchor: anchors(liveF) },
  hero: { layout: flat(heroD), fruit: flat(heroF.F), anchor: anchors(heroF), parent: hParent, ang: ang.map((a) => Math.round(a * 1000) / 1000), unit: S },
};
D.cluster = cluster;
fs.writeFileSync(path.join(__dirname, 'field-data-v3.json'), JSON.stringify(D));
console.error('bytes', fs.statSync(path.join(__dirname, 'field-data-v3.json')).size);
const show = (name, f) => { const by = {}; Object.entries(anchors(f)).forEach(([u, a]) => { by[a] = (by[a] || 0) + 1; }); console.error(name, 'anchors', Object.keys(by).length, 'max fruit per anchor', Math.max(...Object.values(by))); };
show('live', liveF); show('hero', heroF);
const ys = (P) => { let a = 1e9, b = -1e9; for (let i = 0; i < N; i++) { a = Math.min(a, P[i * 3 + 1]); b = Math.max(b, P[i * 3 + 1]); } return [Math.round(a), Math.round(b)]; };
console.error('hero y range', ys(heroD), 'live y range', ys(liveD));
