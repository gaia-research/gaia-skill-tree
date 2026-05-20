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

## Layouts

| Key | Method | What it answers |
|---|---|---|
| `spring` | networkx force-directed | Visual baseline. No ML. |
| `spectral` | Laplacian eigenmaps (sklearn `SpectralEmbedding`) | "Skills with similar prerequisite neighborhoods should sit near each other." |
| `semantic` | TF-IDF over `name + description` → TruncatedSVD to 2D | "Skills that *mean* the same thing should sit near each other, regardless of edges." |

Communities are detected once on the structural graph (Louvain) and reused
across all panels so the same color tracks the same cluster as it migrates
between layouts.

## Regenerating

```bash
python docs/experiments/ml-graph-viz/build_layouts.py
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
