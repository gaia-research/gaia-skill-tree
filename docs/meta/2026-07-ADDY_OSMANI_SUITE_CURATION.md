---
title: "Curation Report: Addy Osmani 7-Skill Suite Integration"
author: "Gaia Research"
summary: "Gaia integrates Addy Osmani's 7-Skill suite, establishing component-level mappings to canonical generic references and applying mothership discounting."
abstract: |
  This note documents the curation of the 7-Skill suite from Addy Osmani's agent-skills repository into the Gaia registry. All 7 components, including the existing test-driven-development skill, have been successfully linked to the newly minted agent-skills suite capstone at Level 1★ (Awakened).
label: "Curation"
---

## Abstract

Following the Git Ship Done (GSD) integration, Gaia has successfully curated the 7-Skill developer pipeline from Addy Osmani's `agent-skills` repository. The new named skills map cleanly to existing generic references in the registry and establish a structured software engineering loop for AI agents. Stargazer evidence has been mapped to each component with a repository divisor of 7 to prevent signal inflation.

## Component Mappings

The following named skills have been registered and linked under the `addy-osmani` contributor namespace:

- `/spec` mapped to `addy-osmani/spec-driven-development` (`prd-generation`)
- `/plan` mapped to `addy-osmani/planning-and-task-breakdown` (`vertical-slice-planning`)
- `/build` mapped to `addy-osmani/incremental-implementation` (`executing-plans`)
- `/test` linked to `addy-osmani/test-driven-development` (`test-driven-development`, existing 2★ skill)
- `/review` mapped to `addy-osmani/code-review-and-quality` (`code-review-pipeline`)
- `/ship` mapped to `addy-osmani/shipping-and-launch` (`finishing-a-development-branch`)
- `/code-simplify` mapped to `addy-osmani/code-simplification` (`refactor-code`)

All components were successfully associated with the suite capstone `addy-osmani/agent-skills` using the `suiteRef` / `suiteComponents` attributes.

## Evidence and Discounting

The suite is backed by a repository carrying ~68,564 GitHub Stars. In line with Gaia's star-bar rules and to prevent the mothership discount from distorting individual skill levels, a divisor of `skillCountInRepo: 7` was applied. This counts only the true user-facing pipeline components and intentionally excludes minor utility helper files.

The components have been introduced at Level 1★ (Awakened). A timeline note has been appended to the suite capstone registry node logging the successful fusion event.

## References

[1] Addy Osmani Agent Skills Repository: https://github.com/addyosmani/agent-skills
[2] Gaia Issue 928 (L5 Approved Curation): https://github.com/gaia-research/gaia-skill-tree/issues/928
[3] Git Ship Done Curation Report: https://github.com/gaia-research/gaia-skill-tree/blob/main/docs/meta/reports/2026-07-03-gsd-suite-curation.html
