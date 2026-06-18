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
- [Tier 6★ Source Dump](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/tier_6.md)
- [Tier 5★ Source Dump](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/tier_5.md)
- [Tier 4★ Source Dump](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/tier_4.md)
- [Tier 3★ Source Dump](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/tier_3.md)
- [Tier 2★ Source Dump](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/tier_2.md)
- [Tier 1★ Source Dump](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/tier_1.md)

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
*   [Adversarial Verification Report](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/collectors/verification/verification_report.md)

### 5. Collectors Directory Index

All raw evidence collection reports are organized and stored locally within the repository under `founder/sources/collectors/`:

*   **Raw Evidence Dumps:**
    *   [Tiers 1–2 Raw Evidence](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/collectors/raw/tiers_1_2_evidence.md)
    *   [Tiers 3–6 Raw Evidence](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/collectors/raw/tiers_3_6_evidence.md)
*   **Social & Engagement Signals:**
    *   [YouTube Showcase Videos](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/collectors/social/youtube_showcases.md)
    *   [Developer Blogs & Newsletters](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/collectors/social/blogs_newsletters.md)
*   **Technical & Academic Evaluations:**
    *   [Objective Benchmark Results](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/collectors/technical/benchmark_results.md)
    *   [Structured Peer Reviews & Audits](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/collectors/technical/peer_reviews_audits.md)
    *   [Academic Papers & arXiv Preprints](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/collectors/technical/academic_papers.md)
*   **Adversarial Audit Logs:**
    *   [Verification Report](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/collectors/verification/verification_report.md)
