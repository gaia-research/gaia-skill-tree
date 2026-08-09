# Handover: PR-3 — Evidence Backfill (class → type + grade) (#646)

**Type:** Data migration · **Branch:** `review/meta/...` (e.g. `review/meta/evidence-backfill`) · **Refs #646**
**Milestone:** Immediate Next 30 Days (#7), due Jul 10 2026.
**Governing spec:** `handovers/TRUST_IMPL_HANDOVER.md` §PR-3 and `handovers/TRUST_MODEL_RFC.md` v2. This file is the execution brief; the master handover wins on any conflict.

## ⚠️ Dependency — do PR-2 first

PR-3 re-grades existing evidence **through the PR-2 CLI flow** (`gaia dev evidence --type --trust`). It **cannot start until PR-2 is merged** (or at minimum the `--type/--trust` grading path is available on the working branch). Hand this over alongside PR-2, but schedule it second. Branch is `review/meta/` (registry curation), **not** `cli/`.

## Deliverables

1. **Re-grade every existing evidence entry** via the PR-2 CLI (`gaia dev evidence ... --type ... --trust ...`). Do **not** hand-edit `registry/nodes/` — Programmatic-First Policy. Grades are **recomputed from scratch** from a freshly-assigned trust number, **not** copied across from the old `class`.

2. **Legacy type mapping** (provenance only — the *grade* is re-derived independently):
   - `class A → type arxiv`
   - `class B → type repo`
   - `class C → type repo`
   - **Flag exceptions** rather than forcing them (e.g. a `class A` that is clearly a repo, or a stars-based citation → `github-stars`). List every exception in the PR description.

3. **Audit markers:** every backfilled entry notes `(backfilled — class-to-type migration)` per repo convention. If any CLI gap forces a direct edit, document it in the PR description and add the `(direct edit — CLI gap)` marker — never silently omit the timeline/audit trail.

4. **Trust-number assignment:** assign each entry a defensible `--trust` value so the derived grade reflects real evidence quality (arxiv/peer-reviewed → high; credible demo → mid; weak → may fall **ungraded** <40, which is fine — it stays visible but doesn't gate). Capture the rationale/heuristic you used in the PR description so it's reproducible.

## Cross-cutting constraints

- **CI — `meta-guard`:** this PR mutates registry/timeline files, so the meta-guard workflow applies. Bot actors are allowlisted; a human Verifier (4★+ named skill) or `GAIA_OPERATOR_OVERRIDE=1` is otherwise required. Add the `skip-meta-guard` label only as a maintainer override if needed.
- **CI — `branch-scope`:** `review/meta/...` is the correct scope for `registry/` curation. Do not mix CLI source changes into this branch.
- **Vocabulary:** `CONTEXT.md` is the source of truth; **no rarity-axis references**; new grade/type terms already exist (PR-1).
- **Naming:** kebab-case enum values (`github-stars`); new `grade` A/B ≠ old `class` A/B.
- **Hermes-owned files:** never touch (see master handover / repo `CLAUDE.md`).
- **`class` stays valid** (deprecated) until the next major — this PR populates `type`+`grade` but does **not** delete `class`.
- **Testing:** run the full suite and `gaia validate` after the backfill; timeline validation (`scripts/validate_timelines.py`) must stay green. Fix regressions before reporting done.
- **PR hygiene:** `Refs #646`. Move #646 forward on board #2 if not already In Progress.

## Definition of Done

Every existing evidence entry carries a `type` and a freshly-derived `grade` (or is explicitly ungraded), produced through the PR-2 CLI with `evidence_graded` timeline events; all class→type exceptions and any CLI-gap direct edits are enumerated in the PR description; `gaia validate` + full suite + meta-guard all green; `class` values left intact and deprecated.

## What comes after (not this PR)

PR-4 — Actionable reports for #648 (`design/` branch): per-skill rank+tenure, evidence inventory, Overall Trust Grade, and the gap to the next grade/rank. **Trap:** `docs/js/skill-graph.js` bootstrap guard — null-check overlay selectors or the IIFE silently falls back to `FALLBACK_SKILLS` (repo `CLAUDE.md`, PR #365). The PR completing the end-to-end model says `Resolves #646`; PR-4 says `Resolves #648`.

---

## Execution notes (as actually landed — PR #688, 2026-06-14)

**Two PR-2 gaps were found during execution** (fixed in PR-2.5 / #687, which PR-3 stacks on):
1. `gaia dev evidence` was **append-only** — added `--index N` to re-grade an existing entry in place (preserving `class`/`evaluator`/`date`).
2. `evidence_graded` was fired but missing from the schema timeline `action` enum → `gaia validate` failed. Added to both schemas (and their bundled copies under `src/gaia_cli/data/...`).

**What was actually backfilled:** the **220 generic-node** entries in `registry/nodes/`. Heuristic — `type` by host provenance, `trust→grade` by quality tier: arxiv 85→A (103), repo 70→B (114), github-stars 50→C (3). 12 class→type exceptions flagged.

**Known scope gap (deferred, see #689 + `handovers/GRADE_LAYERING_HANDOVER.md`):** the **173 named-skill (`registry/named/*.md`) evidence entries** — the repo-specific, *differentiating* layer — were **not** graded here (the initial `class` scan was JSON-only and missed YAML frontmatter). The catalog/gate also don't yet honor parent→child evidence inheritance. This is the next agent's task, on top of PR-3.
