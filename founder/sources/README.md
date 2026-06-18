# Gaia Trust Methodology: Evidence Sources & Adversarial Audits

This directory compiles research evidence sources, engagement signals, peer reviews, and multi-agent adversarial audit reports verifying the trust methodology of the Gaia skill registry.

---

## 1. Directory Structure

The directory is structured as follows:

*   **`data_lake/`**: The unified evidence data lake containing clean, raw source evidence grouped by star tiers.
    *   `unified_evidence_lake.md`: Master consolidated database index.
    *   `tier_1.md` through `tier_6.md`: Individual evidence files for each star tier.
*   **`collectors/`**: Raw verification and signal collection channel dumps:
    *   `raw/`: Initial scraped dumps for Tiers 1–6.
    *   `social/`: Scraped developer blogs, newsletters, and YouTube showcase video logs.
    *   `technical/`: Peer reviews, arXiv academic preprints, and objective benchmark results.
    *   `verification/`: Chronological verification logs (`verification_report_YYYY_MM_DD.md`) detailing link status, casing errors, and capability mapping checks.
*   **`scripts/`**: Automation scripts to generate source dumps, query star metrics, and compile the unified data lake.
*   **`source_report_YYYY_MM_DD.md`**: Master reports compiling live-verified GitHub star updates, curation logs, and synthesized adversarial audit findings for specific dates.

---

## 2. Canonical Evidence Types

Evidence is mapped to 10 standard categories:

1.  `github-stars-own` — Primary star count for contributor repositories.
2.  `proxy-containment` — External repos consuming/implementing the capability.
3.  `verifier-attestation` — Cross-org verifications of working execution.
4.  `benchmark-result` — Task success rates on objective harnesses (SWE-bench, WebArena, etc.).
5.  `arxiv` — Academic preprints/papers establishing theoretical/empirical validation.
6.  `peer-review` — RFC audits, verifications, and design consultations.
7.  `repo-own` — Target framework repository itself.
8.  `self-attestation` — Contributor's own statements of capabilities.
9.  `social-signal` — Community blog tutorials, newsletter highlights, and YouTube demonstrations.
10. `fusion-recipe` — Core workflow composition rules for agent suites.

---

## 3. Adversarial Curation Rules

Every evidence file and entry must adhere to the following principles:
*   **Strict Curation Guideline #1:** GitHub subfolder links must use `blob/` format (not default `tree/` format) to be recognized by the skill installer.
*   **Strict Curation Guideline #4:** Suite component links must point to specific subdirectory paths (`blob/main/skills/subpath`), never to the bare repository root.
*   **Zero Evaluative Noise:** Evidence descriptions must remain strictly factual. Strip all subjective praise ("elite", "high-quality"), database migration notes, verifier markers ("verified live"), or rank threshold logic.

---

## 4. Evidence Inheritance (v2 Inheritance Contract)

Under the v2 inheritance contract, a named skill's **effective evidence** is the union of its own evidence (`layer: named`) and the evidence inherited from its starless/generic parent skill (`layer: generic`):
*   **Inherited Standing Floor:** A implementing named skill inherits its starless parent's capability floor. It will never report a weaker Overall Trust Grade than the generic capability it implements.
*   **Inherited Row Discounts:** Certain evidence types linked at the starless/generic level are inherited by implementing named skills subject to an inheritance multiplier discount (e.g., academic `arxiv` rows inherit with a `0.70` multiplier, whereas `named`-layer evidence receives a `1.0` multiplier).
