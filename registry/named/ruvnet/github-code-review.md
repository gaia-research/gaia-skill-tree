---
id: ruvnet/github-code-review
name: GitHub Code Review
contributor: ruvnet
origin: false
role: variant
genericSkillRef: code-review-pipeline
status: named
title: "The PR Surgeon"
catalogRef: ruvnet-github-code-review
level: "3★"
description: Automates GitHub pull request code review workflows including diff analysis, inline comments, review assignments, and approval gating.
links:
  github: https://github.com/ruvnet/ruflo
tags:
  - github
  - code-review
  - pull-request
  - automation
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
suiteRef: "ruvnet/ruflo"
---

## Overview

GitHub Code Review automates the full pull request review lifecycle on GitHub. It handles diff analysis for identifying problematic changes, inline comment generation, reviewer assignment based on file ownership, and approval gating workflows. The skill integrates with GitHub Actions for automated review triggers.

## Key Capabilities

- **Automated diff analysis**: identification of problematic changes across pull request diffs
- **Inline PR comments**: targeted comment generation at the file and line level
- **Reviewer assignment**: file-ownership-based routing to appropriate reviewers
- **Approval gating**: workflow enforcement requiring review sign-off before merge

## Origin

Published by @ruvnet as a variant implementation for the `code-review-pipeline` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
