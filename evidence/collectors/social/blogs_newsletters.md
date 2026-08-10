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

<!-- appended: 2026-07-29 -->

## 13. `token-observability` — Gaia Research Lab (self-attestation)
*   **Article URL:** [https://research.gaiaskilltree.com/](https://research.gaiaskilltree.com/)
*   **Grade:** D

---

## 14. `format-output` — Data Science Collective (Medium), Gao Dalie
*   **Article URL:** [https://medium.com/data-science-collective/how-to-use-claude-adhd-skill-better-than-99-of-people-9876934d8548](https://medium.com/data-science-collective/how-to-use-claude-adhd-skill-better-than-99-of-people-9876934d8548)
*   **Grade:** A

---

## 15. `format-output` — Joe Njenga (Medium)
*   **Article URL:** [https://medium.com/@joe.njenga/i-tried-this-claude-code-adhd-skill-that-no-one-is-talking-about-a990a647b1c7](https://medium.com/@joe.njenga/i-tried-this-claude-code-adhd-skill-that-no-one-is-talking-about-a990a647b1c7)
*   **Grade:** B

---

## 16. `format-output` — New2026 (Medium)
*   **Article URL:** [https://new2026.medium.com/how-an-open-source-skill-turns-verbose-coding-agent-answers-into-action-first-instructions-for-410303d35765](https://new2026.medium.com/how-an-open-source-skill-turns-verbose-coding-agent-answers-into-action-first-instructions-for-410303d35765)
*   **Grade:** C

---

## 17. `format-output` — Matthew Harwood (LinkedIn)
*   **Article URL:** [https://www.linkedin.com/posts/matthewcharwood_github-ayghrii-have-adhd-a-skill-for-activity-7484663342012334081-ejHy](https://www.linkedin.com/posts/matthewcharwood_github-ayghrii-have-adhd-a-skill-for-activity-7484663342012334081-ejHy)
*   **Grade:** D

---

## 18. `nextlevelbuilder/ux-audit` — Snyk, Stephen Thoemmes
*   **Article URL:** [https://snyk.io/articles/top-claude-skills-ui-ux-engineers/](https://snyk.io/articles/top-claude-skills-ui-ux-engineers/)
*   **Grade:** A

---

## 19. `nextlevelbuilder/ux-audit` — Abhinav Dobhal (Medium, Feb 2026)
*   **Article URL:** [https://medium.com/@abhinav.dobhal/the-end-of-ai-slop-how-ui-ux-pro-max-is-solving-the-design-crisis-in-ai-generated-code-bbc23995f0e0](https://medium.com/@abhinav.dobhal/the-end-of-ai-slop-how-ui-ux-pro-max-is-solving-the-design-crisis-in-ai-generated-code-bbc23995f0e0)
*   **Grade:** C

---

## 20. `nextlevelbuilder/ux-audit` — dev.to, Petri Lahdelma / VertaaUX
*   **Article URL:** [https://dev.to/vertaaux/i-gave-my-ai-agent-a-ux-audit-superpower-cli-mcp-in-5-minutes-58d8](https://dev.to/vertaaux/i-gave-my-ai-agent-a-ux-audit-superpower-cli-mcp-in-5-minutes-58d8)
*   **Grade:** D

---

## 21. `scroll-world` — Chase AI Blog
*   **Article URL:** [https://www.chaseai.io/blog/one-shot-scroll-animation-website-ai-skill](https://www.chaseai.io/blog/one-shot-scroll-animation-website-ai-skill)
*   **Grade:** B

---

## 22. `scroll-world` — Instagram trending repos post
*   **Article URL:** [https://www.instagram.com/p/DasdkWbgHLN/](https://www.instagram.com/p/DasdkWbgHLN/)
*   **Grade:** C

---

## 23. `agent-reach` — LobeHub Skills Marketplace
*   **Article URL:** [https://lobehub.com/skills/panniantong-agent-reach-skill](https://lobehub.com/skills/panniantong-agent-reach-skill)
*   **SKILL.md:** [https://github.com/Panniantong/Agent-Reach/blob/main/SKILL.md](https://github.com/Panniantong/Agent-Reach/blob/main/SKILL.md)
*   **Grade:** A

---

## 24. `agent-reach` — SitePoint
*   **Article URL:** [https://www.sitepoint.com/agent-reach-giving-your-ai-eyes-on-the-web/](https://www.sitepoint.com/agent-reach-giving-your-ai-eyes-on-the-web/)
*   **Grade:** B

---

## 25. `agent-reach` — David Lee, Medium
*   **Article URL:** [https://medium.com/@lordmoma/six-skills-that-turn-a-coding-agent-into-a-team-b9f6f49e9064](https://medium.com/@lordmoma/six-skills-that-turn-a-coding-agent-into-a-team-b9f6f49e9064)
*   **Grade:** C

---

## 26. `agent-reach` — SkillsLLM directory
*   **Article URL:** [https://skillsllm.com/skill/agent-reach](https://skillsllm.com/skill/agent-reach)
*   **Grade:** B

---

## 27. `agent-reach` — VoltAgent/awesome-agent-skills
*   **Article URL:** [https://github.com/VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
*   **Grade:** C

---

## 28. `react-performance-optimization` — InfoQ
*   **Article URL:** [https://www.infoq.com/news/2026/02/vercel-react-best-practices/](https://www.infoq.com/news/2026/02/vercel-react-best-practices/)
*   **Grade:** B

---

## 29. `react-performance-optimization` — MarkTechPost
*   **Article URL:** [https://www.marktechpost.com/2026/01/18/vercel-releases-agent-skills-a-package-manager-for-ai-coding-agents-with-10-years-of-react-and-next-js-optimisation-rules/](https://www.marktechpost.com/2026/01/18/vercel-releases-agent-skills-a-package-manager-for-ai-coding-agents-with-10-years-of-react-and-next-js-optimisation-rules/)
*   **Grade:** C

---

## 30. `react-performance-optimization` — Medium, Doran Gao
*   **Article URL:** [https://medium.com/@dorangao/optimizing-a-next-js-codebase-with-cursor-and-vercels-react-best-practices-skill-a263bd2d2f6a](https://medium.com/@dorangao/optimizing-a-next-js-codebase-with-cursor-and-vercels-react-best-practices-skill-a263bd2d2f6a)
*   **Grade:** C

---

## 31. `react-performance-optimization` — Vercel Official Docs
*   **Article URL:** [https://vercel.com/docs/agent-resources/skills](https://vercel.com/docs/agent-resources/skills)
*   **Grade:** B

---

## 32. `static-artwork-design` — Simon Willison's blog
*   **Article URL:** [https://simonwillison.net/2025/Oct/16/claude-skills/](https://simonwillison.net/2025/Oct/16/claude-skills/)
*   **Grade:** B

---

## 33. `static-artwork-design` — Medium, 100 Claude Skills roundup
*   **Article URL:** [https://medium.com/@surajkhaitan16/i-tried-100-claude-skills-these-are-the-best-639e419b0325](https://medium.com/@surajkhaitan16/i-tried-100-claude-skills-these-are-the-best-639e419b0325)
*   **Grade:** C

---

## 34. `static-artwork-design` — Snyk, AR/VR article
*   **Article URL:** [https://snyk.io/articles/top-claude-skills-ar-vr-developers-unity-webxr-spatial-computing/](https://snyk.io/articles/top-claude-skills-ar-vr-developers-unity-webxr-spatial-computing/)
*   **Grade:** C

---

## 35. `opinion` — note.com Japanese article
*   **Article URL:** [https://note.com/humble_bobcat51/n/n540d5333d005](https://note.com/humble_bobcat51/n/n540d5333d005)
*   **Grade:** D

---

## 36. `plan-synthesis` — Learning Atlas editorial summary
*   **Article URL:** [https://www.learningatlas.us/learning/video/AQl5Q-0l7FQ](https://www.learningatlas.us/learning/video/AQl5Q-0l7FQ)
*   **Grade:** C

---

## 37. `plan-synthesis` — Alexander Talavera Karslake (LinkedIn)
*   **Article URL:** [https://www.linkedin.com/posts/alexander-talavera-karslake_anyone-that-thinks-they-can-run-a-local-model-activity-7483858611954290688-N5rb](https://www.linkedin.com/posts/alexander-talavera-karslake_anyone-that-thinks-they-can-run-a-local-model-activity-7483858611954290688-N5rb)
*   **Grade:** D

---

## 38. `disler/agent-fusion` — OpenRouter LinkedIn post
*   **Article URL:** [https://www.linkedin.com/posts/openrouter_introducing-fusion-the-smartest-compound-activity-7471706620662812673-lJUS](https://www.linkedin.com/posts/openrouter_introducing-fusion-the-smartest-compound-activity-7471706620662812673-lJUS)
*   **Grade:** C

---

## 39. `disler/agent-fusion` — Stacey Schneider (LinkedIn)
*   **Article URL:** [https://www.linkedin.com/posts/schneiderstacey_fable-dropped-yesterday-im-not-trying-it-activity-7470837127140904960-tRFE](https://www.linkedin.com/posts/schneiderstacey_fable-dropped-yesterday-im-not-trying-it-activity-7470837127140904960-tRFE)
*   **Grade:** C

---

## 40. `disler/agent-fusion` — Ji Chi (LinkedIn)
*   **Article URL:** [https://www.linkedin.com/posts/jichi_i-made-a-small-codex-skill-called-ask-n-times-activity-7478155793599492096-PrM4](https://www.linkedin.com/posts/jichi_i-made-a-small-codex-skill-called-ask-n-times-activity-7478155793599492096-PrM4)
*   **Grade:** C

### `programmatic-video-composition` — self-attestation
* **Skill:** `programmatic-video-composition`
* **Source:** https://github.com/remotion-dev/skills/blob/main/skills/remotion-best-practices/SKILL.md
* **Claimed evidence type:** self-attestation
* **Attribution scope:** standalone


### `postgres-best-practices` — self-attestation
* **Skill:** `postgres-best-practices`
* **Source:** https://github.com/supabase/agent-skills/blob/main/skills/supabase-postgres-best-practices/SKILL.md
* **Claimed evidence type:** self-attestation
* **Attribution scope:** standalone

