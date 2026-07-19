# Yggdrasil II — Meta Schema Ratification (2026-07-07)

---

## v4 Amendment — 2026-07-19 (Q3 origin gates: 4★ = bucket-level; 5★+ = fusion-structure)

> This amendment corrects **Q3**. The original Q3 wording — "Origin counted in **fusion
> structure** (`prerequisites`), not `suiteComponents`" — was written as a single rule for
> the whole Unique branch, but it conflated the **4★ Unique** gate with the **5★+ Unique
> Ultimate** gate. META.md §4.1 governs the 4★ gate and it wins. This supersedes the
> "count origin in fusion structure" wording **for the 4★ Unique gate only**; the 5★+
> fusion-structure rule stands unchanged.

### The correction

Origin at the Unique-branch gates is evaluated on **two different axes**, one per gate tier:

| Gate | Origin axis | Definition |
|---|---|---|
| **4★ Unique** | **Bucket-level** (META.md §4.1) | Does THIS skill hold Origin on the generic bucket it **directly** implements (`genericSkillRef`)? Origin is "the most renowned implementation IN A GENERIC BUCKET … exactly one Origin per bucket." **No prerequisite / fusion-structure check at 4★.** |
| **5★ Unique Ultimate** | **Fusion-structure** (`prerequisites`) | Does the contributor hold Origin on ≥1 node in the generic parent's `prerequisites` (the fusion recipe they built)? This is where fusion structure matters — the creator must hold the prerequisite skills as part of the fusion. |

### Why the original Q3 was wrong (load-bearing)

A 4★ Unique skill can be the SOLE, world-renowned implementation of a fusion generic whose
prerequisite sub-nodes have **zero named implementations**. Under the original Q3, its 4★
Origin was tested against those empty prerequisite buckets — an **unsatisfiable structural
predicate** — so it demoted for a structural reason rather than on merit. The archetype:
`safishamsi/graphify` (sole named skill on `knowledge-graph-build`, `origin: true`, prereqs
`extract-entities` / `logical-inference` with no named implementations) was wrongly demoted
4★→3★. Under the corrected 4★ gate it holds bucket-level Origin on its own generic and
passes (TM ≈ 123 ≥ 100).

Fusion-structure / prerequisite Origin is a **5★+** concern — that is the tier at which the
creator is expected to hold the prerequisite skills that compose the fusion. Pushing that
requirement down to 4★ punished standalone excellence for a structure it never claimed.

### Where the fix lives

