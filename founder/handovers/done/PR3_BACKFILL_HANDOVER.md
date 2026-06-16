# Handover: PR-3 — Evidence Backfill (class → type + grade) (#646)

**Type:** Data migration · **Branch:** `review/meta/...` (e.g. `review/meta/evidence-backfill`) · **Refs #646**
**Milestone:** Immediate Next 30 Days (#7), due Jul 10 2026.
**Governing spec:** `handovers/TRUST_IMPL_HANDOVER.md` §PR-3 and `handovers/TRUST_MODEL_RFC.md` v2. This file is the execution brief; the master handover wins on any conflict.

## ⚠️ Dependency — the grading-CLI patches must land first (updated 2026-06-14)

**Blocker (Marco, verified):** merged PR-2 (#686) shipped two gaps that block running PR-3 as first written — `gaia dev evidence` only *appends* (re-running over the ~220 entries would duplicate them to ~440), and `evidence_graded` isn't in the schema's timeline `action` enum (so `gaia validate` fails on any graded entry). Full write-up + patch spec: **`handovers/GRADING_CLI_FIXES_HANDOVER.md`**.

PR-3 therefore depends on **both pre-PR-3 patches landing on `main` first**:
- **Patch A** (`schema/`): add `evidence_graded` to the timeline action enum (so validate passes).
- **Patch B** (`cli/`): in-place re-grade for `gaia dev evidence` (so re-grading doesn't duplicate).

Once both are in, PR-3 is **pure `review/meta/` data with no CLI changes** — which also cleanly satisfies the "no CLI changes on the review/meta branch" rule. Branch is `review/meta/`, **not** `cli/`.

## Deliverables

1. **Re-grade every existing evidence entry IN PLACE** via the patched CLI (`gaia dev evidence --update --source <url> --type <t> --trust <n>`) — update the existing record (set type/trustNumber/derived grade, **keep `class`**), never append a duplicate. Do **not** hand-edit `registry/nodes/` — Programmatic-First Policy. Grades are **recomputed from scratch** from a freshly-assigned trust number, **not** copied across from the old `class`. **Verify no count inflation** (≈220 entries in, ≈220 out).

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

Every existing evidence entry carries a `type` and a freshly-derived `grade` (or is explicitly ungraded), updated **in place** via the patched CLI (no duplicate entries; ≈220 in/out) with `evidence_graded` timeline events; all class→type exceptions are enumerated in the PR description; `gaia validate` + full suite + meta-guard all green; `class` values left intact and deprecated.

## What comes after (not this PR)

PR-4 — Actionable reports for #648 (`design/` branch): per-skill rank+tenure, evidence inventory, Overall Trust Grade, and the gap to the next grade/rank. **Trap:** `docs/js/skill-graph.js` bootstrap guard — null-check overlay selectors or the IIFE silently falls back to `FALLBACK_SKILLS` (repo `CLAUDE.md`, PR #365). The PR completing the end-to-end model says `Resolves #646`; PR-4 says `Resolves #648`.
