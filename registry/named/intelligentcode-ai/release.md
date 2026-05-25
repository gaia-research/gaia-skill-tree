---
id: intelligentcode-ai/release
name: Release
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md
genericSkillRef: release-automation
status: named
title: The Shipwright's Will
catalogRef: intelligentcode-ai-release
level: 2★
description: Automates the full release cycle — semantic version bump, CHANGELOG update,
  PR merge, git tag, and GitHub release creation with multiple verification gates.
tags:
- release
- semver
- changelog
- git-tag
- github-release
- automation
updatedAt: '2026-05-25'
---

## Overview

Drives a release from a merged feature branch to a published GitHub release. Determines the correct semantic version from commit messages (conventional commits), updates CHANGELOG.md, creates and pushes the tag, and publishes a release with auto-generated notes.

## Key behaviours

- Conventional commits parser to determine major/minor/patch bump
- CHANGELOG.md update following Keep-a-Changelog format
- Git tag creation with signed commits where configured
- GitHub Release API call with release notes derived from commit log

## Source

[intelligentcode-ai/skills — release/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md)
