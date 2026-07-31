---
name: ev-link-validation
description: >
  Phase 4 of the Gaia evidence verification pipeline. Checks every URL in the evidence data lake for HTTP liveness — catches dead links (404, 403, timeout, connection errors) before evidence is ingested into the registry. Use this skill when running the full /ev-pipeline, asked to "validate links", "check evidence URLs", "run link validation", "find dead links in the data lake", "check HTTP status of evidence sources", or "verify evidence links still work". Wraps validate_sources.py as a temporary coexistence URL-health shim.
---

# Link Validation (ev-link-validation)

Phase 4 validates URL health after by-type collection, live star verification, and adversarial audit.

## Type-First Evidence Lake Contract (#1148)

The evidence lake is **type-first**. The primary working set is `evidence/by-type/<canonical-evidence-type>.md`. Legacy `evidence/tier_*.md` files may still exist as coexistence artifacts, but they are **not** the semantic routing key.

## Coexistence Shim

`evidence/scripts/validate_sources.py` intentionally remains a temporary coexistence URL-health shim. Until it is replaced, use it for URL liveness checks but interpret/report results against the type-first lake: `evidence/by-type/` is primary, and `tier_*.md` is compatibility-only.

```bash
python evidence/scripts/validate_sources.py
```

For a small sample:

```bash
python evidence/scripts/validate_sources.py 10
```

## Output

Write Firecrawl validation findings to the verification report and append a summary to the source report. Do not commit generated validation reports without human approval. Hand only live, correctly scoped rows to ingestion.
