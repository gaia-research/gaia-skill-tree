# META: Gaia Registry Source of Truth

This document serves as the **single source of truth** for the Gaia Skill Registry's taxonomy, evidence methodology, and ranking strategy. It defines the "Meta" — the rules and standards that ensure Gaia remains a high-prestige, high-trust ecosystem for agent capabilities.

---

## 1. Core Taxonomy (The Hierarchy)

Gaia uses a tiered star system (`0★`–`6★`) to rank skills. Levels are both a measure of technical complexity and a mark of community prestige.

### 1.1 Star Tiers & Rank Labels
| Level | Label | Significance | Evidence Floor |
|---|---|---|---|
| **0★** | **Basic** | Generic primitive, no implementation. | None |
| **1★** | **Awakened** | Verified generic primitive. | None |
| **2★** | **Named** | Minimum level for named implementations. | Tier C |
| **3★** | **Evolved** | Demonstrates reproducibility and stability. | Tier B |
| **4★** | **Hardened** | Production-ready, well-documented, reliable. | Tier B/A |
| **5★** | **Transcendent** | Mastery level, often an Ultimate capstone. | Tier B/A |
| **6★** | **Apex** | The pinnacle of Gaia; extreme ecosystem impact. | Tier A + Review |

### 1.2 Skill Types
- **○ Basic Skill**: Root primitives. 0 prerequisites.
- **◇ Extra Skill**: Composite workflows. Requires ≥ 2 prerequisites.
- **◉ Unique Skill**: Specialized depth. Level 4★+, 0 prerequisites, graph-isolated.
- **◆ Ultimate Skill**: Platform capstones. Requires ≥ 5 named prerequisites + Origin Fusion.

---

## 2. Evidence Methodology (The Trust Stack)

Evidence is categorized by "Class," representing the level of third-party verification and reproducibility.

### 2.1 Evidence Classes
- **Class A (Peer-Reviewed)**: Published papers (arXiv, journals), large-scale adoption (10k+ stars), or official vendor documentation.
- **Class B (Reproducible Demo)**: Public repositories with clear installation steps, tests, and video/log evidence.
- **Class C (Credible Demo)**: Blog posts, social media demos, or "coming soon" repositories with code.

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
  - **3★+**: MUST have a verified GitHub link. If no link exists, the skill is demoted to 2★.
  - **Suites**: Exempt from individual link requirements if components are linked.

---

## 3. Effective Level & Demerits

The **Canonical Level** (e.g., 4★) is the claimed tier based on evidence. The **Effective Level** is the level used for runtime advice and fusion, adjusted by demerits.

### 3.1 Canonical Demerits
- **`niche-integration`**: Tied to a narrow or obscure platform.
- **`experimental-feature`**: Unstable API or alpha-status code.
- **`heavyweight-dependency`**: Requires massive local resources or complex setup.

**Rule**: Each demerit lowers the Effective Level by **1 star**, floored at `1★`.

---

## 4. Governance & Promotion

### 4.1 Named Skill Promotion
- **Awakened**: Initial intake state. Verified as a real skill.
- **Named**: Promoted by a reviewer once a unique RPG `title` or `catalogRef` is assigned.
- **Origin Status**: The first contributor to implement an abstract generic skill in a bucket holds permanent "Origin" status.

### 4.2 Ultimate & Apex Pathways
- **Ultimate Fusion**: Proposer must hold Origin status on at least 1 of the 5+ named prerequisites.
- **Grandmaster Path (6★ Apex)**: Requires Tier A evidence OR holding 2+ skills at 5★ Ultimate tier with 10k+ repository stars.

---

## 5. Rank History (The "Hero's Journey")

Every named implementation tracks its evolution through the `timeline` schema property.

### 5.1 Timeline Events
- **`propose`**: Initial 2★ submission.
- **`rank_up`**: Promotion to a higher star tier.
- **`demote`**: Star tier reduction due to audit or evidence rot.
- **`verified`**: Successful peer verification of evidence.
- **`disputed`**: Active challenge to the skill's rank or evidence.

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

- **`registry/nodes/*.json`**: Canonical generic skill definitions (Managed via `gaia dev`).
- **`registry/named/**/*.md`**: Named implementations and their meta-tags.
- **`registry/schema/meta.json`**: Central registry for nomenclature, colors, symbols, and floors.
- **`registry/gaia.json`**: Generated artifact; do not hand-edit.

---

## 8. Implementation Status Tracker

| Feature | Status | Tracking |
|---|---|---|
| Star Tiers (0★–6★) | ✅ Implemented | `registry/schema/meta.json` |
| Demerits & Effective Level | ✅ Implemented | `GOVERNANCE.md` |
| Unique Skill Promotion | ✅ Implemented | `CONTRIBUTING.md` |
| Ultimate Fusion Criteria (5-Prereq) | ✅ Implemented | `GOVERNANCE.md` |
| Timeline Schema | ✅ Implemented | `registry/schema/namedSkill.schema.json` |
| Web of Trust / Verification | 🏗️ In Discussion | [Issue #457](https://github.com/mbtiongson1/gaia-skill-tree/issues/457) |
| Liveness Heartbeat Script | 🏗️ Planned | `scripts/verify_evidence.py` |
| Hero's Journey UI Tab | 🏗️ Planned | `docs/js/skill-explorer.js` |
