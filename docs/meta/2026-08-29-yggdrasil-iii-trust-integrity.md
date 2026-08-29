---
title: "Yggdrasil III: Structural Provenance Is Not Trust"
author: "Gaia Research"
date: "2026-08-29"
summary: "Yggdrasil III keeps suite structure visible while preventing shared repository evidence from being counted repeatedly as independent proof. Trust Magnitude changed; stars did not."
abstract: |
  Yggdrasil III makes Trust Magnitude fairer across suites and unique skills. Fusion-recipe rows still describe how a suite is assembled, but contribute 0 Trust Magnitude. Shared suite-repository evidence remains a useful baseline, capped at 50 Trust Magnitude per component, while component-specific evidence remains eligible. An S grade also needs positive evidence from an eligible benchmark result, verifier attestation, or peer review at the skill's own layer. These rules correct evidence accounting; they do not change stored stars or claim that a skill became less capable.
label: "Meta Shift"
---

## Abstract

Trust Magnitude (TM) summarizes the positive evidence supporting a named skill. It is **not a capability score**, a performance ranking, or a verdict on usefulness. Yggdrasil III corrects how TM treats suites so that a suite's structure and shared repository standing cannot look like many independent confirmations.

The intent is balance, not punishment. Suites keep their composition, provenance, and eligible evidence. Unique skills and suite components are simply compared without repeatedly turning one shared signal into fresh corroboration. The rules changed TM calculations and public projections; they did not change stars.

## What was corrected

Previously, a `fusion-recipe` row could add a large number to TM. That row describes which skills make up a Fusion; it does not independently test or validate them. Yggdrasil III therefore keeps the row for provenance, graph traversal, and rank rules, but fixes its TM contribution at `0` and excludes it from scoring Evidence Type diversity.

| Question | Before | Yggdrasil III |
|---|---|---|
| What does a fusion recipe show? | Structure and a numeric TM contribution | Structure only |
| Does it add a scoring Evidence Type? | It could | No |
| Does the suite disappear from the graph? | No | No |

<img src="2026-08-29-yggdrasil-iii-before-after-tm-evidence-flow.svg" alt="Before and after evidence flow. Before Yggdrasil III, shared repository evidence and fusion structure could both increase component Trust Magnitude. After the change, shared suite evidence is capped at 50 TM per component, fusion structure contributes zero TM, and unique evidence remains eligible." role="img" style="display:block;width:100%;height:auto;margin:1.5rem auto 0.5rem;" loading="lazy">

*Figure 1. Structure remains visible, but only eligible evidence contributes to Trust Magnitude.*

## The suite-versus-unique balance, in plain language

Imagine a suite repository containing several components. When a component has `repo-own` or `github-stars-own` evidence pointing to that shared repository, the evidence can contribute a baseline. But the repository does not become new, independent proof each time the same source supports another component.

Yggdrasil III applies three simple rules:

- Shared `repo-own` and `github-stars-own` evidence from the suite repository is capped at a combined **50 TM per component**.
- `fusion-recipe` structure contributes **0 TM**. It still records how the suite is assembled.
- Evidence specific to a component—including evidence from its own or another repository—remains eligible under the normal rules.

This bounds repeated shared or structural evidence while preserving component-specific evidence. Unique skills receive no bonus, and suites receive no blanket penalty: eligible evidence follows the same scoring rules, with only a suite component's repeated shared-repository baseline capped.

<img src="2026-08-29-yggdrasil-iii-suite-unique-balance.svg" alt="Suite and unique-skill balance diagram. One suite repository provides each component with at most a 50 TM shared baseline. Component-specific evidence can add normally. Fusion-recipe links remain visible as structure but add zero TM. A unique skill is scored from its own eligible evidence." role="img" style="display:block;width:100%;height:auto;margin:1.5rem auto 0.5rem;" loading="lazy">

*Figure 2. Shared suite standing is a bounded baseline; specific evidence does the differentiating work.*

## The S-grade safeguard

An S grade now requires all three of the following:

