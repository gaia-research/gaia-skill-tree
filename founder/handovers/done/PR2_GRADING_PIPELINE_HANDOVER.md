# Handover: PR-2 — Grading Pipeline (#646)

**Type:** Feature · **Branch:** `cli/...` (e.g. `cli/grading-pipeline`) · **Refs #646**
**Milestone:** Immediate Next 30 Days (#7), due Jul 10 2026 — **critical path.**
**Governing spec:** `handovers/TRUST_IMPL_HANDOVER.md` §PR-2 and `handovers/TRUST_MODEL_RFC.md` v2 (accepted 2026-06-10; summary on #646 comment 4669151912). This file is the execution brief; the master handover wins on any conflict.

## Status / prerequisites — all met

PR-1 (#659, schema) is **merged and live on main**, verified 2026-06-14:

- `registry/schema/{skill,namedSkill}.schema.json` `evidenceEntry` carries `grade`, `type`, `trustNumber` (and `class`, now deprecated).
- `registry/schema/meta.json`: `evidence.types = [arxiv, repo, github-stars]`, `evidence.gradeThresholds = {S:90, A:80, B:60, C:40}`, `evidence.ultimateGate = {minEvidencedComponents:3, requiredComponentGrades:{S:1, A:2}, componentFloor:"C"}`.

So the grade/type/threshold vocabulary already exists in data — PR-2 wires the **CLI + build pipeline** to it.

## Deliverables

1. **Extend `gaia dev evidence`** with `--type <type>` and `--trust <number>`:
   - `--type` validated against `meta.json` `evidence.types` (list-driven, so #654 can add types without a schema PR). Reject unknown types with a helpful message listing valid ones.
   - `grade` is **auto-derived** from `--trust` via `meta.json` `gradeThresholds` (S≥90, A≥80, B≥60, C≥40; **<40 ⇒ ungraded** — entry is stored and shown but does **not** count toward gates).
   - Keep `--class` **accepted-but-deprecated for one release** — emit a deprecation warning, do not error.
   - Write `trustNumber`, `type`, derived `grade` onto the evidence entry. `class` only if explicitly passed (legacy).

2. **Overall Trust Grade aggregation** in the catalog/build step (`gaia dev build` path):
   - Per-skill accumulation of evidence grades establishing "beyond reasonable doubt" (definition per RFC §Trust). Computed, **not** stored in nodes (Programmatic-First) — materializes only in generated catalogs (`registry/named-skills.json`, `docs/graph/gaia.json`).
   - Suite **ultimate gate** uses the pillar rule from `meta.json.evidence.ultimateGate`: ≥3 components carrying direct evidence, ≥1 graded **S**, ≥2 graded **A**, none below **C**. Non-suite ultimates use the direct-evidence equivalent (≥3 sources, ≥1 S, ≥2 A).

3. **Grade colors** Platinum / Gold / Silver / Bronze (S / A / B / C) added to `src/gaia_cli/formatting.py` **alongside** `RANK_COLORS` — single source for design tokens. Do not fork color definitions elsewhere.

4. **New timeline action `evidence_graded`** (alongside `evidence_added` / `evidence_removed`) so grading is auditable. CLI-writes the timeline event — **never hand-edit** timeline arrays (Programmatic-First Policy / CLI-only timeline rule).

5. **Authorization:** all `gaia dev evidence` mutations stay **Verifier-gated** (`gaia whoami`; `GAIA_OPERATOR_OVERRIDE=1` for CI/bots). Don't loosen the guard.

## Cross-cutting constraints

- **Vocabulary:** read `CONTEXT.md` before any user-facing copy or CLI output. **No rarity-axis references.** New terms (Evidence Grade/Type, Overall Trust Grade, trust number, tenure) landed in CONTEXT.md with PR-1 — reuse them, don't reinvent.
- **Naming:** enum/identifier values are **kebab-case** (`github-stars`, not `stars`); existing camelCase JSON **keys** in schema/meta stay as-is. New `grade` A/B is **not** the old `class` A/B — never read one as the other.
- **Versioning:** bump in lockstep via `gaia release patch|minor` (pyproject / cli-npm / mcp / gaia.json); the pre-commit hook fails loudly if they drift. `class` **removal** is **not** this PR — it lands at the next **major**.
- **Hermes-owned files:** never touch (`STEWARDSHIP_PLAN.md`, `scripts/marketing_engine.py`, `scripts/email_sender.py`, `scripts/share_deliverable.py`, `scripts/generate_adoption_dashboard.py`, `scripts/generate_showcase.py`, `docs/ADOPTION.html`, `docs/SHOWCASE.html`, `docs/WHY-GAIA.md`, `docs/QUICKSTART.md`).
- **Testing:** run the full suite (see `DEV.md`); add unit tests for grade derivation (boundary cases: 39/40/60/80/90), type validation (valid + rejected), the ungraded-doesn't-gate rule, and the pillar gate (pass + each failure mode). Fix any regressions before reporting done.
- **PR hygiene:** `Refs #646` (this is one of several PRs; only the PR that completes the end-to-end model says `Resolves #646`). Move #646 to **In Progress** on board #2 when work starts.

## Definition of Done

`gaia dev evidence <skill> "<url>" --type repo --trust 85` records a B-grade entry with an `evidence_graded` timeline event; `gaia dev build` emits Overall Trust Grade + the pillar-gated ultimate status into the generated catalogs; grade colors render from `formatting.py`; `--class` still works with a warning; full suite green; Verifier gate intact.

**Post-ship obligation (carried from the master handover):** once the gate ships, the Orchestrator opens a **recalibration RFC** ~1 month out to revisit the pillar thresholds against real grade distributions. Note this in the PR description.
