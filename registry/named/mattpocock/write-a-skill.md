---
id: mattpocock/write-a-skill
name: Write a Skill
contributor: mattpocock
origin: false
genericSkillRef: tool-creation
status: named
title: "The Skill Builder"
title: "The Skill Scaffolder"
catalogRef: mattpocock-write-a-skill
level: "3★"
description: Guides creation of new agent skills through a structured requirements interview, then produces a SKILL.md with a trigger-aware description, progressive-disclosure layout, and optional bundled scripts or reference files — ready for installation in any Claude Code, Cursor, or Codex CLI skills directory.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/productivity/write-a-skill/SKILL.md
tags:
  - skill-authoring
  - meta-agent
  - claude-code
  - skill-scaffolding
  - progressive-disclosure
createdAt: "2026-04-30"
updatedAt: "2026-04-30"
suiteRef: "mattpocock/productivity"
---

## Overview

Write a Skill is a meta-agent skill that walks the author through a structured interview (task domain, use cases, need for scripts, reference materials) before generating a SKILL.md. The output follows progressive-disclosure principles: the description field is crafted as the sole trigger signal visible to the agent at selection time (max 1024 chars, "use when…" pattern), and the body is split across SKILL.md, REFERENCE.md, and EXAMPLES.md when content exceeds 100 lines.

The skill also codifies the decision rules for when to bundle scripts (deterministic operations that would otherwise be regenerated each turn) and when to split files (distinct domains, rarely-needed advanced features).

## Origin

Second named implementation of the `tool-creation` skill bucket (origin: anthropic/skill-creator). Matt Pocock's version emphasises progressive disclosure, the trigger-description contract, and the scripts-vs-instructions decision rubric.
