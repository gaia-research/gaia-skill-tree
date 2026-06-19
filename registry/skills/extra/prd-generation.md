# [mattpocock](../../../docs/u/mattpocock/)/to-prd  [2★]
**ID:** prd-generation  
**Type:** Extra Skill  
**Rank:** _rank-less generic reference — stars are earned by named implementations_  
**Top named variant:** 2★  
**Skill Call:** `/prd-generation`

---

**Summary:** Synthesizes conversational context and codebase knowledge into a structured Product Requirements Document.

## Description
Synthesizes conversation context and codebase knowledge into a structured Product Requirements Document containing a problem statement, extensive user stories, implementation decisions, module boundaries, testing decisions, and out-of-scope items. It sketches major modules with deep-module opportunities, confirms scope with the user, and produces a strict issue tracker format without brittle code snippets.

## Use Case
A developer initiates a planning session to implement a new feature. They discuss requirements with the agent. The agent synthesizes this conversation, explores the current codebase architecture, and identifies the deep modules needed. It then generates a highly detailed PRD, formatting it as a structured issue with clear testing guidelines, and automatically pushes it to the project's issue tracker with a `ready-for-agent` triage label.

## Directives
1. Do NOT interview the user; solely synthesize known context and codebase state.
2. Respect domain glossary vocabulary and existing ADRs during synthesis.
3. Sketch deep modules (small interface, deep implementation).
4. Follow the strict PRD template: Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions, Out of Scope, and Further Notes.
5. Omit specific file paths or volatile code snippets to prevent fast-rotting documentation.

## Prerequisites
- [Write Report](../basic/write-report.md)
- [Plan and Decompose](../basic/plan-decompose.md)

## Unlocks
_None._

## Fusion Condition
_None specified._

## Named Implementations
| Named Skill | Contributor | Stars | Evidence |
|---|---|---|---|
| mattpocock/to-prd ⭑ | mattpocock | 2★ | 5 |

## Evidence (inherited capability)
_Capability-level evidence for this generic reference. Every named implementation above inherits it._

| Class | Source | Evaluator | Date |
|---|---|---|---|
| A | https://arxiv.org/abs/2507.19113 | mbtiongson1 | 2026-04-30 |

## Known Agents
_None verified yet._

---
