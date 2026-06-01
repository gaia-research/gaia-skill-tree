---
id: vercel/find-skills
name: Find Skills
contributor: vercel
origin: true
genericSkillRef: skill-discovery
status: named
title: The Registry Scout
catalogRef: vercel-find-skills
level: 2★
description: Searches the skills.sh registry by keyword or category, queries install
  counts to surface popular skills, and auto-installs the selected skill into the
  current project's skills directory.
links:
  github: https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md
tags:
- skill-registry
- discovery
- skills-sh
- auto-install
createdAt: '2026-04-30'
updatedAt: '2026-04-30'
evidence:
- class: B
  source: https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: Vercel /find-skills slash command -- queries the skills.sh registry, checks
    install counts, and auto-installs matching skills.
---

## Overview

Find Skills is a registry-aware discovery tool published by Vercel Labs. The agent queries the skills.sh registry, filters results by the user's keyword, ranks candidates by install count, and installs the chosen skill with a single command. It eliminates the need for manual browsing of skill repositories.

## Origin

First published by @vercel (Vercel Labs). This is the origin implementation for the `skill-discovery` skill bucket.
