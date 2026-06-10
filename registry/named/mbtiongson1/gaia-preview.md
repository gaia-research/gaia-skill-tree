---
id: mbtiongson1/gaia-preview
name: Gaia Preview
contributor: mbtiongson1
origin: false
genericSkillRef: deployment-automation
status: named
level: 2★
description: Generates a preview render of proposed registry changes — showing how
  new or modified skill entries will appear on the profile page and in the skill graph
  before the PR is merged.
createdAt: '2026-05-27'
updatedAt: '2026-06-10'
title: The Change Previewer
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md
tags:
- registry-curation
- preview
- staging
timeline:
- timestamp: '2026-05-26T16:37:01Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-preview
- timestamp: '2026-06-10T05:38:17Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md
evidence:
- class: B
  source: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: Project-local agent skill driving branch preview deploys via sync-artifacts.yml;
    implementation public at SKILL.md.
---

## Overview

Triggers a remote documentation regeneration and Cloudflare deployment for the current branch via `gh workflow run sync-artifacts.yml -f deploy=true`. Preferred for design previews when working in containerized environments where `localhost` is not available. Zero local footprint, consistent canonical build environment, automatic deployment.
