# Yggdrasil III — Fusion Score and era stamp plan

Status: proposed implementation contract; no runtime, schema, registry, or frontend changes in this planning PR.

## 1. Stack baseline

This plan is based on the full open restoration stack, in merge order:

1. [#1668](https://github.com/gaia-research/gaia-skill-tree/pull/1668) — `dev/yggdrasil-iii-newmeta` → `main`
2. [#1669](https://github.com/gaia-research/gaia-skill-tree/pull/1669) — `dev/steward-sensors-fleet` → `dev/yggdrasil-iii-newmeta`
3. [#1667](https://github.com/gaia-research/gaia-skill-tree/pull/1667) — `fix/trust-magnitude-full-recalibration` → `dev/steward-sensors-fleet`
4. This planning branch → `fix/trust-magnitude-full-recalibration`

The current top is `48ccfd57e`. The implementation must begin from that full-stack state, not from `main`, because Yggdrasil III already establishes the boundary this plan extends: `fusion-recipe` is structural provenance and contributes `0` Trust Magnitude.

## 2. Product decision

Yggdrasil III should expose two independent numeric readings:

| Reading | Question answered | Inputs | Promotion authority |
|---|---|---|---|
| **Trust Magnitude (TM)** | How much corroborating evidence supports this named implementation? | Positive-scoring evidence rows, with the existing witness and diversity rules | Existing TM/Trust Grade gates |
| **Fusion Score (FS)** | How much distinct structure is composed by this capability? | Canonical prerequisite, suite-component, and origin structure | Informational in V1; no star or Trust Grade gate |

Fusion Score is not an Evidence Type, evidence row, Trust Grade ingredient, TM multiplier, or substitute for an Apex predicate. TM must remain unchanged when FS changes. FS must remain unchanged when evidence, stars, Trust Grade, or TM changes while the underlying structure is unchanged.

This supersedes the current sentence in `META.md` §2.1c that says no Fusion/Composition scalar is introduced. The rest of the Yggdrasil III trust ruling remains intact: structural provenance still contributes `0 TM` and does not satisfy TM diversity or independent-witness requirements.

## 3. Fusion Score V1 contract

### 3.1 Canonical inputs

Resolve structure from canonical graph fields, in this order:

1. The starless generic node's `prerequisites`, reached through a Named Skill's `genericSkillRef`.
2. The Named Skill's `suiteComponents`.
3. Explicit `fusion-recipe.origins` only as a compatibility fallback when the same edge is not available from the canonical fields above.

Then:

- deduplicate by canonical skill ID;
- exclude entries whose resolved or inline `role` is `variant`;
- guard cycles even though registry validation should already enforce a DAG;
- exclude the root skill ID itself from the closure and from `N`;
- compute the transitive closure to a declared traversal limit;
- never inspect Evidence Grade, Overall Trust Grade, TM, repository stars, rank, or source freshness.

A Basic with no composed structure has FS `0`. A Fusion or Suite receives a score from its resolved structural closure. Named implementations inherit their generic recipe and may add suite composition; starless generic projections may expose the same structural calculation directly.

### 3.2 Recommended scalar

V1 should reuse the familiar softening curve from the former fusion magnitude, but remove every trust-specific modifier:

```text
N  = distinct non-variant nodes in the resolved structural closure
FS = 0                                      when N = 0
FS = 20 × N                                 when 1 ≤ N ≤ 10
FS = 200 + 20 × sqrt(N - 10)                when N > 10
```

Do **not** apply the former `fusion-recipe` evidence weight (`1.5×`), TM cap, freshness factor, grade filter, set bonus, or Trust Grade threshold. Those belonged to evidence aggregation and would recreate the coupling Yggdrasil III removed. The canonical numeric result is rounded to two decimal places before projection so Python, CLI text, and JSON remain byte-stable.

The scalar should ship with an inspectable breakdown:

```json
{
  "fusionScore": 200.0,
  "fusionScoreVersion": "yggdrasil-iii-v1",
  "fusionBreakdown": {
    "directCount": 5,
    "transitiveCount": 10,
    "maxDepth": 2,
    "nestedSuiteCount": 1
  }
}
```

`fusionScoreVersion` is a formula identifier, not a package version and not decorative cache-bust metadata.

### 3.3 Persistence boundary

The registry persists the structural inputs, not the derived answer.

- Do not add `fusionScore` to Named Skill frontmatter or canonical node JSON.
- Do not run a corpus-wide cache migration or add a Fusion Score input hash.
- Compute FS in one Python authority and serialize it only into generated projections that need it.
- Browser code should consume the generated value and breakdown. It should not carry a second JavaScript formula.

This keeps formula changes rebuildable, avoids another full-registry recalibration, and makes FS structurally independent from the disposable TM cache fields currently being restored in #1667.

## 4. Implementation architecture

### 4.1 Core authority

Create a dedicated module such as `src/gaia_cli/fusionScore.py` rather than placing the new metric in `trustMagnitude.py`.

Recommended public functions:

- `resolveFusionStructure(skill, genericSkillMap, namedSkillMap)`
- `computeFusionScore(skill, genericSkillMap, namedSkillMap)`
- `explainFusionScore(skill, genericSkillMap, namedSkillMap)`

The existing `_fusionRecipeMagnitude`, `_fusionOriginIds`, `_fusionAndSuiteOriginIds`, and Apex graph walkers in `src/gaia_cli/trustMagnitude.py` are useful migration references, but shared graph traversal should move to a neutral structural helper so TM and Apex code do not become the owner of FS.

### 4.2 Projection and CLI surfaces

Initial public surface:

- add FS and its breakdown through `scripts/generateNamedIndex.py` into the generated named index, then let `scripts/build_docs.py` mirror the public projection to `docs/graph/named/index.json`;
- show a clearly separate `Fusion Score` line in skill inspection/appraisal output;
- show FS beside, never inside, the TM breakdown in Skill Explorer and relevant plaques;
- keep the Trust leaderboard and `docs/graph/ledger/data.json` trust-only;
- defer a dedicated Fusion leaderboard until the V1 distribution is reviewed.

Likely implementation touchpoints include `scripts/generateNamedIndex.py`, `scripts/buildApiProjection.py`, the CLI appraisal/inspection path, `docs/js/skill-explorer.js`, and shared plaque rendering. Exact projection ownership must be confirmed before code is written.

### 4.3 Contract documentation

The implementation stack must update together:

- `META.md` — ratify the second scalar and preserve TM's sole trust-promotion authority;
- `CONTEXT.md` — define Fusion Score and ban conflation with TM, Trust Grade, rank, or Evidence Grade;
- `docs/codex/trust-methodology.html` — show two independent lanes and keep `fusion-recipe` at `0 TM`;
- API documentation — declare FS as a computed structural projection;
- tests — lock the independence invariants.

## 5. Yggdrasil III frontend stamp

### 5.1 Canonical placement

Add one global era stamp to the shared site navigation, attached to the Gaia wordmark/diamond-seal group:

- visible text: **`III`**;
- accessible name: **`Yggdrasil III, current registry ruleset`**;
- optional title/tooltip: **`Yggdrasil III`**.

The literal `III` remains visible at mobile width. If horizontal space is constrained, the wordmark may yield before the stamp does; the stamp must not increase the fixed navigation height.

No footer duplicate is required for V1. The Codex/Trust methodology header may repeat the full `Yggdrasil III` label as contextual prose, but the global stamp has one canonical component.

### 5.2 Visual rules

The stamp is registry-era metadata, not a skill rank:

- no star glyph;
- no rank name;
- no `--rank-3`, violet glow, medallion, plaque, or circular badge treatment;
- compact rectangular ledger stamp using `var(--font-mono)`, `var(--text)` or `var(--muted)`, and `var(--border)`/existing neutral surface tokens;
- static treatment with no shimmer or pulse;
- visible focus/hover context only if the stamp links to the Yggdrasil III report.

This prevents `III` from reading as 3★ Evolved while preserving the Hunter's Atlas ledger register.

Likely files are `docs/js/site-nav.js` and `docs/css/styles.css`. The implementation must use existing tokens, avoid hardcoded hex, and verify every shared nav depth.

### 5.3 Entrypoints

This is an addition to an existing global component, not a new page or section.

- Main nav: **touched** — canonical stamp placement.
- Footer: **waived** — duplicate era chrome adds no discovery value.
- Homepage: **waived** — the homepage is frozen and already links to the Yggdrasil III report.
- `window.GAIA_MOUNTS`: **waived** — no new mount.
- Cross-page link: stamp may link to the existing Yggdrasil III report.
- Cache-busting: handled by `scripts/build_docs.py`; never patch query strings manually.

## 6. Delivery slices

Keep the implementation reviewable and stacked on the same integration line:

1. **Contract and core FS engine**
   Ratify docs, add neutral structural traversal, implement the V1 formula and independence tests. No generated corpus churn.
2. **Projection and CLI exposure**
   Add FS to generated named/API projections and appraisal output, then regenerate only deterministic Class S artifacts.
3. **Frontend FS presentation plus `III` stamp**
   Render FS as a peer to TM and add the shared navigation stamp. This is a human-gated frontend PR.
4. **Distribution review and closeout**
   Inspect real FS distribution, confirm no hidden rank/TM coupling, update the Yggdrasil III report, and decide separately whether a Fusion leaderboard or future promotion gate is warranted.

FS remains informational through all four slices. Any proposal to make FS a promotion gate is a later governance decision with its own calibration study.

## 7. Required tests and guards

Core invariants:

- changing only evidence, stars, TM, or Trust Grade does not change FS;
- changing only canonical structure does not change TM;
- Basic/no-structure returns `0`;
- duplicate paths count once;
- `role: variant` never counts;
- generic prerequisites and named suite components both contribute;
- direct/transitive/depth breakdown is deterministic;
- cycles fail closed without hanging;
- Python result equals every generated public projection;
- no frontend code reimplements the FS formula.

Repository checks:

- targeted Fusion Score unit tests;
- existing `tests/test_trust_magnitude.py` and frontend TM parity tests unchanged and green;
- registry/schema mirror checks if contract metadata changes;
- `python scripts/check_nav_mounts.py`;
- rank-vocabulary, hex-color, HTML-sink, and JavaScript syntax guards;
- `python scripts/build_docs.py --check` after deterministic regeneration;
- `git diff --check`.

## 8. Human design gate

The frontend slice changes global visible chrome and Skill Explorer output, so green CI is not merge authority.

Before merge, prepare the repository's design-gate evidence page with:

- before/after shared nav at desktop width;
- before/after shared nav at 390 px mobile width;
- at least one root route and one nested route to prove path-depth behavior;
- Skill Explorer with TM and FS shown simultaneously;
- keyboard focus, screen-reader label, and 200% zoom checks;
- explicit confirmation that nav height and fixed-nav clearance did not change.

Founder approval is required before that frontend slice can merge.

## 9. Decisions locked by this plan vs. deferred

Recommended to lock before implementation:

- FS is structural and independent from TM.
- FS V1 is informational, not a rank gate.
- Structural inputs are canonical; trust/evidence grades are not inputs.
- The derived score is not persisted in registry source files.
- The global stamp visibly says `III` and is accessible as Yggdrasil III.

Deferred until the V1 distribution is available:

- a Fusion Score grade ladder;
- any star-level or Apex gate tied to FS;
- a public Fusion leaderboard;
- formula changes that reward depth or nested suites beyond the published breakdown.
