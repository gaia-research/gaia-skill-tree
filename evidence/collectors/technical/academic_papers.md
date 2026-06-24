# Academic Research Report: Named Skills & Underlying Methodologies

This report documents the academic papers, preprints (arXiv), and conference publications that discuss, evaluate, or cite the twelve registered named skills (or their underlying frameworks and methodologies) in the Gaia Skill Tree.

---

## Summary Table of Academic Evidence

| # | Skill ID | Academic Paper Title | Primary Authors | Publication Date | Citations | Link |
|---|---|---|---|---|---|---|
| 1 | `devin-ai/autonomous-swe` | Beyond Final Code: A Process-Oriented Error Analysis of Software Development Agents in Real-World GitHub Scenarios | Zhi Chen, Wei Ma, Lingxiao Jiang | March 2025 | Low / New | [arXiv:2503.12374](https://arxiv.org/abs/2503.12374) |
| 2 | `safishamsi/graphify` | CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases | Xiangyan Liu et al. | August 2024 | ~89 | [arXiv:2408.03910](https://arxiv.org/abs/2408.03910) |
| 3 | `browser-use/browser-harness` | When Bots Take the Bait: Exposing and Mitigating the Emerging Social Engineering Attack in Web Automation Agent | Xinyi Wu et al. | January 2026 | ~2 | [arXiv:2601.07263](https://arxiv.org/abs/2601.07263) |
| 4 | `firecrawl/firecrawl` | Improving and Evaluating Open Deep Research Agents | Doaa Allabadi, Kyle Bradbury, Jordan M. Malof | August 2025 | Low / New | [arXiv:2508.10152](https://arxiv.org/abs/2508.10152) |
| 5 | `anthropic/skill-creator` | Large Language Models as Tool Makers | Tianle Cai et al. | May 2023 | ~300+ | [arXiv:2305.17126](https://arxiv.org/abs/2305.17126) |
| 6 | `upsonic/unittest-generator` | CoverUp: Coverage-Guided LLM-Based Test Generation | Juan Altmayer Pizzorno, Emery D. Berger | March 2024 | ~15 | [arXiv:2403.16218](https://arxiv.org/abs/2403.16218) |
| 7 | `sickn33/mcp-builder` | Model Context Protocol (MCP) at First Glance: Studying the Security and Maintainability of MCP Servers | Mohammed Mehedi Hasan et al. | June 2025 | Low / New | [arXiv:2506.13538](https://arxiv.org/abs/2506.13538) |
| 8 | `mattpocock/skills` | SoK: Agentic Skills — Beyond Tool Use in LLM Agents | Yanna Jiang et al. | February 2026 | ~52 | [arXiv:2602.20867](https://arxiv.org/abs/2602.20867) |
| 9 | `ruvnet/ruflo` | "Do Not Mention This to the User": Detecting and Understanding Malicious Agent Skills in the Wild | Yi Liu et al. | February 2026 | Low / New | [arXiv:2602.06547](https://arxiv.org/abs/2602.06547) |
| 10 | `garrytan/gstack` | Agentic Social Affordance Framework (ASAF): Agent Identity Design as a Collaboration Interface in Multi-Agent Systems | Meng-Han Lee | June 2026 | Low / New | [arXiv:2606.09832](https://arxiv.org/abs/2606.09832) |
| 11 | `obra/superpowers` | From Runnable to Shippable: Multi-Agent Test-Driven Development for Generating Full-Stack Web Applications from Requirements | Yuxuan Wan et al. | May 2026 | ~0-6 | [arXiv:2605.17242](https://arxiv.org/abs/2605.17242) |
| 12 | `pbakaus/impeccable` | DesignRepair: Dual-Stream Design Guideline-Aware Frontend Repair with Large Language Models | Mingyue Yuan et al. | November 2024 | ~19 | [arXiv:2411.01606](https://arxiv.org/abs/2411.01606) |

---

## Detailed Findings per Skill

### 1. `devin-ai/autonomous-swe`
*   **Paper Title:** Beyond Final Code: A Process-Oriented Error Analysis of Software Development Agents in Real-World GitHub Scenarios (Accepted at ICSE 2026)
*   **Authors:** Zhi Chen, Wei Ma, and Lingxiao Jiang
*   **Publication URL:** [https://arxiv.org/abs/2503.12374](https://arxiv.org/abs/2503.12374)
*   **Publication Date:** March 2025
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    Devin by Cognition Labs is historically recognized as the first commercial autonomous software engineering (SWE) agent. This study shifts the evaluation of autonomous SWE agents from final code outputs to process trajectories on the **SWE-bench** benchmark. By analyzing trajectories and execution logs of top-ranked coding agents, the authors characterize the debugging behaviors, error patterns (e.g., `ModuleNotFoundError` and complex `OSError` occurrences), and tool-usage strategies critical to the design of autonomous debuggers.

---

### 2. `safishamsi/graphify`
*   **Paper Title:** CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases (NAACL 2025)
*   **Authors:** Xiangyan Liu, Bo Lan, Zhiyuan Hu, Yang Liu, Zhicheng Zhang, Fei Wang, Michael Qizhe Shieh, and Wenmeng Zhou
*   **Publication URL:** [https://arxiv.org/abs/2408.03910](https://arxiv.org/abs/2408.03910)
*   **Publication Date:** August 2024
*   **Citation Count:** ~89 citations
*   **Summary & Relevance:** 
    Graphify maps codebases into structured, queryable knowledge graphs using AST parsing. CodexGraph is the foundational methodology paper for this approach. It bridges the gap between LLMs and codebases by constructing a queryable code graph database modeling entity relationships (inheritance, usage, imports). This allows agents to perform structure-aware navigation and multi-hop queries, mimicking Graphify's AST-guided memory layer to optimize retrieval and reduce token usage in repository-scale tasks.

---

### 3. `browser-use/browser-harness`
*   **Paper Title:** When Bots Take the Bait: Exposing and Mitigating the Emerging Social Engineering Attack in Web Automation Agent
*   **Authors:** Xinyi Wu, Geng Hong, Yueyue Chen, MingXuan Liu, Feier Jin, Xudong Pan, Jiarun Dai, and Baojun Liu
*   **Publication URL:** [https://arxiv.org/abs/2601.07263](https://arxiv.org/abs/2601.07263)
*   **Publication Date:** January 12, 2026
*   **Citation Count:** ~2 citations
*   **Summary & Relevance:** 
    `browser-use` is a mainstream open-source web-interaction and browser control framework. This paper evaluates the security of `browser-use` and related agentic browsers against a social engineering threat paradigm called **AgentBait**. The authors demonstrate how adversarial inducement prompts embedded in web interfaces can manipulate the agent's browser-harness reasoning. They propose **SUPERVISOR**, a consistency verification layer to mitigate these exploits.

---

### 4. `firecrawl/firecrawl`
*   **Paper Title:** Improving and Evaluating Open Deep Research Agents
*   **Authors:** Doaa Allabadi, Kyle Bradbury, and Jordan M. Malof
*   **Publication URL:** [https://arxiv.org/abs/2508.10152](https://arxiv.org/abs/2508.10152)
*   **Publication Date:** August 2025
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    Firecrawl converts websites into LLM-ready markdown or structured data. This paper evaluates Deep Research Agents (DRAs) that perform autonomous web navigation to answer multifaceted queries. The authors analyze the reliance of open agents on advanced scraping and crawling pipelines—including Firecrawl—for robust context extraction and search-guided question decomposition.

---

### 5. `anthropic/skill-creator`
*   **Paper Title:** Large Language Models as Tool Makers (LATM)
*   **Authors:** Tianle Cai, Xuezhi Wang, Tengyu Ma, Xinyun Chen, and Denny Zhou
*   **Publication URL:** [https://arxiv.org/abs/2305.17126](https://arxiv.org/abs/2305.17126)
*   **Publication Date:** May 2023
*   **Citation Count:** ~300+ citations
*   **Summary & Relevance:** 
    Skill Creator acts as a meta-agent that interviews users to generate ready-to-use skill files (`SKILL.md`). This process maps directly to the **Large Language Models as Tool Makers (LATM)** paradigm. LATM splits agent architectures into a "tool maker" phase (where a powerful LLM designs and verifies reusable tools) and a "tool user" phase (where a cheaper LLM deploys them). This serves as the underlying methodology for automated skill/tool authoring.

---

### 6. `upsonic/unittest-generator`
*   **Paper Title:** CoverUp: Coverage-Guided LLM-Based Test Generation
*   **Authors:** Juan Altmayer Pizzorno and Emery D. Berger
*   **Publication URL:** [https://arxiv.org/abs/2403.16218](https://arxiv.org/abs/2403.16218)
*   **Publication Date:** March 2024
*   **Citation Count:** ~15 citations
*   **Summary & Relevance:** 
    Upsonic's unittest-generator autonomously crafts unittest suites by interacting with the code. CoverUp provides the theoretical and empirical implementation details for this. It utilizes a coverage-guided loop where LLMs generate regression tests, run code coverage tools, and iteratively debug failing tests or missing mocks to achieve high line and branch coverage.

---

### 7. `sickn33/mcp-builder`
*   **Paper Title:** Model Context Protocol (MCP) at First Glance: Studying the Security and Maintainability of MCP Servers
*   **Authors:** Mohammed Mehedi Hasan, Hao Li, Emad Fallahzadeh, Gopi Krishnan Rajbahadur, Bram Adams, and Ahmed E. Hassan
*   **Publication URL:** [https://arxiv.org/abs/2506.13538](https://arxiv.org/abs/2506.13538)
*   **Publication Date:** June 2025
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    MCP Builder creates Model Context Protocol (MCP) servers in Python and Node.js. This empirical study conducts a security and maintainability review of the emergent MCP ecosystem. It evaluates server health, tool schemas, and maintainability pitfalls developers face when building and deploying MCP servers, outlining key best practices.

---

### 8. `mattpocock/skills`
*   **Paper Title:** SoK: Agentic Skills — Beyond Tool Use in LLM Agents
*   **Authors:** Yanna Jiang, Delong Li, Haiyu Deng, Baihe Ma, Xu Wang, Qin Wang, and Guangsheng Yu
*   **Publication URL:** [https://arxiv.org/abs/2602.20867](https://arxiv.org/abs/2602.20867)
*   **Publication Date:** February 24, 2026
*   **Citation Count:** ~52 citations
*   **Summary & Relevance:** 
    This Systematization of Knowledge (SoK) paper investigates the shift from simple raw tool calls to "agentic skills"—packaged procedural expertise (such as Matt Pocock's skills framework). It formalizes how skills structure agent workflows, allow multi-turn planning, decouple execution from raw prompts, and enhance consistency.

---

### 9. `ruvnet/ruflo`
*   **Paper Title:** "Do Not Mention This to the User": Detecting and Understanding Malicious Agent Skills in the Wild (USENIX Security 2026)
*   **Authors:** Yi Liu, Zhihao Chen, Yanjun Zhang, Gelei Deng, Yuekang Li, Jianting Ning, and Leo Yu Zhang
*   **Publication URL:** [https://arxiv.org/abs/2602.06547](https://arxiv.org/abs/2602.06547)
*   **Publication Date:** February 2026 (v3 updated June 2026)
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    Ruflo is a multi-agent swarm platform featuring the **Flow Nexus** workflow system. This security audit paper specifically studies and references Ruflo's Flow Nexus skill platform (`flow-nexus`) as a case study for evaluating malicious behaviors in third-party agent skill ecosystems. The authors analyze how layered permissions and credential harvesting are modeled inside agent skills.

---

### 10. `garrytan/gstack`
*   **Paper Title:** Agentic Social Affordance Framework (ASAF): Agent Identity Design as a Collaboration Interface in Multi-Agent Systems
*   **Authors:** Meng-Han Lee
*   **Publication URL:** [https://arxiv.org/abs/2606.09832](https://arxiv.org/abs/2606.09832)
*   **Publication Date:** June 2026
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    Garry Tan's `gstack` is a multi-agent startup builder utilizing defined personas (CEO, Designer, EM, QA). ASAF explores the "social affordance layer" of multi-agent networks, identifying `gstack` as a prime example of "roleplaying clusters." The study demonstrates how identity signaling and defined social personas improve collaborative governance and structure human-agent expectations.

---

### 11. `obra/superpowers`
*   **Paper Title:** From Runnable to Shippable: Multi-Agent Test-Driven Development for Generating Full-Stack Web Applications from Requirements
*   **Authors:** Yuxuan Wan, Tingshuo Liang, Jiakai Xu, Jingyu Xiao, Yintong Huo, and Michael R. Lyu
*   **Publication URL:** [https://arxiv.org/abs/2605.17242](https://arxiv.org/abs/2605.17242)
*   **Publication Date:** May 17, 2026
*   **Citation Count:** ~0-6 citations
*   **Summary & Relevance:** 
    Superpowers by Jesse Vincent enforces strict planning, testing, and git branch discipline. This study introduces **TDDev**, a multi-agent framework implementing test-driven development (TDD) and verification loops. TDDev mirrors the core cycle of Superpowers by mandating a requirements-to-test specification phase, running sandboxed testing, and performing plan-driven refactoring before code is shipped.

---

### 12. `pbakaus/impeccable`
*   **Paper Title:** DesignRepair: Dual-Stream Design Guideline-Aware Frontend Repair with Large Language Models (ICSE 2025)
*   **Authors:** Mingyue Yuan, Jieshan Chen, Zhenchang Xing, Aaron Quigley, Yuyu Luo, Tianqi Luo, Gelareh Mohammadi, Qinghua Lu, and Liming Zhu
*   **Publication URL:** [https://arxiv.org/abs/2411.01606](https://arxiv.org/abs/2411.01606)
*   **Publication Date:** November 2024
*   **Citation Count:** ~19 citations
*   **Summary & Relevance:** 
    Impeccable is a visual auditing and frontend polishing tool for AI agents. DesignRepair provides the theoretical backing for guideline-aware frontend repair. It introduces a dual-stream architecture (combining visual design rules and code structure) to automatically fix UI layout inconsistencies, color contrast errors, and design violations in generated frontend code, validating the efficacy of automated UX audits.
