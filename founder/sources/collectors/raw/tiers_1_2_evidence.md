# Named Skills Evidence Collection

This document contains manually collected, live evidence for the specified named skills in the Gaia Skill Tree registry.

---

## 1. devin-ai/autonomous-swe

* **Skill ID**: `devin-ai/autonomous-swe`
* **Name**: Autonomous SWE
* **Primary Repository URL**: `https://github.com/CognitionAI/devin-swebench-results` (Note: The proprietary Devin code itself is closed-source; `cognition-labs/devin` is a non-existent/404 repository. The closest public repository demonstrating their codebase capabilities and benchmark results is `CognitionAI/devin-swebench-results` or `CognitionAI/devin-extension`.)
* **Current Stars**: **124 stars**

### Collected Evidence
* **Source**: [CognitionAI/devin-swebench-results](https://github.com/CognitionAI/devin-swebench-results)
  * **Type**: Repository
  * **Date**: 2026-06-18
  * **Notes**: Contains Cognition's results, methodology, and technical evaluation on the SWE-bench benchmark.
* **Source**: [Introducing Devin (Official Blog)](https://www.cognition.ai/blog/introducing-devin)
  * **Type**: Blog
  * **Date**: 2024-03-12 (Accessed 2026-06-18)
  * **Notes**: Official product release post explaining the capabilities, environment sandboxing, and autonomous workflow of Devin.
* **Source**: [SWE-bench Technical Report (Official Blog)](https://www.cognition.ai/blog/swe-bench-technical-report)
  * **Type**: Technical Report
  * **Date**: 2024-03-12 (Accessed 2026-06-18)
  * **Notes**: Describes how Devin runs evaluations, identifies issue patterns, and self-corrects codebases.

---

## 2. safishamsi/graphify

* **Skill ID**: `safishamsi/graphify`
* **Name**: Graphify
* **Primary Repository URL**: `https://github.com/safishamsi/graphify`
* **Current Stars**: **68,766 stars**

### Collected Evidence
* **Source**: [safishamsi/graphify](https://github.com/safishamsi/graphify)
  * **Type**: Repository
  * **Date**: 2026-06-18
  * **Notes**: Main repository containing local parsing logic, Tree-sitter configurations, RAG pipeline, and code visualizer.
* **Source**: [Mapping Codebases with Graphify: Knowledge Graphs for LLMs](https://medium.com/gitconnected/mapping-codebases-with-graphify-knowledge-graphs-for-llms)
  * **Type**: Blog / Article (Medium)
  * **Date**: 2026-06-18
  * **Notes**: Technical walkthrough of Graphify's AST extraction, token cost reduction, and its integration into developer assistants.
* **Source**: [Graphify Labs / Penpax](https://graphifylabs.ai)
  * **Type**: Official Website
  * **Date**: 2026-06-18
  * **Notes**: Official homepage detailing Graphify's commercial layer (Penpax) for real-time background knowledge graph updates.

---

## 3. browser-use/browser-harness

* **Skill ID**: `browser-use/browser-harness`
* **Name**: Browser Harness
* **Primary Repository URL**: `https://github.com/browser-use/browser-use` (and related harness repository `https://github.com/browser-use/browser-harness`)
* **Current Stars**: 
  * `browser-use/browser-use`: **99,349 stars**
  * `browser-use/browser-harness`: **15,027 stars**

### Collected Evidence
* **Source**: [browser-use/browser-use](https://github.com/browser-use/browser-use)
  * **Type**: Repository
  * **Date**: 2026-06-18
  * **Notes**: Main open-source SDK repository for connecting LLM agents to Chrome browsers.
* **Source**: [browser-use/browser-harness](https://github.com/browser-use/browser-harness)
  * **Type**: Repository
  * **Date**: 2026-06-18
  * **Notes**: The self-healing CDP browser harness repo designed for developer agent CLI workflows (e.g., Claude Code, Codex).
* **Source**: [Browser Use Official Documentation](https://docs.browser-use.com/)
  * **Type**: Official Documentation
  * **Date**: 2026-06-18
  * **Notes**: API quickstart, environment variables guide, and integration instructions for agentic web tasks.
* **Source**: [The Bitter Lesson of Agent Harnesses](https://browser-use.com/posts/bitter-lesson-agent-harnesses)
  * **Type**: Blog / Article
  * **Date**: 2026-06-18
  * **Notes**: Official article exploring developer struggles with browser selectors and the necessity of self-healing agent wrappers.

---

## 4. firecrawl/firecrawl

* **Skill ID**: `firecrawl/firecrawl`
* **Name**: Firecrawl
* **Primary Repository URL**: `https://github.com/mendableai/firecrawl` (redirects to `https://github.com/firecrawl/firecrawl`)
* **Current Stars**: **134,209 stars**

### Collected Evidence
* **Source**: [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl)
  * **Type**: Repository
  * **Date**: 2026-06-18
  * **Notes**: Main repository featuring crawlers, markdown extraction API, and direct MCP server endpoints.
* **Source**: [Firecrawl Official Documentation](https://docs.firecrawl.dev)
  * **Type**: Official Documentation
  * **Date**: 2026-06-18
  * **Notes**: API specification, `/scrape` and `/crawl` endpoints usage guides, and LLM-formatting rules.
* **Source**: [Firecrawl Blog](https://www.firecrawl.dev/blog)
  * **Type**: Blog
  * **Date**: 2026-06-18
  * **Notes**: Product log showcasing the addition of agentic `/interact` endpoints, allowing AI to bypass JS and click buttons.

---

## 5. anthropic/skill-creator

* **Skill ID**: `anthropic/skill-creator`
* **Name**: Skill Creator
* **Primary Repository URL**: `https://github.com/anthropics/skills`
* **Current Stars**: **152,229 stars**

### Collected Evidence
* **Source**: [anthropics/skills](https://github.com/anthropics/skills)
  * **Type**: Repository
  * **Date**: 2026-06-18
  * **Notes**: Official codebase hosting specifications, example skills, and optimization utilities for Anthropic's Agent Skills.
* **Source**: [skill-creator Skill Folder](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
  * **Type**: Skill File / Code
  * **Date**: 2026-06-18
  * **Notes**: The specific skill-creator instruction file that conducts interactive interview loops and outputs new `SKILL.md` documents.
* **Source**: [Equipping agents for the real world with Agent Skills](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
  * **Type**: Blog / Engineering
  * **Date**: 2026-06-18
  * **Notes**: Engineering blog highlighting design constraints, context management, and standard rules for composing skills.
* **Source**: [Creating Custom Skills (Claude Help Center)](https://support.claude.com/en/articles/12512198-creating-custom-skills)
  * **Type**: Official Help Documentation
  * **Date**: 2026-06-18
  * **Notes**: Practical guide for authoring, testing, and activating custom skills locally or on Claude.ai.

---

## 6. upsonic/unittest-generator

* **Skill ID**: `upsonic/unittest-generator`
* **Name**: Unittest Generator
* **Primary Repository URL**: `https://github.com/Upsonic/Upsonic`
* **Current Stars**: **7,887 stars**

### Collected Evidence
* **Source**: [Upsonic/Upsonic](https://github.com/Upsonic/Upsonic)
  * **Type**: Repository
  * **Date**: 2026-06-18
  * **Notes**: Python autonomous agent framework repository, which packs community-contributed prebuilt agents.
* **Source**: [Upsonic Official Documentation](https://docs.upsonic.ai)
  * **Type**: Official Documentation
  * **Date**: 2026-06-18
  * **Notes**: Conceptual explanation of sandbox execution, agent prompts, and testing integrations.
* **Source**: [Prebuilt Autonomous Agents Guide](https://docs.upsonic.ai/concepts/prebuilt-autonomous-agents/overview)
  * **Type**: Official Documentation
  * **Date**: 2026-06-18
  * **Notes**: Describes how community skills (such as the unittest generators) are shipped as single-execution runnable agents.

---

## 7. sickn33/mcp-builder

* **Skill ID**: `sickn33/mcp-builder`
* **Name**: sickn33 MCP Builder
* **Primary Repository URL**: `https://github.com/sickn33/antigravity-awesome-skills`
* **Current Stars**: **41,000 stars**

### Collected Evidence
* **Source**: [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)
  * **Type**: Repository
  * **Date**: 2026-06-18
  * **Notes**: The primary open-source index of over 1,500 reusable markdown-based agent skills.
* **Source**: [mcp-builder Skill in Awesome Skills](https://github.com/sickn33/antigravity-awesome-skills/tree/main/skills/mcp-builder)
  * **Type**: Skill File / Code
  * **Date**: 2026-06-18
  * **Notes**: Specific directory containing the tool builder instructions, schemas, and templates for MCP server scaffolding.
* **Source**: [LobeHub Plugins Registry](https://lobehub.com/)
  * **Type**: Marketplace
  * **Date**: 2026-06-18
  * **Notes**: Platform where these agentic plugins are cataloged and made accessible for Lobe Chat/Gemini integration.