`src/gaia_cli/promotion.py :: checkUniqueBranchGate` now forks the origin predicate by rank:
4★ → `_holds_bucket_origin(named)` (reads the authoritative stored `origin` flag on the
skill's own `genericSkillRef` bucket, per §4.1); 5★+ → `_contributor_holds_origin_in(...)`
against the generic parent's `prerequisites` (unchanged). The stored `origin: true` flag is
treated as authoritative because §4.1 defines Origin as the curator-granted merit mark,
singular per bucket — not something re-derived at gate time.

---

## v3 Amendment — 2026-07-18 (Three orthogonal axes: Membership · Rank word · Decoration)

> This amendment refines v2 by naming the three **independent** axes that the v2 rules
> already implied but did not separate cleanly. It supersedes nothing in v2 — the
> derivation rules and ladders stand — but it disambiguates the vocabulary so design,
> copy, and code stop conflating "which branch a skill belongs to" with "how it is
> decorated." Every consumer (badges, medallions, SSR, JS) must respect the split.

### The three axes

1. **Membership** — which branch a skill *belongs to*, for grouping / sorting / membership.
   Values: `standard` | `suite` | `unique`.
   - Membership holds **from 1★ up**. A suite-component skill is `suite` at 2★; a
     standalone-mastery skill is `unique` at 4★. Membership is derived, never declared:
     `suiteComponents present → suite`; else `rank ≥ 4 → unique`; else `standard`.
   - Membership is the axis `taxonomy.branchFor()` returns.

2. **Rank word** — the ladder word for the skill's current star level.
   Values: `Awakened` (1★), `Named` (2★), `Evolved` (3★) — shared across all membership —
   then the fork at 4★+: `Extra`/`Ultimate`/`Apex` (suite) or `Unique`/`Unique Ultimate`/`Unique Impossible` (unique).
   - The rank word is `taxonomy.rankWord(level, branch)`.
   - **1★–3★ always return the shared word regardless of membership.** A 2★ suite-member
     reads "Named," never "Extra."

3. **Decoration** — the prestige *treatment*: plain vs. Suite/Unique glyph and medallion,
   plus the branch's color tokens.
   - Decoration only *renders* at 4★+. Below 4★ every skill uses the plain glyph
     (white diamond) and the shared rank color ramp, **even though its Membership is
     already `suite`/`unique`.**
   - At 4★+ the decoration forks by Membership:
     - **Suite** → suite medallion (◆ black diamond) + gold escalation (4★ tint → 5★ deeper → 6★ Apex metallic gold).
     - **Unique** → unique medallion (◉ circled bullet) + the Unique color ladder:
       **4★ violet → 5★ darker gold → 6★ inverted (gold ground / dark ink).**
   - Decoration is `taxonomy.medallion(branch, rank)` for the glyph, plus the per-rank
     color tokens (`RANK_COLORS`, `RANK_COLORS_UNIQUE`).

### Why the split matters (load-bearing)

The three axes were tangled in the v1/v2 badge generator: `_UNIQUE_COLOR` was a single
violet applied to every unique rank, so 5★ and 6★ uniques rendered identically to 4★.
Under v3 the axes are independent — a skill's **Membership** does not dictate its
**Decoration** color; the rank *within* the membership does. The Unique ladder is:

| Stars | Unique rank word | Unique decoration (color/treatment) |
|---|---|---|
| 4★ | Unique | violet (`#7c3aed`) |
| 5★ | Unique Ultimate | **darker gold** |
| 6★ | Unique Impossible | **inverted** (gold ground, dark ink) |

Any surface that draws a unique 5★ in plain violet, or a 6★ non-inverted, is wrong.

---

## v2 Amendment — 2026-07-14 (Branch decoupled from Type)

> This amendment supersedes **Q2** and the **Unique branch**, **Suite branch**, and **`computeBranch`** entries in the Ubiquitous Language section below. Original text for each is preserved with an inline `[SUPERSEDED]` marker.

### Changes from v1

1. **Branch is derived from `suiteComponents` + rank — NOT from `type`.** `type` is removed from every branch-derivation formula and from the definition of Unique.
> **[SUPERSEDED 2026-07-18 — membership is suiteComponents-first from any rank; only DECORATION forks at 4★+. See founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md]**
2. **The unique↔suite fork is recognised ONLY at 4★+.** At 1★–3★ there is NO branch distinction — all skills share the ladder: 1★ Awakened, 2★ Named, 3★ Evolved.
3. **"Transcendent" is DROPPED.** The two 4★+ ladders are:
   - **Suite** (generic parent HAS `suiteComponents`): 4★ **Extra**, 5★ **Ultimate**, 6★ **Apex**
   - **Unique** (generic parent has NO `suiteComponents`): 4★ **Unique**, 5★ **Unique Ultimate**, 6★ **Unique Impossible**

### Branch-derivation rule (canonical)

`branch = f(suiteComponents present?, rank)`

> **[SUPERSEDED 2026-07-18 — the `rank ≥ 4` conjunct is wrong for MEMBERSHIP. Membership is suiteComponents-first from any rank (suiteComponents present → suite at any rank; else rank ≥ 4 → unique; else standard). Only DECORATION/ladder-word forks at 4★+. See founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md]**
- rank 1–3 → shared ladder (Awakened / Named / Evolved), no branch
- rank ≥ 4 AND suiteComponents present → Suite ladder (Extra / Ultimate / Apex)
- rank ≥ 4 AND no suiteComponents → Unique ladder (Unique / Unique Ultimate / Unique Impossible)

### Rank ladder

> **[SUPERSEDED 2026-07-18 — as a MEMBERSHIP map only. This table is correct as a DECORATION / rank-word ladder (the words rendered per branch per star). Do NOT read the 1★–3★ suite/unique blanks as "no membership": membership is suiteComponents-first from any rank, so a 2★/3★ suite-component skill is already `suite` and merely renders the shared word. See founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md]**

| Stars | Shared (no branch) | Suite branch | Unique branch |
|---|---|---|---|
| 1★ | **Awakened** | — | — |
| 2★ | **Named** | — | — |
| 3★ | **Evolved** | — | — |
| 4★ | — | **Extra** | **Unique** |
| 5★ | — | **Ultimate** | **Unique Ultimate** |
| 6★ | — | **Apex** | **Unique Impossible** |

### Orthogonality assertion

> Type and Branch are orthogonal. `type` (basic|fusion) is pure structural metadata — a starless/generic node is `fusion` iff it has prerequisites — and is NEVER consulted for branch. Branch is driven solely by `suiteComponents` presence and rank. In practice fusion and suiteComponents usually coincide, but they are independent fields: a `fusion` node with no `suiteComponents` is Unique branch, and a `basic` node carrying `suiteComponents` is Suite branch. `suiteComponents` remains an input to downstream Trust Magnitude computation as well.

---

> **This document is a ratification handover, not an implementation plan.** It records the decisions, names the Meta Shift, defines the staging-branch protocol, and scopes the follow-up (TM Index 2026 Q3). Implementation PRs are staged separately after ratification lands and all target the same staging branch.

---

## Naming: the two RFC series

Gaia has accumulated enough Meta Shifts that two independent RFC lineages need distinct human-readable versioning schemes. Both are ratified here so future contributors don't invent conflicting names.

### Series A — **Yggdrasil** (Meta Schema RFCs)

Schema-type Meta Shifts that reshape how the skill tree grows: taxonomy axes, rank vocabulary, structural invariants, curator-facing field semantics. Named after the Norse world tree.

| # | Codename | Date | Scope |
|---|---|---|---|
| I | **Yggdrasil I** *(retroactive)* | 2025 | Original Basic / Extra / Unique / Ultimate taxonomy + 0★–6★ rank ladder + Origin Contributor mechanic. Established the tree's shape. |
| II | **Yggdrasil II** *(this doc)* | 2026-07-07 | Type + Branch axis split; Ultimate rank rename; Evidence Floor removal; Option D (type on starless only). Reshapes the branch axis. |

Future Meta Schema RFCs continue the series (Yggdrasil III, IV, …).

### Series B — **TM Index** (Trust Magnitude / benchmark cadence)

Business-technical quarterly cadence for TM formula, weight recalibration, benchmark taxonomy, and gate mechanics. Public-facing name for the scoring engine.

| Public name | Internal codename | Ratified | Scope |
|---|---|---|---|
| **TM Index (2026 Q2)** | G7 Trust Taxonomy RFC | 2026-06-16 | 10-type evidence taxonomy, Trust Magnitude formula, sqrt-softened fusion, 6-predicate Apex Gate. |
| **TM Index (2026 Q3)** | G8 (planned) | *pending, this doc scopes it* | Branch-aware TM formula rebuild. Fixes fusion-scoring for Uniques (see § Follow-through). |

The G-series stays as the engineering codename; **TM Index (YYYY QN)** is what external docs, changelogs, and leaderboards use. `docs/codex/trust-methodology.html` should reference "TM Index" going forward.

---

## Staging-branch protocol

**All Yggdrasil II implementation PRs target `dev/yggdrasil-ii-staging`, not `main`.**

The staging branch is forked from `design/v6.1.1-ascension-overdrive-v2` (the active Ascension design work), so the in-flight Ascension redesign moves in lockstep with the taxonomy shift. This is the only way to guarantee the Y-fork diagram (deferred) and the Type/Branch semantics land together without a cross-branch merge race.

**Rules:**

1. Every sub-issue PR listed in the Deliverable Inventory targets `dev/yggdrasil-ii-staging` in its `base` ref, **not** `main`.
2. `dev/yggdrasil-ii-staging` merges to `main` **once**, at the end of the sprint, as a single squash-merged EPIC-closer PR (or a rebase-preserving merge if commit provenance matters — decide at closure time).
3. CI's `branch-scope.yml` allows `dev/*` unrestricted scope (per CLAUDE.md), so schema + registry + docs + CLI + frontend can all move on one branch without prefix constraints.
4. If a sub-issue PR needs to be revised, it is revised **on the staging branch**, not on a new fork of main.
5. The Ascension design work (Y-fork diagram, animated cycle, hero backdrops, plates, arch, thread, risers) continues on `design/v6.1.1-ascension-overdrive-v2` in parallel and **merges INTO `dev/yggdrasil-ii-staging` (not directly to main) once ready.** The design branch is effectively the eighth sub-issue of this EPIC — it does not have its own dedicated GitHub issue (the design work predates the Yggdrasil II ratification), but it participates in the sprint under the same staging-branch protocol. This ensures the taxonomy shift and its visual expression land together at the single staging→main merge at sprint closure.
6. **Never push directly to `main`** (CLAUDE.md invariant). The staging branch is the only landing zone for Yggdrasil II work until closure.

**Branch topology:**

```
main
 └─ dev/yggdrasil-ii-staging                    ── this doc lands here first
     ├─ #994 Docs ratification PR               ── base: dev/yggdrasil-ii-staging
     ├─ #995 Schema PR                          ── base: dev/yggdrasil-ii-staging
     ├─ #996 CLI PR                             ── base: dev/yggdrasil-ii-staging
     ├─ #997 Migration script PR                ── base: dev/yggdrasil-ii-staging
     ├─ #998 Frontend PR                        ── base: dev/yggdrasil-ii-staging
     ├─ #999 CI guards PR                       ── base: dev/yggdrasil-ii-staging
     ├─ #1000 Agent-skills PR                   ── base: dev/yggdrasil-ii-staging
     └─ design/v6.1.1-ascension-overdrive-v2    ── merges INTO staging when ready
```

At sprint closure, `dev/yggdrasil-ii-staging` → `main` in one merge.

---

## Context — why Yggdrasil II exists

Gaia's rank system today conflates two axes into one `type` enum on starless nodes (`basic` / `extra` / `unique` / `ultimate`) and gates promotion through a per-star **Evidence Floor** (Grade C+ / B+ / S) layered on top of the TM Index (2026 Q2) Trust Magnitude score. Three problems have accumulated:

1. **Ascension descriptions are ambiguous.** The Ascension Cycle copy on the site talks about "Ultimate" and "Apex" without anchoring to the 1★–6★ maturity axis, so a first-time reader can't tell whether "Ultimate" is a rank or a taxonomy class. The word "Ultimate" is deliberately gacha-anchored to 5★ in product intent, but the schema still uses it as a taxonomy word.
2. **Evidence Floor duplicates Trust Magnitude.** TM Index (2026 Q2) Grade thresholds (S ≥ 250, A ≥ 100, B ≥ 50, C ≥ 20) already gate promotion; the Evidence Floor column adds a second, inconsistent layer.
3. **The `type` enum can't express "prestige branch".** Impeccable-style graph-isolated standalone skills earn "Unique" today via a starless `type=unique` field, but "Unique" is a *progression path* a named skill lives on, not a structural property of its starless parent.

**Yggdrasil II ratifies:**

- **Type axis** (starless only, structural): collapses from 4 values to 2 — `{basic, fusion}`.
- **Branch axis** (named only, progression): `{standard, unique, suite}`, derived at read-time from `(generic.type, generic.suiteComponents present?, named.level)`. Never declared; always computed.
  > **[SUPERSEDED 2026-07-18 — branch is EMITTED at BUILD time by src/gaia_cli/taxonomy.py onto every named entry (with rank/rankWord/medallion/contractVersion); consumers READ it, not derive it at read-time. (`generic.type` input already retired by v2.) "Never declared on the source node" still holds. See founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md]**
- **Rank names**: 5★ becomes **Ultimate** (Suite branch) / **Unique Ultimate** (Unique branch); 6★ stays **Apex** (Suite) / becomes **Unique Impossible** (Unique). "Ultimate" is henceforth a canonical rank-axis word.
- **Evidence Floor removed.** Trust Magnitude is the sole gate.

---

## Ubiquitous language (glossary — mirrored to CONTEXT.md)

The following terms are the shared vocabulary of Yggdrasil II. They live authoritatively in CONTEXT.md under the new `### Taxonomy v6 (Yggdrasil II)` subsection; this list is the readable synopsis.

- **Type axis** — structural, on starless nodes only. Values: `basic` (0 prerequisites) or `fusion` (≥1 prerequisite). Named skills have no `type` field; they inherit via `genericSkillRef`.
- **Branch axis** — progression, on named skills only. Values: `standard` (1★–3★), `unique` (4★–6★ non-suite), `suite` (4★–6★ suite-based). Always derived, never declared.
  > **[SUPERSEDED 2026-07-18 — two fixes. (1) Branch is EMITTED at BUILD time by src/gaia_cli/taxonomy.py; consumers READ it. (2) Membership is suiteComponents-first from any rank — a 2★/3★ suite-component skill is `suite`, not `standard`; the 1★–3★/4★–6★ split shown here is a DECORATION ladder, not the membership map. See founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md]**
- **Standard branch** — 1★ Awakened → 2★ Named → 3★ Evolved. The default; every named skill starts here.
- **Unique branch** — 4★ Unique → 5★ Unique Ultimate → 6★ Unique Impossible. For skills that reach 4★+ *without* being a suite (their generic parent has no `suiteComponents`). Standalone prestige track. Impeccable is the archetype.
  > **[SUPERSEDED by v2 Amendment 2026-07-14]** Branch no longer reads `type`; derived from `(suiteComponents present?, rank)`, fork at 4★+.
- **Suite branch** — 4★ Extra → 5★ Ultimate → 6★ Apex. For skills whose generic parent carries `suiteComponents` (structural fusion of grouped components). Group prestige track.
  > **[SUPERSEDED by v2 Amendment 2026-07-14]** Branch no longer reads `type`; derived from `(suiteComponents present?, rank)`, fork at 4★+.
- **Ultimate** — the 5★ rank name. Universal across branches (Suite: **Ultimate**, Unique: **Unique Ultimate**). Intentional gacha-anchor collision — every 5★ skill is "Ultimate". Deprecates the legacy `type=ultimate` taxonomy usage.
- **Apex** — the 6★ Suite-branch rank name (preserved from Yggdrasil I).
- **Unique Impossible** — the 6★ Unique-branch rank name (new). Provisional 5-predicate gate (Apex minus `directNestedSuiteGte1`); formal ratification deferred.
- **Fusion structure** — the `prerequisites` graph of a starless node (fusion-recipe origin edges). Contrasted with `suiteComponents` (co-located sibling components of a Suite). Unique gates count origins in fusion structure; Suite gates count origins in `suiteComponents`.
- **Fusion Skill** — the new taxonomy label for what was previously "Extra" / "Ultimate" (starless side). Retires "Extra Skill" and the taxonomy usage of "Ultimate Skill".
- **`computeBranch(named)`** — read-time helper that walks `named → genericSkillRef → generic.{type, suiteComponents}` and returns the branch label given the named skill's current level.
  > **[SUPERSEDED by v2 Amendment 2026-07-14]** Branch no longer reads `type`; derived from `(suiteComponents present?, rank)`, fork at 4★+.
- **Option D** — the named-skill-type-by-inheritance rule. Starless nodes carry `type`; named skills do not. Simplifies both axes: starless is purely structural, named is purely progression.
- **Meta Schema RFC** — Series A (Yggdrasil I, II, III, …). Schema-type Meta Shifts that reshape the tree's structure or vocabulary.
- **TM Index** — Series B (TM Index (2026 Q2) = G7; TM Index (2026 Q3) = planned). Trust Magnitude scoring engine, versioned by quarter.
- **Meta Shift** — the generic term for any ratified change to the registry's meta-rules. Umbrella over both RFC series.

---

## Decisions locked (from grill-me interview, 2026-07-07)

| # | Branch | Decision |
|---|---|---|
| Q1 | 5★ naming collision | "Ultimate" = 5★ rank universally (Suite: **Ultimate**, Unique: **Unique Ultimate**). Intentional gacha-anchor. The old taxonomy usage retires. |
| Q2 | Branch declaration | Branch is completely derived from `(generic.type, generic.suiteComponents present?, named.level)`. Never declared on nodes; always computed at read-time.<br>**[SUPERSEDED by v2 Amendment 2026-07-14]** Branch no longer reads `type`; derived from `(suiteComponents present?, rank)`, fork at 4★+.<br>**[SUPERSEDED 2026-07-18 — "computed at read-time" is wrong: branch is EMITTED at BUILD time by src/gaia_cli/taxonomy.py and read by consumers. "Never declared on the source node" still holds. See founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md]** |
| Q3 | Unique gates | **4★ Unique**: Origin + TM ≥ 100 (A). **5★ Unique Ultimate**: Origin + TM ≥ 250 (S). Origin counted in **fusion structure** (`prerequisites`), not `suiteComponents`. `suiteRef` membership does NOT disqualify from Unique — a "world-renowned handoff skill" that happens to live inside a suite is still Unique.<br>**[SUPERSEDED (4★ only) by v4 Amendment 2026-07-19]** The "count origin in fusion structure" rule applies at **5★+ only**. The **4★ Unique** origin is **bucket-level** (META.md §4.1): does the skill hold Origin on the generic it directly implements? No prerequisite/fusion-structure check at 4★. See the v4 Amendment at the top of this doc. |
| Q4 | Type field on named skills | **Option D**: type lives on starless only, named inherits via `genericSkillRef` walk. Bulk rewrite: `extra`→`fusion`, `ultimate`→`fusion`, `unique`→`basic`. |
| Q5 | Suite 5★ gate | **Preserved per #935** (Origin in suiteComponents + 5 A-graded origins in suiteComponents + TM ≥ 250). Asymmetric-by-design — Unique counts fusion-structure origins; Suite counts suiteComponents origins. The 5 existing 5★ Suites keep rank. |
| Q6 | Migration policy | **Hard cutover at implementation-PR land.** All 43 4★s and 5 5★s re-evaluated; failures demote to 3★ Evolved with `type_change` + `demote` timeline events. At least 1 of the 5 5★s will demote (S=4 registry-wide). Impeccable = clean archetype migration to 4★ Unique. |
| Q7 | "Ultimate" word invariant | CONTEXT.md invariant rewrites: "Ultimate is a 5★ rank word (Suite: Ultimate; Unique: Unique Ultimate)." Guard A gatekeeps the word from self-proclaimers as before; Yggdrasil II ratifies the semantic meaning it always implied. |
| Q8 | Ascension diagram | Y-fork dual-color deferred to `dev/*` staging alongside `design/v6.1.1-ascension-overdrive-v2`. Interim: dual-label rows OR WIP-banner. |
| Q9 | 6★ Unique Impossible gate | **Provisional 5-predicate gate** (Apex minus `directNestedSuiteGte1`). Marked `◇ Provisional`. Formal follow-up RFC required. |
| Q10 | TM Index Q3 scope | **Branch-aware TM formula rebuild.** Suite branch keeps current sqrt-softening; Unique branch gets a depth-weighted standalone-adoption formula (peer-review + benchmark-result dominate); Standard branch uses simple sum. See § Follow-through. |

---

## Follow-through — TM Index (2026 Q3)

Yggdrasil II ships the *vocabulary*: it declares the Unique branch exists, gives it gates, and reclassifies existing skills onto it. But TM Index (2026 Q2)'s fusion-scoring mechanic remains **broken for Uniques**:

- The `fusion-recipe` weight (1.5×) and sqrt-softening (`200 + 20 × sqrt(origins − 10)` past 10) were engineered for **suites**.
- Applied to a Unique that happens to live inside a suite (`suiteRef` present, `suiteComponents` absent), the skill inherits fusion signal it did not structurally earn.
- Applied to a genuinely-standalone Unique (`suiteRef` absent), the skill scores lower than merit warrants because the fusion-recipe row is either missing or zero-weighted.

**TM Index (2026 Q3) deliverable — branch-aware TM formula rebuild:**

- **Suite branch**: current TM formula preserved unchanged (sqrt-softening, 1.5× fusion-recipe weight).
- **Unique branch**: fusion-recipe rows contribute 0. TM is scored purely from non-fusion evidence types, with re-weighting favoring `peer-review` (currently 1.2×), `benchmark-result` (currently 1.4×), and social-signal / adoption evidence. New Unique-specific weight: `depth-of-integration` proxy (proposed).
- **Standard branch (1★–3★)**: current formula unchanged — most Standard skills never accumulate enough fusion signal for the weighting to matter.

**Scope boundary:** TM Index (2026 Q3) is a separate ratification (its own handover doc when it lands). Yggdrasil II must land first because Q3 needs the branch axis to key on. This doc *scopes* Q3; it does not ratify it.

**Tracking:** open new issue **"TM Index (2026 Q3) — Branch-aware TM formula rebuild"** as a follow-up to #749 (which currently tracks the depth-2 / recalibration work). Reference back to Yggdrasil II by codename.

---

## Deliverable inventory (post-ratification implementation)

All PRs target `dev/yggdrasil-ii-staging`. Sequenced roughly Docs → Schema → CLI → Migration → Frontend → CI → Agent Skills, but sub-issues can be parallelized where they don't share files.

**Doc ratification** — one lockstep PR:
- `META.md` — §1.1 star table (drop Evidence Floor), §1.2 (Type + Branch rewrite), §4.2 (Suite path preserved + Unique path added), §4.3 → split into Suite Apex + Unique Impossible provisional, §8 tracker.
- `CONTEXT.md` — taxonomy vocabulary, rank names, invariant rewrite, banned-synonym list. (This ratification handover already lands part of it.)
- `docs/codex/trust-methodology.html` — Evidence Floor retirement, Apex Gate splits, references "TM Index" going forward.
- `DESIGN.md` — rank sequence updates, branch-tier tokens.
- `founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md` — this doc.

**Schema** — one PR:
- `registry/schema/skill.schema.json` — `type` enum collapse; retire `type=ultimate → minPrereqs=3` invariant.
- `src/gaia_cli/data/registry/schema/*` — mirror in lockstep.
- `registry/schema/meta.json` — rank labels; drop Evidence Floor keys.
- `namedSkill.schema.json` unchanged (Option D).

**CLI** — one PR:
- `gaia dev add --type choices=["basic","fusion"]`.
- `gaia dev fuse` drops `--type ultimate` flag.
- `promotion.py::detect_unique_candidates` collapses; new `checkUniqueBranchGate`.
- `trustMagnitude.py`: new `computeBranch()`; rename `checkApexGate*` → `checkSuiteApexGate*`; new `checkUniqueImpossibleGate` (provisional).
- `formatting.py`: branch-aware rank labels.

**Migration** — one-shot script:
- `scripts/migrate_taxonomy_v6.py` (dry-run default, idempotent, CSV report). Reference pattern: existing `checkApexGate*` predicate-return shape.

**Frontend / site copy** — one PR:
- `docs/js/{skill-graph,skill-explorer,named-skills}.js` — type readers become inheritance-walks (watch the two-IIFE gotcha in `skill-explorer.js` per CLAUDE.md).
- `docs/index.html` Ascension section — explicit 1★–6★ references; WIP-banner OR dual-label rows.
- `docs/badges/index.html` — rank-label copy (verify `?u=mattpocock&s=grill-me` after edits).

**CI guards** — alongside schema PR:
- Guard A banned-synonym list — updated per Q7.
- `scripts/validate.py` meta-sync check.
- `scripts/validate_timelines.py` — verify every taxonomy-v6 demotion produced a `type_change` + `demote` pair.

**Agent skills** — low-urgency PR:
- `.claude/skills/gaia-curate*/`, `.claude/skills/gaia-fuse-full-suite/` — prompts reference new taxonomy.

**Deferred** — tracked separately, not blockers to the staging→main merge, but should land on staging before closure if possible:
- Ascension Cycle Y-fork animated diagram (continues on `design/v6.1.1-ascension-overdrive-v2`, merges into staging when ready).
- 6★ Unique Impossible formal ratification (follow-up RFC — Yggdrasil III candidate).
- TM Index (2026 Q3) branch-aware formula rebuild (see § Follow-through — separate EPIC).

---

## Consolidating EPIC

One new EPIC issue titled **"Yggdrasil II: Type + Branch axis split, Ultimate rank rename, Evidence Floor removal"** links the seven sub-issue PRs (Docs, Schema, CLI, Migration, Frontend, CI, Agent Skills), each targeting `dev/yggdrasil-ii-staging`. The EPIC's closing PR is the one that merges the staging branch to `main`.

Related existing issues in scope: **#975**, **#935**, **#749**, **#746**, **#464**, **#715**, **#925**, **#654**, **#599**, **#598**, **#757**, **#529**, **#250**, **#526**, **#597**, **#652**, **#638**, **#637**, **#69**, **#601**, **#611**, **#212**, **#139**, **#332**.

A second EPIC issue **"TM Index (2026 Q3) — Branch-aware TM formula rebuild"** is opened as a follow-through, blocked-by the Yggdrasil II staging→main merge.

---

## Non-goals of Yggdrasil II

- No changes to the TM Index (2026 Q2) Trust Magnitude formula itself — that is TM Index (2026 Q3) scope.
- No changes to the Suite 5★ Ultimate or Suite 6★ Apex gates (preserved per #935).
- No formal ratification of the 6★ Unique Impossible gate — provisional only.
- No Y-fork Ascension diagram in this ratification handover (deferred to `design/v6.1.1-ascension-overdrive-v2` staging).
- No changes to redaction rules, `installable: false` exempt list, or the 8 permanent redaction exemptions.
- No push directly to `main` at any point during the sprint (staging-branch protocol).

---

## Verification of the ratification itself

This is a handover ratification, not code. Verification is:

1. All ten decision-log questions answered and internally consistent.
2. Both series names (Yggdrasil / TM Index) applied without conflict to prior work.
3. Staging-branch protocol codified — every sub-issue PR base ref is `dev/yggdrasil-ii-staging`.
4. Every deferred item has a named home (issue, EPIC, or follow-up RFC).
5. Ubiquitous language mirrored to CONTEXT.md.
6. Non-goals are explicit.

Post-approval, the doc is referenced by the EPIC and each sub-issue.
