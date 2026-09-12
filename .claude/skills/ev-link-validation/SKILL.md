---
name: ev-link-validation
description: >
  Phase 4 of the Gaia evidence verification pipeline. Checks every URL in the evidence data lake for HTTP liveness — catches dead links (404, 403, timeout, connection errors) before evidence is ingested into the registry. Use this skill when running the full /ev-pipeline, asked to "validate links", "check evidence URLs", "run link validation", "find dead links in the data lake", "check HTTP status of evidence sources", or "verify evidence links still work". Wraps validate_sources.py as a temporary coexistence URL-health shim.
---

# Link Validation (ev-link-validation)

Phase 4 validates URL health after by-type collection, live star verification, Phase 2B benchmark-source verification, and adversarial audit.

## Type-First Evidence Lake Contract (#1148)

The evidence lake is **type-first**. The primary working set is `evidence/by-type/<canonical-evidence-type>.md`. Legacy `evidence/tier_*.md` files may still exist as coexistence artifacts, but they are **not** the semantic routing key.

## Coexistence Shim

`evidence/scripts/validate_sources.py` intentionally remains a temporary coexistence URL-health shim. It reads `evidence/by-type/*.md` (primary, type-first) and `evidence/tier_*.md` (compatibility-only) by default (#1786).

```bash
python3 evidence/scripts/validate_sources.py
```

For benchmark rows, include every row/source URL plus catalog-level `sourceUrl`, `methodologyUrl`, `harnessUrl`, attestor URLs, and any candidate manifest methodology/attestor links in the URL-health pass.

For a small sample:

```bash
python3 evidence/scripts/validate_sources.py --limit 10
```

### Targeting an intake's candidate rows (not yet in the lake)

A pre-registry intake's candidate rows aren't in `evidence/by-type/` yet, so the default lake scan won't see them. Point the validator at them directly instead:

```bash
# Plain URL list, one per line
python3 evidence/scripts/validate_sources.py --urls /tmp/intake-urls.txt

# JSON/YAML candidate manifest — bare URL list, {"url": ...} objects, or an
# object with a urls/candidates/entries/rows list of either shape (same
# shape generate_source_dump.py's --candidate-manifest accepts, see
# ev-pipeline)
python3 evidence/scripts/validate_sources.py --manifest /tmp/intake-candidates.json
```

`--urls` and `--manifest` are mutually exclusive; `--limit N` and `--report <path>` apply in every mode.

## Output

Write Firecrawl validation findings to the verification report and append a summary to the source report. Benchmark-source candidates remain candidate-only until Phase 2B findings, adversarial findings, and link-health results are reviewed by a human. For #1418 scratch multi-target peer-review partitions, validate the repeated URL once per reviewed skill row in `peer-review.md` when the source legitimately covers each target; the repetition is expected, not duplicate-noise by itself. Do not commit generated validation reports, scratch manifests, or generated partitions without human approval. Hand only live, correctly scoped rows to ingestion.
