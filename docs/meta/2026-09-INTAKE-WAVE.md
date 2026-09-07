---
title: "September 2026 Intake Wave: Evidence Before Promotion"
author: "Gaia Research"
summary: Seven intake issues resolved through one topology gate, evidence verification, bounded suite curation, and honest rejection.
abstract: |
  Gaia completed a coordinated review of seven human-submitted intake issues. Five new promotion pull requests added 26 named entries and nine generic capabilities, one previously landed batch received its missing formal closure, and one incomplete proposal was declined with a concrete path to resubmission. Every accepted entry was mapped, evidenced, calibrated, validated, and merged without squashing.
label: Curation Report
---

## Abstract

Gaia completed a coordinated review of seven human-submitted intake issues. Five new promotion pull requests added 26 named entries and nine generic capabilities, one previously landed batch received its missing formal closure, and one incomplete proposal was declined with a concrete path to resubmission. Every accepted entry was mapped, evidenced, calibrated, validated, and merged without squashing.

## Executive Summary

This intake wave tested the full curation promise: broad enough to recognize new capability boundaries, strict enough not to mistake every upstream folder for a new generic skill, and transparent enough to explain rejection without discouraging future contribution.

The result was five registry merges:

| Intake | Outcome | Trust result | Merge |
|---|---|---|---|
| [#1676](https://github.com/gaia-research/gaia-skill-tree/issues/1676) | `mksglu/context-mode` under new `context-safe-execution` | 151.89 TM, Grade A, 4★ | [PR #1745](https://github.com/gaia-research/gaia-skill-tree/pull/1745) |
| [#1677](https://github.com/gaia-research/gaia-skill-tree/issues/1677) | `citrolabs/ego-browser` mapped to existing `browser-control` | 36.00 TM, Grade C, 2★ | [PR #1746](https://github.com/gaia-research/gaia-skill-tree/pull/1746) |
| [#1734](https://github.com/gaia-research/gaia-skill-tree/issues/1734) | `nateherkai/scroll-craft` under new `scroll-driven-web-design` | 82.22 TM, Grade B, 3★ | [PR #1748](https://github.com/gaia-research/gaia-skill-tree/pull/1748) |
| [#1481](https://github.com/gaia-research/gaia-skill-tree/issues/1481) | Bounded GBrain suite: one capstone and three reviewed components | 121.52 TM capstone; components 50.00 TM | [PR #1747](https://github.com/gaia-research/gaia-skill-tree/pull/1747) |
| [#1733](https://github.com/gaia-research/gaia-skill-tree/issues/1733) | HyperFrames capstone and 18 reviewed components | 163.63 TM capstone; components 50.00 TM | [PR #1740](https://github.com/gaia-research/gaia-skill-tree/pull/1740) |

The wave also completed the overdue close-out for [intake #1607](https://github.com/gaia-research/gaia-skill-tree/issues/1607), whose `leonxlnx/taste-skill` suite and `leonxlnx/unlazy` implementation had already landed through [PR #1608](https://github.com/gaia-research/gaia-skill-tree/pull/1608).

## New Capability Boundaries

Nine generic capabilities entered the graph across the five new merges:

- `context-safe-execution`
- `scroll-driven-web-design`
- `concept-synthesis`
- `gbrain`
- `audio-mixing`
- `creative-direction`
- `design-source-import`
- `interactive-presentation-authoring`
- `media-asset-orchestration`

Other implementations were deliberately mapped to existing capabilities. `citrolabs/ego-browser` became an implementation of `browser-control`; GBrain's `brain-ops` and `capture` mapped to `knowledge-management` and `personal-knowledge-management`; and HyperFrames components reused established video, animation, discovery, and framework-upgrade nodes wherever those boundaries already fit.

This distinction matters. Named implementations can multiply without forcing the generic graph to fragment around repository vocabulary.

## Suite Curation Without Scope Inflation

### GBrain

The GBrain capstone was kept separate from existing gstack-derived entries. Its suite contains only the three components reviewed in this intake:

- `garrytan/brain-ops`
- `garrytan/capture`
- `garrytan/concept-synthesis`

The review explicitly rejected `gbrain-advisor` and `gbrain-upgrade`. Both are useful project operations, but in their submitted form they are vendor-specific diagnostic and update wrappers rather than independent transferable capabilities.

### HyperFrames

HyperFrames landed as a 4★ suite capstone with 18 installable 3★ components. The evidence calculation discounts repository-wide adoption across the upstream skill count rather than crediting the same 44,308-star signal at full strength to every component.

`general-video` was excluded because its fallback/router scope duplicated the capstone. Five genuinely missing vendor-neutral capability boundaries were added; the remaining components mapped into existing topology.

Tooling remediation [PR #1744](https://github.com/gaia-research/gaia-skill-tree/pull/1744) landed before the suite. Installation instructions and evidence were pinned to upstream commit `7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd`.

## Honest Rejection Is Part of Curation

[Intake #1673](https://github.com/gaia-research/gaia-skill-tree/issues/1673) proposed `agent-checkpoint-resume`, a capability Gaia still considers valid through [gap #1426](https://github.com/gaia-research/gaia-skill-tree/issues/1426). The intake itself could not be promoted because it supplied no installable `SKILL.md`, claimed self-made attribution while citing LangGraph, and linked only to a bare third-party repository with no matching skill artifact.

The issue was closed with an explicit invitation to try again: publish a runnable skill, provide a pinned `blob/.../SKILL.md` URL, align attribution with the actual author, and attach evidence to the implementation being submitted. Rejecting an incomplete packet is not rejecting the contributor or the capability.

## Operational Result

Every promotion branch was merged forward onto the current `main`, regenerated from canonical registry source, and passed schema, DAG, reference, timeline, Trust Magnitude, generated-document, test, authorship, and security checks. Mainline merges used merge commits rather than squashing, preserving the curation and evidence history.

The five new promotion merges are:

1. `985fc01ad3c656fc429f87411b0571bdb804458c` — Context Mode
2. `9c1e575a` — Ego Browser
3. `54bfaa12a53f` — Scroll Craft
4. `6473e906fd67ead261c3de2151ab5717369b8f95` — GBrain
5. `0e89ccd43be22f7481d1cebc5773a73cc06b3740` — HyperFrames

Together they added 26 named entries in this session's new merges while retaining a clear audit trail for excluded candidates and the previously landed batch closure.

## References

[1] Gaia Research. [New skill intake schema](https://github.com/gaia-research/gaia-skill-tree/blob/main/.github/ISSUE_TEMPLATE/new_skill_intake.yml).

[2] Gaia Research. [Trust Magnitude methodology](https://gaiaskilltree.com/codex/trust-methodology.html).

[3] Gaia Research. [Public registry](https://gaiaskilltree.com/).
