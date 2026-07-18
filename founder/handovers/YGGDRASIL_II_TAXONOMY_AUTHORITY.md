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

**Read order in #1 (legacy Ygg I — reconciled into `normalize()`, NOT the Ygg II resolver):**
1. `type === 'basic' && rank >= 4 && !hasSuiteComponents` → `unique`
2. `hasSuiteComponents` → `suite`
3. else → `standard`

> **Epoch reconciliation (founder, 2026-07-18 — reconciles §1 with §7).** The `type ===`-gated read above is the **Ygg I** behavior, where a node's structural class was carried by `type`. It is **NOT** what the Ygg II resolver evaluates. Under **Ygg II the branch is MEMBERSHIP — resolved TYPE-BLIND**: `suiteComponents` present → `suite` (any rank); else rank 4–6 → `unique`, rank 1–3 → `standard`. `type` (`basic`/`fusion`) is **presentation structure only, never a resolution input** (see §7). Backwards-compat is achieved *inside `taxonomy.py::normalize()`*, which folds the legacy Ygg I `type` signal (`ultimate`/`extra` → suite carrier; `unique` → the unique branch) into the canonical membership shape (`suiteComponentsPresent` + rank) — so `resolveDisplayBranch` stays type-blind for BOTH epochs. "Port #1 exactly" therefore means *reproduce resolver #1's outcomes via the `normalize()` fork*, not *gate the Ygg II resolver on `type`*. A resolver that literally re-introduces the `type==='basic'` gate into `resolveDisplayBranch` is a **regression** (it drags Ygg I into Ygg II) and must be rejected by the parity oracle.

