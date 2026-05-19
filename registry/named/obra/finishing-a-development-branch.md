---
id: obra/finishing-a-development-branch
name: Finishing a Development Branch
contributor: obra
origin: true
genericSkillRef: finishing-a-development-branch
status: named
title: "The Clean Landing"
level: "2★"
description: Guides completion of development work by verifying tests first, then presenting structured options for merge, PR creation, or cleanup — never declaring done without a passing build.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md
tags:
  - branch-management
  - pull-request
  - merge
  - testing
  - completion
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
suiteRef: "obra/superpowers"
---

## Overview

Finishing a Development Branch by @obra defines the ritual for closing out a feature branch. Before offering any merge or PR option, the agent runs the test suite and confirms it passes. It then presents a structured menu — open a PR, squash-merge directly, or clean up — so the developer makes an informed choice rather than the agent acting unilaterally. The skill prevents the common failure mode of declaring work "done" with a broken build.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `finishing-a-development-branch` skill bucket.
