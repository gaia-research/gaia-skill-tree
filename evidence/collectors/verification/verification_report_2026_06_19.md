# Named Skills Evidence Verification Report (June 19, 2026)

This report presents the verification and validation findings for evidence collected across the Gaia Skill Tree registry, specifically focused on the June 19, 2026 adversarial audit. Each evidence source and link was checked for HTTP status, repository structure rules, case-sensitivity, and alignment with target skill capabilities.

---

## 1. Executive Summary

A link-by-link adversarial audit of the Gaia data lake (`tier_1.md` through `tier_6.md`) was conducted by parallel reviewer subagents on June 19, 2026. Three main classes of issues were identified:
1. **Broken Links (404):** Non-existent private repositories or paths that were renamed/moved in upstream repositories.
2. **Format Errors:** Curation guideline violations including bare repository roots used for suite components (Curation Guideline #4) or missing metadata lines.
3. **Proxy & Classification Mismatches:** Competitor tools, generic libraries, and unrelated academic papers incorrectly mapped to individual named skills as proxy-containment evidence.

---

## 2. Verification Status Table

The following table details the verification status of the audited links from today's run:

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **devin-ai/autonomous-swe** | [cognition-labs/devin](https://github.com/cognition-labs/devin) | **Broken (404)** | Private repository (Devin is closed source) |
| **google-deepmind/science_skills_common** | [scienceskillscommon SKILL.md](https://github.com/google-deepmind/scienceskillscommon/blob/main/skills/science_skills_common/SKILL.md) | **Broken (404)** | Underscore casing mismatch in folder name |
| **langgenius/component-refactoring** | [component-refactoring SKILL.md](https://github.com/langgenius/dify/blob/main/.agents/skills/component-refactoring/SKILL.md) | **Broken (404)** | Missing/unmerged file path |
| **mattpocock/diagnose** | [diagnose SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/diagnose/SKILL.md) | **Broken (404)** | Directory renamed to `diagnosing-bugs` |
| **mattpocock/zoom-out** | [zoom-out SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/zoom-out/SKILL.md) | **Broken (404)** | Folder missing/deleted in upstream repository |
| **mbtiongson1/gaia-audit** | [gaia-audit skill.md](https://github.com/gaia-research/gaia-skill-tree/blob/main/skills/gaia-audit/skill.md) | **Broken (404)** | Case-sensitivity mismatch (uses lowercase `skill.md`) |
| **mattpocock/write-a-skill** | [write-a-skill SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/write-a-skill/SKILL.md) | **Broken (404)** | Folder renamed to `writing-great-skills` |
| **mattpocock/ubiquitous-language** | [ubiquitous-language SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/ubiquitous-language/SKILL.md) | **Broken (404)** | Moved to `skills/deprecated/ubiquitous-language/SKILL.md` |
| **ruvnet/ruflo** (Suite Components) | [ruvnet/ruflo Root URL](https://github.com/ruvnet/ruflo) | **Format Error** | 27 component skills point to bare repo root (Rule #4 violation) |
| **gaiabot/repo-docs-before-pr** | [repo-docs-before-pr Root URL](https://github.com/gaiabot/repo-docs-before-pr) | **Format/Install Error** | Bare repo root used and local directory is missing |
| **Taoidle/plan-decompose-gh-plan-cascade** | - | **Format Error** | Missing `- Primary GitHub Repository` line |
| **changkun/plan-decompose-gh-wallfacer** | - | **Format Error** | Missing `- Primary GitHub Repository` line |
| **mattpocock/caveman** | [skillsmp.com Search Endpoint](https://skillsmp.com) | **Format Error** | References a dynamic search endpoint without trailing `/SKILL.md` |

---

## 3. Detailed Findings and Discrepancies

### A. Broken Links (404 Not Found)
*   **Devin-AI Private Codebase:** The link `https://github.com/cognition-labs/devin` is listed as the primary repository but returns a 404 since Devin is proprietary software.
*   **Case-Sensitivity and Typo Paths:**
    *   `scienceskillscommon` was referenced with underscores in the folder path (`science_skills_common`).
    *   `mbtiongson1/gaia-audit` referenced `skill.md` in lowercase instead of `SKILL.md`.
*   **Renamed or Moved Folders:**
    *   `diagnose` was renamed to `diagnosing-bugs` in the Matt Pocock skills repository.
    *   `write-a-skill` was renamed to `writing-great-skills`.
    *   `ubiquitous-language` was archived under a `deprecated` subdirectory.
    *   `zoom-out` was deleted entirely from the upstream repository.

### B. Curation Rule Violations (Format Errors)
*   **Bare Repo Roots in Suite Components:** 27 skills belonging to the `ruvnet/ruflo` suite point to the bare repository `https://github.com/ruvnet/ruflo` instead of their respective `blob/branch/subpath` subdirectories. This violates Curation Guideline #4, which is required to prevent symlink resolution failures during installation.
*   **Missing Metadata Headers:** `plan-decompose-gh-plan-cascade` and `plan-decompose-gh-wallfacer` lack the standard `- Primary GitHub Repository` attribute.

### C. Evaluative Noise
*   **Subjective Praises:** Text fields contained terms like *"Elite design and UX auditing tool"* (`pbakaus/impeccable`), *"high-quality"* (`sickn33/mcp-builder`), or *"Most widely adopted AI agent discipline framework; confirms landmark methodology status"* (`obra/superpowers`).
*   **Database Logs:** Commentary like `(backfilled — class-to-type migration)` and verifier-attestation markers like `"verified live"` are still present inside the raw descriptions.

### D. Proxy Containment & Capability Mismatches
*   **Competitor Codebase Mappings:** Competitor codebases are mapped to named skills to claim stars (e.g. mapping `shadcn-ui/ui` to `nexu-io/open-design`, `DIYgod/RSSHub` to `nousresearch/feed-monitoring`, and `microsoft/graphrag` to `safishamsi/graphify`).
*   **Generic Academic Benchmarks & Papers:** Mapped general evaluation frameworks (like `SWE-bench`, `WebArena`, `SQuAD 2.0`) to individual skills, inflating star counts artificially.

---

## 4. Recommendations

1. **Remove/Update 404 Links:** Correct the case-sensitivity of URLs (change `skill.md` to `SKILL.md`), correct the folder paths for renamed folders (`diagnose` to `diagnosing-bugs`, `write-a-skill` to `writing-great-skills`), and update the Devin repository to the public SWE-bench results repository (`CognitionAI/devin-swebench-results`).
2. **Re-map Suite Components:** Update all 27 `ruvnet/ruflo` suite components to point to their specific subdirectories under `blob/main/skills/` to satisfy Curation Guideline #4.
3. **Cleanse Evaluative Noise:** Run a script or manual pass to strip subjective adjectives, database migration notes, and `"verified live"` markers from evidence descriptions.
