---
id: ruvnet/github-multi-repo
name: GitHub Multi-Repo
contributor: ruvnet
origin: true
genericSkillRef: multi-repo-coordination
status: named
title: "The Repository Conductor"
catalogRef: ruvnet-github-multi-repo
level: "2★"
description: Manages synchronized operations across multiple GitHub repositories including cross-repo PRs, dependency tracking, and bulk workflow automation.
links:
  github: https://github.com/ruvnet/ruflo
tags:
  - github
  - multi-repo
  - cross-repo
  - dependency-tracking
  - bulk-operations
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
suiteRef: "ruvnet/ruflo"
---

## Overview

GitHub Multi-Repo provides coordination across multiple repositories simultaneously. It handles cross-repository pull requests, dependency version tracking, bulk issue operations, and coordinated workflow triggers across repository sets. Useful for monorepo migrations and microservice fleet management.

## Key Capabilities

- **Cross-repo PR management**: coordinated pull requests spanning multiple repositories
- **Dependency tracking**: version synchronization and dependency graph management across repos
- **Bulk workflow triggers**: coordinated GitHub Actions execution across repository sets
- **Coordinated tagging and releases**: synchronized version tagging and release publishing

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `multi-repo-coordination` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
