---
id: mattpocock/improve-codebase-architecture
name: Improve Codebase Architecture
contributor: mattpocock
origin: false
genericSkillRef: refactor-code
status: named
title: "The Architecture Improver"
title: "The Depth Seeker"
catalogRef: mattpocock-improve-codebase-architecture
level: "3★"
description: Identifies architectural deepening opportunities in a codebase — shallow modules with high interface-to-implementation ratios — using domain-glossary vocabulary and the deletion test, then grills the developer on the chosen candidate to design a deep-module replacement with better locality and testability.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/improve-codebase-architecture/SKILL.md
tags:
  - architecture-review
  - deep-modules
  - refactoring
  - locality
  - testability
  - deletion-test
createdAt: "2026-04-30"
updatedAt: "2026-04-30"
suiteRef: "mattpocock/engineering"
---

## Overview

Improve Codebase Architecture applies a specific vocabulary of architectural leverage: modules, interfaces, implementations, depth, seams, adapters, and the deletion test. The agent explores the codebase organically looking for shallow modules (interface nearly as complex as the implementation), tightly-coupled modules leaking across seams, and pure functions extracted for testability but hiding the real bugs in their call sites.

Candidate opportunities are presented as a numbered list with files, problem, solution, and benefits framed in terms of locality and leverage. The agent then drops into a grilling loop on the chosen candidate, updating CONTEXT.md as new terms crystallise and offering ADRs only when rejections contain load-bearing reasons a future reviewer would need.

## Origin

Published by @mattpocock (Matt Pocock, Total TypeScript). Named implementation of the `refactor-code` skill bucket for the architecture-analysis-and-deepening use case.
