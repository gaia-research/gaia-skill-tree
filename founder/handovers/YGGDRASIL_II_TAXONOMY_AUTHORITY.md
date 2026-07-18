# Yggdrasil II — Taxonomy Resolution Authority (Build-Time Cut)

**Status:** Ratified 2026-07-18 (founder: Marcus Tiongson). Lands inside EPIC #1002 before `dev/yggdrasil-ii-staging` → `main` (PR #1185).
**Root issues closed:** #1228, #1229, #1230, #1231 (design-framed cluster) + #1220–#1225 (dry-run sweep) + finishes #998.
**Integration branch:** `dev/yggdrasil-ii-staging`. All feature branches PR into it, never `main`.

---

## 1. The problem (verified on staging, 3 scouts, 2026-07-18)

Yggdrasil II's design chose **read-time branch derivation** — the `skill-semantics.js` header enforces it as rubric E1: *"branch MUST be derived at read-time — NEVER from a stored branch/tier field."* That choice forces the derivation logic to physically exist in every runtime that renders, hand-kept identical. It isn't. There are **FOUR resolvers with no shared code path**, already structurally drifted:

| # | Resolver | Location | Reads | Output | Note |
|---|---|---|---|---|---|
| 1 | JS `computeBranch(node, effRank)` | `docs/js/skill-semantics.js` | `type==='basic'`, `suiteComponents`, `effRank ?? level` | `standard\|suite\|unique` + rank words | declared "single source of truth" |
| 2 | JS `resolveSemantics(node, effRank, metaIsYggI)` | `docs/js/world-tree-layout.js:356-413` | same predicate + `metaIsYggI` fork | `{hemisphere, coreness, isUnique, isSuite, glyph, boughGroup}` | **no rank ladder; extra Ygg-I fork #1 lacks** |
| 3 | Python `computeBranch(named, genericSkillMap)` | `src/gaia_cli/trustMagnitude.py:1283-1310` | `suiteComponents` + rank; **never `type`** | branch string | diverges from #1 (ignores `type`) |
| 4 | Python `rank_word(level, branch)` | `src/gaia_cli/formatting.py:384-401` | `meta.LEVEL_LABELS_SUITE` + hardcoded UNIQUE | rank word | 4th copy of the ladder |

