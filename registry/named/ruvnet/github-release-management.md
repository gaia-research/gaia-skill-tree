---
id: ruvnet/github-release-management
name: GitHub Release Management
contributor: ruvnet
origin: false
role: variant
genericSkillRef: release-automation
status: named
title: "The Release Gatekeeper"
catalogRef: ruvnet-github-release-management
level: "3★"
description: Automates GitHub release creation, changelog generation, semantic versioning, and release note publishing.
links:
  github: https://github.com/ruvnet/ruflo/blob/main/.agents/skills/github-release-management/SKILL.md
tags:
  - github
  - release
  - versioning
  - changelog
  - automation
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
suiteRef: "ruvnet/github-suite"
---

## Overview

GitHub Release Management handles the full release lifecycle: semantic version calculation from conventional commits, automated changelog generation, release branch management, tag creation, and GitHub Releases publishing with generated notes. Integrates with CI/CD for automated release triggers.

## Key Capabilities

- **Semantic versioning**: automatic version calculation from conventional commit history
- **Automated changelog**: generated release notes from commit messages and PR descriptions
- **Release branch management**: branching strategies for stable release isolation
- **GitHub Releases publishing**: automated tag creation and release artifact attachment

## Origin

Published by @ruvnet as a variant implementation for the `release-automation` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
