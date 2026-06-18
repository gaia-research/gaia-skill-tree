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