Plus stale Ygg-I enum code in `scripts/generateProjections.py` (`get_tier_symbol`, `_build_skill_display` branch on `type == 'ultimate'/'unique'/'extra'` — matches ZERO nodes post-#997).

**Read order in #1 (must be preserved when porting):**
1. `type === 'basic' && rank >= 4 && !hasSuiteComponents` → `unique`
2. `hasSuiteComponents` → `suite`
3. else → `standard`

**Rank ladders (canonical, from #1):**
- SHARED: `{0 Basic, 1 Awakened, 2 Named, 3 Evolved}`
- SUITE: `{4 Extra, 5 Ultimate, 6 Apex}`
- UNIQUE: `{4 Unique, 5 Unique Ultimate, 6 Unique Impossible}`
- BANNED anywhere: `Transcendent`, `Hardened` (enforced by `check_rank_vocabulary.py`).

## 2. The decision

Reverse rubric E1. **One build-time authority resolves branch/rank/medallion; consumers read the resolved field; all four resolvers are deleted.**

- **Authority module:** `src/gaia_cli/taxonomy.py` (new). Exposes:
  - `normalize(entry, metaEpoch)` — the ONLY meta-version-aware code. Ygg I/II/III forks live here and nowhere else. Maps any-era shape → one canonical internal shape.
  - `resolveDisplayBranch(normalized) -> 'standard'|'suite'|'unique'` — the single branch resolver (port #1's read-order exactly).
  - `rankWord(level, branch)` / `rankLabel(level, branch)` — the single ladder.
  - `medallion(branch, rank)` — resolved art token.
  - **Absent-field fallback (CLI-compat, scout #4):** the resolvers MUST accept both a pre-resolved entry (reads the emitted `branch`/`rank` field) AND a raw entry (field absent → derive). The fallback lives *inside* `taxonomy.py`, so it satisfies the §4 grep guard while letting a stale bundled wheel snapshot (patch releases never refresh the bundle) render correctly before the user's first `gaia pull`. Never hard-index a resolved field anywhere downstream.
  - Gating (`passesApexGate`) STAYS in `trustMagnitude.py` — scout confirmed it is already display-independent (1/10 difficulty; do NOT merge it into the display resolver). This is the deliberate "branch-for-display vs branch-for-gating" split.

- **Emission home:** the **named index** — `registry/named-skills.json` → `docs/graph/named/index.json`. This is where `suiteComponents` + per-variant `level` co-exist (they are NOT on `gaia.json` generic nodes) and is the same source the three SSR generators already read. Resolving here collapses the frontend AND SSR resolvers at once.

- **Backwards-compat:** by construction. A Ygg I `type:'ultimate'` node and a Ygg II `type:'fusion'` node both pass through `normalize()` to one shape; everything downstream is meta-version-blind. Ygg III = edit `normalize()` + the ladder table, regenerate, done. One file, one runtime.

## 2.5 Closeout strategy (ratified 2026-07-18 after 8-scout blast-radius sweep)

**The call: build-first, unchanged.** The miss-list (§6) didn't crack the foundation — it mapped the cliffs. We now know where "site-dark" lives *before* we build. The architecture, emission home, 4-phase shape, #1227 rewind, and landing inside #1002 are all UNCHANGED. Two guardrails and one principle changed. That's it.

**Three additions:**

1. **Additive wire format (Phase 2 invariant).** We *add* `branch`/`rank`/`medallion`; we **never remove or rename** raw `type` or `contractVersion`, and never rename the `registry/` source field names. gaia-mcp fail-closes *every* fetch if `type` or the contract string moves; gaia-research's vendored sync (`scripts/craft/sync-skill-tree.ts:36`) breaks on field renames. One sentence to honor, one downed integration if forgotten.

2. **Delete-gate (between Phase 2 and Phase 3, not a new phase).** No resolver is deleted until CI proves it safe: (a) the grep guard for read-time derivation (`type ===`, branch-word literals) returns **zero** outside `taxonomy.py`; and (b) the additive-wire contract test confirms gaia-mcp / gaia-research still parse the output. Converts "we hope the rewire list is complete" into "CI won't let us delete until it provably is."

3. **Completeness via grep, not checklist (Phase 1 mandate).** We missed 8 derivers because hand inventories are never exhaustive. So the contract test asserts per-node parity against *every* live resolver (the completeness oracle), and the grep guard *finds* stragglers mechanically. We stop maintaining a longer list; CI maintains it.

**Scope line:** the grep guard covers **production `docs/` only**. `docs/experiments/` and `docs/samples/` are EXCLUDED with a one-line comment in the guard + a tracking issue ("sample/experiment surfaces still derive from dead `type`; out of scope for the authority cut"). Honors the "disclose the bridge state" convention without inflating Phase 3 to touch throwaway demos.

**Sits outside this refactor (flagged, not folded):** (a) banned-word **prose** cleanup across `docs/en/*` + samples — separate copy task, own issue; (b) patch-wheel snapshot staleness (§6 item 4) — release-sequencing, handled at release time via the co-release-in-one-minor rule + the `taxonomy.py` fallback below.

## 3. Phases (each = one feature branch → staging)

### Phase 1 — Authority module + contract test (`cli/ygg2-taxonomy-authority`)
- Write `src/gaia_cli/taxonomy.py` with `normalize`/`resolveDisplayBranch`/`rankWord`/`rankLabel`/`medallion`. Port the agreed logic from resolvers #1 and #3; unit-test BOTH Ygg I and Ygg II input shapes.
- **Contract test** (`tests/test_taxonomy_contract.py`): for every node/named entry on staging, assert `taxonomy.resolveDisplayBranch` == JS `computeBranch` == Python `trustMagnitude.computeBranch` == `resolveSemantics` isUnique/isSuite. This makes the *current* four-way drift a RED build and guarantees the port is faithful before anything is deleted. (Node the JS side via a small harness or a golden-file dump — do not hand-transcribe.)
- **Completeness oracle (Phase 1 mandate, §2.5 principle 3):** the contract test is the completeness mechanism — it asserts per-node parity against *every* live resolver, so a resolver we forgot to port shows up as a parity failure, not a silent survivor. Do NOT rely on the §6 miss-list as a hand checklist; it is a snapshot. The grep guard (§4) + this parity test are what actually enforce completeness. When new derivers are found (as 8 were on 2026-07-18), they get added to the parity cross-check, not just to prose.
- Nothing consumes the module yet. Pure add + test.

### Phase 2 — Emit resolved fields (`cli/ygg2-emit-resolved`)
- Thread `taxonomy.py` through the build so `docs/graph/named/index.json` carries resolved `branch`/`rank`/`rankWord`/`medallion` per variant; also thread `suiteComponents` into the index (closes #1229).
- **ADDITIVE WIRE FORMAT (invariant, §2.5 principle 1) — do not violate:** this phase ONLY adds fields. Never remove or rename raw `type`; never change `contractVersion` (keep `"gaia-public-v1"`); never rename the `registry/` source field names (`id`/`title`/`description`/`genericSkillRef`/`level`/`contributor`). gaia-mcp (`src/data/source.ts:9-12`, `z.string().min(1)` on `type`) fail-closes EVERY fetch if `type` or the contract string moves; gaia-research's vendored sync (`scripts/craft/sync-skill-tree.ts:36`) breaks on a field rename. Dropping raw `type` after everyone reads resolved fields is a FUTURE breaking change requiring gaia-mcp coordination — not part of this cut.
- **Ordering signal (added 2026-07-18, scout-confirmed):** the resolved index field MUST carry the fusion-weight / suite-ordering signal, not just the `branch` label — the tree.md generator sorts suites biggest-fusion-first (`_sorted_ults`) and must be able to do so reading the index alone, without a local resolver. Emit whatever `_sorted_ults` needs (rank + fusion weight) as a resolved field.
- **HONOR #798:** every step that does `rmtree(committed Class S) + copytree(from gitignored Class P)` must replicate `build_badges`' count-drop abort guard (`scripts/build_docs.py:1112-1152`). Steps missing it: `build_api_projection`, `build_profile_pages`, `build_og_cards`, `build_trending`. Add a sanity floor before any new resolved artifact goes through the swap.
- Full `gaia dev docs` regen; commit Class S (`docs/graph/*`) + source in the same PR (Guard E).
- On Windows: `PYTHONPATH=./src python -m gaia_cli dev docs`; prefix `PYTHONIOENCODING=utf-8` for validators (cp1252 glyph crash).

### Phase 3 — Collapse consumers + rewind #1227 (`design/ygg2-consumers-resolved`)
- **⟨DELETE-GATE⟩ (§2.5 principle 2) — BLOCKS the deletions in this phase.** No resolver is deleted until CI proves it safe: (a) the grep guard for read-time derivation (`type ===` / branch-word literals) returns **zero** hits outside `taxonomy.py` in production `docs/` (see §4 scope line); AND (b) the additive-wire contract test confirms gaia-mcp / gaia-research still parse the emitted output. Repointing precedes deletion; deletion is gated on green. This converts "we hope the rewire list is complete" into "CI won't let us delete until it provably is."
- **Release sequencing (§6 item 4):** the Phase 2 emit and this phase's consume SHOULD land in the same minor (vX.Y.0) — patch wheels never refresh the bundled snapshot. The `taxonomy.py` absent-field fallback (§2) is the defense-in-depth that keeps a stale snapshot rendering if they ever split across releases.
- Repoint the 3 SSR generators (`generateBadges.py` skill_branch, `generateOgCards.py` og_branch, `generateProfilePages.py` skill_branch) to read the resolved field from the index; delete their local branch derivation and the `trustMagnitude.computeBranch` + `formatting.rank_word` duplication.
- **tree.md generator (added 2026-07-18, scout-confirmed GAP — HIGH severity):** `scripts/generateProjections.py` (`branch_of` L145, `_sorted_ultimates` L264, writes `skill-trees/<user>/skill-tree.md` L582 + `docs/tree.md` L561) and `scripts/_tree_renderer.py` (`branch_of` L69, `_sorted_ults` L186) were NOT in the original rewire list but carry the D14-added local resolver. Repoint both to read the resolved `branch`/`rank`/ordering field from the index; delete `branch_of` / `_fusion_weight` / `_sorted_ultimates` / `_sorted_ults` local derivation. **If skipped, discarding D14 collapses `docs/tree.md` + every per-user `skill-tree.md` to Basics-only** (fallback selects dead `type=="ultimate"`, which matches zero Ygg II nodes) — the exact total-collapse regression D14 fixed, not merely stale ordering.
- Repoint JS consumers to read resolved fields, then **DELETE** `skill-semantics.js::computeBranch`, the branch predicate + ladder in `resolveSemantics`. Consumer rewire list (staging-verified): `plaque.js` (L71,78,172), `named-skills.js` (L190-191,572,655,732), `skill-explorer.js` (31 sites: L1316,1362-1369,1421,1523,1568,1589,2237,2506), `skill-graph.js` (L1734 via nodeMeta.glyph).
- **Expanded rewire list (added 2026-07-18, 8-scout 2nd-pass — production surfaces):** the original list undercounted. Also repoint: `skill-graph.js` extra derivers (L43,409-410,736,1106 — raw `type`→rank/bucket beyond L1734); `page-ia.js` (L102,107,239-259,299 — homepage Ultimates/HoH/sort/diversity, HIGH); `badges/index.html` inline `SAMPLER_RANKS` ladder (L1302-1318 — HIGH, still emits banned `Hardened`/`Transcendent`) + picker branch (L1620-1621); `profile-timeline.js` (L314-406,595-702,738-747 — `parseRank`/RANK_HEX/TIER_HEX, HIGH); `share/share.js` (L141,228,244 — `TIER_SYMBOL[type]`); `skills/index.js` (L31-35,70 — FAMILY_COLORS, no unique/suite keys); `hoh-modal.js` (L60,254,270-271,290); `profile-filter.js` (L197,257-272 — sorts on derived data-branch). Confirmed CLEAN (correct target pattern — do NOT touch): `leaderboard.js` (delegates to `GaiaSemantics.computeBranch`), `heroes.js`, `named/report.html`, `docs/u/*` profiles, `docs/og/**` SVGs. Excluded as non-production (scope line, §2.5): `docs/experiments/ml-graph-viz/*`, `docs/samples/*` (flowchart `getTier` twins etc.) — grep guard skips these + tracking issue.
- **Rewind #1227:** cherry-pick the SURVIVES set onto this base — `332736ab0` (D12 badges words, clean), `55a62ac13` (D15 prev-week, clean), `e31f58077` (D6/D8 plaque, clean), re-strip live.js (`a9f4e3124`, mechanical), hand-port the ~30-line gold-★ block from `4801e0c13` into the new graph renderer (shares file with the deleted D9 derivation). DISCARD `c0def6d62` (D9), and the derivation halves of `04d6114d6` (D14) + `3555c40da` (D74) — the resolved field replaces them.

### Phase 4 — Close-out (`review/meta/ygg2-closeout` or as needed)
- #1000 (agent skills alignment). Full regen. Green staging (validate, rank-vocab, timelines, schema lockstep). Mark PR #1185 ready; merge to main with a **merge commit** (never squash a `dev/*`→`main` EPIC PR).

## 4. Hard constraints (do not violate)
- **Class P vs S:** `docs/graph/*` is tracked Class S served by Pages; `registry/gaia.json` etc. is gitignored Class P. New resolved fields MUST be emitted by `syncDocsGraphAssets.py` into Class S, not left at Class P (Guard E won't catch a Class-P-only field; the phase-1 contract test must).
- **#798 wipe-guard** on every destructive swap (see Phase 2).
- **Programmatic-first:** any registry mutation via `gaia dev` verbs, never hand-edits.
- **No `type ===` / branch-word literals outside `taxonomy.py`** after phase 3 — add a CI grep guard (reuse the guard-topology muscle) so a future meta can't re-scatter derivation. **Scope line (§2.5):** the guard covers **production `docs/` + `src/` + `scripts/` only**, and MUST scan inline `<script>` blocks in `docs/*.html` (not just `docs/js/*.js` — the badge `SAMPLER_RANKS` miss lived in inline HTML). `docs/experiments/` and `docs/samples/` are EXCLUDED with a one-line comment + a tracking issue.
- **Downstream contract lock (scout #3):** emitted output MUST retain generic `type` and `contractVersion="gaia-public-v1"`; MUST NOT rename `registry/` source fields. gaia-mcp + gaia-research fail on violation (see Phase 2 additive-wire invariant). This is a permanent constraint, not a phase step.
- **Token duplication** (`generateCssTokens.py:189` evidence_colors vs `formatting.py:148` GRADE_COLORS) — genuine parallel table; fold into the same source while in `formatting.py`.

## 5. Scout evidence (ground truth, 2026-07-18)
- No node in `docs/graph/gaia.json` (243 nodes) carries `branch`/`rank`/`medallion`/`suiteComponents` today — all raw `type` (130 fusion / 113 basic) + `namedMaxLevel`.
- `passesApexGate` (`trustMagnitude.py:1247`) is display-independent — split is trivial.
- The four resolvers agree functionally on Ygg II *now* but read different fields (drift already present).
- #1227 diff is ~99% regenerated artifact (~34k lines); only ~476 hand-authored lines, ~50 of which survive the rewind.

## 6. Blast-radius miss-list (8-scout sweep, 2026-07-18)

The original inventory (§1) was scoped to this repo's rendering path. Eight scouts (2 passes: repos / CLI-compat / whole-frontend, then data-flow / art-glyph / CLI-deeper) mapped the full radius. Handled per §2.5 (guardrails + grep completeness); listed here as the snapshot, NOT a maintenance checklist — the Phase 1 parity oracle + §4 grep guard are the enforcement.

**HIGH — ships broken/split-brain if not repointed:**
1. tree.md generator — `generateProjections.py:145,264,561,582` + `_tree_renderer.py:69,186` (Basics-only collapse; see Phase 3).
2. Homepage IA — `docs/js/page-ia.js:102,107,239-259,299`.
3. Badge sampler ladder (+banned words) — `docs/badges/index.html:1302-1318`.
4. New-CLI + stale bundled snapshot — `publish-pypi.yml` (bundle on vX.Y.0 only); mitigated by `taxonomy.py` fallback + co-release rule.
5. ML-graph-viz 2D+3D `nodeColor()`/TYPE_COLORS — `docs/experiments/ml-graph-viz/index.html`,`index_3d.html` (EXCLUDED — non-production, tracking issue).
6. profile-timeline rank derivation — `docs/js/profile-timeline.js:314-406,595-702,738-747`.
7. Flowchart `getTier()` twins — `docs/samples/flowchart.html:320-324`,`skill-flowchart.html:337-341,528` (EXCLUDED — samples, tracking issue).

**MED:** `skill-graph.js:43,409-410,736,1106`; `badges/index.html:1620-1621`; `share/share.js:141,228,244`; `skills/index.js:31-35,70`; `hoh-modal.js:60,254,270-271,290`; `profile-filter.js:197,257-272`.

**LOW / hygiene:** `graph.py:37` type→label; `localContext.py:190-205` effective-rank (numeric, consistency-only); banned-word residue (`formatting.py:8` comment, `src/gaia_cli/CLAUDE.md`, wide `docs/en/*` prose — separate copy issue); test fixtures to update post-refactor (`test_treeManager.py:419`, `test_build_docs_redaction_backstop.py:53`, `test_promotion.py:331`).

**External contracts (must NOT break — §4 lock):** keep emitting `type` (gaia-mcp `source.ts:9-12`); keep `contractVersion="gaia-public-v1"`; don't rename `registry/` fields (gaia-research `sync-skill-tree.ts:36`).

**Verified clean (correct target pattern, do NOT touch):** `leaderboard.js:160-194` (delegates to `GaiaSemantics.computeBranch` — the color table is a consumer, not a resolver; ground-truth read confirmed the 2nd-pass false-positive), `heroes.js`, `named/report.html`, `docs/u/*` profiles, `docs/og/**` SVGs, MCP `packages/mcp/src/*`, `share.py` (provenance label only), `cardRenderer.py` (single-source `format_rank_label`).
