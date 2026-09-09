---
title: "September 9 Rank Calibration"
author: "Gaia Research"
summary: "Updated named-skill ranks to match current Trust Magnitude grades and added Steward drift detection."
abstract: |
  A registry-wide calibration pass corrected stale named-skill ranks after Trust Magnitude recomputation. Frozen skills remain exempt, and two review items were intentionally deferred.
label: Registry Update
---

## Changes

A Trust Magnitude calibration pass updated 48 named skills:

| Rank&nbsp;Change | Skills |
|---|---|
| 5★ → 4★ | nextlevelbuilder/ui-ux-pro-max; addy-osmani/agent-skills; addy-osmani/code-simplification; obra/superpowers; pbakaus/impeccable; ruvnet/ruflo |
| 5★ → 3★ | addy-osmani/incremental-implementation; addy-osmani/planning-and-task-breakdown; addy-osmani/spec-driven-development |
| 4★ → 3★ | addy-osmani/code-review-and-quality; addy-osmani/performance-optimization; addy-osmani/shipping-and-launch; firecrawl/firecrawl-build-interact; firecrawl/firecrawl-build-onboarding; firecrawl/firecrawl-build-search; firecrawl/firecrawl-skills; garrytan/cso; mattpocock/diagnose; mattpocock/to-tickets; ruvnet/agentdb; ruvnet/reasoningbank |
| 3★ → 2★ | garrytan/garrytan; mattpocock/tdd; ruvnet/dual-mode; ruvnet/flow-nexus; ruvnet/github-suite; ruvnet/ruflo-v3 |
| 3★ → 1★ | martin-stepanoski/nielsen-heuristics-audit |
| 2★ → 1★ | laravel/upgrade-laravel-v13; remotion-dev/remotion-best-practices; remotion-dev/remotion-captions; remotion-dev/remotion-create; remotion-dev/remotion-docs; remotion-dev/remotion-interactivity; remotion-dev/remotion-maps; remotion-dev/remotion-markup; remotion-dev/remotion-multimedia; remotion-dev/remotion-render; remotion-dev/remotion-saas; remotion-dev/remotion-studio; remotion-dev/remotion-upgrade; supabase/supabase-postgres-best-practices; supabase/supabase |
| 1★ → 4★ | google-deepmind/workflow-skill-creator |
| 1★ → 3★ | firecrawl/firecrawl-research-index; leonxlnx/unlazy; panniantong/agent-reach |
| 1★ → 2★ | aplaceforallmystuff/log-to-daily; disler/agent-fusion |

`gaiabot/repo-docs-before-pr` and `xquik-dev/hermes-tweet` remain unchanged for joint review. Explicitly frozen skills were excluded from calibration.

## Steward

Added a read-only Steward sensor that detects rank/TM drift and proposes the exact `gaia dev calibrate` command without mutating registry data. The sensor distinguishes explicit `upstream_deprecated` freeze events from ordinary `installable: false` records.
