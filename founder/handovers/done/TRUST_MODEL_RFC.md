# RFC: GAIA Trust Model — Ranks + Evidence Grades (not numeric trust scores)

**Status:** v2 — ACCEPTED 2026-06-10 (Marco's decisions in chat). Summary posted to #646 (comment 4669151912). Evidence-types question spun out to sub-issue #654.
**Supersedes:** the numeric trust-score formula in #646's issue body (v2 roadmap weights).
**Governs:** #646, #648, #650, the future verification-workflow issue.

---

## 1. Problem (unchanged)

Numeric 0–100 trust scores are arbitrary and unscientific even with a formula; every registry has one; "56 out of 126" is not actionable. DXOMark lesson: ceilings drift. Antutu lesson: raw cross-skill comparison fails because skills are repo-dependent and capability-varied. GAIA already has ranks that inherit tiers and evidence markers.

## 2. The Model (decided)

### 2.1 Ranks are the trust signal

No skill-level numeric trust score is exposed. The rank IS the trust statement.

### 2.2 Evidence types ≠ evidence grades (overhaul of the old tier system)

Before: evidence tier conflated provenance with quality (tier A = arxiv, tier B = repo).

After — two orthogonal axes:

| Axis | Values | Notes |
|---|---|---|
| **Evidence Grade** | S / A / B / C | Design colors Platinum / Gold / Silver / Bronze; derived from an underlying trust number |
| **Evidence Type** | arxiv, repo, stars (proxy); more TBD | Open RFC → sub-issue #654 (candidates: community posts, YouTube/Instagram views) |

**Overall Trust Grade** (per skill): accumulation of the gathered evidence to paint the picture that, beyond reasonable doubt, this is a good skill.

### 2.3 Rank tenure — display-only

Tenure ("held rank X since Y") is tracked and displayed. **No regression**: tenure never demotes.

### 2.4 Everything is skill-level

No repo-level trust in v1. Repositories exist only as evidence providers for skills.

### 2.5 #648 = actionable reports

Per skill: current rank + tenure, evidence inventory with grades, Overall Trust Grade, and the exact gap (which evidence at which grade) to the next grade/rank. Flags: stale evidence, dead links, unreproduced claims.

### 2.6 Certification tiers (#650)

Threshold predicates over Overall Trust Grade + tenure (+ security scan from #185 for the top tier). Define after the grade calibration exists.

## 3. Out of scope (logged futures)

Token-savings metric (no telemetry; possible separate repo), Antutu-style cross-skill benchmarks (#649 design must account for repo-dependence).

## 4. Implementation handover outline (next deliverable)

1. **Schema** (`schema/` branch): evidence `grade` (S/A/B/C) + `type` fields replacing the conflated tier; underlying trust-number field; skill-level Overall Trust Grade; tenure derivable from existing timeline events. Vocabulary check against CONTEXT.md; no rarity references.
2. **Grading pipeline** (`cli/` or `infra/` branch): trust-number → grade mapping; Overall Trust Grade aggregation; via `gaia dev` flows (Programmatic-First, Verifier-gated).
3. **Backfill**: existing evidence re-graded; legacy tier A/B mapped provisionally (arxiv→type, repo→type; grades recomputed).
4. **Reports** (#648, `design/` branch): actionable report rendering.

PR hygiene: `Resolves #646` on the scoring/schema work only when the model lands end-to-end; otherwise `Refs`. Milestone 7 due Jul 10.

## 5. Decisions — RESOLVED 2026-06-10

- [x] Grades vs classes → overhauled: types and grades are separate axes (§2.2).
- [x] Names → grades S/A/B/C with Platinum/Gold/Silver/Bronze design colors; types remain RFC (#654).
- [x] Tenure → display-only, no regression.
- [x] Repo-level trust → none; skill-level only.
- [x] Post summary to #646 → posted (comment 4669151912).
