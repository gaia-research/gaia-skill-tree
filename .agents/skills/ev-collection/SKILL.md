---
name: ev-collection
description: Collects raw evidence sources from different channels (GitHub, YouTube, arXiv, blogs) for all named skills in the registry.
---

# Evidence Collection (ev-collection)

This skill coordinates the aggregation of raw proof vectors from multiple primary channels to populate the evidence data lake.

## Context

Raw source evidence for skills in the Gaia Registry is compiled from:
1. Primary GitHub Repositories (and stargazer metrics).
2. Showcase Videos (developer screen captures, demos, and presentations).
3. Academic/Scientific Publications (arXiv preprints, papers, conference slides).
4. Developer Blogs & Newsletters (tutorials, community guides, ecosystem integrations).

## Workflow

1. Gather raw inputs from active contributors and collectors under `evidence/collectors/`.
2. Consolidate these sources into the master `unified_evidence_lake.md` index.
3. Run the compiler script to align metadata structures:

```bash
.venv/bin/python evidence/scripts/compile_data_lake.py
```
