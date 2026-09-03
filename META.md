# META: Gaia Skill Tree — Source of Truth

This document serves as the **single source of truth** for the Gaia Skill Tree registry's taxonomy, evidence methodology, and ranking strategy. It defines the "Meta" — the rules and standards that ensure Gaia remains a high-prestige, high-trust ecosystem for agent capabilities.

---

## 1. Core Taxonomy (The Hierarchy)

Gaia uses a tiered star system (`0★`–`6★`) to rank skills. Levels are both a measure of technical complexity and a mark of community prestige.

> **Stars live on named skills only.** Generic skill references are **starless** — rank-less taxonomy nodes that carry no stars of their own (see `CONTEXT.md` § Starless). A starless ref's *effective rank* is the top star among its named-skill children. The star table below therefore describes **named implementations**; the starless reference they map to has no level of its own and renders as *generic* (italic, greyed-out) in the UI.

### 1.1 Star Tiers & Rank Labels (named implementations)

> **Yggdrasil III ruling — Trust Magnitude measures accumulated scoring evidence only.** The per-star **Evidence Floor** remains retired; TM is the numeric promotion gate. Evidence rows carry a `grade` field (S/A/B/C, Platinum → Bronze) as a row-quality signal derived as described in §2.1b. The promotion engine (`src/gaia_cli/promotion.py`) reads `grade` first and falls back to the deprecated `class` field (A/B/C legacy) during the migration window — Evidence Grade A ≠ Class A, and neither is the skill-level Overall Trust Grade. Never conflate them.

| Level | Label | Significance | Verification Tier (max) |
|---|---|---|---|
| **0★** | **Basic** | Pre-named primitive — a freshly scanned candidate against a starless reference. | — |
| **1★** | **Awakened** | Verified candidate, not yet named. | — |
| **2★** | **Named** | Minimum level for named implementations. | community-verified |
| **3★** | **Evolved** | Demonstrates reproducibility and stability. | community-verified / benchmark-verified |
| **4★** | **Extra** (Suite branch) / **Unique** (Unique branch) | Proved at production depth; branch forks here. TM gate: ≥ 100 (A-grade). | up to security-reviewed |
| **5★** | **Ultimate** (Suite branch) / **Unique Ultimate** (Unique branch) | Mastery level — 'Ultimate' is the universal 5★ word. TM gate: ≥ 250 (S-grade). | up to enterprise-ready |
| **6★** | **Apex** (Suite branch) / **Unique Impossible** (Unique branch) | The pinnacle of Gaia; extreme ecosystem impact. 6-predicate Apex gate (Suite, §4.3); provisional 5-predicate Unique Impossible gate (Unique, §4.4). | enterprise-ready required |

### 1.2 Node Types and Branch Axis (Yggdrasil II, 2026-07-07)

**Type axis** — starless / generic nodes only. Named skills carry no `type` field; they inherit via `genericSkillRef` walk:
- **`basic`** — 0 prerequisites. Root primitive nodes.
- **`fusion`** — ≥ 1 prerequisite. Any non-basic starless node. PURE STRUCTURE — `type` does **not** determine a named skill's branch. Legacy values `extra`, `ultimate`, and `unique` are retired; all non-basic nodes are `fusion`.

