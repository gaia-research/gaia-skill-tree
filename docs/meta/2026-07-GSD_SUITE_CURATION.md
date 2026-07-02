---
title: "GSD Suite Curation: From Command Pipeline to Registry Fusion"
author: "Gaia Research"
summary: "Gaia adds the GSD pipeline as a named suite and introduces a stricter trust-appraisal step for high-star suite curation."
abstract: |
  This note records the initial curation of Git Ship Done (GSD) into Gaia. The registry now tracks five concrete pipeline steps and a starless fusion node, while deferring automatic S-grade treatment until independent evidence and suite-fusion mechanics mature.
label: "Curation"
---

## Abstract

Gaia added the Git Ship Done pipeline as a named suite candidate with five user-facing steps: discuss, plan, execute, verify, and ship. The curation intentionally separates installation-oriented suite metadata from canonical fusion structure: the starless `git-ship-done-pipeline` node records how the capabilities fuse, while the named `gsd-build/get-shit-done` implementation carries repository evidence and remains Awakened pending further review.

## What changed

The new curation adds:

- `gsd-build/discuss-phase` mapped to `brainstorming`.
- `gsd-build/plan-phase` mapped to `writing-plans`.
- `gsd-build/execute-phase` mapped to `subagent-driven-development`.
- `gsd-build/verify-work` mapped to `verification-before-completion`.
- `gsd-build/ship` mapped to `finishing-a-development-branch`.
- `gsd-build/get-shit-done` mapped to the new starless `git-ship-done-pipeline` fusion node.

The source repository is archived, but it carries substantial historical adoption signal. Gaia therefore records it without treating the star count as sufficient for immediate high-star promotion.

## Trust appraisal before promotion

This PR also introduces `/trust-appraise`, a non-mutating dry-run helper for proposed suites. It compares repository stars, repository activity, and proposed fusion components before curation reaches human review. The companion `/trust-appraise-all` keeps the existing full-registry Trust Magnitude inspection workflow.

The dry run showed why caution matters: broad suite component counts can manufacture high Trust Magnitude if helper files are counted as origins. For GSD, the curated boundary is five user-facing pipeline steps, not every command and helper agent in the repository.

## Follow-up evidence requests

Gaia opened follow-up issues requesting independent evidence for GSD and future Addy Osmani suite candidates. Desired signals include verifier attestations, independent usage reports, benchmark results, social signals, and installability checks. This evidence will decide future star movement.

## Open mechanics

A CLI gap remains: Gaia needs a registry-level `gaia dev fuse` command that creates or updates a starless fusion node, writes suite manifests when requested, and appends schema-valid fusion timeline events without touching user trees. That work is tracked separately so future suite curation does not rely on multi-command choreography.

## References

[1] GSD v1 repository: https://github.com/gsd-build/get-shit-done
[2] GSD v2 candidate: https://github.com/open-gsd/gsd-core
[3] Addy Osmani agent skills: https://github.com/addyosmani/agent-skills
