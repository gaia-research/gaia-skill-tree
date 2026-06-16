# META: Gaia Registry Source of Truth

This document serves as the **single source of truth** for the Gaia Skill Registry's taxonomy, evidence methodology, and ranking strategy. It defines the "Meta" — the rules and standards that ensure Gaia remains a high-prestige, high-trust ecosystem for agent capabilities.

---

## 1. Core Taxonomy (The Hierarchy)

Gaia uses a tiered star system (`0★`–`6★`) to rank skills. Levels are both a measure of technical complexity and a mark of community prestige.

> **Stars live on named skills only.** Generic skill references are **starless** — rank-less taxonomy nodes that carry no stars of their own (see `CONTEXT.md` § Starless). A starless ref's *effective rank* is the top star among its named-skill children. The star table below therefore describes **named implementations**; the starless reference they map to has no level of its own and renders as *generic* (italic, greyed-out) in the UI.

### 1.1 Star Tiers & Rank Labels (named implementations)

> **Evidence Floor reads from `grade` first.** Per the G7 Trust Taxonomy RFC (`founder/handovers/G7_TRUST_TAXONOMY_RFC.md`, ratified 2026-06-16), evidence rows now carry a `grade` field (S/A/B/C, S strongest) as the primary quality signal. The promotion engine (`src/gaia_cli/promotion.py`) reads `grade` first and falls back to the deprecated `class` field (A/B/C legacy) during the migration window. The two axes are distinct — Grade A is not Class A; never conflate them. See `CONTEXT.md` § Evidence Class for the deprecation notice and §2.1b below for the full dual-axis description.

| Level | Label | Significance | Evidence Floor | Verification Tier (max) |
|---|---|---|---|---|
| **0★** | **Basic** | Pre-named primitive — a freshly scanned candidate against a starless reference. | None | — |
| **1★** | **Awakened** | Verified candidate, not yet named. | None | — |
| **2★** | **Named** | Minimum level for named implementations. | Grade C+ | community-verified |
| **3★** | **Evolved** | Demonstrates reproducibility and stability. | Grade B+ | community-verified / benchmark-verified |
| **4★** | **Hardened** | Production-ready, well-documented, reliable. | Grade B+ (rank-floor protected) | up to security-reviewed |
| **5★** | **Transcendent** | Mastery level, often an Ultimate capstone. | Grade B+ (rank-floor protected) | up to enterprise-ready |
| **6★** | **Apex** | The pinnacle of Gaia; extreme ecosystem impact. | Grade A+ + 9-predicate gate | enterprise-ready required |

### 1.2 Skill Types
- **○ Basic Skill**: Root primitives. 0 prerequisites.
- **◇ Extra Skill**: Composite workflows. Requires ≥ 2 prerequisites.
- **◉ Unique Skill**: Specialized depth. Level 4★+, 0 prerequisites, graph-isolated.
- **◆ Ultimate Skill**: Platform capstones. Requires ≥ 5 named prerequisites + Origin Fusion. **Requirement**: ≥ 10k repository stars.

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
- **Named skills** add their own **implementation-specific** evidence (their repo, tests, adoption, demos) on top of the inherited pool. A named skill's rank is gated by its *own* implementation evidence, not by the inherited capability evidence alone.

This keeps the starless reference rank-less while still letting it carry the shared academic backing that justifies the capability's existence in the graph.

