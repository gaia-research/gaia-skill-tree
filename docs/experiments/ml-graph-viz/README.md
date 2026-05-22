# ML Layout Sampler

Branch: `dev/ml-graph-viz-sampler`

Three candidate layouts for the Gaia skill graph rendered side-by-side so we can
eyeball which approach is worth investing in before building it for real.

## Files

- `build_layouts.py` — loads `registry/gaia.json`, builds a networkx graph,
  computes three 2D embeddings, runs Louvain community detection, and writes
  `layouts.json`.
- `layouts.json` — pre-computed positions + community assignments. Checked in so
  the HTML works without running Python.
- `index.html` — vanilla JS + Canvas viewer. Open it directly in a browser.

## Versions

### V1 — 2D Side-by-Side (`index.html`)
The original 2D comparison using TF-IDF and Laplacian eigenmaps.

### V2 — 3D Interactive Upgrade (`index_3d.html`)
Projects the graph into 3D (x, y, z) using SVD and spectral decomposition. Supports rotation and zoom.

| Key | Method | 3D Dimension |
|---|---|---|
| `deterministic` | Golden Spiral | Tier-based spheres (Design parity) |
| `spectral` | Laplacian Eigenmaps | Structural proximity in 3D space |
| `semantic` | Embedding SVD | Shared "meaning" clusters in 3D space |

## Regenerating

**For 2D Layouts (V1):**
```bash
python docs/experiments/ml-graph-viz/build_layouts.py
```

**For 3D Layouts (V2):**
```bash
python docs/experiments/ml-graph-viz/build_layouts_3d.py
```

Re-run after registry edits to refresh `layouts.json`. Requires `networkx`,
`scikit-learn`, and `numpy` (already present in the dev install).

## Why this is a sampler, not the production layout

For a real shipped layout we'd swap:

- spectral → **node2vec** (random-walk based; sharper cluster separation)
- TF-IDF → **sentence-transformer embeddings** (semantic similarity, not bag-of-words)
- both → **UMAP** for the 2D reduction (preserves local + global structure better than SVD)

This sampler intentionally uses sklearn primitives so it runs with zero new
dependencies and is fast to iterate on.
