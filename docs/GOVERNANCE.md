# Gaia Governance

This document outlines how the Gaia Skill Registry is managed, how decisions are made, and how disputes are resolved.

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
- Ultimate skill validation (requires two Core Maintainer approvals). Validation now includes confirming the named-fusion criteria: 5+ named prerequisites with ≥1 origin contribution from the proposer.

## 2. Decision Making

Decisions are made through Pull Requests. Most PRs require one Maintainer approval.
- **Basic/Extra Skills**: 1 Maintainer approval.
- **Ultimate Skills**: 2 Core Maintainer approvals. (named-fusion criteria apply — see §2.2)
- **Schema Changes**: 2 Core Maintainer approvals.
- **Named Skills**: 1 Maintainer approval (standard intake process, then `gaia propose` promotion).

## 2.1 Named Skill Governance

### Naming Rights
- The **origin** contributor is the first to promote a skill in a bucket via `gaia propose`.
- Origin status is permanent unless the contributor explicitly transfers it via a PR.
- Additional contributors can add implementations to the same bucket without affecting origin status.

### Promotion Process
- A skill must first be accepted via the standard intake review process (lifecycle: "awakened").
- Promotion from "awakened" to "named" requires a contributor to run `gaia propose` and open a PR.
- Named skills inherit their generic parent's level floor (minimum 2★).
- Canonical level remains the source of truth for promotion gates; effective level is a visibility signal used by runtime projections and advisor surfaces.
- Demerits are valid only for 2★+ canonical skills. Each demerit lowers effective potential by one level, floored at 1★.

### Named Skill Disputes
- If two contributors claim origin status for the same bucket, priority goes to the earlier `createdAt` date.
- Disputes follow the same 14-day resolution process as generic skill disputes (see § 3).

### Unclaimed Ultimate Claiming
- Unclaimed Ultimate skills appear as `◆ /skill-id [Unclaimed ✦]` in the registry — no named implementation exists yet.
- The first contributor to run `gaia propose` against an awakened intake record whose `genericSkillRef` points to an unclaimed Ultimate automatically becomes the origin contributor and the seed title stored in `gaia.json` becomes visible in projections.
- Claiming priority follows the same rule as named skill origin status: the earlier `createdAt` date wins if two contributors submit simultaneously.
- Once claimed, the display changes from `[Unclaimed ✦]` to `Ultimate Skill: contributor/skill-name`.

## 2.2 Ultimate Skill Promotion

### Origin-Fusion Requirement
To propose a new `◆ Ultimate` skill, the contributor must satisfy all of:
- All 5+ prerequisite skills must have named implementations in `registry/named/`
- The proposer must hold `origin: true` status on at least 1 prerequisite named skill
- ≥3 Class A/B evidence sources required (existing rule, unchanged)

### 4★ Alternative Pathway (Origin-Fusion)
A contributor may reach **4★ (Hardened)** through either:
- Evidence path: ≥1 Tier B/A evidence source (existing rule)
- **Fusion path**: 3+ skill fuses with ≥1 origin named skill among them

### 6★ Grandmaster Path
A contributor may reach **6★ (Apex)** through either:
- Standard path: Tier A evidence + peer review (existing rule)
- **Grandmaster path**: Hold 2+ skills at 5★ Ultimate tier AND the proposer's GitHub repository has ≥10,000 stars

### Reclassification Notice
Existing Ultimate skills registered under the old 3-prerequisite rule that do not meet the new 5-named-prereq criteria will be reclassified to `extra` tier in a `review/meta/` follow-up PR. Affected skills:
- `autonomous-research-agent` (3 prereqs → demoted to extra)
- `full-stack-developer` (3 prereqs → demoted to extra)
- `autonomous-data-scientist` (3 prereqs → demoted to extra)
- `gstacks` (5 prereqs — provisional; requires named-skill verification before retaining ultimate status)

## 3. Dispute Resolution

If a skill's definition, level, or evidence is disputed:
1. A GitHub Issue is opened with the label `disputed`.
2. Both sides present evidence and rationale.
3. The skill status is set to `disputed` in `gaia.json`.
4. If no consensus is reached after 14 days, a Core Maintainer makes a final determination based on the **Evidence Hierarchy** (Evidence Tier A > B > C).

## 4. Audit Schedule

### 4.1 Quarterly Re-Audit
Every 90 days, the maintainers will conduct a full re-audit of the registry to:
- Review `provisional` skills for potential validation.
- Re-assess `disputed` skills.
- Verify ultimate status requirements.
- Identify stale skills (not updated or referenced in 180 days).

## 5. Release Cadence

### 5.1 Registry Snapshots
The registry is updated continuously as PRs are merged. Every month, a new version (e.g., `v2.1.0`) is tagged as a **Frontier Release**, including:
- A summary of all new skills.
- Updated rarity scores based on real user tree data.
- The **Frontier Report** (graph analytics and gaps).

## 6. Code of Conduct

All contributors and maintainers are expected to follow the project's Code of Conduct. We prioritize technical accuracy, evidence over opinion, and respectful debate.
