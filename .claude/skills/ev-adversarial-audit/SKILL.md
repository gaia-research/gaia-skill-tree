---
name: ev-adversarial-audit
description: >
  Run this skill for Phase 3 of the evidence verification pipeline — the adversarial audit step. Use when you need to check the evidence data lake for bad data before ingestion: dead links, wrong URL formats (tree/ vs blob/), subjective wording ("elite", "high-quality"), stale migration notes, or skills whose star evidence conflicts with classified evidence level. Triggers on phrases like: "audit the data lake", "adversarial check", "ev-adversarial-audit", "check for noise in evidence", "flag bad evidence", "run the audit phase", "quality check the by-type files", or any reference to Phase 3 of the pipeline.
---

# Adversarial Evidence Audit (ev-adversarial-audit)

Phase 3 audits the evidence lake from a Devil's Advocate perspective before URL health validation and ingestion.

## Type-First Evidence Lake Contract (#1148)

The evidence lake is **type-first**. Audit `evidence/by-type/<canonical-evidence-type>.md` files. Legacy `evidence/tier_*.md` files may still exist as coexistence artifacts, but they are **not** the semantic routing key.

## Audit Target

Split reviewer work across `evidence/by-type/<type>.md` files, not tier files. Suggested sharding:

- Repo/adoption signals: `repo-own`, `github-stars-own`, `social-signal`
- Technical proof: `benchmark-result`, `arxiv`, `peer-review`
- Governance/proxy proof: `proxy-containment`, `verifier-attestation`
- Composition/self proof: `fusion-recipe`, `self-attestation`

## Findings to Flag

- Dead or malformed URLs, including GitHub `tree/` links where a `blob/` source is required.
- Subjective/evaluative wording not supported by the source.
- Evidence type mismatches or legacy alias leakage.
- Star evidence that conflicts with live verification notes from Phase 2.
- Stale migration notes that still treat `tier_*.md` as the semantic working set.

Append concise findings to the source report. Do not mutate registry files.