**Rank ladders (canonical, from #1):**
- SHARED: `{0 Basic, 1 Awakened, 2 Named, 3 Evolved}`
- SUITE: `{4 Extra, 5 Ultimate, 6 Apex}`
- UNIQUE: `{4 Unique, 5 Unique Ultimate, 6 Unique Impossible}`
- BANNED anywhere: `Transcendent`, `Hardened` (enforced by `check_rank_vocabulary.py`).

## 2. The decision

Reverse rubric E1. **One build-time authority resolves branch/rank/medallion; consumers read the resolved field; all four resolvers are deleted.**

- **Authority module:** `src/gaia_cli/taxonomy.py` (new). Exposes:
  - `normalize(entry, metaEpoch)` — the ONLY meta-version-aware code. Ygg I/II/III forks live here and nowhere else. Maps any-era shape → one canonical internal shape.
  - `resolveDisplayBranch(normalized) -> 'standard'|'suite'|'unique'` — the single branch resolver. **Ygg II = MEMBERSHIP, type-blind** (suite-presence first, no rank gate; rank only splits the no-suite case into standard 1–3 / unique 4–6). Reproduce resolver #1's *outcomes* via the `normalize()` Ygg I fork — do NOT re-introduce #1's `type==='basic'` gate into this resolver (that would drag Ygg I into Ygg II; see §1 epoch reconciliation).
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
- Write `src/gaia_cli/taxonomy.py` with `normalize`/`resolveDisplayBranch`/`rankWord`/`rankLabel`/`medallion`. Port the agreed logic from resolvers #1 and #3; unit-test BOTH Ygg I and Ygg II input shapes. **The Ygg II resolver is MEMBERSHIP (type-blind); the Ygg I `type` gate is reconciled inside `normalize()`, not inside `resolveDisplayBranch` (§1 epoch reconciliation).**
- **Contract test** (`tests/test_taxonomy_contract.py`): the PRIMARY, resolver-independent check asserts `taxonomy.resolveDisplayBranch` == the inline **membership** ground truth (`synthesisBranch`) on every node/named entry — that is the canonical correctness oracle. Separately, per-node parity of the authority against the legacy JS `computeBranch` (#1) + Python `trustMagnitude.computeBranch` (#3) is a **RED-by-design delete-gate** (`xfail(strict=True)`): the legacy resolvers diverge from membership on the known Ygg-I-vs-membership drift (fusion rank≥4 no-suite; rank<4 suite parents), so the parity test fails on purpose until Phase 3 DELETES them and parity holds — at which point strict-xfail flips to a hard failure, forcing the marker's removal (the delete-gate handshake). Do NOT bless the drift as "ratified-equivalent green"; the gate exists precisely to block deletion until parity is real. (Node the JS side via a small harness or a golden-file dump — do not hand-transcribe.)
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

---

## 7. Amendment — Origin mechanic reconciles the STARLESS-graph "stray" (2026-07-18, session audit)

**Scope of this section: STARLESS PRESENTATION only** — the graph/tree buckets (`docs/graph/gaia.json`, `docs/tree.md`, per-user `skill-tree.md`). This is where origins and buckets matter *at build time*. Hall-type builds (Hall of Heroes, `/heroes`) do NOT use the bucket/origin surfacing — see §8 for their expected behavior.

**Context.** A post-doc alignment audit on `dev/ygg2-consume-frontend` initially flagged the origin-fix commit `6dc2dc7e8` (which stamps `branch`/`rank`/`rankWord`/`medallion` onto `docs/graph/gaia.json` nodes) as a STRAY from §2's "named-index-only" emission home. That flag was **wrong**, based on a misreading of what a starless node *is*. This amendment records the corrected model so a later session does not act on the bad flag.

**The corrected model (founder, this session).** A starless generic node is the parent of a **bucket — the set of NAMED skills grouped under it (there can be MULTIPLE named skills in one node).** The node's `type` (`fusion`/`basic`) is **presentation structure only** — how the tree branches visually — never a resolution input. What surfaces onto the node is the bucket's **origin**: per the Yggdrasil II ORIGIN RULE, among the multiple named entries in a bucket at most one is CLI-declared `origin: true`, and that origin's **already-emitted** `branch`/`rank`/`medallion` (resolved in the named index by `taxonomy.py`) is stamped onto the node at build time. No origin → nothing stamped → plain starless node. "Once something is named origin — it shows in the tree."

This is **already implemented and on-plan**: `scripts/syncDocsGraphAssets.py::_bucket_origins()` (L34) maps each generic id → its bucket's origin entry; the sync stamps the origin's emitted fields (L134-138). The named index remains the **single resolution home** (§2); the starless node merely *carries the surfaced value* the graph reads. It reads the emitted field — it does not recompute.

**Corrected Stray assessment:**

| Prior flag | Corrected call |
|---|---|
| **Stray #1** — `6dc2dc7e8` stamped gaia.json (should be named-index-only) | **NOT a stray.** The stamp *surfaces* the origin's emitted named-index branch onto its bucket (origin mechanic). Named-index-only emission is honored; the graph reads a surfaced value, not a recompute. On-plan. |
| **Stray #2** — `skill-semantics.js::computeBranch` frozen, not deleted per §3 | The audit's fallback-vs-stamp parity check (62 identical / 17 differ; fallback resolves 0 suite, mis-labels unique) asked the **wrong question**. `computeBranch` run on a *bare bucket* correctly fails — buckets carry no `suiteComponents`/rank; the **origin entry** does. The fallback was never the intended resolver for starless nodes. Its "insufficiency" is irrelevant: the origin-stamp is the real path. Freezing it as a defensive-only fallback is fine; role to be finalized when the build shape is next revised. |

**Stale prose to correct (not a code revisit):** §5 bullet 1 ("No node in `docs/graph/gaia.json` … carries `branch`/`rank`/`medallion`") is now factually stale — `6dc2dc7e8` stamps 79 of 243 nodes (58 standard / 15 suite / 6 unique) via the origin mechanic. The *architecture* (origin-surfaced, named-index-first) is unchanged; only the §5 snapshot predates the stamp. `founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md` §5 already carries the correct shape.

**Buildability note (founder).** The origin→bucket surfacing is the pattern going forward and is "very very buildable": presentation structure (fusion/basics visual branching) layers on top without changing the resolution source, and the origin mechanics are already in the pipeline. Future presentation work does not reopen the resolution home.

---

## 8. Hall of Heroes — expected behavior for Hall-type builds (founder, 2026-07-18)

**Hall-type builds are NOT starless-graph builds.** Where §7's starless presentation surfaces one **origin per bucket** onto a generic node, a Hall-type build (Hall of Heroes, the `/heroes` page, and the homepage `#hall-of-heroes` mini-section) presents the **named skills themselves** — every qualifying named entry, not one-per-bucket. Both read the same emitted taxonomy fields (`branch`/`rank`/`rankWord`/`medallion` from the named index); they differ in *selection* and *ordering*.

**Expected behavior (founder-specified):**

1. **No limit on the number.** The Hall shows *all* qualifying named skills — there is no top-N cap, no per-contributor cap, no "8 plates." Any cap in a current build (e.g. the `topSkill.level >= 4` single-skill filter on the contributors API that yields only ~7) is a **defect**, not the intended behavior.
2. **Ranks presented as Unique·Suite pairs.** Within each star level, the two 4★+ branches are shown as a pair — **Unique before Suite** (`Unique Impossible · Apex` at 6★; `Unique Ultimate · Ultimate` at 5★; `Unique · Extra` at 4★).
3. **Higher rank to lower rank.** Ordered by star level **descending**: 6★ → 5★ → 4★.
4. **Down to 4★, in that order.** The Hall floor is **4★** — nothing below 4★ appears (below 4★ there is no branch decoration; the shared ladder Awakened/Named/Evolved is not Hall material). Order stops at the 4★ Unique·Suite pair.

**Canonical order:**
`6★ Unique Impossible · 6★ Apex → 5★ Unique Ultimate · 5★ Ultimate → 4★ Unique · 4★ Extra`

**Current data (2026-07-18, for reference — no cap applied):** 11 Hall-eligible named skills — `5★ Suite`: agent-skills, gstack, skills, superpowers, ruflo (5); `4★ Unique`: performance-optimization, firecrawl-build-scrape, firecrawl-build-search, impeccable, subagent-driven-development, few-shot-learning (6). No 6★ and no 5★ Unique / 4★ Suite exist yet, so those pair-slots are simply empty until earned.

**Resolution source (do NOT recompute):** Hall builds read the emitted `branch`/`rank` per named entry (via the `GaiaSemantics.branchOf`/`rankWordOf` seam or the emitted field directly). Where a Hall consumer's input blob omits the emitted fields (e.g. `heroes.js` fed by the contributors-API `topSkill` blob), the fix is to **thread the emitted fields into that input**, not to reinstate read-time `computeBranch`. Selection (rank ≥ 4, all entries) and ordering (rank-desc, Unique·Suite pairs) are Hall-layer logic on top of the emitted fields — they are not a second taxonomy resolver.