> **Upcoming meta shift.** Per-named **evidence-floor enforcement** (validating each named child's own evidence against the floor for its claimed star, independent of the inherited pool) and finer-grained **advanced evidence tiers** are on the roadmap. The model above is the current, forward-looking direction — exact enforcement thresholds will be settled in a future meta shift.

### 2.1b Evidence Type + Evidence Grade (G7 dual axis)

Per the G7 Trust Taxonomy RFC, each evidence row carries two independent fields:

- **Evidence Type** — *where* the demonstration comes from (provenance). Values are kebab-case, list-driven from `registry/schema/meta.json` `evidence.types`. Initial canonical types: `arxiv`, `repo`, `github-stars`. The `benchmark-result` type is reserved by the Benchmark Framework RFC (`docs/architecture/benchmark-framework.md`). Always write the full phrase "Evidence Type"; never the bare word "type", which names the skill taxonomy field (Basic/Extra/Unique/Ultimate).

- **Evidence Grade** — *how strong* the demonstration is, on an **S / A / B / C** scale (Platinum / Gold / Silver / Bronze). Derived from the evidence row's `trustNumber` via `registry/schema/meta.json` `evidence.gradeThresholds` (S ≥ 90, A ≥ 80, B ≥ 60, C ≥ 40). Evidence whose `trustNumber` falls below 40 is **ungraded** — on the record but counting toward no gate. Grade A/B are deliberately distinct from the deprecated Class A/B.

The `grade` field is the primary read target for all promotion gates; `class` is the legacy fallback. A row carrying both fields is evaluated on `grade` alone.

### 2.1c Trust Magnitude formula (G7 RFC summary)

The G7 RFC replaces the legacy `trustNumber` aggregate with **Trust Magnitude** — an unbounded, set-bonus-driven score derived from a fixed taxonomy of ten evidence types. Each evidence row produces an **artifact score** (`magnitude × weight × freshness`); the skill's Trust Magnitude is the sum of artifact scores across all rows.

Key mechanics (summary; see `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` for the full spec):

- **Grade thresholds:** S requires Trust Magnitude ≥ 250, A ≥ 100, B ≥ 50, C ≥ 20.
- **Type weights:** `benchmark-result` 1.4×, `verifier-attestation` and `fusion-recipe` 1.5×, `repo-own` 0.6×, most others 1.0×.
- **Diversity gate:** S requires ≥ 3 distinct Evidence Types including at least 1 non-self-producible type. A contributor cannot reach S by stacking self-minted evidence alone.
- **Suite-fusion sqrt-softening:** fusion-recipe magnitude grows linearly to 10 origins then as `200 + 20 × sqrt(origins − 10)` past 10 to prevent runaway scores on large suites.
- **Same-source dedup:** multiple evidence rows pointing at the same URL collapse to one.
- **Fork-network canonicalization:** forks of a repo share one star pool unless `links.canonicalRepo` is set explicitly.
- **Null-on-derank verifier:** when a 4★+ Verifier loses rank, their attestations evaluate to null (not flagged, not zero — null); the skill's Trust Magnitude is recomputed without those rows.

The Overall Trust Grade is computed at the skill level from the accumulated Trust Magnitude and is **never stored on a node** — it materialises only in generated catalogs. Distinct from any single row's Evidence Grade.

**Note:** The current implementation in `src/gaia_cli/verification.py` uses MAX-grade across evidence rows as a proxy for the Overall Trust Grade until the full Trust Magnitude formula lands in code. The full formula is targeted for a recalibration RFC (scheduled 2026-07-10).

### 2.1d Anti-auto-mint clause (registry-wide)

Per G7 RFC §10.14: every non-fusion-recipe evidence row must be **physically present** in the skill's `evidence:` array. No phantom rows. A grade that cannot be traced back to an explicit row in the array is invalid. The sole exception is the fusion-recipe entry generated automatically for suites — all other types must be explicitly declared.

### 2.2 The "Prestige Pivot" Roadmap (RFC #457)

- **Web of Trust**: Contributors holding a **4★ (Hardened)** skill may act as "Verifiers" for new evidence, reducing reliance on central maintainers. Verified evidence is marked in the schema and visualized in the Skill Explorer history.
- **Liveness Heartbeat**: Automated monthly checks for URL health and repository activity. Dead or inactive repositories are flagged for demotion. Stable, "finished" software with Class A/B evidence is protected from rot demerits.
- **Specialist Path**: A rubric allowing vendor-locked skills (e.g., Palantir, Salesforce) to reach 4★+ by proving "Depth of Integration" (robustness and production usage) rather than general portability.

### 2.3 Specialist Path Rubric (4★+ Promotion)
To reach Hardened (4★) or higher as a Specialist (vendor-locked) skill, the implementation must meet the **Depth of Integration** bar:
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

### 4.2 Ultimate & Apex Pathways
- **Ultimate Fusion**: Proposer must hold Origin status on at least 1 of the 5+ named prerequisites. Requires ≥ 10k repository stars.
- **The Ascension Cycle (6★ Apex)**: Reaching the **Apex** rank requires Grade A evidence AND that the skill is the product of a fusion involving at least one **Origin 5★ Transcendent** skill. Additionally, any skill currently recorded at 6★ before the G7 cutover will be subject to demotion review against the new 9-predicate gate (§4.3) at migration time.

### 4.3 NEW: Apex (6★) Gate — 9-Predicate Requirements

Reaching or retaining 6★ Apex rank requires satisfying all nine predicates enumerated in the G7 Trust Taxonomy RFC (`founder/handovers/G7_TRUST_TAXONOMY_RFC.md` §10.12). The predicates are:

1. **≥ 12 nested origins** — transitive `suiteComponents` closure, deduplicated, each graded ≥ C.
2. **≥ 1 direct nest** — at least one direct component must itself be a suite or Ultimate skill.
3. **≥ 1 deep-nested origin** — at least one origin reachable only through nesting, not also a direct component.
4. **Trust Magnitude ≥ 250** from physically-present evidence rows (no phantom rows; anti-auto-mint clause §2.1d applies).
5. **≥ 8 nodes in the closure** with Overall Trust Grade ≥ A.
6. **≥ 2 verifier cosigns** from 2 distinct GitHub organizations.
7. **≥ 180-day tenure** — earliest evidence row must be at least 180 calendar days old.
8. **PR-gated promotion** — must carry the `apex-promotion` label and receive ≥ 2 verifier sign-offs in the PR.
9. **System-wide cap of 5** concurrent 6★ Apex skills.

The G7 RFC is the normative spec; META.md is a summary only. Enforcement of all nine predicates in code is scheduled as post-recalibration work (see §8 implementation status).

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
- **`type_change`**: Recorded when the skill's taxonomy type changes (e.g. `basic` → `unique`).

---

## 6. Master Skill Fusion & Pruning

To maintain high prestige and avoid "Vendor Bloat," Gaia employs a proactive pruning strategy.

### 6.1 Champion System
- Multiple implementations of the same `genericSkillRef` are grouped together.
- The implementation with the highest **Trust Score** (social proof + liveness) is featured as the **Champion**.
- Other implementations remain accessible as variants but do not clutter the primary graph view.

### 6.2 Semantic Fusion
- When multiple distinct named skills represent specialized capabilities that can be orchestrated in a single high-level workflow, they are fused into a new **Extra (Master)** generic skill.
- The original basic skills are linked as prerequisites, and the composite named implementations are promoted to higher star tiers (3★ or 4★).

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
| Unique Skill Promotion | ✅ Implemented | `CONTRIBUTING.md` |
| Ultimate Fusion Criteria (5-Prereq) | ✅ Implemented | `GOVERNANCE.md` |
| Timeline Schema | ✅ Implemented | `registry/schema/namedSkill.schema.json` |
| Web of Trust / Verification | ✅ Implemented | [Issue #457](https://github.com/mbtiongson1/gaia-skill-tree/issues/457) |
| Liveness Heartbeat Script | ✅ Implemented | `scripts/verify_evidence.py` |
| Hero's Journey UI Tab | ✅ Implemented | `docs/js/skill-explorer.js` |
| Evidence `grade` field (S/A/B/C) reading | ✅ Implemented | PR #704 (G2) |
| Defensive Security Scanner | ✅ Implemented | PR #705 (G3) |
| Benchmark Framework RFC | ✅ Designed | PR #706 (G7) |
| 4-tier Verification Workflow | ✅ Implemented | PR #709 (G4) |
| `verification.firstEvidenceAt` write path | ✅ Implemented | PR #709 (G4) |
| Trust Magnitude formula in code | 🟡 Planned | Recalibration RFC 2026-07-10 |
| 9-predicate Apex gate enforcement | 🟡 Designed | G7 RFC, post-recalibration |
| `security_scan_passed` timeline emit wiring | 🟡 Planned | Follow-up PR (G4 TODO) |
