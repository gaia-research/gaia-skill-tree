# PR #364 / PR #365 — Design Milestones

Branch: `claude/pr364-nodes-colors-NstcU`  
PR: [#365](https://github.com/mbtiongson1/gaia-skill-tree/pull/365)  
Date: 2026-05-22  
Status: Open — pending Cloudflare preview bug (tracked in [#377](https://github.com/mbtiongson1/gaia-skill-tree/issues/377))

---

## What shipped

### 1. 4D ML Hyper-Atlas layout system

The skill graph now supports three scientifically-derived layout modes per skill, replacing the legacy single spherical position:

| Mode | Method |
|---|---|
| `semantic` | PCA reduction of skill name/description embeddings to 4D |
| `spectral` | Laplacian spectral analysis of the graph adjacency matrix |
| `deterministic` | Stable sphere + W-variance layout seeded from skill ID hash |

Each skill in `docs/graph/gaia.json` carries:
```json
{
  "cluster": 3,
  "positions": {
    "semantic":      [x, y, z, w],
    "spectral":      [x, y, z, w],
    "deterministic": [x, y, z, w]
  }
}
```

Coordinates are normalized to `[-1, 1]` and scaled by `450 × graphScale` at render time.

### 2. Semantic clustering — 8-color palette via CSS tokens

Eight semantic clusters are rendered using CSS custom properties defined on `:root` in `docs/css/styles.css`:

```css
--cluster-0-rgb: 78, 155, 255;   /* blue */
--cluster-1-rgb: 249, 115, 22;   /* orange */
--cluster-2-rgb: 16, 185, 129;   /* emerald */
--cluster-3-rgb: 239, 68, 68;    /* red */
--cluster-4-rgb: 139, 92, 246;   /* violet */
--cluster-5-rgb: 236, 72, 153;   /* pink */
--cluster-6-rgb: 34, 211, 238;   /* cyan */
--cluster-7-rgb: 251, 113, 133;  /* rose */
```

`skill-graph.js` reads these at runtime via `getComputedStyle` — no hex codes in JS. This unblocked the Guard A CI check which bans bare hex in `docs/js/*.js`.

### 3. Dynamic node sizing by rank

Node radius follows an exponential curve keyed to skill rank (★ level):

```
r(n) = 2.3 × e^(0.25 × n)     n = star count (1–6)
r(0) = 2.5                      (no rank / basic)
```

Static overrides for named types: `ultimate = 12.5`, `unique = 9.5`, `extra = 6.9`, `basic = 3.5`.

### 4. Schema-clean separation of concerns

`cluster` and `positions` fields live **only** in `docs/graph/gaia.json` (the served graph).  
`registry/gaia.json` (the canonical schema-validated registry) has these fields stripped, preserving `additionalProperties: false` compliance.

Two scripts manage the split:
- `scripts/generateProjections.py` — writes `generated-output/layouts.json`, adds only `meta.clusterNames` / `meta.centroids` to `registry/gaia.json`
- `scripts/syncDocsGraphAssets.py` — enriches `docs/graph/gaia.json` with per-skill cluster/positions

### 5. Accessibility

The graph canvas now carries an `aria-label` describing the 4D semantic layout for screen readers.

### 6. Cloudflare infrastructure

- Root `wrangler.toml` added (`directory = "docs"`) so `wrangler dev` serves `docs/` as static assets
- `docs/wrangler.toml` added as belt-and-suspenders (`directory = "."`)
- `docs/graph/ping.json` probe added to confirm asset directory reachability
- CI workflow guarded against missing `CLOUDFLARE_API_TOKEN` secret to prevent noisy failures on forks

### 7. 200-node graph published

`docs/graph/gaia.json` contains all 200 curated skills with full 4D positions and cluster assignments. Previously only 20 hardcoded `FALLBACK_SKILLS` were visible in the graph.

---

## Known issues / parked

| Issue | Detail | Tracking |
|---|---|---|
| Cloudflare preview still shows 20 FALLBACK_SKILLS | `/graph/gaia.json` fetch succeeds but graph may be receiving HTML 404 silently | [#377](https://github.com/mbtiongson1/gaia-skill-tree/issues/377) |
| NODE_RADII unique discrepancy | `.get()` forces unique to `'5★'` formula (~7.8px) instead of static `9.5` | [#377](https://github.com/mbtiongson1/gaia-skill-tree/issues/377) |
| PR #365 mergeable_state: dirty | Merge conflicts with main need resolution before merge | — |
