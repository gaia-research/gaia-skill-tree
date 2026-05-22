# [getagentseal](../../../docs/u/getagentseal/)/codeburn  [2★ · Named]
**ID:** token-observability  
**Type:** Basic Skill  
**Level:** 2★  
**Tier:** Named  
**Skill Call:** `/token-observability`

---

**Summary:** Observability tool for tracking AI coding agent token spend locally.

## Description
Tracks and analyzes token usage and cost across multiple AI models and agents, providing session-level and project-level spending metrics. Operates locally by reading session data directly from disk and utilizes local pricing calculation, ensuring no proxies or API keys are required. Features CLI commands to optimize token waste, compare models, and track yield.

## Use Case
A developer or engineering team uses this skill to monitor and optimize their spending across various AI coding assistants. By running it against local session logs from tools like Cursor or Aider, they can attribute token usage to specific projects, compare model costs, and identify inefficient, abandoned, or reverted tasks to reduce overall budget waste.

## Directives
Prioritize accurate local parsing of multi-tool session logs. Use up-to-date pricing data to convert tokens to cost. Provide actionable insights via clear CLI commands for optimization and comparison. Never send session data to external servers; all analysis must remain local to preserve privacy.

## Prerequisites
_None._

## Unlocks
- [Data Analysis](../extra/data-analysis.md)

## Evidence
| Class | Source | Evaluator | Date |
|---|---|---|---|
| B | https://github.com/getagentseal/codeburn | gemini-cli | 2026-05-14 |

## Known Agents
_None verified yet._

---
