# Handover: Trust Model Implementation — #646 + #648

**Status:** FINAL — approved 2026-06-10, all decisions resolved. Ready for a Claude Code session / coding agent.
**Governing spec:** `handovers/TRUST_MODEL_RFC.md` v2 (accepted 2026-06-10; summary on #646, comment 4669151912).
**Milestone:** Immediate Next 30 Days (#7), due Jul 10 2026.

## Current schema reality (verified against the repo, 2026-06-10)

- `registry/schema/skill.schema.json` and `namedSkill.schema.json` both define `evidenceEntry`: required `class` (enum A/B/C — A "peer-reviewed", B "reproducible demo", C "credible demo"), `source` (URI), `evaluator`, `date`; optional `notes`, `verified` (4★ Verifier), `disputed`, `verificationSource`.
- In practice `class` encodes provenance (A≈arxiv, B≈repo) — exactly the conflation the RFC kills.
- `registry/schema/meta.json`: `evidence.classes [A,B,C]`, `ultimateMinSources: 3`, `ultimateRequiredClasses: [A,B]` — these gates reference classes and must be re-expressed.
- Timeline actions include `evidence_added` / `evidence_removed`.
- Tier/rank colors are centralized in `src/gaia_cli/formatting.py` (RANK_COLORS).

## PR plan (split; each lands separately)

### PR-1 — Schema (`schema/...` branch — MANDATORY for `registry/schema/` changes)

In both `skill.schema.json` and `namedSkill.schema.json` `evidenceEntry`:

- Add `grade`: enum **S / A / B / C** (quality, derived from trust number). Evidence with trust number **below 40 gets no grade** (ungraded — present but doesn't count toward gates).
- Add `type`: string, validated against a list in `meta.json` (initially `arxiv`, `repo`, `github-stars`) — list-driven so #654 can extend types without another schema PR. **Type values are kebab-case** per repo convention; `github-stars`, not `stars` (avoids collision with the ★ rank vocabulary).
- Add `trustNumber`: number (internal input to grade; not user-facing).
- Mark `class` **deprecated** in description; stays valid until the **next major release**, removed then (decided 2026-06-10).
- `meta.json`: add `evidence.gradeThresholds` — **S ≥ 90, A ≥ 80, B ≥ 60, C ≥ 40, ungraded < 40** (decided 2026-06-10) — and `evidence.types` list; ultimate gate re-expression pending the suite-gate decision (§Open decisions).
- **Update `CONTEXT.md` in this PR**: add the new terms (Evidence Grade, Evidence Type, Overall Trust Grade, trust number, rank tenure, verification levels) — ensure clarity and no clashes with existing vocabulary or the banned-synonym list (CI greps it).
- **Naming collision warning:** new `grade` A/B ≠ old `class` A/B. Migration code must never read one as the other.
- Skill-level **Overall Trust Grade and rank tenure are computed, not stored in nodes** (Programmatic-First; tenure derives from existing timeline events) — they materialize only in generated catalogs (`named-skills.json`, `docs/graph/gaia.json`) via the build pipeline.

### PR-2 — Grading pipeline (`cli/...` branch)

- Extend `gaia dev evidence` with `--type` and `--trust <number>`; grade auto-derived from `meta.json` thresholds. Keep `--class` accepted-but-deprecated for one release (warn).
- Overall Trust Grade aggregation implemented in the catalog/build step (`gaia dev build` path), definition per RFC: accumulation of evidence grades that establishes "beyond reasonable doubt".
- Add grade colors Platinum/Gold/Silver/Bronze (S/A/B/C) to `formatting.py` alongside RANK_COLORS — single source for design tokens.
- New timeline action `evidence_graded` (alongside `evidence_added`/`evidence_removed`) so grading is auditable; CLI-only, no hand-edits.
- All mutations remain Verifier-gated (`gaia whoami`; `GAIA_OPERATOR_OVERRIDE=1` for CI).

### PR-3 — Backfill (`review/meta/...` branch)

- Re-grade existing evidence via the PR-2 CLI flow. Legacy mapping: `class A → type arxiv`, `class B → type repo`, `class C → type repo` (flag exceptions); grades recomputed from scratch, not copied from classes.
- Every backfilled entry notes `(backfilled — class-to-type migration)` per repo convention; gap-forced direct edits documented in the PR description.
- meta-guard CI applies (registry mutations); bot actors are allowlisted.

### PR-4 — Actionable reports, #648 (`design/...` branch)

Per-skill report on the site: current rank + tenure ("held [rank] since [date]"), evidence inventory (type, grade, verified/disputed flags), Overall Trust Grade, and the explicit gap to the next grade/rank; staleness and dead-link flags. **Known trap:** `docs/js/skill-graph.js` bootstrap guard — null-check overlay selectors or the IIFE silently falls back to FALLBACK_SKILLS (see repo CLAUDE.md, PR #365).

## Cross-cutting constraints

- Vocabulary from `CONTEXT.md` before any user-facing copy; **no rarity-axis references**. CONTEXT.md gains the new schema terms in PR-1.
- Version lockstep via `gaia release` (pyproject / cli-npm / mcp / gaia.json). `class` removal lands with the next **major** release.
- Never touch Hermes-owned files.
- Identifiers and enum values are **kebab-case** per repo convention (e.g. `github-stars`); existing JSON key style (camelCase keys in meta.json/schemas) stays consistent with what's already there.
- PR hygiene: `Refs #646` on PR-1/2/3 individually; the PR that completes the end-to-end model says `Resolves #646`. PR-4 says `Resolves #648`. Issues move to In Progress on board #2 when work starts.

## Open decisions

- [x] Trust-number bands — **S ≥ 90, A ≥ 80, B ≥ 60, C ≥ 40, ungraded < 40** (Marco, 2026-06-10).
- [x] `class` removal — deprecated now, **removed at next major release** (Marco, 2026-06-10).
- [x] **Ultimate gate for suites** — **Option 1, pillar rule** (Marco, 2026-06-10): ≥3 components carrying direct evidence, ≥1 graded S, ≥2 graded A, no component below C. meta.json shape: `ultimateGate: { minEvidencedComponents: 3, requiredComponentGrades: { "S": 1, "A": 2 }, componentFloor: "C" }`. Non-suite ultimates: direct-evidence equivalent (≥3 sources, ≥1 S, ≥2 A).

**Post-implementation obligation (part of this handover):** after the gate ships, open a **recalibration RFC issue** targeting ~1 month out (once the meta settles) to revisit the pillar thresholds against real grade distributions. The implementing agent includes this in the final PR description; the Orchestrator drafts the RFC issue at that time.

Options considered for the record:

| Option | Gate | Trade-off |
|---|---|---|
| 1. Pillar rule (recommended) | ≥3 components carrying direct evidence, of which ≥1 graded S and ≥2 graded A; no component below C | Closest to today's `ultimateMinSources: 3` + classes A/B semantics; easy migration; floor blocks junk-padding |
| 2. Weakest link | suite grade = min(component Overall Trust Grades); gate = min ≥ A | Simplest to explain; brutal on large suites — one weak component sinks an otherwise great ultimate |
| 3. Coverage ratio | all components ≥ B, ≥50% ≥ A, ≥1 S | Scales with suite size; ratio needs calibration per suite-size band |
| 4. Aggregate + floor | suite trust number = median of component trust numbers, gate ≥ 80 (grade A), floor: none below C | Most "honest" mathematically; reintroduces a numeric aggregate, slightly against the no-numbers spirit |

Proposed meta.json shape for option 1: `ultimateGate: { minEvidencedComponents: 3, requiredComponentGrades: { "S": 1, "A": 2 }, componentFloor: "C" }`. Non-suite ultimates fall back to the direct-evidence equivalent (≥3 sources, ≥1 S, ≥2 A).
