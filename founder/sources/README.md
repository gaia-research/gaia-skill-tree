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

### Evidence Type Curation Policy (Allowed Layers & Multipliers)

The table below lists which evidence types can be mapped to `layer: generic` (starless parent) or `layer: named` (implementing child), along with their inheritance multipliers:

| Evidence Type | ID | Allowed Layers | Inherit Multiplier | Description / Policy Note |
| :--- | :--- | :--- | :---: | :--- |
| **ArXiv Paper** | `arxiv` | `["generic", "named"]` | **0.70** | Academic citations (0.7x discount when inherited) |
| **Benchmark Result** | `benchmark-result` | `["generic", "named"]` | **0.15** | Objective harness results (0.15x discount when inherited) |
| **Fusion Recipe** | `fusion-recipe` | `["named"]` | *N/A* | Suite composition rules (only allowed on `named` skills) |
| **GitHub Stars** | `github-stars-own` | `["named"]` | *N/A* | Primary star counts (only allowed on `named` skills) |
| **Peer Review** | `peer-review` | `["generic", "named"]` | **0.30** | Review evaluations (0.3x discount when inherited) |
| **Proxy Containment** | `proxy-containment` | `["generic", "named"]` | **0.25** | External consumer codebases (0.25x discount when inherited) |
| **Repository Own** | `repo-own` | `["named"]` | *N/A* | Contributor's own project codebase (only allowed on `named` skills) |
| **Self Attestation** | `self-attestation` | `["named"]` | *N/A* | Creator self-attestation logs (only allowed on `named` skills) |
| **Social Signal** | `social-signal` | `["generic", "named"]` | **0.35** | External blog posts, YouTube videos (0.35x discount when inherited) |
| **Verifier Attestation** | `verifier-attestation` | `["named"]` | *N/A* | Cross-org verifier approvals (only allowed on `named` skills) |
