# Gaia Governance

This document outlines how the Gaia Skill Tree registry is managed, how decisions are made, and how disputes are resolved.

**Yggdrasil IV:** [Ratified trust degradation, challenge and recovery doctrine](founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md) applies. `META.md` §4.1 is authoritative for **merit-based current Origin**. Policy ratification does not authorize automatic score, evidence or rank changes.

## 1. Maintainer Roles

### 1.1 Taxonomy Maintainers
Taxonomy Maintainers are responsible for:
- Reviewing and merging skill submissions.
- Ensuring graph integrity (DAG correctness, reference validity).
- Verifying evidence quality against the Gaia Evidence Policy.
- Managing reclassifications and deprecations.

### 1.2 Plugin Maintainers
Plugin Maintainers are responsible for:
- Developing and maintaining the Gaia CLI and GitHub Action.
- Ensuring compatibility with various agent frameworks and repos.
- Optimizing scan performance and accuracy.

### 1.3 Core Maintainers
Core Maintainers have final approval authority and manage:
- Project vision and roadmap.
- Repository settings and branch protection.
- Dispute resolution.
- 5★ Ultimate / 6★ Apex rank validation (requires two Core Maintainer approvals). See [META.md](META.md#42-suite-branch-56-pathways) for the technical promotion criteria.

### 1.4 Verifiers
Verifiers are trusted members of the community who hold at least one **4★ (Extra / Unique)** skill implementation. They have the authority to:
- Review evidence for new skill submissions.
- Mark evidence as `verified` or `disputed` via the `gaia dev verify` command.
- Verification from a Verifier reduces the requirement for Maintainer review for 3★ promotions.
- 4★+ promotions still require final Maintainer sign-off, but Verifier confirmation is the primary weight in that decision.

## 2. Decision Making

Decisions are made through Pull Requests. Most PRs require one Maintainer approval.
- **Basic / Fusion nodes**: 1 Maintainer approval.
- **5★ Ultimate / 6★ Apex promotions**: 2 Core Maintainer approvals. (named-fusion criteria apply — see §2.2)
- **Schema Changes**: 2 Core Maintainer approvals.
- **Named Skills**: 1 Maintainer approval (standard intake process, then `gaia propose` promotion).

## 2.1 Named Skill Governance

### Naming Rights
- An initial approved claim may create the **first current Origin**, but `META.md` §4.1 governs ongoing merit-based selection of the most renowned qualified Named Skill.
- There is **exactly one current Origin per claimed, eligible generic node**. A challenge cannot vacate it; a qualified successor may assume Origin via approved transfer at any time.
- **Historical Origin attribution remains permanent; current Origin ownership is transferable.** Another implementation can earn current Origin without erasing the earlier holder's achievement.

### Promotion Process
- A skill must first be accepted via the standard intake review process (lifecycle: "awakened").
- Promotion from "awakened" to "named" requires a contributor to run `gaia propose` and open a PR.
- Generic nodes are starless. Named implementations hold their own level; no 2★ generic level floor is inferred.
- Canonical level remains the source of truth for promotion gates; effective level is a visibility signal used by runtime projections and advisor surfaces.
- Existing valid demerits use `META.md` §3.1's **0★** effective floor, not the stale 1★ floor. Neither age nor unverified link failure can automatically create a demerit.

### Named Skill Disputes
- Competing current Origin claims are adjudicated according to **merit and qualification**, not earliest `createdAt`. Preserve historical attribution and the exactly-one-current-Origin invariant.
- Disputes follow the same 14-day resolution process as generic skill disputes (see § 3).

### Unclaimed Capstone Claiming
- Unclaimed Fusion capstones appear as `◆ /skill-id [Unclaimed ✦]` in the registry — no named implementation exists yet.
- The first contributor to run `gaia propose` against an awakened intake record whose `genericSkillRef` points to an unclaimed Fusion capstone automatically becomes the origin contributor and the seed title stored in `gaia.json` becomes visible in projections.
- Simultaneous initial claims require a recorded maintainer decision establishing one current holder; earlier chronology cannot permanently override later merit-based selection.
- Once claimed, the display changes from `[Unclaimed ✦]` to `Ultimate Skill: contributor/skill-name`.

## 2.2 Fusion Capstone Promotion

Technical requirements for the 5★ Ultimate and 6★ Apex ranks (prerequisite counts, origin fusion, and Trust Magnitude gates) are maintained in the central meta-strategy document. The per-star Evidence Floor is retired under Yggdrasil II — Trust Magnitude is the sole promotion gate.

> **Technical Specification:** See [META.md](META.md#42-suite-branch-56-pathways) for promotion pathways and the Grandmaster path criteria.

### Reclassification Notice
Existing capstones registered under the old 3-prerequisite rule that do not meet the current criteria keep `type: fusion` and are re-ranked down the shared ladder in a `review/meta/` follow-up PR. (`extra` is a retired Yggdrasil I type; the type axis is `{basic, fusion}` only.)

## 3. Dispute Resolution

If a skill's definition, level, or evidence is disputed:
1. Authenticate and independently verify the specific counterclaim. Publish a **verified** challenge immediately after verification (operational target: within 24 hours); notify the contributor. Preserve exact task, version, method and limitations.
2. Provide an ordinary **14-calendar-day** contributor response opportunity for rebuttal or upstream improvement; no automatic demotion by timeout. Availability concerns use bounded repeat probes before unavailability debt.
3. Steward watches challenged implementation and comparator where traceable. **Class B** may close an objectively reproduced **technical** challenge with independent proof and a linked public receipt, including before the response window ends. It cannot change canonical evidence assertions, TM/Grade, stars, Origin or policy.
4. **Class C / Core Maintainer** adjudicates ambiguous superiority, material ranking, Origin transfer and all canonical trust or evidence consequences, taking the entire scope and proof into account rather than a grade letter alone.
5. Preserve the public challenge, contributor response, adjudication, recovery and appeal chain. A formerly valid challenge may be superseded by independently proven improvements.

## 4. Audit Schedule

### 4.1 Quarterly Re-Audit
Every 90 days, the maintainers will conduct a full re-audit of the registry to:
- Review `provisional` skills for potential validation.
- Re-assess `disputed` skills.
- Verify 5★ Ultimate / 6★ Apex rank requirements.
- Identify potentially stale evidence and open investigation debt; inactivity or elapsed time alone never causes published trust degradation.

### 4.2 Audit Disentanglement & Imposter Taxonomy
To protect legitimate early-stage, self-hosted, and prototype skills from being conflated with bad-faith actors during registry sweeps, all audits and curation workflows must evaluate candidates against four distinct classifications. Curators and AI agents must **never** lump non-malicious defects into an "imposter" label.

1. **Tier 1 — Malicious / Imposter Squatter**:
   - *Definition*: Bad-faith aggregation, monorepo star hijacking (claiming unrelated repository stars for empty stubs), falsified upstream attribution, or squatting on namespaces.
   - *Action*: Immediate expungement from the registry, blacklist of offending repository/domain/author pattern from intake.
2. **Tier 2 — Packaging / Install Shape Gap**:
   - *Definition*: Legitimate skill concept and authentic author, but missing standard `SKILL.md` packaging upstream, circular forks, or broken/stale repository links.
   - *Action*: For skills at ≤ 2★, tag `installable: false` per [CONTRIBUTING.md §12](CONTRIBUTING.md#12-named-skill-installability-policy) and retain in the registry as registry-only implementations. If > 2★, demote to 2★ (or 1★ Awakened if lacking a verified blob link per Star Bar) and request upstream repackaging. **Never purge or brand as an imposter.**
3. **Tier 3 — Early-Stage / Under-Evidenced Stub**:
   - *Definition*: Legitimate author and valid conceptual primitive, but carrying thin documentation, exploratory notes, or preliminary evidence.
   - *Action*: Retain at baseline 1★ (Awakened), request documentation enrichment, or tag with `needs-info`. **Do not purge.**
4. **Tier 4 — Product-Coupled / Non-Generalized**:
   - *Definition*: Real tool documentation that describes a proprietary tool's CLI or specific commands without sufficient generalization or proper maker credit (e.g. #1766 `herdr`, #1801 `k-dense-ai` prompt wrappers).
   - *Action*: Route to generalization guidance and enforce maker attribution via `scripts/check_product_attribution.py`. Retain at baseline rank; do not brand as malicious.

### 4.3 Mandatory Safeguards Before Purge
Before any named skill is removed from the registry, the following safeguards are mandatory:
- **Mandatory Disentanglement**: PRs performing forensic evidence scrubs, audits, or cleanup sweeps must explicitly classify every candidate into one of the four tiers above. PR descriptions and commit messages must itemize each target by tier. Blanket batches labeled generically as "imposter purges" or "non-skill purges" are strictly prohibited.
- **Contributor Check**: If the author is a known community contributor, co-founder, or team member, maintainers must conduct direct outreach and complete a documented audit review before any permanent deletion.
- **Restoration Protocol**: If a legitimate self-hosted or prototype skill is identified as having been mistakenly purged in a past sweep, it must be restored with author documentation and proper Trust Magnitude calibration (exemplified by `rico-favor/implement-with-discernment` restored in PR #1812 per RFC #1809).

## 5. Release Cadence

### 5.1 Registry Snapshots
The registry is updated continuously as PRs are merged. Every month, a new version (e.g., `v2.1.0`) is tagged as a **Frontier Release**, including:
- A summary of all new skills.
- The **Frontier Report** (graph analytics and gaps).

## 6. Code of Conduct

All contributors and maintainers are expected to follow the project's Code of Conduct. We prioritize technical accuracy, evidence over opinion, and respectful debate.
