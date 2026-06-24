# Trust Methodology Source Report

**Date:** June 18, 2026  
**Subject:** Live-Verified Evidence Sources Collection for Gaia Skill Registry (Tiers 2★ to 6★)

---

## 1. Overview
This report lists the raw evidence sources compiled for the Gaia project. It is compiled from the pre-existing named and generic skills in the repository, updated with live GitHub star counts.

---

## 2. Registry Evidence Summary

Registry evidence parsed directly from the local repository (with updated star counts from the live GitHub API):

- **Tier 6★:** 2 skills total, 2 have verified sources (3 raw source entries)
- **Tier 5★:** 4 skills total, 4 have verified sources (4 raw source entries)
- **Tier 4★:** 33 skills total, 33 have verified sources (45 raw source entries)
- **Tier 3★:** 35 skills total, 35 have verified sources (62 raw source entries)
- **Tier 2★:** 140 skills total, 140 have verified sources (227 raw source entries)
- **Tier 1★:** 21 skills total, 20 have verified sources (28 raw source entries)

### Registry Files Directory:
- **[Unified Evidence Data Lake (Master)](file:///home/gaia-skill-tree/evidence/unified_evidence_lake.md)**
- [Tier 6★ Source Dump](file:///home/gaia-skill-tree/evidence/collectors/tier_6.md)
- [Tier 5★ Source Dump](file:///home/gaia-skill-tree/evidence/collectors/tier_5.md)
- [Tier 4★ Source Dump](file:///home/gaia-skill-tree/evidence/collectors/tier_4.md)
- [Tier 3★ Source Dump](file:///home/gaia-skill-tree/evidence/collectors/tier_3.md)
- [Tier 2★ Source Dump](file:///home/gaia-skill-tree/evidence/collectors/tier_2.md)
- [Tier 1★ Source Dump](file:///home/gaia-skill-tree/evidence/collectors/tier_1.md)

---

## 3. Recent Curation & Evidence Updates (June 18, 2026)

A systematic round of manual verification and curation was conducted, focusing on resolving gaps in secondary evidence, correcting proxy labels, and incorporating high-fidelity `social-signal` sources.

### Key Findings & Methodology Adjustments
1. **Proxy Containment Strategy (`proxy-containment`):**
   - For entries referencing repositories that do not represent the contributor's own project but contain/use the skill capability, the evidence type was migrated from `repo` to `proxy-containment`.
   - Descriptions for all `proxy-containment` sources were updated to explicitly call out the target skill capability they implement or consume (e.g., pointing out `mcp-integration`, `knowledge-graph-build`, or `mcp-server-creation`).

2. **Social Signal Enrichment (`social-signal`):**
   - Added validated blogs, technical reviews, and community post references to provide qualitative signal verification for high-impact agent skills.

### Summary of Contributor Updates
- **`devin-ai` (Tier 1★):** Added E3 `social-signal` (A Systematic Survey of Self-Evolving Agents) to `devin-ai/autonomous-swe` validating environment-driven co-evolution.
- **`safishamsi` (Tier 1★):** Added E1 `repo` for the primary Graphify repository. Updated `microsoft/graphrag` to `proxy-containment` mapping back to the `knowledge-graph-build` skill.
- **`browser-use` (Tier 2★):** Added E3 & E4 `social-signal` (Notte blog comparing harnesses, and online Mind2Web benchmark) to `browser-use/browser-harness`.
- **`firecrawl` (Tier 2★):** Migrated `mendableai/firecrawl-mcp-server` to `proxy-containment`. Added E3 & E4 `social-signal` (Firecrawl Blog use cases, and YouTube explanation video) to `firecrawl/firecrawl`.
- **`anthropic` (Tier 2★):** Added E4 & E5 `social-signal` (KDnuggets guide and Dev.to community post) to `anthropic/skill-creator`.
- **`upsonic` (Tier 2★):** Added E2 `repo` referencing the primary framework repository for `upsonic/unittest-generator`.
- **`sickn33` (Tier 2★ & Tier 3★):**
   - **`sickn33/mcp-builder` (Tier 3★):** Updated E1 & E2 proxies to `proxy-containment` pointing back to `mcp-server-creation`. Added E3 repo description.
   - **`sickn33/ai-dev-jobs-mcp` (Tier 2★):** Updated E1 & E2 to `proxy-containment` pointing back to `mcp-integration`.
   - **`sickn33/n8n-mcp-tools-expert` (Tier 2★):** Updated E1 & E2 to `proxy-containment` pointing back to `mcp-integration`.
- **`pbakaus` (Tier 4★):** Verified single E1 `repo` source mapping for `pbakaus/impeccable`. No additional sources required.
- **`spring-ai` (Tier 2★) & `stanfordnlp` (Tier 1★):** Verified sources align with registry metadata; mapped primary repos successfully.
- **`ruvnet` (Ecosystem Suite):** Confirmed exemption from file-level checks as per registry guidelines. Mapped directly to the raw repository root.

---

## 4. Multi-Agent Evidence Verification & Adversarial Auditing (June 18, 2026)

To ensure the integrity and robustness of the Gaia Skill Tree trust model, a fleet of specialized **Gemini 3.5 Flash (Low)** collector subagents was fanned out across multiple signal channels, followed by an **Adversarial Evidence Verifier** to test all links and context relevance one-by-one.

### Summary of New Multi-Agent Evidence Families
1. **Objective Benchmarks (`benchmark-result`):**
   - Verified **SWE-bench** unassisted solve rate of **13.86%** for `devin-ai/autonomous-swe` and **84.8%** swarm solve rate for `ruvnet/ruflo` (vendor claim).
   - Verified **78% - 97% task success** for `browser-use/browser-harness` on BU Bench V1 (100 verified tasks).
   - Documented **71.5x token compression** for `safishamsi/graphify` AST-based query RAG.
   - Documented **+59% layout consistency** audits for `pbakaus/impeccable` design checker.
2. **Academic Citations (`arxiv`):**
   - Mapped key arXiv papers establishing theoretical/empirical validation for target skills:
     - `safishamsi/graphify` -> *CodexGraph: Bridging LLMs and Code Repos via Code Graph Databases* (arXiv:2408.03910, ~89 citations).
     - `anthropic/skill-creator` -> *Large Language Models as Tool Makers* (arXiv:2305.17126, ~300+ citations).
     - `pbakaus/impeccable` -> *DesignRepair: Dual-Stream Design Guideline-Aware Frontend Repair* (arXiv:2411.01606, ~19 citations).
3. **Showcase Videos (`social-signal`):**
   - YouTube demos featuring handlers showcasing their skills:
     - **Garry Tan** demonstrating `garrytan/gstack` Virtual Engineering Team workflows.
     - **Matt Pocock** demonstrating the `/teach` custom Claude Code skill.
     - **Jesse Vincent** detailing `obra/superpowers` multi-agent SDLC planning.
     - **Paul Bakaus** showing `pbakaus/impeccable` aesthetic steering in action.
4. **Developer Blogs (`social-signal`):**
   - Active tutorials and articles explaining integration patterns on Dev.to, Medium, and official product blogs.

### Actionable Audit Findings & Recommendations
The adversarial verifier identified several gaps and mismatches that must be resolved in future metadata releases:
*   **Broken Links (404):**
    - The repository link `https://github.com/cognition-labs/devin` does not exist because Devin is closed-source. Future updates should use the public results repo: `https://github.com/CognitionAI/devin-swebench-results`.
    - Broken tutorial/marketplace pages found at `https://dev.to/anthropic/eval-driven-skill-creation-with-anthropics-skill-creator`, `https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code`, and `https://skillsmp.com/skills/unittest-generator`.
*   **Registry Format Mismatches (Curation Guideline #1):**
    - Subpaths for `sickn33/mcp-builder` and `anthropic/skill-creator` use GitHub's default `tree/` format instead of the required `blob/` format. These must be replaced to allow the skill installer to function.
*   **Placeholder Links:**
    - Generic homepages for Reddit (`https://reddit.com`) and Dev.to (`https://dev.to`) were used for `ruvnet/ruflo`. These must be upgraded to deep links referencing actual discussions.

For a detailed link-by-link audit log, refer to the full verifier report:
*   [Adversarial Verification Report](file:///home/gaia-skill-tree/evidence/collectors/verification/verification_report_2026_06_18.md)

### 5. Collectors Directory Index

All raw evidence collection reports are organized and stored locally within the repository under `evidence/collectors/`:

*   **Raw Evidence Dumps:**
    *   [Tiers 1–2 Raw Evidence](file:///home/gaia-skill-tree/evidence/collectors/tiers_1_2_evidence.md)
    *   [Tiers 3–6 Raw Evidence](file:///home/gaia-skill-tree/evidence/collectors/tiers_3_6_evidence.md)
*   **Social & Engagement Signals:**
    *   [YouTube Showcase Videos](file:///home/gaia-skill-tree/evidence/collectors/social/youtube_showcases.md)
    *   [Developer Blogs & Newsletters](file:///home/gaia-skill-tree/evidence/collectors/social/blogs_newsletters.md)
*   **Technical & Academic Evaluations:**
    *   [Objective Benchmark Results](file:///home/gaia-skill-tree/evidence/collectors/technical/benchmark_results.md)
    *   [Structured Peer Reviews & Audits](file:///home/gaia-skill-tree/evidence/collectors/technical/peer_reviews_audits.md)
    *   [Academic Papers & arXiv Preprints](file:///home/gaia-skill-tree/evidence/collectors/technical/academic_papers.md)
*   **Adversarial Audit Logs:**
    *   [Verification Report](file:///home/gaia-skill-tree/evidence/collectors/verification/verification_report_2026_06_18.md)

---

## 6. Adversarial Data Lake Audit Findings (June 19, 2026)

Following a comprehensive multi-agent adversarial audit of Tiers 1★ to 6★ in the Gaia data lake (`tier_1.md` through `tier_6.md`), this section synthesizes the critical discrepancies, link failures, formatting violations, and classification errors identified.

### 6.1 Dead/Broken Links (404)
A total of 8 active 404/broken link failures were confirmed:
*   **`devin-ai/autonomous-swe` (Tier 1★):** The primary and E1 repository link points to `cognition-labs/devin` which is a private, non-existent repository. *Recommendation:* Remove or replace with `CognitionAI/devin-swebench-results`.
*   **`google-deepmind/science_skills_common` (Tier 2★):** E1 points to a path with underscores (`skills/science_skills_common/SKILL.md`) that 404s. The actual directory is `scienceskillscommon` without underscores. *Recommendation:* Correct the folder name in the URL.
*   **`langgenius/component-refactoring` (Tier 2★):** Primary and E1 link `langgenius/dify/blob/main/.agents/skills/component-refactoring/SKILL.md` 404s due to unmerged changes. *Recommendation:* Verify merge status or mark as non-installable.
*   **`mattpocock/diagnose` (Tier 2★):** E1 link 404s. The folder in the `mattpocock/skills` repository is named `diagnosing-bugs` instead of `diagnose`. *Recommendation:* Correct the folder path.
*   **`mattpocock/zoom-out` (Tier 2★):** The primary `SKILL.md` link 404s because the skill folder does not exist. *Recommendation:* Remove or mark as `installable: false`.
*   **`mbtiongson1/gaia-audit` (Tier 2★):** E1 link returns a 404 due to case-sensitivity (uses lowercase `skill.md` instead of `SKILL.md` in the URL). *Recommendation:* Correct to uppercase `SKILL.md`.
*   **`mattpocock/write-a-skill` (Tier 3★):** Primary `SKILL.md` 404s. The folder is named `writing-great-skills` in the upstream repository. *Recommendation:* Correct path or mark as deprecated.
*   **`mattpocock/ubiquitous-language` (Tier 4★):** Primary `SKILL.md` 404s because the skill was moved to `skills/deprecated/ubiquitous-language/SKILL.md`. *Recommendation:* Update the URL path.

### 6.2 Format Errors
Formatting inconsistencies violating core Curation Guidelines were detected:
*   **Bare Repository URLs for Suite Components:** Under *Curation Guideline #4*, each component of a suite must have a `blob/branch/subpath` URL instead of a bare repository root to prevent symlink resolution failure. **27 skills** in the `ruvnet/ruflo` suite incorrectly list the bare root `https://github.com/ruvnet/ruflo`.
*   **Bare Repository / Uninstallable Pre-PR Skills:** `gaiabot/repo-docs-before-pr` (Tier 2★) lists the bare repository root as its primary link and lacks a corresponding local skill directory, making it uninstallable. *Recommendation:* Set `installable: false` or create the directory.
*   **Missing Title Headers:** `Taoidle/plan-decompose-gh-plan-cascade` and `changkun/plan-decompose-gh-wallfacer` (Tier 2★) are both missing the `- Primary GitHub Repository` line under their title headers.
*   **Missing SKILL.md trailing suffixes:** `mattpocock/caveman` (Tier 3★) lacks the trailing `/SKILL.md` suffix on its primary GitHub link.
*   **General Format Anomalies:**
    - `stanfordnlp/dspy` (Tier 1★) contains encoding artifacts (e.g. `â€”`) in its description text.
    - `xquik-dev/hermes-tweet` (Tier 4★) uses `blob/master/` instead of `blob/main/`, which diverges from default naming conventions.
    - `mattpocock/caveman` (Tier 3★) references a dynamic JSON Search API endpoint (`skillsmp.com`) rather than a direct documentation link.

### 6.3 Evaluative Noise
Numerous descriptions contain subjective judgments, verifier-attestation markers, or database migration logs, violating the pure raw evidence requirement of `gaia-evidence-dump`:
*   **Database Migration Commentary:** Leftover notes such as `(backfilled — class-to-type migration)` and details about replacing seed evidence are present in `devin-ai/autonomous-swe`, `ruvnet/flow-nexus-swarm`, `ruvnet/v3-swarm-coordination`, and `addy-osmani/performance-optimization`.
*   **Procedural Rule/Rank Annotation:** Evaluative synthesis notes referencing META rules/thresholds are present in `ruvnet/ruflo` Tier 6★ (*"Meets Class A threshold..."*), `garrytan/gstack` Tier 5★ (*"meets the >=5 named-skills threshold..."*), and `mbtiongson1/gaia-audit` (*"Downgraded A->C per META §2.4..."*).
*   **Subjective Adjectives / Synthesis:** Subjective claims such as *"Most widely adopted AI agent discipline framework; confirms landmark methodology status"* (`obra/superpowers` Tier 5★), *"Elite"* (`pbakaus/impeccable`), *"high-quality"* (`sickn33/mcp-builder`), or *"supersedes the Nielsen heuristics"* (`martin-stepanoski/nielsen-heuristics-audit`) are mapped.
*   **Verifier Attestations:** All 31 `garrytan/gstack` suite components in Tiers 3★ and 4★ contain the text string `"verified live"` in their descriptions.

### 6.4 Incorrect Categorizations & Proxy Mismatches
We identified systematic proxy inflation and category classification errors where external codebases, generic benchmarks, or unrelated papers are linked to individual named skills:
*   **Circular Self-Reference:** `mattpocock/skills` (Tier 6★) lists its own Gaia pull request registration (`pull/352`) as evidence.
*   **Ecosystem/Suite Repository Bloat:**
    - `mattpocock/engineering` (Tier 5★) and `ruvnet/agentdb` (Tier 5★) list their top-level suite repositories without specific folders/subpaths.
    - **9 distinct `ruvnet` Tier 1★ skills** point to the exact same top-level `ruflo` root without specific subpaths to multi-map star metrics.
*   **Competitor / Independent Repository Mapping:**
    - `huggingface/semantic-cache` (Tier 1★) maps competitor tools `codefuse-ai/ModelCache` and `vcache-project/vCache` as proxy-containment evidence.
    - `nexu-io/open-design` (Tier 1★) maps `shadcn-ui/ui`.
    - `nousresearch/feed-monitoring` (Tier 1★) maps `DIYgod/RSSHub`.
    - `safishamsi/graphify` (Tier 1★) maps `microsoft/graphrag`.
    - `yonatangross/orchestkit-rag` (Tier 1★) maps Exploding Gradients' `ragas` library.
    - `Taoidle/plan-decompose-gh-plan-cascade` and `changkun/plan-decompose-gh-wallfacer` (Tier 2★) are cross-pollinated (each contributor maps the other's repository).
    - `intelligentcode-ai/*`, `ruvnet/*`, and `yundu-ai/*` skills (Tier 2★) incorrectly categorize external projects (`go-sdk`, `5ire`, `PromptKit`, `autospec`, `n8n`, `activepieces`, `Flowise`, `skill-creator`, `AgentSkillOS`) as `repo` (the contributor's primary repository) instead of `proxy-containment`.
*   **Generic Benchmarks & Academic Paper Mismatches:**
    - Large generic evaluation benchmarks (`SWE-bench`, `WebArena`, `SQuAD 2.0`) are incorrectly linked as proxy-containment or direct evidence for specific named skills (e.g. `devin-ai/autonomous-swe`, `gooseworks/notte-browser`, `0xdarkmatter/pytest-patterns`, `mattpocock/improve-codebase-architecture`, `garrytan/office-hours`).
    - General academic survey papers on multi-agent debate, prompt jailbreak/guardrails, prompt compression, memory models, and code reviews are mapped as evidence for unrelated skills (e.g. `gaiabot/gaia-triage`, `garrytan/careful`, `garrytan/freeze`, `garrytan/context-restore`, `garrytan/gstack-upgrade`, `garrytan/benchmark-models`, `huggingface/transformers-js`).
*   **Skill ID Mismatch:**
    - `garrytan/garrytan` (Tier 4★) has a folder/ID mismatch, pointing to `autoplan/SKILL.md` but registered under ID `garrytan/garrytan`.
