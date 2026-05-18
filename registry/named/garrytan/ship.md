---
id: garrytan/ship
name: Ship
contributor: garrytan
origin: false
genericSkillRef: finishing-a-development-branch
status: named
title: "Gstack Ship"
catalogRef: garrytan-ship
level: "4★"
description: Automated end-to-end deployment workflow that merges the base branch, runs tests, reviews the diff, bumps the VERSION file, updates the CHANGELOG, commits, pushes to the remote, and creates a pull request in a single command.
links:
  github: https://github.com/garrytan/gstack/blob/main/ship/SKILL.md
tags:
  - ship
  - deploy
  - pr-automation
  - release
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
---

## Overview

Gstack Ship automates the entire last-mile shipping ritual. On hearing "ship it", "create a PR", or "deploy this", it detects and merges the base branch, executes tests, reviews the diff for regressions, increments the VERSION file, writes a CHANGELOG entry, commits the release artifacts, pushes, and opens a pull request — all without manual steps.
