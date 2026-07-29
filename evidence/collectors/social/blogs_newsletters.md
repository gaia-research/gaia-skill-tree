# Named Skills Social Signals Search Report

This report documents the social signals (developer articles, blogs, newsletters, and case studies) referencing the 12 registered named skills in the AI agent developer ecosystem, collected on June 18, 2026.

## Summary Table

| # | Named Skill | Primary Source / Article | Author / Publisher | Date | Description |
|---|---|---|---|---|---|
| 1 | `devin-ai/autonomous-swe` | [What is Devin and why is everyone talking about it?](https://medium.com/@codingwithjd/what-is-devin-and-why-is-everyone-talking-about-it-b7fc2c0365b4) | Jaimal Dullat | March 25, 2024 | First autonomous AI software engineer featuring its own command line, code editor, and browser to build and deploy applications independently. |
| 2 | `safishamsi/graphify` | [Graphify: Navigate Our Codebase by Structure, Not Similarity](https://medium.com/pankajpandey/graphify-navigate-our-codebase-by-structure-not-similarity) | Pankaj Pandey | April 17, 2026 | AST-based static codebase parser (`graphifyy` on PyPI) mapping modules, calls, and dependencies into a queryable knowledge graph for AI agents, cutting token usage up to 70x. |
| 3 | `browser-use/browser-harness` | [Browser Harness: A Thin Agent Infrastructure](https://github.com/browser-use/browser-harness) | Browser Use Team | Early 2026 | Minimal direct-to-CDP browser control harness that lets AI agents dynamically write and inject their own self-healing JavaScript and Python helper files at runtime. |
| 4 | `firecrawl/firecrawl` | [The Death of the Brittle Scraper](https://medium.com/firecrawl/the-death-of-the-brittle-scraper) | Firecrawl Community | Mid 2025 | API-first scraping engine that processes javascript, bypasses anti-bot measures, and returns clean, LLM-ready Markdown or structured JSON schemas. |
| 5 | `anthropic/skill-creator` | [Eval-Driven Skill Creation with Anthropic's Skill Creator](https://dev.to/anthropic/eval-driven-skill-creation-with-anthropics-skill-creator) | Anthropic / Claude Code Community | Early 2026 | Meta-skill for Claude Code to automate the authoring, A/B blind testing, and triggering optimization of custom `SKILL.md` capability files. |
| 6 | `upsonic/unittest-generator` | [SkillsMP Unit Test Generator for AI Agents](https://skillsmp.com/skills/unittest-generator) | Upsonic / SkillsMP Community | April 30, 2026 | Claude Code agent tool that parses module structures and generates comprehensive `unittest.TestCase` files with mockup structures in concept-based test directories. |
| 7 | `sickn33/mcp-builder` | [antigravity-awesome-skills: mcp-builder](https://github.com/sickn33/antigravity-awesome-skills) | @sickn33 | May 27, 2026 | Community implementation of the Model Context Protocol (MCP) server builder pattern to automatically register tools, schema specs, and endpoints in Python/Node.js. |
| 8 | `mattpocock/skills` | [Skills for Real Engineers: Matt Pocock's Claude Code Skills](https://github.com/mattpocock/skills) | Matt Pocock | Early 2026 | Engineering-focused skills library featuring `/grill-me` and `/grill-with-docs` that add friction (questioning, context, ADR updates) to keep AI models from reckless coding. |
| 9 | `ruvnet/ruflo` | [Ruflo (formerly Claude Flow): Multi-Agent Orchestration](https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code) | Reuven Cohen (@ruvnet) | Mid 2025 / 2026 | Multi-agent swarm orchestration platform written in Rust/WASM, utilizing SPARC methodology and AgentDB high-speed vector memory for parallel engineering swarms. |
| 10 | `garrytan/gstack` | [GStack: Build a Virtual Engineering Team in Claude Code](https://github.com/garrytan/gstack) | Garry Tan (CEO of Y Combinator) | March 2026 | Collection of 23+ slash commands representing startup engineering roles (CEO, PM, QA) guiding the agent through a structured Think-Plan-Build-QA-Ship lifecycle. |
| 11 | `obra/superpowers` | [Superpowers: An Opinionated Development Framework for AI Agents](https://github.com/obra/superpowers) | Jesse Vincent (@obra) | Early 2026 | Highly opinionated developer framework and skills marketplace for Claude Code, Cursor, and Codex, enforcing a structured brainstorming, design, and TDD process. |
| 12 | `pbakaus/impeccable` | [Impeccable: Preventing Generic UI Designs in AI Coding Assistants](https://github.com/pbakaus/impeccable) | Paul Bakaus | Early 2026 | Design extension for AI agents with commands like `/polish` and `/critique` alongside a set of anti-pattern rules (avoid Inter, Arial, nested cards, and pure grays). |

---

## Detailed Findings

### 1. `devin-ai/autonomous-swe`
*   **Article URL:** [https://medium.com/@codingwithjd/what-is-devin-and-why-is-everyone-talking-about-it-b7fc2c0365b4](https://medium.com/@codingwithjd/what-is-devin-and-why-is-everyone-talking-about-it-b7fc2c0365b4) (also published on DEV.to)
*   **Author/Publisher:** Jaimal Dullat (@jaimaldullat)
*   **Publication Date:** March 25, 2024
*   **Metrics:** High traction and virality in early 2024.
*   **Description:** Introduces Devin as the first fully autonomous AI software engineer developed by Cognition AI. It outlines Devin's built-in sandbox (terminal, browser, editor, planner) and details how it operates independently to execute projects, learn new technologies, debug, and push code. It also reflects community debates about developer job displacement versus agent-assisted productivity.

### 2. `safishamsi/graphify`
*   **Article URL:** [https://medium.com/pankajpandey/graphify-navigate-our-codebase-by-structure-not-similarity](https://medium.com/pankajpandey/graphify-navigate-our-codebase-by-structure-not-similarity) (documented across Medium and DEV.to under PyPI package `graphifyy`)
*   **Author/Publisher:** Pankaj Pandey
*   **Publication Date:** April 17, 2026
*   **Metrics:** Promoted in AI engineering newsletters for its high token-savings ratio.
*   **Description:** Outlines how Graphify uses AST static analysis (`tree-sitter` for 31+ languages) to build local, privacy-first codebase knowledge graphs. By mapping actual structural relationships (imports, call graphs, class structures) instead of using similarity-based vector retrieval, it enables AI agents to "navigate by structure," reducing LLM context requirements up to 70x.

### 3. `browser-use/browser-harness`
*   **Article URL:** [https://github.com/browser-use/browser-harness](https://github.com/browser-use/browser-harness) (covered in detail on Dev.to and Medium articles regarding thin browser harnesses)
*   **Author/Publisher:** Browser Use Team
*   **Publication Date:** Early 2026
*   **Metrics:** Part of the trending "thin agent infrastructure" movement in early 2026.
*   **Description:** Discusses Browser Harness as a lightweight, low-level browser automation solution. Operating in about 600 lines of Python, it interacts directly with Chrome via Chrome DevTools Protocol (CDP) WebSocket commands rather than bundling heavy frameworks like Playwright or Selenium. Crucially, the AI agent is given runtime self-healing capabilities to dynamically generate and rewrite its own local helper functions (`agent_helpers.py`) when it runs into custom elements or page-blocking steps.

### 4. `firecrawl/firecrawl`
*   **Article URL:** [https://medium.com/firecrawl/the-death-of-the-brittle-scraper](https://medium.com/firecrawl/the-death-of-the-brittle-scraper) (also covered in DEV.to tutorials)
*   **Author/Publisher:** Firecrawl Team / AI Engineering Community
*   **Publication Date:** Mid 2025
*   **Metrics:** Thousands of stars on GitHub and standard integration in RAG tools.
*   **Description:** Details Firecrawl's role in converting entire sites or individual pages into clean, LLM-ready formats (chiefly Markdown and structured JSON schemas). It discusses bypassing rate limits, reverse proxies, and anti-bot checks. It also introduces the `/scrape` and `/crawl` endpoints which serve as RAG feeds for modern AI coding frameworks.

### 5. `anthropic/skill-creator`
*   **Article URL:** [https://dev.to/anthropic/eval-driven-skill-creation-with-anthropics-skill-creator](https://dev.to/anthropic/eval-driven-skill-creation-with-anthropics-skill-creator)
*   **Author/Publisher:** Anthropic / Claude Code Community
*   **Publication Date:** Early 2026
*   **Metrics:** Shipped natively as a core developer utility in Claude Code plugins.
*   **Description:** Highlights Anthropic's Skill Creator meta-skill, which introduces software engineering rigor to prompt engineering. It helps authors design `SKILL.md` instruction files by conducting intake interviews, generating A/B evaluation test suites (comparing output quality with and without the skill), optimizing trigger instructions in the YAML frontmatter, and compiling benchmarks.

### 6. `upsonic/unittest-generator`
*   **Article URL:** [https://skillsmp.com/skills/unittest-generator](https://skillsmp.com/skills/unittest-generator) (indexed on SkillsMP and LobeHub)
*   **Author/Publisher:** Upsonic / SkillsMP Marketplace Contributors
*   **Publication Date:** April 30, 2026
*   **Metrics:** Tied directly to the popular Upsonic Python agent framework (7,800+ GitHub stars).
*   **Description:** Focuses on the autonomous Claude Code agent designed for generating test suites. Given a module, it utilizes standard `unittest.TestCase` structures, organizes tests conceptually into subfolders (e.g., `tests/`), sets up setup/mocking parameters, and covers edge cases and boundary conditions automatically.

### 7. `sickn33/mcp-builder`
*   **Article URL:** [https://github.com/sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) (tracked via developer registries and the Antigravity skill tree)
*   **Author/Publisher:** @sickn33
*   **Publication Date:** May 27, 2026
*   **Metrics:** Cured into the Gaia skill catalog; marked as non-installable in June 2026.
*   **Description:** Represents a community skill implementation of the Model Context Protocol (MCP) server builder. It automates the generation of MCP servers in Python and Node.js. It manages the registration of tool functions, translates standard code interfaces to MCP schemas, and handles endpoint dispatch.

### 8. `mattpocock/skills`
*   **Article URL:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills) (reviewed extensively on Medium under "Real Engineering Claude Code Skills")
*   **Author/Publisher:** Matt Pocock
*   **Publication Date:** Early 2026
*   **Metrics:** Extremely high viral traction in the Claude Code community.
*   **Description:** A library of 19 engineering skills (installed via `npx skills@latest add mattpocock/skills`). It includes `/grill-me` and `/grill-with-docs` designed to force AI agents to pause and perform deep structural question-and-answer interviews before coding. It also handles Test-Driven Development (TDD) cycles, architectural reviews, and maintains project files like `CONTEXT.md` and ADRs.

### 9. `ruvnet/ruflo`
*   **Article URL:** [https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code](https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code) (formerly Claude Flow)
*   **Author/Publisher:** Reuven Cohen (@ruvnet)
*   **Publication Date:** Mid 2025 / Updated WASM release early 2026
*   **Metrics:** Highlighted in multi-agent orchestration publications.
*   **Description:** Explores Ruflo (previously Claude Flow), a Rust/WASM-based multi-agent orchestration harness. It coordinates 60-100+ specialized agents in parallel (Architect, QA, Coder) via a high-performance shared memory layer (HNSW-indexed vector memory) to execute complex, multi-module software tasks using the SPARC methodology.

### 10. `garrytan/gstack`
*   **Article URL:** [https://github.com/garrytan/gstack](https://github.com/garrytan/gstack) (featured in startup developer newsletters)
*   **Author/Publisher:** Garry Tan
*   **Publication Date:** March 2026
*   **Metrics:** Massive viral growth, exceeding 100,000 GitHub stars within weeks.
*   **Description:** GStack introduces a "Virtual Engineering Team" for Claude Code using 23+ persona-based slash commands (PM, QA, CEO, Release Manager). It enforces a strict startup iteration workflow (Think → Plan → Build → QA → Ship → Retro). It includes a automated QA capability using Playwright to run headless browser validation tests.

### 11. `obra/superpowers`
*   **Article URL:** [https://github.com/obra/superpowers](https://github.com/obra/superpowers) (detailed in DEV.to developer guides)
*   **Author/Publisher:** Jesse Vincent (@obra)
*   **Publication Date:** Early 2026
*   **Metrics:** Top-tier developer tool for agentic workflows.
*   **Description:** Details Superpowers, an opinionated framework that organizes development workflows for agents. It guides the model through brainstorming, planning, and TDD cycles before executing code. It is designed to prevent "context rot" and ensure the AI remains aligned with the human developer's specifications.

### 12. `pbakaus/impeccable`
*   **Article URL:** [https://github.com/pbakaus/impeccable](https://github.com/pbakaus/impeccable) (published on DEV.to and designer-developer blogs)
*   **Author/Publisher:** Paul Bakaus
*   **Publication Date:** Early 2026
*   **Metrics:** Widely adopted by frontend AI developers.
*   **Description:** Impeccable is a design-first skill library for AI coding assistants. Created by jQuery UI's founder, it aims to prevent generic AI designs. It provides rules to avoid common anti-patterns (system-default typography, nested cards, pure grays) and introduces commands like `/polish`, `/audit`, and `/critique` to ensure clean, customized layout and styling decisions.

---

## 13. `token-observability` (`gaia-research/skill-cost`) — Gaia Research Lab (self-attestation)
*   **Article URL:** [https://research.gaiaskilltree.com/](https://research.gaiaskilltree.com/)
*   **Author/Publisher:** Gaia Research (official org)
*   **Publication Date:** 2026
*   **Grade:** D
*   **Metrics:** estimatedViews: 0
*   **Description:** The official Gaia Research lab page (research.gaiaskilltree.com) lists gaia-research/skill-cost as a published, installable skill: 'Multi-harness token-usage cost reporter for pi, Claude Code, Codex, and opencode session logs. $ npx skills install gaia-research/skill-cost'. Self-attestation from the owning org. No independent third-party endorsement found. Source: isNew discovery 2026-07-30.

---

## 14. `format-output` (ayghri/i-have-adhd) — Data Science Collective (Medium), Gao Dalie
*   **Article URL:** [https://medium.com/data-science-collective/how-to-use-claude-adhd-skill-better-than-99-of-people-9876934d8548](https://medium.com/data-science-collective/how-to-use-claude-adhd-skill-better-than-99-of-people-9876934d8548)
*   **Author/Publisher:** Gao Dalie, Data Science Collective (941K followers)
*   **Publication Date:** ~2026-07-26 (~3 days before 2026-07-29)
*   **Grade:** A
*   **Metrics:** 142 claps; estimatedViews: 0 (Medium hides view count)
*   **Description:** Article in the Data Science Collective publication (941K followers). Shows 142 claps. Covers installation, use cases, and references a r/ClaudeCode Reddit post titled 'I gave Claude Code ADHD…and it thinks 2x better now'. Source: isNew discovery 2026-07-29.

---

## 15. `format-output` (ayghri/i-have-adhd) — Joe Njenga (Medium)
*   **Article URL:** [https://medium.com/@joe.njenga/i-tried-this-claude-code-adhd-skill-that-no-one-is-talking-about-a990a647b1c7](https://medium.com/@joe.njenga/i-tried-this-claude-code-adhd-skill-that-no-one-is-talking-about-a990a647b1c7)
*   **Author/Publisher:** Joe Njenga (23K followers on Medium)
*   **Publication Date:** 2026-07-20
*   **Grade:** B
*   **Metrics:** 3 claps visible; estimatedViews: 0
*   **Description:** Full install walkthrough for ayghri/i-have-adhd via claude plugin marketplace. Source: isNew discovery 2026-07-29.

---

## 16. `format-output` (ayghri/i-have-adhd) — New2026 (Medium)
*   **Article URL:** [https://new2026.medium.com/how-an-open-source-skill-turns-verbose-coding-agent-answers-into-action-first-instructions-for-410303d35765](https://new2026.medium.com/how-an-open-source-skill-turns-verbose-coding-agent-answers-into-action-first-instructions-for-410303d35765)
*   **Author/Publisher:** New2026 (251 followers)
*   **Publication Date:** ~2026-07-24 (~5 days before 2026-07-29)
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** 9-minute explainer describing all 10 rules of i-have-adhd and confirms multi-agent support (Claude Code, Codex, Zed). Minor account. Source: isNew discovery 2026-07-29.

---

## 17. `format-output` (ayghri/i-have-adhd) — Matthew Harwood (LinkedIn)
*   **Article URL:** [https://www.linkedin.com/posts/matthewcharwood_github-ayghrii-have-adhd-a-skill-for-activity-7484663342012334081-ejHy](https://www.linkedin.com/posts/matthewcharwood_github-ayghrii-have-adhd-a-skill-for-activity-7484663342012334081-ejHy)
*   **Author/Publisher:** Matthew Harwood (LinkedIn)
*   **Publication Date:** 2026
*   **Grade:** D
*   **Metrics:** estimatedViews: 0
*   **Description:** LinkedIn post sharing the repo with description 'A skill for your coding agent to stop it from burying the answer. ADHD-friendly output.' No view/reaction count verifiable from search snippet. Source: isNew discovery 2026-07-29.

---

## 18. `nextlevelbuilder/ux-audit` — Snyk, Stephen Thoemmes
*   **Article URL:** [https://snyk.io/articles/top-claude-skills-ui-ux-engineers/](https://snyk.io/articles/top-claude-skills-ui-ux-engineers/)
*   **Author/Publisher:** Snyk (developer security platform), Stephen Thoemmes
*   **Publication Date:** 2026
*   **Grade:** A
*   **Metrics:** estimatedViews: 0
*   **Description:** Snyk developer security blog lists ui-ux-pro-max as #5 of 8 top Claude skills for UI/UX engineers, alongside Anthropic and Vercel official skills. Star count shown as 29,636 at time of writing (repo has since grown to 111k). High-credibility publisher. Source: isNew discovery 2026-07-29.

---

## 19. `nextlevelbuilder/ux-audit` — Abhinav Dobhal (Medium, Feb 2026)
*   **Article URL:** [https://medium.com/@abhinav.dobhal/the-end-of-ai-slop-how-ui-ux-pro-max-is-solving-the-design-crisis-in-ai-generated-code-bbc23995f0e0](https://medium.com/@abhinav.dobhal/the-end-of-ai-slop-how-ui-ux-pro-max-is-solving-the-design-crisis-in-ai-generated-code-bbc23995f0e0)
*   **Author/Publisher:** Abhinav Dobhal (Medium)
*   **Publication Date:** 2026-02-05
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** 10-minute read covering the skill's architecture (BM25 ranking, 100 reasoning rules, 13-stack adaptation, design system persistence). Directly references the repo. Source: isNew discovery 2026-07-29.

---

## 20. `nextlevelbuilder/ux-audit` — dev.to, Petri Lahdelma / VertaaUX
*   **Article URL:** [https://dev.to/vertaaux/i-gave-my-ai-agent-a-ux-audit-superpower-cli-mcp-in-5-minutes-58d8](https://dev.to/vertaaux/i-gave-my-ai-agent-a-ux-audit-superpower-cli-mcp-in-5-minutes-58d8)
*   **Author/Publisher:** Petri Lahdelma / VertaaUX (dev.to)
*   **Publication Date:** 2026-04
*   **Grade:** D
*   **Metrics:** 0 reactions visible; estimatedViews: 0
*   **Description:** Covers a ux-audit CLI+MCP workflow (not directly the ui-ux-pro-max-skill repo). Very low engagement. Not directly about this skill; included for completeness. Source: isNew discovery 2026-07-29.

---

## 21. `scroll-world` (oso95/scroll-world) — Chase AI Blog
*   **Article URL:** [https://www.chaseai.io/blog/one-shot-scroll-animation-website-ai-skill](https://www.chaseai.io/blog/one-shot-scroll-animation-website-ai-skill)
*   **Author/Publisher:** Chase AI (156K YouTube subscribers)
*   **Publication Date:** 2026-07-12
*   **Grade:** B
*   **Metrics:** estimatedViews: 0
*   **Description:** Dedicated blog post (8 min read) by Chase AI. Covers full workflow, Fable 5 vs GPT-5.6 comparison, cost breakdown (~800 Higgsfield credits for 6 scenes, ~32 min build time for 4 scenes). Cross-posted with YouTube video. Substantive third-party coverage. Source: isNew discovery 2026-07-29.

---

## 22. `scroll-world` (oso95/scroll-world) — Instagram trending repos post
*   **Article URL:** [https://www.instagram.com/p/DasdkWbgHLN/](https://www.instagram.com/p/DasdkWbgHLN/)
*   **Author/Publisher:** Instagram (unattributed)
*   **Publication Date:** 2026
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** Instagram post highlighting scroll-world as one of 5 repos gaining +1,160 new stars in 7 days, with scroll-world specifically at +405 stars that week. No verified view count available. Source: isNew discovery 2026-07-29.

---

## 23. `agent-reach` (Panniantong/agent-reach) — LobeHub Skills Marketplace
*   **Article URL:** [https://lobehub.com/skills/panniantong-agent-reach-skill](https://lobehub.com/skills/panniantong-agent-reach-skill)
*   **Author/Publisher:** LobeHub (marketplace)
*   **Publication Date:** 2026
*   **Grade:** A
*   **Metrics:** estimatedViews: 10,200; 1,400 installs, 35 reviews, rated 4.5/5 as of 2026-07-29
*   **Description:** Listed in LobeHub Skills Marketplace under Search & Research category. Shows 10,200 views, 1,400 installs, 35 reviews, rated 4.5/5. Note: SKILL.md link points to tree/ path — flag for curation. Source: isNew discovery 2026-07-30.

---

## 24. `agent-reach` (Panniantong/agent-reach) — SitePoint
*   **Article URL:** [https://www.sitepoint.com/agent-reach-giving-your-ai-eyes-on-the-web/](https://www.sitepoint.com/agent-reach-giving-your-ai-eyes-on-the-web/)
*   **Author/Publisher:** SitePoint Team
*   **Publication Date:** 2026-03-02
*   **Grade:** B
*   **Metrics:** estimatedViews: 0
*   **Description:** Full tutorial covering installation, configuration, social platform search, React dashboard integration, MCP-compatible agent workflow, and best practices. Published on a major developer publisher. Source: isNew discovery 2026-07-30.

---

## 25. `agent-reach` (Panniantong/agent-reach) — David Lee, Medium
*   **Article URL:** [https://medium.com/@lordmoma/six-skills-that-turn-a-coding-agent-into-a-team-b9f6f49e9064](https://medium.com/@lordmoma/six-skills-that-turn-a-coding-agent-into-a-team-b9f6f49e9064)
*   **Author/Publisher:** David Lee (3.2K followers, Medium)
*   **Publication Date:** 2026-06-21
*   **Grade:** C
*   **Metrics:** estimatedViews: 0 (member-only story)
*   **Description:** Names Agent-Reach as 'the one to install carefully' for giving agents internet eyes, calling it harness-agnostic across Codex, Claude Code, Cursor, Gemini CLI. Source: isNew discovery 2026-07-30.

---

## 26. `agent-reach` (Panniantong/agent-reach) — SkillsLLM directory
*   **Article URL:** [https://skillsllm.com/skill/agent-reach](https://skillsllm.com/skill/agent-reach)
*   **Author/Publisher:** SkillsLLM (independent skills directory)
*   **Publication Date:** Added 2026-02-26
*   **Grade:** B
*   **Metrics:** estimatedViews: 0
*   **Description:** Independent skills directory listing showing 61,933 stars and 5,010 forks (data from GitHub). Security scan passed (pip audit + npm audit ran 2026-04-16, no issues found). Confirms early traction timeline. Source: isNew discovery 2026-07-30.

---

## 27. `agent-reach` (Panniantong/agent-reach) — VoltAgent/awesome-agent-skills
*   **Article URL:** [https://github.com/VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
*   **Author/Publisher:** VoltAgent (curated community collection)
*   **Publication Date:** 2026
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** Panniantong/Agent-Reach is listed in this curated community collection of agent skills alongside other notable skills. Confirms broad ecosystem awareness. Source: isNew discovery 2026-07-30.

---

## 28. `react-performance-optimization` (`vercel-labs/vercel-react-best-practices`) — InfoQ
*   **Article URL:** [https://www.infoq.com/news/2026/02/vercel-react-best-practices/](https://www.infoq.com/news/2026/02/vercel-react-best-practices/)
*   **Author/Publisher:** InfoQ, Daniel Curtis
*   **Publication Date:** 2026-02-27
*   **Grade:** B
*   **Metrics:** estimatedViews: 0
*   **Description:** InfoQ editorial news article covering the react-best-practices skill launch. InfoQ is a high-quality peer-edited tech publication with 57K+ Twitter followers and 232K YouTube subscribers. Source: isNew discovery 2026-07-30.

---

## 29. `react-performance-optimization` (`vercel-labs/vercel-react-best-practices`) — MarkTechPost
*   **Article URL:** [https://www.marktechpost.com/2026/01/18/vercel-releases-agent-skills-a-package-manager-for-ai-coding-agents-with-10-years-of-react-and-next-js-optimisation-rules/](https://www.marktechpost.com/2026/01/18/vercel-releases-agent-skills-a-package-manager-for-ai-coding-agents-with-10-years-of-react-and-next-js-optimisation-rules/)
*   **Author/Publisher:** MarkTechPost
*   **Publication Date:** 2026-01-18
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** Detailed writeup covering all three skills in the vercel-labs/agent-skills repo including react-best-practices. Mentions 40+ rules in 8 categories and the npm-style install pattern. Source: isNew discovery 2026-07-30.

---

## 30. `react-performance-optimization` (`vercel-labs/vercel-react-best-practices`) — Medium, Doran Gao
*   **Article URL:** [https://medium.com/@dorangao/optimizing-a-next-js-codebase-with-cursor-and-vercels-react-best-practices-skill-a263bd2d2f6a](https://medium.com/@dorangao/optimizing-a-next-js-codebase-with-cursor-and-vercels-react-best-practices-skill-a263bd2d2f6a)
*   **Author/Publisher:** Doran Gao (Medium)
*   **Publication Date:** 2026
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** 12-minute read showing a practical walkthrough of applying vercel-react-best-practices to a real Next.js codebase. Source: isNew discovery 2026-07-30.

---

## 31. `react-performance-optimization` (`vercel-labs/vercel-react-best-practices`) — Vercel Official Docs
*   **Article URL:** [https://vercel.com/docs/agent-resources/skills](https://vercel.com/docs/agent-resources/skills)
*   **Author/Publisher:** Vercel (official)
*   **Publication Date:** 2026
*   **Grade:** B
*   **Metrics:** estimatedViews: 0
*   **Description:** Vercel's own documentation page lists vercel-react-best-practices with the description 'React and Next.js performance optimization guidelines with 40+ rules across 8 categories'. Links to skills.sh marketplace entry. Confirms official first-party endorsement. Source: isNew discovery 2026-07-30.

---

## 32. `static-artwork-design` (`anthropics/canvas-design`) — Simon Willison's blog
*   **Article URL:** [https://simonwillison.net/2025/Oct/16/claude-skills/](https://simonwillison.net/2025/Oct/16/claude-skills/)
*   **Author/Publisher:** Simon Willison (high-authority independent developer commentator)
*   **Publication Date:** 2025-10-16
*   **Grade:** B
*   **Metrics:** estimatedViews: 0
*   **Description:** High-authority developer blog post covering the anthropics/skills repo launch, including canvas-design. Covers the broader skills paradigm that canvas-design is part of. Source: isNew discovery 2026-07-30.

---

## 33. `static-artwork-design` (`anthropics/canvas-design`) — Medium, 100 Claude Skills roundup
*   **Article URL:** [https://medium.com/@surajkhaitan16/i-tried-100-claude-skills-these-are-the-best-639e419b0325](https://medium.com/@surajkhaitan16/i-tried-100-claude-skills-these-are-the-best-639e419b0325)
*   **Author/Publisher:** Suraj Khaitan (Medium)
*   **Publication Date:** 2026
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** Lists canvas-design among top skills reviewed, described as producing 'HTML5 canvas compositions for marketing assets'. Source: isNew discovery 2026-07-30.

---

## 34. `static-artwork-design` (`anthropics/canvas-design`) — Snyk, AR/VR article
*   **Article URL:** [https://snyk.io/articles/top-claude-skills-ar-vr-developers-unity-webxr-spatial-computing/](https://snyk.io/articles/top-claude-skills-ar-vr-developers-unity-webxr-spatial-computing/)
*   **Author/Publisher:** Snyk (developer security platform)
*   **Publication Date:** 2026-02 (last updated)
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** Lists 'Anthropic Canvas & Frontend Design' at #7 for AR/VR developers, citing 66,460 stars (older snapshot) and verified SKILL.md. Notes canvas-design is useful for VR/AR UI mockups. Source: isNew discovery 2026-07-30.

---

## 35. `opinion` (`disler/opinion`) — note.com Japanese article
*   **Article URL:** [https://note.com/humble_bobcat51/n/n540d5333d005](https://note.com/humble_bobcat51/n/n540d5333d005)
*   **Author/Publisher:** humble_bobcat51 (note.com, Japanese)
*   **Publication Date:** 2026-07-25
*   **Grade:** D
*   **Metrics:** 8 likes visible; estimatedViews: 0
*   **Description:** Japanese-language in-depth analysis of fusion-harness covering the /opinion command as part of the AND-not-OR model fusion paradigm. Not in existing data lake. Source: isNew discovery 2026-07-29.

---

## 36. `plan-synthesis` (`merged-plan`) — Learning Atlas editorial summary
*   **Article URL:** [https://www.learningatlas.us/learning/video/AQl5Q-0l7FQ](https://www.learningatlas.us/learning/video/AQl5Q-0l7FQ)
*   **Author/Publisher:** Learning Atlas (third-party editorial)
*   **Publication Date:** 2026
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** Third-party editorial site independently indexed and summarised the IndyDevDan fusion-harness video, describing the architecture: two models run in parallel, outputs combined via /opinion, /fusion, /autovalidate commands. Confirms the skill is notable enough for editorial curation. Source: isNew discovery 2026-07-29.

---

## 37. `plan-synthesis` (`merged-plan`) — Alexander Talavera Karslake (LinkedIn)
*   **Article URL:** [https://www.linkedin.com/posts/alexander-talavera-karslake_anyone-that-thinks-they-can-run-a-local-model-activity-7483858611954290688-N5rb](https://www.linkedin.com/posts/alexander-talavera-karslake_anyone-that-thinks-they-can-run-a-local-model-activity-7483858611954290688-N5rb)
*   **Author/Publisher:** Alexander Talavera Karslake (LinkedIn)
*   **Publication Date:** 2026
*   **Grade:** D
*   **Metrics:** estimatedViews: 0 (LinkedIn not scrapeable)
*   **Description:** Developer community member discusses fusion-harness potentially becoming a standard open-source architecture for multi-model output merging. Source: isNew discovery 2026-07-29.

---

## 38. `disler/agent-fusion` — OpenRouter LinkedIn post
*   **Article URL:** [https://www.linkedin.com/posts/openrouter_introducing-fusion-the-smartest-compound-activity-7471706620662812673-lJUS](https://www.linkedin.com/posts/openrouter_introducing-fusion-the-smartest-compound-activity-7471706620662812673-lJUS)
*   **Author/Publisher:** OpenRouter (LinkedIn)
*   **Publication Date:** 2026
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** OpenRouter post announcing Fusion compound model feature; comments include explicit reference to fusion-harness and requests for it to be open-sourced. Confirms community awareness of disler/fusion-harness. Source: isNew discovery 2026-07-29.

---

## 39. `disler/agent-fusion` — Stacey Schneider (LinkedIn)
*   **Article URL:** [https://www.linkedin.com/posts/schneiderstacey_fable-dropped-yesterday-im-not-trying-it-activity-7470837127140904960-tRFE](https://www.linkedin.com/posts/schneiderstacey_fable-dropped-yesterday-im-not-trying-it-activity-7470837127140904960-tRFE)
*   **Author/Publisher:** Stacey Schneider (LinkedIn)
*   **Publication Date:** 2026
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** References fusion-harness in the context of model fusion becoming a standard open-source architecture. Appeared alongside OpenRouter DRACO benchmark results in search. Source: isNew discovery 2026-07-29.

---

## 40. `disler/agent-fusion` — Ji Chi (LinkedIn)
*   **Article URL:** [https://www.linkedin.com/posts/jichi_i-made-a-small-codex-skill-called-ask-n-times-activity-7478155793599492096-PrM4](https://www.linkedin.com/posts/jichi_i-made-a-small-codex-skill-called-ask-n-times-activity-7478155793599492096-PrM4)
*   **Author/Publisher:** Ji Chi (LinkedIn)
*   **Publication Date:** 2026
*   **Grade:** C
*   **Metrics:** estimatedViews: 0
*   **Description:** References fusion-harness as a potentially standard multi-agent composition architecture. Source: isNew discovery 2026-07-29.
