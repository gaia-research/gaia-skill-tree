# Handover: Grade layering & inheritance for named skills + suite ultimates

**Refs:** #646 (trust model), #689 (design decision — read first), PR #687 (PR-2.5), PR #688 (PR-3 — this builds on it)
**Builds on:** PR-3 evidence backfill (`review/meta/evidence-backfill`). Start from that branch (or `main` once #687 → #688 have merged).
**Governing spec:** `handovers/TRUST_MODEL_RFC.md` v2 + `handovers/TRUST_IMPL_HANDOVER.md`. Issue #689 is the authoritative scope for THIS task.

## Why this exists

PR-3 graded only the **generic-node (parent)** evidence layer (220 entries). The
graded-evidence rollout does **not** honor the documented parent → child
evidence-inheritance model (`src/gaia_cli/evidence.py`): generic refs hold
capability evidence that named skills inherit; named skills add
**implementation-specific (repo) evidence**, which is the *differentiator* between
implementations sharing a parent. Result: suite ultimates read
`ultimateGateStatus: "only 0/3 components carry graded evidence"`, and child grades
ignore inherited parent grades.

## Target design (confirm with Orchestrator before coding — this is the gating decision)

1. Grade **both** layers. Parents = capability/academic evidence (A baseline).
   Children = repo-specific evidence with their **own** trust tiering (the differentiator).
2. A named skill's **effective grade = `overall_trust_grade(inherited_evidence(named, generic))`**
   (own ∪ inherited; the child's own evidence may exceed the inherited floor).
3. The suite gate scores each component by its **child effective grade**, NOT the shared
   parent grade.

## Work items

### A. Code — `cli/` branch (touches `src/` + `scripts/`; use `cli/...`, or `claude/*` if it must span scopes; add `skip-scope-check` if needed)

1. `scripts/generateNamedIndex.py::_inject_trust_grades` (~line 411): compute
   `overallTrustGrade` from `inherited_evidence(entry, generic_node)` (import from
   `gaia_cli.evidence`), not `entry.get("evidence")` alone. Resolve the generic via
   `genericSkillRef`.
2. `src/gaia_cli/grading.py::check_ultimate_gate` + the `generic_skills_map` passed in
   (`generateNamedIndex.py:502`): build a component lookup that resolves each **named**
   `suiteComponents` id to that named skill's **effective (inherited) evidence**, and score
   `_component_grade` from it. (Currently the map is keyed by generic ids, so named component
   ids miss → 0/3.)
3. Fix `scripts/build_docs.py` named-index **write** step: it drops `ultimateGateStatus`
   (the `--check` / `generateNamedIndex.py --out` path keeps it). Until fixed, regenerate the
   index via `python scripts/generateNamedIndex.py` directly. (Infra; can be a separate small PR.)
4. Tests: extend `tests/test_grading.py` / add cases — effective grade = max(own, inherited);
   gate counts named components by child grade; gate floor/S/A logic on real component grades.

### B. Data — `review/meta/` branch, on top of PR-3

Grade the **173 `registry/named/*.md`** evidence entries (YAML frontmatter `class:`) via the
PR-2.5 CLI — **no hand-edits**:

```
GAIA_OPERATOR_OVERRIDE=1 gaia dev evidence <contributor>/<skill> <source> \
    --index <i> --type <t> --trust <n> \
    --notes "<existing notes> (backfilled — class-to-type migration)" --no-build
```

- These are mostly repo-centric (`SKILL.md` in a GitHub repo) → `type: repo`. Define a
  defensible **child** trust tiering (capture rationale in the PR, per spec). Children with
  only a SKILL.md link should NOT auto-reach A/S — that's editorial.
- Preserve `class`; add `(backfilled — class-to-type migration)`; one `evidence_graded`
  timeline event per entry (the `--index` path emits it).
- Find the entries PR-3 missed with `grep -rl "class:" registry/named/`.

### C. Editorial (separate, not this task)

Verifier pass to assign **S** (trust ≥ 90) where real demonstrations justify it. Required for
any suite to actually `passes: true` (gate needs ≥1 S, ≥2 A). A mechanical backfill must not
fabricate S.

## Constraints & gotchas

- **Programmatic-first:** all registry mutations via `gaia dev evidence --index`; never
  hand-edit node/frontmatter fields or timelines.
- **Auth:** export `GAIA_OPERATOR_OVERRIDE=1` for CLI mutations.
- **Branch scope** (`.github/workflows/branch-scope.yml`): schema → `schema/`, src/scripts →
  `cli/`/`infra/`, registry → `review/meta/`. Don't mix; split PRs or use `skip-scope-check`
  (+ `claude-bot` label also bypasses scope & meta-guard).
- **Regenerate catalogs:** after data changes run `python scripts/generateNamedIndex.py` then
  `cp registry/named-skills.json docs/graph/named/index.json`. Do NOT rely on `gaia docs build`
  for the named index (write bug, item A3).
- **Bundled schemas:** if you touch `registry/schema/`, also copy to
  `src/gaia_cli/data/registry/schema/` (exact-compared by `scripts/validate.py::check_meta_sync`).
- **No version bump** in code/data PRs; leave to `gaia release`.

## Definition of done

- `overallTrustGrade` on named skills reflects own ∪ inherited evidence.
- Suite `ultimateGateStatus` reads real component grades (off "0/3"); reason is accurate
  (e.g. "missing required S-grade component") rather than a lookup artifact.
- All 173 named evidence entries carry `type` + `grade` (or explicit ungraded) with
  `evidence_graded` events; `class` intact.
- `gaia validate` green; `python scripts/build_docs.py --check` clean; full `pytest` green
  (note: 7 `test_authz.py` cases fail only when `GAIA_OPERATOR_OVERRIDE=1` is exported — run
  that suite without it).
- Exceptions + child trust-tier rationale enumerated in the PR description.

## Key files

- `src/gaia_cli/evidence.py` — `inherited_evidence`, `merge_evidence`
- `src/gaia_cli/grading.py` — `overall_trust_grade`, `check_ultimate_gate`, `_component_grade`
- `scripts/generateNamedIndex.py` — `_inject_trust_grades` (~411), `generic_skills_map` (~502)
- `scripts/build_docs.py` — `build_named_index` (~481), write-path bug
- `registry/named/**/*.md` — child evidence (173 with `class:`)
- `registry/schema/meta.json` — `evidence.ultimateGate` pillar rule (S:1, A:2, floor C)
