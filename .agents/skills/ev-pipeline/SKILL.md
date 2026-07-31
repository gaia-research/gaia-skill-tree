---
name: ev-pipeline
description: >
  Top-level orchestrator for the Gaia Skill Tree evidence verification pipeline. Run this when you want to do a full evidence pass — collecting raw sources, verifying live GitHub star counts, adversarially auditing for quality/formatting issues, and checking that every URL is reachable — all in one coordinated sequence. Trigger phrases: "run the evidence pipeline", "full evidence pass", "verify evidence", "evidence verification pipeline", "run ev-pipeline", "check all evidence", "audit the data lake", "evidence quality sweep", "refresh evidence", "validate evidence sources". Also aliased as /evidence-verification-pipeline. Use the individual sub-skills (ev-collection, ev-star-verification, ev-adversarial-audit, ev-link-validation) only when you need to re-run one phase in isolation; for end-to-end work, always start here.
---

# Evidence Verification Pipeline (ev-pipeline)

Orchestrates the evidence verification phases that take raw evidence from collected to audited and link-checked before ingestion. It operates on the `evidence/` data lake only and does not mutate registry files.

## Type-First Evidence Lake Contract (#1148)

The evidence lake is **type-first**. The primary working set for every phase is `evidence/by-type/<canonical-evidence-type>.md` using the canonical evidence vocabulary: `repo-own`, `github-stars-own`, `social-signal`, `benchmark-result`, `arxiv`, `peer-review`, `proxy-containment`, `verifier-attestation`, `fusion-recipe`, and `self-attestation`.

Legacy `evidence/tier_*.md` files may still exist as coexistence artifacts for older tooling, but they are **not** the semantic routing key. New collection, audit, compile, and handoff work must route by evidence type.

```mermaid
graph TD
    Phase0[Phase 0: ev-discovery (skippable)] -->|Append discovered rows| A
    A[Phase 1: ev-collection] -->|Materialize + compile by evidence type| B[Phase 2: ev-star-verification]
    B -->|Verify live stars, no rank repartition| C[Phase 3: ev-adversarial-audit]
    C -->|Audit by-type files| D[Phase 4: ev-link-validation]
    D -->|Validate URL health| E[Source Report & Ingestion Handoff]
```

## Phase Responsibilities

- **Phase 0 — `ev-discovery` (skippable):** searches for new Stage-2 evidence on declared need and appends discovered rows into source inputs for Phase 1. It does not score or rank evidence.
- **Phase 1 — `ev-collection`:** materializes primary partitions under `evidence/by-type/` and compiles `evidence/unified_evidence_lake.md` from those by-type files. It may emit `tier_*.md` only as coexistence output.
- **Phase 2 — `ev-star-verification`:** verifies live GitHub stargazer counts and records stale/inflated metrics. It must not repartition the lake by rank; by-type partitions remain primary.
- **Phase 3 — `ev-adversarial-audit`:** audits by-type files for bad URLs, subjective wording, proxy/source mismatches, stale notes, and star/evidence inconsistencies.
- **Phase 4 — `ev-link-validation`:** validates URL health. `validate_sources.py` remains a temporary coexistence URL-health shim while the lake is type-first.

## Additive loop — no green gate

Evidence is additive, not pass/fail. New rows can arrive from Stage 1 minimum rows (`github-stars-own`, `repo-own`, `self-attestation`) or from skippable Phase 0 discovery (`benchmark-result`, `arxiv`, `peer-review`, richer `social-signal`). The only human gate is L4 at ingestion; Trust Magnitude and rank are recomputed at appraisal time.

## Outputs and Handoff

Generated evidence outputs are review artifacts, not registry mutation. Do not commit generated `evidence/by-type/**`, `evidence/tier_*.md`, source reports, validation reports, unified lake files, seeds, or collector rows without a human gate. For L4-approved intake, pass a reviewed manifest of live, correctly scoped rows to `/gaia-ingest-batch`.
