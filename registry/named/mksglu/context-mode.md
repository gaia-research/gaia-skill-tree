---
id: mksglu/context-mode
name: Context Mode
contributor: mksglu
origin: true
genericSkillRef: context-safe-execution
status: named
level: 4★
description: "Use context-mode tools (ctx_execute, ctx_execute_file) instead of Bash/cat\
  \ when processing large outputs. Triggers: \"analyze logs\", \"summarize output\"\
  , \"process data\", \"parse JSON\", \"filter results\", \"extract errors\", \"check\
  \ build output\", \"analyze dependencies\", \"process API response\", \"large file\
  \ analysis\", \"page snapshot\", \"browser snapshot\", \"DOM structure\", \"inspect\
  \ page\", \"accessibility tree\", \"Playwright snapshot\", \"run tests\", \"test\
  \ output\", \"coverage report\", \"git log\", \"recent commits\", \"diff between\
  \ branches\", \"list containers\", \"pod status\", \"disk usage\", \"fetch docs\"\
  , \"API reference\", \"index documentation\", \"call API\", \"check response\",\
  \ \"query results\", \"find TODOs\", \"count lines\", \"codebase statistics\", \"\
  security audit\", \"outdated packages\", \"dependency tree\", \"cloud resources\"\
  , \"CI/CD output\".\n  Also triggers on ANY MCP tool output that may exceed 20 lines.\n\
  \  Subagent routing is handled automatically via PreToolUse hook."
createdAt: '2026-09-07'
updatedAt: '2026-09-07'
title: Context Mode
links:
  github: https://github.com/mksglu/context-mode/blob/6b8bf61f83abed6c3faf4e7c3ba02c162fadfedf/skills/context-mode/SKILL.md
timeline:
- timestamp: '2026-09-06T17:59:36Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mksglu/context-mode
- timestamp: '2026-09-06T17:59:39Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mksglu/context-mode (type: repo-own)'
- timestamp: '2026-09-06T17:59:43Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mksglu/context-mode/blob/6b8bf61f83abed6c3faf4e7c3ba02c162fadfedf/skills/context-mode/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-09-06T17:59:52Z'
  action: rank_up
  contributor: mbtiongson1
  details: Origin status set to true.
- timestamp: '2026-09-06T17:59:58Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 4★
evidence:
- source: https://github.com/mksglu/context-mode
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: repo-own
  notes: Verified upstream repository metrics at the approved pinned source; repo
    skill-count discount is based on 11 SKILL.md files.
  commits: 2172
  contributors: 110
  grade: B
- source: https://github.com/mksglu/context-mode/blob/6b8bf61f83abed6c3faf4e7c3ba02c162fadfedf/skills/context-mode/SKILL.md
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: github-stars-own
  notes: Verified GitHub stars and 11 SKILL.md files at the approved canonical root
    pinned commit; license is Elastic License 2.0 (ELv2).
  stars: 20473
  skillCountInRepo: 11
  grade: A
verification:
  firstEvidenceAt: '2026-09-06T17:59:39Z'
---

## Installation
Add installation instructions here.
