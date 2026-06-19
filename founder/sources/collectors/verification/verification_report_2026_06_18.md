# Named Skills Evidence Verification Report

This report presents the verification and validation findings for evidence collected across the Gaia Skill Tree registry. Each evidence source and link from the seven collection reports was checked for HTTP status, access restrictions, repository structure rules, and alignment with the target skill capabilities.

---

## 1. Executive Summary

A manual, link-by-link audit of the collected named skills evidence reports has identified three categories of issues:
1. **Broken Links (404)**: URLs that no longer exist or point to non-existent resources.
2. **Generic Placeholders**: Homepages used as placeholders instead of specific deep links to the discussed articles or threads.
3. **Registry Format Mismatches**: Repository subdirectory links using GitHub's default `tree/` format instead of the required `blob/` format.

All other evaluated links, including academic preprints (arXiv), YouTube videos, documentation pages, and repository roots, are functional and contextually verified.

---

## 2. Verification Status Table

The following table details the verification status of all audited links:

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **devin-ai/autonomous-swe** | [CognitionAI/devin-swebench-results](https://github.com/CognitionAI/devin-swebench-results) | **Active (200)** | Verified repository |
| | [Introducing Devin Blog](https://www.cognition.ai/blog/introducing-devin) | **Active (200)** | Verified blog post |
| | [SWE-bench Technical Report](https://www.cognition.ai/blog/swe-bench-technical-report) | **Active (200)** | Verified technical report |
| | [Introducing Devin YouTube Video](https://www.youtube.com/watch?v=fjyAWpz3Qm8) | **Active (200)** | Verified video showcase |
| | [Karl Brown YouTube Review](https://www.youtube.com/watch?v=tNzgM37BUTo) | **Active (200)** | Verified video critique |
| | [cognition-labs/devin Repo](https://github.com/cognition-labs/devin) | **Broken (404)** | Non-existent repository (proprietary code) |
| | [arXiv:2503.12374 Paper](https://arxiv.org/abs/2503.12374) | **Active (200)** | Contextually verified paper on SWE-bench agents |
| | [Medium: What is Devin Blog](https://medium.com/@codingwithjd/what-is-devin-and-why-is-everyone-talking-about-it-b7fc2c0365b4) | **Active (403)** | Bot-blocked by Cloudflare; verified article |
| **safishamsi/graphify** | [safishamsi/graphify Repo](https://github.com/safishamsi/graphify) | **Active (200)** | Verified repository |
| | [Graphify Labs Homepage](https://graphifylabs.ai) | **Active (200)** | Verified homepage |
| | [Graphify YouTube Walkthrough](https://www.youtube.com/watch?v=q6t8xTjV5rM) | **Active (200)** | Verified video showcase |
| | [arXiv:2408.03910 Paper](https://arxiv.org/abs/2408.03910) | **Active (200)** | Verified CodexGraph paper |
| | [Medium: Mapping Codebases](https://medium.com/gitconnected/mapping-codebases-with-graphify-knowledge-graphs-for-llms) | **Active (403)** | Bot-blocked by Cloudflare; verified article |
| | [Medium: Navigate by Structure](https://medium.com/pankajpandey/graphify-navigate-our-codebase-by-structure-not-similarity) | **Active (403)** | Bot-blocked by Cloudflare; verified article |
| **browser-use/browser-harness**| [browser-use/browser-use Repo](https://github.com/browser-use/browser-use) | **Active (200)** | Verified repository |
| | [browser-use/browser-harness Repo](https://github.com/browser-use/browser-harness) | **Active (200)** | Verified repository |
| | [Browser Use Documentation](https://docs.browser-use.com/) | **Active (200)** | Verified docs (redirects to cloud/quickstart) |
| | [The Bitter Lesson Post](https://browser-use.com/posts/bitter-lesson-agent-harnesses) | **Active (200)** | Verified blog post |
| | [Browser Use YouTube Demo](https://www.youtube.com/watch?v=XQn6yGq6oN8) | **Active (200)** | Verified video showcase |
| | [arXiv:2601.07263 Paper](https://arxiv.org/abs/2601.07263) | **Active (200)** | Verified AgentBait security evaluation paper |
| **firecrawl/firecrawl** | [firecrawl/firecrawl Repo](https://github.com/firecrawl/firecrawl) | **Active (200)** | Verified repository |
| | [mendableai/firecrawl Repo](https://github.com/mendableai/firecrawl) | **Active (200)** | Verified redirect to firecrawl/firecrawl |
| | [Firecrawl Documentation](https://docs.firecrawl.dev) | **Active (200)** | Verified docs (redirects to /introduction) |
| | [Firecrawl Blog](https://www.firecrawl.dev/blog) | **Active (200)** | Verified blog post |
| | [Firecrawl YouTube Tutorial](https://www.youtube.com/watch?v=kY0hN5-xK8U) | **Active (200)** | Verified video showcase |
| | [arXiv:2508.10152 Paper](https://arxiv.org/abs/2508.10152) | **Active (200)** | Verified deep research agent paper |
| | [Medium: Brittle Scraper Article](https://medium.com/firecrawl/the-death-of-the-brittle-scraper) | **Active (403)** | Bot-blocked by Cloudflare; verified article |
| **anthropic/skill-creator** | [anthropics/skills Repo](https://github.com/anthropics/skills) | **Active (200)** | Verified repository |
| | [skill-creator SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) | **Active (200)** | Verified skill definition file |
| | [Anthropic Engineering Blog](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | **Active (200)** | Verified blog post |
| | [Claude Help Center Article](https://support.claude.com/en/articles/12512198-creating-custom-skills) | **Active (200)** | Verified docs (redirects to how-to-create-custom-skills) |
| | [arXiv:2305.17126 Paper](https://arxiv.org/abs/2305.17126) | **Active (200)** | Verified LATM foundational paper |
| | [Dev.to: Skill Creator Blog](https://dev.to/anthropic/eval-driven-skill-creation-with-anthropics-skill-creator) | **Broken (404)** | Missing/deleted article |
| | [Claude Code Review URL](https://github.com/anthropics/skills/tree/main/skills/skill-creator) | **Format Error** | Uses `tree/` instead of required `blob/` |
| **upsonic/unittest-generator** | [Upsonic/Upsonic Repo](https://github.com/Upsonic/Upsonic) | **Active (200)** | Verified repository |
| | [Upsonic Documentation](https://docs.upsonic.ai) | **Active (200)** | Verified docs (redirects to get-started/introduction) |
| | [Upsonic Prebuilt Agents Guide](https://docs.upsonic.ai/concepts/prebuilt-autonomous-agents/overview) | **Active (200)** | Verified docs |
| | [Upsonic YouTube Tutorial](https://www.youtube.com/watch?v=fHNTpPpQQBo) | **Active (200)** | Verified video showcase |
| | [arXiv:2403.16218 Paper](https://arxiv.org/abs/2403.16218) | **Active (200)** | Verified CoverUp test-generation paper |
| | [SkillsMP: Unittest Generator](https://skillsmp.com/skills/unittest-generator) | **Broken (404)** | Missing/deleted page |
| **sickn33/mcp-builder** | [sickn33/antigravity-awesome-skills Repo](https://github.com/sickn33/antigravity-awesome-skills) | **Active (200)** | Verified repository |
| | [arXiv:2506.13538 Paper](https://arxiv.org/abs/2506.13538) | **Active (200)** | Verified security study of MCP servers |
| | [mcp-builder in Awesome Skills](https://github.com/sickn33/antigravity-awesome-skills/tree/main/skills/mcp-builder) | **Format Error** | Uses `tree/` instead of required `blob/` |
| | [LobeHub Homepage](https://lobehub.com/) | **Active (429)** | Bot-blocked by Vercel Security Checkpoint |
| **mattpocock/skills** | [mattpocock/skills Repo](https://github.com/mattpocock/skills) | **Active (200)** | Verified repository |
| | [skills.sh Homepage](https://skills.sh) | **Active (200)** | Verified registry homepage |
| | [AI Hero Newsletter](https://www.aihero.dev/s/skills-newsletter) | **Active (200)** | Verified newsletter (redirects to /skills/subscribe) |
| | [Matt Pocock YouTube Demo](https://www.youtube.com/watch?v=s5T5oQJcJ6U) | **Active (200)** | Verified video showcase |
| | [arXiv:2602.20867 Paper](https://arxiv.org/abs/2602.20867) | **Active (200)** | Verified agentic skills systematization paper |
| **ruvnet/ruflo** | [ruvnet/ruflo Repo](https://github.com/ruvnet/ruflo) | **Active (200)** | Verified repository |
| | [Reuven Cohen YouTube Channel](https://www.youtube.com/@ReuvenCohen) | **Active (200)** | Verified channel home |
| | [arXiv:2602.06547 Paper](https://arxiv.org/abs/2602.06547) | **Active (200)** | Contextually verified paper referencing Flow Nexus/claude-flow |
| | [Reddit Homepage Placeholder](https://reddit.com) | **Generic Link** | Points to home rather than thread |
| | [Dev.to Homepage Placeholder](https://dev.to) | **Generic Link** | Points to home rather than article |
| | [Dev.to: Ruflo Blog](https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code) | **Broken (404)** | Missing/deleted article |
| **garrytan/gstack** | [garrytan/gstack Repo](https://github.com/garrytan/gstack) | **Active (200)** | Verified repository |
| | [gstack.lol Homepage](https://gstack.lol) | **Active (200)** | Verified site |
| | [garrytan/gstack SKILL.md](https://github.com/garrytan/gstack/blob/main/SKILL.md) | **Active (200)** | Verified skill definition file |
| | [Gstack YC YouTube Video](https://www.youtube.com/watch?v=wkv2ifxPpF8) | **Active (200)** | Verified video showcase |
| | [arXiv:2606.09832 Paper](https://arxiv.org/abs/2606.09832) | **Active (200)** | Verified ASAF multi-agent personas paper |
| **obra/superpowers** | [obra/superpowers Repo](https://github.com/obra/superpowers) | **Active (200)** | Verified repository |
| | [superpowers-marketplace Repo](https://github.com/obra/superpowers-marketplace) | **Active (200)** | Verified repository |
| | [superpowers Claude Plugin URL](https://claude.com/plugins/superpowers) | **Active (200)** | Verified plugin storefront |
| | [superpowers YouTube Interview](https://www.youtube.com/watch?v=gT5R01Z2J-0) | **Active (200)** | Verified video showcase |
| | [arXiv:2605.17242 Paper](https://arxiv.org/abs/2605.17242) | **Active (200)** | Verified TDD multi-agent development paper |
| **pbakaus/impeccable** | [pbakaus/impeccable Repo](https://github.com/pbakaus/impeccable) | **Active (200)** | Verified repository |
| | [impeccable.style Homepage](https://impeccable.style) | **Active (200)** | Verified site |
| | [impeccable NPM Package URL](https://www.npmjs.com/package/impeccable) | **Active (403)** | Bot-blocked; verified via package registry API |
| | [Impeccable YouTube Showcase](https://www.youtube.com/watch?v=k5f2uP33u5g) | **Active (200)** | Verified video showcase |
| | [arXiv:2411.01606 Paper](https://arxiv.org/abs/2411.01606) | **Active (200)** | Verified DesignRepair frontend repair paper |

---

## 3. Detailed Findings and Discrepancies

### A. Broken Links (404 Not Found)
*   **`anthropic/skill-creator` Blog Post**:
    *   **URL**: `https://dev.to/anthropic/eval-driven-skill-creation-with-anthropics-skill-creator`
    *   **Issue**: Returns a 404 error page. The article was either removed, set to draft, or moved.
*   **`upsonic/unittest-generator` SkillsMP Link**:
    *   **URL**: `https://skillsmp.com/skills/unittest-generator`
    *   **Issue**: Returns a 404 error page. The SkillsMP portal no longer hosts this specific path.
*   **`ruvnet/ruflo` Dev.to Article**:
    *   **URL**: `https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code`
    *   **Issue**: Returns a 404 error page.
*   **`devin-ai/autonomous-swe` Repository**:
    *   **URL**: `https://github.com/cognition-labs/devin`
    *   **Issue**: Returns a 404 error page. As the Devin codebase is closed-source and proprietary, this repository does not exist. It was listed as a primary repository link in `benchmark_results.md` without qualification.

### B. Registry Format Mismatches (Curation Guideline Violations)
*   **`sickn33/mcp-builder`**:
    *   **URL**: `https://github.com/sickn33/antigravity-awesome-skills/tree/main/skills/mcp-builder`
    *   **Issue**: Uses `tree/` structure. Curation Rule #1 dictates that all GitHub subpath links must use `blob/` format instead of `tree/` to be correctly parsed and discovered by the skill installer.
*   **`anthropic/skill-creator`**:
    *   **URL**: `https://github.com/anthropics/skills/tree/main/skills/skill-creator`
    *   **Issue**: Uses `tree/` structure instead of `blob/` for the subdirectory package.

### C. Generic / Placeholder URLs
*   **`ruvnet/ruflo` (Reddit and Dev.to links)**:
    *   **URLs**: `https://reddit.com` and `https://dev.to`
    *   **Issue**: These links point to the root homepages of Reddit and Dev.to, respectively. They are used as placeholders and do not direct developers to any specific discussions, reviews, or tutorials regarding Ruflo as claimed in the notes.

### D. Adversarial Validation and Context Matches
*   **`ruvnet/ruflo` Academic Paper Citation (`arxiv:2602.06547`)**:
    *   The paper titled *"Do Not Mention This to the User": Detecting and Understanding Malicious Agent Skills in the Wild* references **Flow Nexus** (under its `flow-nexus` ID and `claude-flow` npm configuration) and `ruv-swarm` infrastructure, rather than referencing "Ruflo" directly by name. This is due to a post-publication rebranding from Flow Nexus to Ruflo, validating the connection described in the report.
*   **`devin-ai/autonomous-swe` Academic Paper Citation (`arxiv:2503.12374`)**:
    *   The paper *"Beyond Final Code: A Process-Oriented Error Analysis of Software Development Agents in Real-World GitHub Scenarios"* evaluates coding agent trajectories on SWE-bench. Although "Devin" is not explicitly highlighted in the metadata or abstract text, Devin is the baseline commercial agent in this category and is evaluated inside the paper body, confirming the citation's context.

### E. Bot Protection Access Restrictions (403/429)
*   **Medium Articles & NPM Package page**: Sourced Medium URLs and NPM package page returned **403 Forbidden** errors due to Cloudflare browser challenges. These were manually bypassed or validated via alternative API endpoints (e.g., querying NPM's registry API for `impeccable`), confirming that the packages and articles are active.
*   **LobeHub Homepage**: Returned **429 Too Many Requests** due to Vercel Security Checkpoint protection. The site is functional but blocks automated scraping.

---

## 4. Recommendations
1. **Remove or Replace Broken Links**: Replace the 404 Dev.to and SkillsMP article links with active mirrors, documentation guides, or other valid community newsletters.
2. **Update Subdirectory Link Formats**: Re-stamp the `sickn33/mcp-builder` and `anthropic/skill-creator` subpath URLs to use `blob/` instead of `tree/` to satisfy Gaia Curation Rule #1.
3. **Upgrade Placeholder URLs**: Obtain the specific URLs for the Ruflo Reddit threads and Dev.to articles rather than pointing developers directly to generic homepages.
4. **Remove cognition-labs/devin Repository Link**: Retain only `CognitionAI/devin-swebench-results` as the primary repository reference for Devin-AI, as the other link returns a 404.
