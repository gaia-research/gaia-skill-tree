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
updatedAt: '2026-05-30'
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
---

## Overview

Triggers a remote documentation regeneration and Cloudflare deployment for the current branch via `gh workflow run sync-artifacts.yml -f deploy=true`. Preferred for design previews when working in containerized environments where `localhost` is not available. Zero local footprint, consistent canonical build environment, automatic deployment.
