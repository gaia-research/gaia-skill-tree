---
id: martin-stepanoski/nielsen-heuristics-audit
name: Nielsen Heuristics Audit
contributor: martin-stepanoski
origin: false
genericSkillRef: ux-audit
status: named
title: The Ten Laws of Sight
catalogRef: martin-stepanoski-nielsen-heuristics-audit
level: 2★
description: Audits a UI interface against Jakob Nielsen's 10 usability heuristics
  step-by-step, scoring each heuristic, surfacing violations, and producing a prioritized
  remediation report.
links:
  github: https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md
tags:
- ux
- usability
- nielsen
- heuristics
- accessibility
createdAt: '2026-04-30'
updatedAt: '2026-06-02'
evidence:
- class: B
  source: https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: Martin Stepanoski @mastepanoski/claude-skills -- /nielsen-heuristics-audit
    audits UI against Nielsen 10 usability heuristics step-by-step.
timeline:
- timestamp: '2026-06-02T01:42:59Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to pbakaus/impeccable.
---

## Overview

Nielsen Heuristics Audit by Martin Stepanoski applies Jakob Nielsen's 10 usability heuristics as a structured evaluation checklist. For each heuristic — visibility of system status, match between system and real world, user control and freedom, consistency, error prevention, recognition over recall, flexibility, aesthetics, error recovery, and help — the agent assesses the interface, assigns a severity score, and documents specific violations. The final output is a prioritized remediation report.

## Origin

First published by @mastepanoski (Martin Stepanoski) as an NPM package. This is the origin implementation for the `ux-audit` skill bucket.
