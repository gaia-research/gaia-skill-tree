---
id: garrytan/land-and-deploy
name: Land and Deploy
contributor: garrytan
origin: false
genericSkillRef: deployment-automation
status: named
title: "Land and Deploy"
catalogRef: garrytan-land-and-deploy
level: "4★"
description: Automates the final production shipping stages — merging a PR, monitoring CI/deploy completion, and verifying live site health through canary checks — picking up where /ship leaves off with safety gates at each step to prevent broken deployments reaching users.
links:
  github: https://github.com/garrytan/gstack/blob/main/land-and-deploy/SKILL.md
tags:
  - deployment
  - production
  - merge
  - canary
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
---

## Overview

Land and Deploy handles the production handoff that /ship leaves at the PR stage. It makes the merge decision, monitors CI pipeline completion, waits for the deploy to propagate, then runs canary health checks against the live site — with safety gates throughout to halt and alert rather than silently shipping a broken build.
