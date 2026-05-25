# DO NOT DELETE!

`embeddings.json` contains 384-dim sentence-transformer vectors (all-MiniLM-L6-v2) for all 211 registry skills.

It is required by `scripts/build_layouts_3d.py` to compute the 4D PCA semantic layout in the 3D graph. Without it, the Semantic mode falls back to the same positions as Deterministic (flat line).

To regenerate: re-run the embedding script after adding new skills, then `python scripts/syncDocsGraphAssets.py`.
