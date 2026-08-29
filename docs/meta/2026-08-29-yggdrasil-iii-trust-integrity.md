---
title: "Yggdrasil III: Structural Provenance Is Not Trust"
author: "Gaia Research"
date: "2026-08-29"
summary: "Yggdrasil III separates structural fusion provenance from Trust Magnitude, requires an eligible independent witness for an S grade, and bounds shared suite-repository evidence."
abstract: |
  Yggdrasil III closes three ways a large suite could look more corroborated than its evidence supports. Fusion-recipe rows remain structural provenance at 0 Trust Magnitude; an S grade needs three positive scoring Evidence Types plus one eligible benchmark result, verifier attestation, or peer review from the skill's own layer; and a suite component may draw no more than 50 Trust Magnitude from shared repository evidence. The rule changes the computation and its public projections, not any named skill's stored stars.
label: "Meta Shift"
---

## Abstract

Yggdrasil III makes a narrow correction to the Trust Magnitude computation. A Fusion can explain how a capability is assembled. It cannot, on its own, establish the corroboration that Trust Magnitude is meant to measure. The same principle applies when many components inherit the same repository signal: shared context is useful baseline evidence, but it is not independent support for every component.

This report accompanies the Yggdrasil III integration review. It states the implemented contract, the resulting public projections, and the boundaries that remain unchanged.

## The correction

The prior formula allowed a large `fusion-recipe` row to contribute substantial Trust Magnitude. That made structure behave like corroboration. Yggdrasil III retains fusion-recipe rows for provenance, graph inspection, and structural predicates, but makes their scoring contribution exactly `0`.

| Question | Before | Yggdrasil III |
|---|---|---|
| What did a Fusion demonstrate? | Structure and a large numeric contribution | Structural provenance only |
| Can fusion count toward scoring Evidence Type diversity? | It could appear in the count | No — only positive scoring Evidence Types count |
| Can fusion certify an S grade? | It could inflate the total near the S floor | No |

The raw origin structure remains inspectable. The change does not erase a suite's composition; it stops composition from being mistaken for independent evidence.

## The S-grade gate

An S grade now requires all of the following:

1. Trust Magnitude of at least `250`.
2. At least three distinct, positive scoring Evidence Types.
3. One positive eligible witness from `benchmark-result`, `verifier-attestation`, or `peer-review`, recorded at the skill's own evidence layer.

Rejected benchmark rows, deranked verifier rows, zero-scoring rows, phantom rows, and inherited witnesses do not satisfy the third condition. Repository ownership, repository stars, and fusion structure can still support the total where their formulas allow; none can substitute for the independent witness.

This is deliberately a narrower test than a generic distinction between self-produced and external evidence. The gate names the evidence that can answer the question it is protecting: has this skill received a positive, eligible, independent observation?

## Shared suite evidence has a boundary

A component with a `suiteRef` may inherit `repo-own` and `github-stars-own` evidence associated with the suite root. Yggdrasil III caps the combined contribution from that shared repository baseline at `50` Trust Magnitude for each component.

The cap is selective. Component-specific repository evidence remains fully eligible under the ordinary formula, as does evidence from a different repository. The result is a bounded shared baseline rather than a multiplier that lets one repository's standing repeat without limit across an entire suite.

## What the projection shows

The build recomputes Trust Magnitude from each skill's evidence inventory. No named-skill source data, Evidence Grades, or stored stars are edited by this change. The generated projections change because they now apply the corrected contract.

On the reviewed registry snapshot, the generated distribution is `0` S, `58` A, `82` B, `106` C, and `18` ungraded across `264` named skills. This is not a declaration that the affected skills lost their capabilities. It is the expected effect of removing structural contribution from a measure of corroboration and requiring a positive, eligible witness for S.

The public graph, API projection, contributor pages, and named-skill pages are regenerated together so that every served surface reads the same calculation.

## What remains unchanged

Yggdrasil III does not change the existing star gates, suite structure, origin attribution, or the underlying evidence records. It does not turn every evaluation into a benchmark, and it does not treat an absent witness as a negative finding. A skill can remain useful while its Trust Magnitude lacks the corroboration needed for an S grade.

The correction therefore preserves two distinct statements:

- A Fusion can be meaningful structural work.
- An S-grade Trust Magnitude requires independent positive evidence in addition to structure.

## References

[1] Gaia Skill Tree. *Yggdrasil III trust integrity rules*. Pull request #1629. https://github.com/gaia-research/gaia-skill-tree/pull/1629

[2] Gaia Skill Tree. *Trust Magnitude methodology*. `docs/codex/trust-methodology.html`.

[3] Gaia Skill Tree. *Evidence Type contract and Trust Magnitude thresholds*. `registry/schema/meta.json`.

[4] Gaia Skill Tree. *Yggdrasil II: Two Types, One Trust Gate, and a Branch Axis That Is Never Declared*. 2026-07-26. https://gaiaskilltree.com/meta/reports/2026-07-26-yggdrasil-ii-two-types-one-trust-gate-and-a-branch-axis-that-is-never-declared.html
