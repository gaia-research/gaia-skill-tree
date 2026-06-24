# Named Skills Benchmark Evaluation Report

This report presents objective benchmark scores, evaluation parameters, and performance metrics collected from manual search for the twelve registered named skills in the registry.

---

## Benchmark Summary Table

| Skill Identifier | Primary Benchmark / Metric | Score / Percentile | Date | Evaluation Setup / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **`devin-ai/autonomous-swe`** | SWE-bench (Unassisted) | **13.86% resolved** | Mar 12, 2024 | Evaluated on resolving real-world GitHub issues in Python repositories unassisted (no file hint provided). |
| **`safishamsi/graphify`** | Token Efficiency / RAG Compression | **Up to 71.5x token reduction** | May 2026 | Measured by querying compressed codebase graphs versus raw text reading across dynamic project directories. |
| **`browser-use/browser-harness`** | BU Bench V1 & Online-Mind2Web | **78% - 97% task success** (via Cloud) | Mid-2026 | 100 hard verified tasks from WebArena/Mind2Web; evaluates agent's ability to self-heal and interact with dynamic DOM pages. |
| **`firecrawl/firecrawl`** | Scrape Content Dataset V1 | **>95% success rate** / **P95 Latency ~3.4s** | May 2026 | Checked across 1,000 dynamic, JS-heavy URLs for markdown and structured output schema correctness. |
| **`anthropic/skill-creator`** | Built-in A/B Testing & Pass Rate | Dynamic (`benchmark.json`) | Apr 2026 | Plugin generates test cases and asserts expected behaviors dynamically to measure skill improvement. |
| **`upsonic/unittest-generator`** | Code Coverage & Test Pass Rate | ~7.8k stars (Adoption metric) | Apr 2026 | No centralized benchmark score; evaluated on test pass rates and mock coverage on target Python codebases. |
| **`sickn33/mcp-builder`** | Library Integration / Stars | Part of 1,500+ skill suite | May 2026 | Evaluated qualitatively by integration capability; does not possess a standalone public benchmark score. |
| **`mattpocock/skills`** | Process Adherence / Workflow gating | Qualitative / Process Adherence | Mid-2026 | Modular prompt engineering suite built to reduce agent drift through VERTICAL-slice TDD and PRD gates. |
| **`ruvnet/ruflo`** | SWE-bench (Swarm Solve Rate) | **84.8% solve rate** (vendor claim) | Feb 2026 | Multi-agent swarm orchestration platform using SONA routing; reports up to 75% API cost savings. |
| **`garrytan/gstack`** | Model Comparison / CWV Regression | **108,000+ stars** (Adoption metric) | Mar 2026 | Includes `gstack-model-benchmark` CLI for prompt performance and `/benchmark` for tracking Web Vitals. |
| **`obra/superpowers`** | Framework Adoption / Stars | **170,000+ stars** (Adoption metric) | Oct 2025 / Mid-2026 | Complete software development methodology suite for AI agents; restricts linear execution using process gates. |
| **`pbakaus/impeccable`** | UX Polishing Success Rate | **+59% layout improvement** / **38k+ stars** | May 2026 | Deterministic design audit checking 44 rules and 23 command helpers to eliminate aesthetic "AI slop". |

---

## Detailed Performance Analysis

