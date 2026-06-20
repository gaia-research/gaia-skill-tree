---
title: "Per-Evidence Row Grading is Live"
author: "Gaia Registry"
summary: Evidence rows now carry individual S/A/B/C grades computed from per-type artifact_score floors. arxiv and peer-review are now S-capable — top cited papers earn Platinum.
abstract: |
  The Evidence Library and per-skill evidence panels have been redesigned to surface the quality of each individual evidence source. Previously, grade pills in the Evidence Library showed only "—" because the per-row grading system was calibrated against unbounded artifact_score values unreachable via the trustNumber proxy. After Opus-assisted recalibration of per-type S floors and lifting the gradeCeiling for arxiv and peer-review to "S", 33 rows were upgraded in the migration — including foundational AI papers (dspy, few-shot-learning, self-consistency) and Nature/Science peer-review entries reaching Platinum.
label: Evidence Update
---

## Abstract

The Evidence Library and per-skill evidence panels have been redesigned to surface the quality of each individual evidence source. Previously, grade pills showed only "—" because per-row floors were calibrated against unbounded artifact_score values unreachable via the trustNumber proxy. After Opus-assisted recalibration and ceiling lifts, 33 rows upgraded — foundational AI papers and Nature/Science peer-review entries now reach Platinum (S).

## What Changed

### Grade Threshold Recalibration

Per-type S floors were recalibrated to p85–p95 of observed trustNumber distributions:

| Type | Old S floor | New S floor | Ceiling |
|------|------------|------------|---------|
| github-stars-own | 140 | **88** | S |
| benchmark-result | 98 | **90** | S |
| verifier-attestation | 94 | **90** | S |
| arxiv | — (capped at A) | **95** | **S** (lifted) |
| peer-review | — (capped at A) | **88** | **S** (lifted) |

arxiv and peer-review `gradeCeiling` was lifted from `"A"` to `"S"`. A 500-citation paper (artifact_score = 100) or a Nature-published skill with 3+ reviewers (artifact_score ≈ 90) now legitimately earns S.

### Migration Results

Running `gaia dev calibrate-evidence-grades` with new thresholds produced **33 upgrades, 0 errors**:

- **arxiv → S**: dspy (`arxiv.org/abs/2310.03714`), few-shot-learning, self-consistency
- **peer-review → S**: gnomad database, GTEx database, Human Protein Atlas, InterpPro, JASPAR, OpenTargets, PubChem, PyMOL, Reactome, and 12 other Nature/NAR/Science entries
- **github-stars-own → A**: graphify

### Evidence Library Redesign

The `/evidence/` page was fully redesigned:

- **Dynamic type tabs**: All 10 canonical evidence types now appear as filter tabs (built from actual data, not hardcoded)
- **Type normalization**: Legacy `"repo"` and `"github-stars"` aliases mapped to `"repo-own"` and `"github-stars-own"` consistently
- **Trust score column**: Each row now shows `trustNumber` alongside grade, source, evaluator, and date
- **Metrics chips**: Rows with `stars`, `views`, `citations`, `reviewers`, or `commits` surface those numbers as chips below the source link
- **All 10 type pills styled**: Each canonical type has a distinct color token (fusion-recipe = amber, arxiv = purple, peer-review = sky, social-signal = emerald, etc.)

### Per-Skill Evidence Cards

The evidence section in the named skill modal was redesigned from a flat grade-bar to rich cards:

- **Grade square** (32×32px metallic) at left
- **Type pill + source link + trust score** on top row
- **Evaluator + date** on meta row
- **Notes** as italic block with left border
- **Metrics chips** (stars, views, citations, reviewers, commits)
- **Fusion-recipe origins**: component skill chips for fused skills

## Verification

- `pytest tests/test_row_grading.py` — 35 tests pass, covering new S-grade paths for arxiv and peer-review
- `gaia dev calibrate-evidence-grades --dry-run` → 0 diffs after migration (idempotent)
- Evidence Library `/evidence/` — Platinum tab shows rows; all 10 type tabs present; trust score column visible
- Named skills modal → Evidence section shows typed cards with grade squares, type pills, and trust scores

## References

[1] RFC §2.4 — Star Bar calibration. `registry/META.md`

[2] Trust Magnitude specification. `docs/codex/trust-methodology.html`

[3] Per-row grade thresholds. `registry/schema/meta.json#perRowGradeThresholds`