1. TM of at least `250`.
2. At least three distinct Evidence Types with positive scores.
3. At least one positive, eligible `benchmark-result`, `verifier-attestation`, or `peer-review` row recorded at the skill's own evidence layer.

Rejected benchmark rows, deranked verifier rows, zero-scoring rows, phantom rows, and inherited witnesses cannot satisfy the third requirement. Repository evidence may still contribute where its formula allows, but it cannot replace the eligible own-layer witness.

The safeguard asks whether strong TM has at least one direct observation of the skill. It does not say that a skill without such a witness is bad, broken, or incapable.

## What changed in the public projection

On the reviewed 264-skill snapshot, the corrected calculation produced `0` S, `58` A, `82` B, `106` C, and `18` ungraded named skills. The graph, API, contributor pages, and named-skill pages were regenerated from that calculation.

Those grade movements describe the available corroborating evidence under the new rules. They do not describe a loss of capability. The Yggdrasil III implementation did not edit evidence rows or stored stars.

## Follow-up: the resolver correction

Review then found a narrower resolver bug. The shared skill-map loader removed every frontmatter `role` field because it confused the RFC marker `role: variant` with an unrelated display-only role. As a result, variant components could be treated as graded origins during fusion-recipe origin resolution.

PR #1647 fixed the shared resolver and added regression coverage. After that fix, merged PR #1649 recalibrated the one affected stored TM projection, `ruvnet/ruflo-v3`:

| Check | Result |
|---|---|
| Trust Magnitude | `216.00 → 186.00` (`−30.00`) |
| Overall Trust Grade | `A → A` |
| Eight genuine `role: variant` entries | Individual dry-runs were no-ops |
| Evidence rows, rank, and stars | Unchanged |

This follow-up synchronized the named-skill record and its generated API, search, and index projections. It was not new evidence, a demotion, or a star change.

## What remains unchanged

Yggdrasil III does not remove suites, erase their provenance, or discount component-specific evidence. It does not change the Star Bar, suite membership, origin attribution, evidence records, rank, or stars. It changes how TM distinguishes structural/shared context from corroborating evidence.

The result preserves two ideas at once:

- Building and organizing a meaningful suite is valuable work.
- Reusing one suite-wide signal is not the same as collecting independent evidence for every component.

## References

[1] Gaia Skill Tree. [META.md: Evidence methodology and active Trust Magnitude contract](https://github.com/gaia-research/gaia-skill-tree/blob/6b64a07eecce4377f5b9e13bd30976a52963419e/META.md).

[2] Gaia Skill Tree. [Trust Magnitude methodology](https://github.com/gaia-research/gaia-skill-tree/blob/6b64a07eecce4377f5b9e13bd30976a52963419e/docs/codex/trust-methodology.html).

[3] Gaia Skill Tree. [Canonical evidence and Trust Grade schema](https://github.com/gaia-research/gaia-skill-tree/blob/6b64a07eecce4377f5b9e13bd30976a52963419e/registry/schema/meta.json).

[4] Gaia Skill Tree. [Trust Magnitude computation, including fusion scoring and the suite repository cap](https://github.com/gaia-research/gaia-skill-tree/blob/6b64a07eecce4377f5b9e13bd30976a52963419e/src/gaia_cli/trustMagnitude.py).

[5] Gaia Skill Tree. [Canonical generic and named skill-map resolver](https://github.com/gaia-research/gaia-skill-tree/blob/ff9ba51cb0ea953f8ce61fd88f61353d8d38c3e3/src/gaia_cli/registryMaps.py).

[6] Gaia Skill Tree. [Canonical `ruvnet/ruflo-v3` record after the resolver recalibration](https://github.com/gaia-research/gaia-skill-tree/blob/ae4d0a531671ca25a407f405e3b9da99f7cea3bf/registry/named/ruvnet/ruflo-v3.md).

[7] Gaia Skill Tree. [Yggdrasil II source report: Two Types, One Trust Gate, and a Branch Axis That Is Never Declared](https://github.com/gaia-research/gaia-skill-tree/blob/6b64a07eecce4377f5b9e13bd30976a52963419e/docs/meta/2026-07-yggdrasil-ii-meta-shift.md). 2026-07-26.