### 1. `devin-ai/autonomous-swe`
* **Repository:** [cognition-labs/devin](https://github.com/cognition-labs/devin)
* **Benchmark:** SWE-bench (unassisted)
* **Score:** 13.86% resolved
* **Date:** March 12, 2024
* **Setup Description:** Tested on SWE-bench, which contains 2,294 software engineering problems from open-source GitHub projects. Devin was given only the codebase and the issue description in natural language. It successfully generated patches, ran tests, and resolved 13.86% of the bugs without human instruction on which files were affected (previous state-of-the-art unassisted was 1.96%).

### 2. `safishamsi/graphify`
* **Repository:** [safishamsi/graphify](https://github.com/safishamsi/graphify)
* **Benchmark:** RAG Token Compression & Retrieval Efficiency
* **Score:** Up to 71.5x token reduction per query
* **Date:** May 2026
* **Setup Description:** Evaluated on compiling unstructured project corpora (source code files, images, markdown documentation) into a local knowledge graph using tree-sitter AST analysis and semantic clustering (Leiden community detection). Token consumption was compared against raw file reading during deep architectural agent queries.

### 3. `browser-use/browser-harness`
* **Repository:** [browser-use/browser-harness](https://github.com/browser-use/browser-harness)
* **Benchmark:** BU Bench V1 (100 verified tasks) & Online-Mind2Web
* **Score:** 78% - 97% task success using Browser Use Cloud (`bu-ultra/max`); 80% using Claude Fable 5
* **Date:** Mid-2026
* **Setup Description:** Evaluated on 100 hard, verified-completable tasks originating from WebArena, Mind2Web, and BrowseComp. Success is judged by an LLM (Gemini 2.5 Flash) checking DOM and screenshot state changes. It tests how well the CDP-based harness handles selectors, rate-limits, and self-heals by runtime script generation.

### 4. `firecrawl/firecrawl`
* **Repository:** [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl)
* **Benchmark:** scrape-content-dataset-v1 (1,000 URLs) & Latency
* **Score:** >95% dynamic page scrape success; P95 Latency of ~3.4s
* **Date:** May 2026
* **Setup Description:** Run against a public test dataset of 1,000 distinct URLs comprising JS-heavy SPAs and sites protected by anti-bot measures. Evaluated on markdown output schema fidelity, truth-recall (comparing content against crawler ground truths), and P50/P90/P99 latency distribution.

### 5. `anthropic/skill-creator`
* **Repository:** [anthropics/skills](https://github.com/anthropics/skills) (plugin: `skill-creator`)
* **Benchmark:** Skill Eval Pass Rate (Dynamic A/B testing)
* **Score:** Variable based on developer prompt (results saved to local `benchmark.json`)
* **Date:** April 2026
* **Setup Description:** Includes a built-in evaluation harness that dynamically generates synthetic test prompts for a drafted skill, runs parallel baseline versus skill-enabled sessions, and uses grading agents to output win-rates, execution time, and token counts.

### 6. `upsonic/unittest-generator`
* **Repository:** [Upsonic/Upsonic](https://github.com/Upsonic/Upsonic)
* **Benchmark:** Execution Pass Rate & Coverage (GitHub Adoption: ~7.8k stars)
* **Score:** Modular TDD correctness (no official static benchmark score)
* **Date:** April 2026
* **Setup Description:** Evaluated by generating full `unittest.TestCase` suites from raw Python modules. The agent parses code concepts, mocks external dependencies, writes the tests to mirror the source folder structure, and validates if the test suite runs and covers error paths correctly.

### 7. `sickn33/mcp-builder`
* **Repository:** [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) (skill: `mcp-builder`)
* **Benchmark:** Library Scale & Stars
* **Score:** Over 1,500+ skills in the collection (no standalone quantitative score)
* **Date:** May 2026
* **Setup Description:** Evaluated qualitatively within the `antigravity-awesome-skills` directory for Claude Code, Cursor, and Gemini CLI. The skill provides step-by-step guidance for tools definition, schema modeling, and connection handling in Python/Node.js MCP setups.

### 8. `mattpocock/skills`
* **Repository:** [mattpocock/skills](https://github.com/mattpocock/skills)
* **Benchmark:** Process Adherence & Safety Constraints
* **Score:** Qualitative improvement in model drift reduction
* **Date:** Mid-2026
* **Setup Description:** Evaluated on how effectively it structures agent behavior. It forces strict verticals (TDD, issue-triage, PRD generation, and zoom-out map creation), preventing models from hallucinating large parallel changes and keeping code generation within tight test feedback loops.

### 9. `ruvnet/ruflo`
* **Repository:** [ruvnet/ruflo](https://github.com/ruvnet/ruflo) (rebranded from Claude Flow)
* **Benchmark:** SWE-bench (Swarm Solve Rate) & cost-routing
* **Score:** 84.8% solve rate (vendor claim); up to 75% API cost savings
* **Date:** February 2026
* **Setup Description:** Tested using multi-agent swarms with SONA adaptive memory routing. Simpler tasks are routed to lightweight models, and complex coding bugs are solved by fanning out specialized sub-agents with graph-based pathfinding, yielding high resolve rates on SWE-bench tasks.

### 10. `garrytan/gstack`
* **Repository:** [garrytan/gstack](https://github.com/garrytan/gstack)
* **Benchmark:** gstack-model-benchmark & CWV metrics (GitHub: 108,000+ stars)
* **Score:** Qualitative LLM speed/cost/layout comparison; Core Web Vitals regression checks
* **Date:** March 2026
* **Setup Description:** Employs a CLI comparison tool (`gstack-model-benchmark`) that runs the same code prompts across models (GPT, Gemini, Claude) to compare cost, latency, and layout. Also integrates a `/benchmark` QA command tracking page speed and regression metrics.

### 11. `obra/superpowers`
* **Repository:** [obra/superpowers](https://github.com/obra/superpowers)
* **Benchmark:** Framework Adoption (GitHub: 170,000+ stars)
* **Score:** v5.1.0 landmark adoption across Claude Code, Codex CLI, Cursor, and Gemini CLI
* **Date:** October 2025 (First release), updated Mid-2026
* **Setup Description:** Evaluated on the execution of complex multi-file codebase changes. Enforces a 7-stage development process (brainstorming, writing-plans, executing-plans, TDD, worktrees, code-review, and validation-before-completion) to eliminate agent path loops and code degradation.

### 12. `pbakaus/impeccable`
* **Repository:** [pbakaus/impeccable](https://github.com/pbakaus/impeccable)
* **Benchmark:** UI polishing success & rule audit (GitHub: 38,000+ stars)
* **Score:** +59% layout/typography consistency improvement (qualitative user testing)
* **Date:** May 2026
* **Setup Description:** Runs an agentic design checker executing 23 specialized commands (e.g., `/audit`, `/polish`, `/typeset`) against generated frontend code. Audits code compliance against 44 deterministic rules (such as OKLCH color spacing, typographic hierarchy, and anti-slop guidelines).
