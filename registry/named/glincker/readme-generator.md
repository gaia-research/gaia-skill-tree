---
id: glincker/readme-generator
name: README Generator
contributor: glincker
origin: false
genericSkillRef: write-report
status: named
title: The Document Weaver
catalogRef: glincker-readme-generator
level: 2★
description: Analyzes a project's directory structure, dependency manifests, and configuration
  files to generate a professional README.md covering installation, usage, API reference,
  and contributing guidelines.
links:
  github: https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md
tags:
- documentation
- readme
- code-analysis
- project-structure
createdAt: '2026-04-30'
updatedAt: '2026-06-10'
timeline:
- timestamp: '2026-06-02T23:33:02Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to garrytan/retro.
- timestamp: '2026-06-10T05:38:16Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md
evidence:
- class: B
  source: https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: Published implementation in the GLINCKER Claude Code Marketplace; reproducible
    from SKILL.md.
---

## Overview

README Generator by GLINCKER inspects the project tree, reads `package.json`, `pyproject.toml`, or equivalent manifests, and infers the project's purpose, dependencies, and entry points. It then produces a structured README.md with badges, installation steps, usage examples, and a contributing section — calibrated to the project's actual technology stack.

## Origin

First published by @GLINCKER via the Claude Code Marketplace. This is the origin implementation for the `write-report` skill bucket under the documentation generation use case.