**`suiteComponents`** — a **Named-Skill-only** list of co-located suite components (never on the starless generic parent, per #996). Its **presence** puts the Named Skill on the `suite` branch at any rank and feeds downstream structural rank/Apex graph predicates. Independent of `type`.

**Branch axis** — named skills only, **derived at read-time, never declared**. `branch = f(suiteComponents present?, rank)`, **suiteComponents-presence first**:
- **`suite`** — `suiteComponents` present, at **any rank** (from the 2★ push floor). Suite **ladder words + glyph appear only at 4★+**: 4★ **Extra** → 5★ **Ultimate** → 6★ **Apex**; a 2★/3★ suite shows the shared word (Named/Evolved) + plain glyph. Membership is structural; the 4★ fork is a decoration gate.
- **`unique`** — no `suiteComponents` AND rank ≥ 4. Unique ladder: 4★ **Unique** → 5★ **Unique Ultimate** → 6★ **Unique Impossible**.
- **`standard`** — no `suiteComponents` AND rank 1–3. Shared ladder: 1★ Awakened → 2★ Named → 3★ Evolved.

**Orthogonality**: type and branch are fully independent. A `fusion` node without `suiteComponents` yields Unique-branch named skills; a `basic` node with `suiteComponents` yields Suite-branch named skills. Never consult `type` to determine branch.

### 1.3 Redaction of Pre-Named & Demoted Handles

Because stars live on **named** skills only, a skill at **1★ (Awakened)** or
**0★ (Basic)** is *not yet named* — and neither is a skill that has been
**demoted** down to 1★ (e.g. the § 2.4 hard-reset). Its contributor handle is
therefore **redacted** ("classified" look) on every **public** surface until it
earns Named (2★+) standing:

- **Visible text** — the handle renders as a slate redaction marker
  (`████████` in monospace contexts, `@[anonymous]` in proportional ones),
  never the honor-red Origin handle.
- **Paths / artifacts** — a pre-named skill owns no shareable public artifact
  (per-skill badge, OG card, registry-manifest entry), and an *entirely*
  pre-named contributor (no skill above 1★) gets no public badge directory.
- **Origin** — a ≤1★ entry cannot hold Origin standing (§ 4.1); it is never a
  bucket's champion/representative.
- **Exception — the contributor's own profile** (`docs/u/<handle>/`): pre-named
  and demoted skills stay *listed* with their real rank and timeline so the
  Hero's Journey (§ 5) and ownership remain visible — but the plaque is
  redacted (slate, never honor-red).

The threshold and placeholders live in one place per runtime
(`src/gaia_cli/redaction.py`, mirrored in `docs/js/atlas-helpers.js`). The
invariant is **enforced in CI** by `scripts/validate_redaction.py` (run via
`gaia validate` and the release workflow), which fails the build if any ≤1★
handle leaks into a generated public asset — or if a 2★+ skill is
over-redacted.

---

## 2. Evidence Methodology (The Trust Stack)

Evidence is evaluated on two orthogonal axes — **Evidence Type** (provenance) and **Evidence Grade** (quality) — plus a skill-level **Overall Trust Grade** derived from the full evidence inventory. The legacy `class` axis is deprecated but still accepted during the migration window (see §2.1 below).

### 2.1 Evidence Class (deprecated — fallback only)

The original single-axis encoding conflated provenance and quality into one letter:

- **Class A (Peer-Reviewed)**: Published papers (arXiv, journals), large-scale adoption (10k+ stars), or official vendor documentation.
- **Class B (Reproducible Demo)**: Public repositories with clear installation steps, tests, and video/log evidence.
- **Class C (Credible Demo)**: Blog posts, social media demos, or "coming soon" repositories with code.

**Status: deprecated.** The `class` field is retained in the schema until the next major release; new evidence should carry a `type` and a `grade` instead. The promotion engine reads `grade` first; `class` is the fallback. Class A/B are **not** Grade A/B — never equate the two. See `CONTEXT.md` § Evidence Class.

### 2.1a Inherited Capability Pool (Starless evidence)

Evidence attaches at two levels:

- **Starless (generic) references** hold the **capability-level** evidence — Class A / academic provenance for the abstract capability itself (the foundational paper, the canonical technique). This is the **inherited capability pool**: every named child of a starless ref inherits this evidence automatically as the baseline for the capability they implement.
- **Suite components** identified by `suiteRef` may also receive a limited inherited repository-wide baseline from `github-stars-own` and `repo-own` evidence at the suite capstone, with a combined cap of **50 TM per component**. This baseline cannot alone make a component A or S; component-specific `benchmark-result`, `peer-review`, and `verifier-attestation` rows remain fully eligible.
- **Named skills** add their own **implementation-specific** evidence (their repo, tests, adoption, demos) on top of the inherited pool. A named skill's rank is gated by its *own* implementation evidence, not by the inherited capability or suite baseline alone.

This keeps the starless reference rank-less while still letting it carry the shared academic backing that justifies the capability's existence in the graph. Generic-layer inheritance remains governed by each evidence type's `allowedLayers` and `inheritMultiplier`; the `suiteRef` baseline is a separate bounded component rule.

> **Upcoming meta shift.** Per-named **evidence-floor enforcement** (validating each named child's own evidence against the floor for its claimed star, independent of the inherited pool) and finer-grained **advanced evidence tiers** are on the roadmap. The model above is the current, forward-looking direction — exact enforcement thresholds will be settled in a future meta shift.

### 2.1b Evidence Type + Evidence Grade (G7 dual axis)

Per the G7 Trust Taxonomy RFC, each evidence row carries two independent fields:

- **Evidence Type** — *where* the demonstration comes from (provenance). Values are kebab-case and list-driven from `registry/schema/meta.json` `evidence.types`; current examples include `arxiv`, `repo-own`, `github-stars-own`, and `benchmark-result`. Always write the full phrase "Evidence Type"; never the bare word "type", which names the skill taxonomy field (basic / fusion).

- **Evidence Grade** — *how strong one demonstration is*, on an **S / A / B / C** scale (Platinum / Gold / Silver / Bronze). For a typed row with quantitative magnitude inputs, the CLI computes that row's `artifact_score` and grades it against the Evidence-Type-specific thresholds in `registry/schema/meta.json` `evidence.perRowGradeThresholds`, subject to the Evidence Type's `gradeCeiling`. There is intentionally no single flat per-row threshold table.

- **Legacy/fallback `--trust` path** — `gaia dev evidence --trust <number>` stores the row's `trustNumber`. When a typed row produces a positive `artifact_score`, the typed per-row calculation above takes precedence. When the row has no magnitude drivers (`artifact_score == 0`), or has no Evidence Type, the CLI falls back to `evidence.gradeThresholds` (S ≥ 250, A ≥ 100, B ≥ 50, C ≥ 20; below 20 is ungraded). This compatibility input does not itself mean that the number is the skill's Trust Magnitude.

Evidence Grade A/B is deliberately distinct from deprecated Class A/B and from the skill-level Overall Trust Grade.

The `grade` field is the primary read target for all promotion gates; `class` is the legacy fallback. A row carrying both fields is evaluated on `grade` alone.

### 2.1c Trust Magnitude formula (G7 RFC summary)

The G7 RFC replaces the legacy `trustNumber` aggregate with **Trust Magnitude** — an unbounded, set-bonus-driven score derived from a fixed taxonomy of ten evidence types. Each evidence row produces an **artifact score** (`magnitude × weight × freshness`); the skill's Trust Magnitude is the sum of artifact scores across all rows.

Key mechanics (summary; see `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` for the full spec):

- **Overall Trust Grade thresholds:** S requires Trust Magnitude ≥ 250, A ≥ 100, B ≥ 50, C ≥ 20. These numeric cutoffs are also reused by the legacy/fallback `--trust` row path above, but the meanings remain distinct: one grades a fallback row input, while the other grades the accumulated skill-level TM.
- **Scoring:** TM sums positive-scoring evidence rows only. `fusion-recipe` is retained as structural/provenance/rank metadata and contributes **0 TM**.
- **Benchmark lanes (#1419):** `benchmark-result` magnitude uses `percentile` when present, otherwise normalized `score`, then applies lane multiplier: `verified` 2.0×, `reported` 1.0×, `rejected` 0×. Catalog `status: rejected` is the blacklist. This is pre TM Index V2; fusion scoring changes are separate.
- **S gate:** S requires TM ≥ 250, at least 3 distinct positive-scoring Evidence Types, and a positive eligible independent witness from `benchmark-result`, `verifier-attestation`, or `peer-review`. `github-stars-own`, `repo-own`, `fusion-recipe`, `self-attestation`, `social-signal`, `arxiv`, and `proxy-containment` are not S witnesses.
- **Fusion/rank structure:** suite membership, origin counts, nested suites, graph traversal, and Apex predicates remain structural. `fusion-recipe` does not count toward Trust Grade diversity. Structural composition is reported by the **Fusion Score** (§2.1e), a second, independent scalar that contributes nothing to TM.
- **Same-source dedup:** multiple evidence rows pointing at the same URL collapse to one.
- **Fork-network canonicalization:** forks of a repo share one star pool unless `links.canonicalRepo` is set explicitly.
- **Null-on-derank verifier:** when a 4★+ Verifier loses rank, their attestations evaluate to null (not flagged, not zero — null); the skill's Trust Magnitude is recomputed without those rows.

The Overall Trust Grade is computed at the skill level from the accumulated Trust Magnitude and is **never stored on a node** — it materialises only in generated catalogs. Distinct from any single row's Evidence Grade.

**Implementation status (updated 2026-06-20):** the Trust Magnitude formula is **live in code** as of Phase 1.5 (`src/gaia_cli/trustMagnitude.py`). Migration regrade has run across all 249 named skills; current distribution is **S=4 / A=42 / B=56 / C=76 / ungraded=71** (post-I11 source-curation pass). The public Trust Magnitude leaderboard at `/trust/leaderboard/` reads `docs/graph/leaderboard/data.json`. The recalibration RFC v3 (depth-2 amendments, evidence-tier weights) is scheduled for follow-up — tracked in issue #749.

### 2.1d Anti-auto-mint clause (registry-wide)

Per G7 RFC §10.14: every non-fusion-recipe evidence row must be **physically present** in the skill's `evidence:` array. No phantom rows. A grade that cannot be traced back to an explicit row in the array is invalid. The sole exception is the fusion-recipe entry generated automatically for suites; it is structural metadata only and scores 0 TM.

### 2.1e Fusion Score (Yggdrasil III structural scalar)

Yggdrasil III ratifies a **second** numeric reading. This supersedes the earlier §2.1c sentence stating that no Fusion/Composition scalar is introduced; the rest of the Yggdrasil III trust ruling stands unchanged.

| Reading | Question answered | Inputs | Promotion authority |
|---|---|---|---|
| **Trust Magnitude** | How much corroborating evidence supports this named implementation? | positive-scoring evidence rows, under the existing witness and diversity rules | the existing TM / Trust Grade gates |
| **Fusion Score** | How much distinct structure does this capability compose? | canonical prerequisite, suite-component, and origin structure | **none** — informational in V1 |

**Trust Magnitude keeps sole promotion authority.** Fusion Score is not an Evidence Type, an evidence row, a Trust Grade ingredient, a TM multiplier, or a substitute for an Apex predicate. `fusion-recipe` still contributes **0 TM** and still satisfies neither TM diversity nor the independent-witness requirement.

**Independence is the contract.** TM must not move when Fusion Score moves; Fusion Score must not move when evidence, stars, Trust Grade, or TM move while the underlying structure is unchanged. Locked by `tests/test_fusion_score.py`.

**Inputs** resolve from canonical graph fields, in order: (1) the starless generic node's `prerequisites`, reached via a Named Skill's `genericSkillRef`; (2) the Named Skill's `suiteComponents`; (3) explicit `fusion-recipe` origins, as a compatibility fallback only. Entries are deduplicated by canonical skill ID, `role: variant` is excluded, the root ID is excluded, cycles are guarded, and the closure walks to a declared traversal limit. Evidence Grade, Overall Trust Grade, TM, repository stars, rank, and source freshness are **never** inspected.

**Formula** (`yggdrasil-iii-v1`), where `N` is the count of distinct non-variant nodes in the resolved closure:

```text
FS = 0                          when N = 0
FS = 20 × N                     when 1 ≤ N ≤ 10
FS = 200 + 20 × sqrt(N - 10)    when N > 10
```

The former `fusion-recipe` evidence weight (`1.5×`), TM cap, freshness factor, grade filter, set bonus, and Trust Grade threshold are all deliberately **absent** — they belonged to evidence aggregation and would recreate the coupling Yggdrasil III removed. Results are rounded to two decimals so Python, CLI text, and JSON stay byte-stable.

**Persistence boundary:** the registry stores the structural *inputs*, never the derived answer. `fusionScore` is **not** written to Named Skill frontmatter or canonical node JSON. It is computed in one Python authority (`src/gaia_cli/fusionScore.py`, over the neutral traversal in `src/gaia_cli/structuralGraph.py`) and serialized only into generated projections (`registry/named-skills.json` → `docs/graph/named/index.json`, and `docs/api/v1/`). Browser code consumes the generated value and breakdown; it carries no second formula.

**Why the public numbers moved.** Under Yggdrasil II a `fusion-recipe` row poured its structure straight into Trust Magnitude, so a large suite carried a large TM. Yggdrasil III fixed that row at 0 TM — which is why TM fell for suites and fusions even though no evidence row, star count, or rank was edited. The structure did not disappear; it is reported as Fusion Score instead. **Every surface that prints a Fusion Score must also state this**, so a returning reader cannot mistake the movement for a demotion.

### 2.2 The "Prestige Pivot" Roadmap (RFC #457)

- **Web of Trust**: Contributors holding a **4★+** skill may act as "Verifiers" for new evidence, reducing reliance on central maintainers. Verified evidence is marked in the schema and visualized in the Skill Explorer history.
- **Liveness Heartbeat**: Automated monthly checks for URL health and repository activity. Dead or inactive repositories are flagged for demotion. Stable, "finished" software with Class A/B evidence is protected from rot demerits.
- **Specialist Path**: A rubric allowing vendor-locked skills (e.g., Palantir, Salesforce) to reach 4★+ by proving "Depth of Integration" (robustness and production usage) rather than general portability.

### 2.3 Specialist Path Rubric (4★+ Promotion)
To reach 4★ or higher as a Specialist (vendor-locked) skill, the implementation must meet the **Depth of Integration** bar:
1. **Production Evidence**: Documented usage in a real-world production environment (Case study, blog post, or Class A/B evidence).
2. **Robustness**: Comprehensive test suite covering edge cases of the vendor's API/Platform.
3. **Documentation**: Detailed "How-to" and "Reference" docs specifically for the vendor-locked context.
4. **Maintenance**: Active updates or a "Stable/Finished" status with verified liveness.

### 2.4 Meta-Audit & Curation Standards
- **4★+ Evidence Verification**: Seed evidence (e.g., placeholder files in the gaia repo) is insufficient. 4★+ skills MUST have live, verifiable usage evidence.
- **Specific URL Requirement**: Links for named claims must point to concrete implementation files (`SKILL.md`, source code, etc.), not generic repository roots.
- **Installability (The Star Bar)**: 
  - **0★–2★**: Allowed to be registry-only (`installable: false`).
  - **3★+**: MUST have a verified GitHub **blob** link pointing to a concrete file (e.g. `.../blob/<branch>/.../SKILL.md`), not a bare repo root. Any 3★+ skill lacking a verified blob link is **hard-demoted to 1★ (Awakened)** and must re-earn its rank with a valid link. *(Updated 2026-06-02: hardened from 2★ to 1★ — a missing verified blob link is a hard reset, not a soft step-down.)*
  - **Suites**: Exempt from individual link requirements if components are linked.

---

## 3. Effective Level & Demerits

The **Canonical Level** (e.g., 4★) is the claimed tier based on evidence. The **Effective Level** is the level used for runtime advice and fusion, adjusted by demerits.

### 3.1 Canonical Demerits
- **`broken-evidence`**: URL(s) in the evidence array are dead or inaccessible.
- **`niche-integration`**: Tied to a narrow or obscure platform.
- **`experimental-feature`**: Unstable API or alpha-status code.
- **`heavyweight-dependency`**: Requires massive local resources or complex setup.

**Rule**: Each demerit lowers the Effective Level by **1 star**, floored at **0★**.

---

## 4. Governance & Promotion

### 4.1 Named Skill Promotion
- **Awakened**: Initial intake state. Verified as a real skill.
- **Named**: Promoted by a reviewer once a unique RPG `title` or `catalogRef` is assigned.
- **Origin Status**: The **most renowned** implementation in a generic bucket earns "Origin" — the highest-rated named skill (ties broken by most-attributed / Trust Score), **not** necessarily the earliest. An early implementation may be **superseded** when a stronger one earns the rank. Origin is a mark of merit granted to the implementation that earned it, in keeping with the product motif. Exactly one Origin exists per bucket. *(Updated 2026-06-02: Origin is merit-based; this supersedes the earlier "first contributor / earliest" rule, since an early entry can be outclassed by a better one.)*

### 4.2 Suite-Branch 5★/6★ Pathways
- **Suite 5★ Ultimate pathway**: Proposer must hold Origin status on at least 1 of the ≥ 5 `suiteComponents`. Trust Magnitude ≥ 250 (S-grade) required from scoring evidence; suite membership and origin status remain structural/rank metadata. The legacy "≥ 10k repository stars" hard-requirement is retired under Yggdrasil II.
- **The Ascension Cycle (6★ Apex, Suite branch)**: Reaching **Apex** requires TM ≥ 250 (S-grade) and the full 6-predicate gate (§4.3), including at least one direct component that is itself a suite. Any skill recorded at 6★ before the G7 cutover was subject to demotion review against the original 9-predicate gate at migration time; the active set is now 6 predicates (§4.3).

### 4.3 Apex (6★) Gate — 6-Predicate Requirements (active set, post-2026-06-17 delta)

Reaching or retaining 6★ Apex rank requires satisfying the six **active** predicates from the G7 Trust Taxonomy RFC (`founder/handovers/G7_TRUST_TAXONOMY_RFC.md` §11.12). The original RFC defined nine predicates; per the 2026-06-17 delta (`founder/handovers/G7_HANDOVER_DELTA_2026-06-17.md`) two were moved behind a feature flag (`crossOrgVerifierGte2`, `systemWideCapRespected`) and one was reframed as a sign-off gate. The active set is:

1. **§11.12.1 — ≥ 5 A-graded origins** in the transitive `suiteComponents` closure (deduplicated).
2. **§11.12.2 — ≥ 1 direct component with `suiteComponents`** (at least one direct child is itself a suite).
3. **§11.12.3 — ≥ 1 node reachable only at depth ≥ 2.** As of I12 (2026-06-20) the depth-2 walker includes overlap with depth-1 — the prior strict-no-overlap rule was relaxed; cycle-self guard kept. Awaits RFC v3 ratification (issue #749).
4. **§11.12.4 — Overall Trust Grade S** (Trust Magnitude ≥ 250).
5. **§11.12.7 — Tenure ≥ 180 days.** Earliest evidence row's `sourceStartedAt` must be at least 180 calendar days old. The `gaia dev evidence --source-started-at YYYY-MM-DD` flag (I12) populates this field.
6. **§11.12.8 — `apexPromotionPrSigned`** by Marco (the verifier) on the named skill's frontmatter `apexGateStatus`. Stamped via PR review, not auto-derived.

**Feature-flagged (not enforced today):**
- §11.12.5 cross-org verifier ≥ 2 — gated on `crossOrgVerifierGte2` flag; awaits Verifier-Signoff sub-system.
- §11.12.6 system-wide cap of 5 concurrent 6★ — gated on `systemWideCapRespected` flag.

Enforcement is **live in code** as of Phase 1.5 (`src/gaia_cli/trustMagnitude.py::checkApexGate*` family). Top-4 S-grade skills (`garrytan/gstack`, `ruvnet/ruflo`, `mattpocock/skills`, `obra/superpowers`) currently pass 4/6 predicates each — §11.12.1 (A-graded origins) and §11.12.7 (tenure) await deeper origin curation and historical `sourceStartedAt` backfill respectively.

The G7 RFC is the normative spec; META.md is a summary.

### 4.4 Unique Impossible (6★) Gate — Provisional 5-Predicate Requirements (Unique branch)

Under Yggdrasil II there are **two distinct 6★ paths**, one per branch:

- **Suite branch → 6★ Apex** — the 6-predicate gate in §4.3.
- **Unique branch → 6★ Unique Impossible** — the **5-predicate gate**: the Apex set **minus `directNestedSuiteGte1`** (§11.12.2). A Unique-branch skill has no `suiteComponents` by definition, so the directly-nested-suite composition-depth predicate does not apply; the remaining five carry over unchanged. Yggdrasil III ratifies this branch distinction without changing the existing rank gates.

The five active Unique Impossible predicates:

1. **§11.12.1 — ≥ 5 A-graded origins** in the transitive origin closure (deduplicated; `role='origin'` only — pure suite variants do not count).
2. **§11.12.3 — ≥ 1 node reachable only at depth ≥ 2** (provenance depth, not installation breadth; suite-only reachability excluded).
3. **§11.12.4 — Overall Trust Grade S** (Trust Magnitude ≥ 250 with the diversity gate satisfied).
4. **§11.12.7 — Tenure ≥ 180 days** (earliest A/S evidence row's public source continuously available ≥ 180 calendar days).
5. **§11.12.8 — `apexPromotionPrSigned`** by the verifier at promotion time (sole human-attestation gate during bootstrap; cosigner quorum once cross-org verifiers exist).

**Dropped for the Unique branch:** §11.12.2 `directNestedSuiteGte1` (no nested suite exists on a Unique skill). **Feature-flagged OFF (both branches):** §11.12.5 `crossOrgVerifierGte2` and §11.12.6 `systemWideCapRespected` — return skipped, not failed, until 2026-Q4 review.

The Evidence Floor requirement has been retired: **Trust Magnitude is the sole promotion gate** on both branches. Yggdrasil III keeps rank predicates structural and separate from TM: fusion/rank structure does not mint scoring evidence. The branch-aware split is authoritatively rendered in `docs/codex/trust-methodology.html` §5; META.md mirrors it.

---

## 5. Rank History (The "Hero's Journey")

Every named implementation tracks its evolution through the `timeline` schema property.

> **Transparency Mandate — every event is on the record.** No rank change may be
> untracked. Every promotion, demotion, fusion, or evidence update **must** emit a
> timeline event so the Hero's Journey tells the whole truth; a star that drops
> with no `demote` event is a transparency failure, not a cosmetic one. This is
> the other half of the Programmatic-First culture (CONTEXT.md § Registry
> Management, PRODUCT.md Design Principle 6): prefer the CLI because it logs the
> event for you. The change is mirrored to **both** the registry node
> (`registry/named/**/*.md`) and the owning contributor's user tree
> (`skill-trees/<owner>/skill-tree.json`) — the latter is what the public profile
> charts. The **Transparency Gate** (`scripts/validate_timelines.py`, run in
> `gaia validate` and release CI) fails any build whose timeline cannot explain a
> skill's current rank; reconcile drift with the `/gaia-trace-timeline` skill.

### 5.1 Timeline Events

The following `action` values are defined in `registry/schema/skill.schema.json` and `registry/schema/namedSkill.schema.json`:

- **`propose`**: Initial 2★ submission.
- **`rank_up`**: Promotion to a higher star tier.
- **`demote`**: Star tier reduction due to audit or evidence rot.
- **`verified`**: Successful peer verification of evidence.
- **`disputed`**: Active challenge to the skill's rank or evidence.
- **`fuse`**: Skill produced by or contributing to a fusion.
- **`name`**: Skill transitions from Awakened to Named status.
- **`ascend`**: Skill reaches 6★ Apex rank.
- **`evidence_added`**: Recorded when an evidence row is added; the first such event sets `verification.firstEvidenceAt` which is the tenure baseline for the enterprise-ready verification tier (G4).
- **`evidence_removed`**: Recorded when an evidence row is retracted.
- **`evidence_graded`**: Recorded when an evidence row's grade is updated.
- **`security_scan_passed`**: Recorded when a skill's content passes the defensive security scanner clean. Read by the `security-reviewed` verification tier (G4). The scanner-to-timeline emit wiring is a follow-up PR; the action enum entry is live in the schema as of PR #709.
- **`type_change`**: Recorded when the skill's taxonomy type changes (e.g. `basic` → `fusion`). Under Yggdrasil II the only valid type values for starless nodes are `basic` and `fusion`.
- **`apex_pr_signed`**: Recorded when a verifier signs the apex-promotion PR for a 6★ candidate (G7 RFC §11.12.8). Sets `apexGateStatus.apexPromotionPrSigned` on the named skill. Ratified in v3 (`founder/handovers/G7_RFC_V3_RATIFICATION_2026-06-20.md`).

---

## 6. Master Skill Fusion & Pruning

To maintain high prestige and avoid "Vendor Bloat," Gaia employs a proactive pruning strategy.

### 6.1 Champion System
- Multiple implementations of the same `genericSkillRef` are grouped together.
- The implementation with the highest **Trust Score** (social proof + liveness) is featured as the **Champion**.
- Other implementations remain accessible as variants but do not clutter the primary graph view.

### 6.2 Semantic Fusion
- When multiple distinct named skills represent specialized capabilities that can be orchestrated in a single high-level workflow, they are fused into a new **`fusion`-type** generic skill. Fusion is composition/provenance/rank structure, not scoring evidence.
- The original `basic` nodes are linked as prerequisites, and the composite named implementations are promoted to higher star tiers (3★ or 4★).

---

## 7. Source of Truth Files

- **`registry/nodes/*.json`**: Canonical generic (starless) skill-reference definitions — rank-less taxonomy nodes plus their inherited capability-evidence pool (Managed via `gaia dev`).
- **`registry/named/**/*.md`**: Named implementations and their meta-tags.
- **`registry/schema/meta.json`**: Central registry for nomenclature, colors, symbols, and floors.
- **`registry/gaia.json`**: Generated artifact; do not hand-edit.
- **`src/gaia_cli/verification.py`**: 4-tier verification predicates (G4): community-verified, benchmark-verified, security-reviewed, enterprise-ready.
- **`src/gaia_cli/securityScanner.py`**: Defensive 5-detector security scanner (G3): shellExec, destructiveFs, outboundNet, promptInjection, credentialHarvesting.
- **`docs/architecture/benchmark-framework.md`**: Benchmark Framework RFC (G7) — reproducibility model, category taxonomy, and score-to-grade mapping for `benchmark-result` evidence rows.
- **`founder/handovers/G7_TRUST_TAXONOMY_RFC.md`**: Trust Magnitude formula, ten evidence types, diversity gate, and 9-predicate Apex gate (normative spec).

---

## 8. Implementation Status Tracker

| Feature | Status | Tracking |
|---|---|---|
| Star Tiers (0★–6★) | ✅ Implemented | `registry/schema/meta.json` |
| Demerits & Effective Level | ✅ Implemented | `GOVERNANCE.md` |
| Unique-branch Promotion (4★+, no `suiteComponents` on parent) | ✅ Implemented | `CONTRIBUTING.md` |
| Suite-branch 5★ gate (`suiteComponents`, TM ≥ 250) | ✅ Implemented | `GOVERNANCE.md` |
| Timeline Schema | ✅ Implemented | `registry/schema/namedSkill.schema.json` |
| Web of Trust / Verification | ✅ Implemented | [Issue #457](https://github.com/gaia-research/gaia-skill-tree/issues/457) |
| Liveness Heartbeat Script | ✅ Implemented | `scripts/verify_evidence.py` |
| Hero's Journey UI Tab | ✅ Implemented | `docs/js/skill-explorer.js` |
| Evidence `grade` field (S/A/B/C) reading | ✅ Implemented | PR #704 (G2) |
| Defensive Security Scanner | ✅ Implemented | PR #705 (G3) |
| Benchmark Framework RFC | ✅ Designed | PR #706 (G7) |
| 4-tier Verification Workflow | ✅ Implemented | PR #709 (G4) |
| `verification.firstEvidenceAt` write path | ✅ Implemented | PR #709 (G4) |
| Trust Magnitude formula in code | ✅ Implemented | `src/gaia_cli/trustMagnitude.py` (Phase 1.5, 2026-06-20) |
| 6-predicate Apex gate enforcement | ✅ Implemented | `trustMagnitude.py::checkApexGate*` (post-delta active set) |
| Public Trust Magnitude Leaderboard | ✅ Implemented | `docs/trust/leaderboard/` (Phase 1.5, I10) |
| `gaia dev evidence --source-started-at` (tenure baseline) | ✅ Implemented | `src/gaia_cli/main.py` argparse (Phase 1.5, I12) |
| `gaia dev evidence` numeric payload flags | ✅ Implemented | `src/gaia_cli/main.py` argparse (Phase 1.5, I9) |
| RFC v3 ratification (depth-2 + apex_pr_signed enum + tenure calibration) | 🟡 Pending | Issue #749, post-Phase-1.5 |
| 9→6 predicate Apex gate (cross-org + cap moved to feature flag) | ✅ Implemented | `G7_HANDOVER_DELTA_2026-06-17.md` |
| `security_scan_passed` timeline emit wiring | 🟡 Planned | Follow-up PR (G4 TODO) |
