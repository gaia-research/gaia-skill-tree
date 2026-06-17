---
title: "The GAIA Trust Methodology: Evidence Types, Grades, and Inherited Standing"
author: "Marco Tiongson, Maintainer"
summary: How GAIA replaced single-letter evidence classes and numeric scores with a two-axis evidence model, a computed Overall Trust Grade, and parent-to-child evidence inheritance.
abstract: |
  GAIA's trust model (issue #646) retires the single Evidence Class letter and the idea of a user-facing numeric trust score. In their place: an Evidence Type axis for provenance, an Evidence Grade axis for quality, a computed Overall Trust Grade per skill, and an inheritance model in which a starless capability reference holds shared evidence that every named implementation inherits and then extends. This report documents the model end to end and records its rollout across the #659, #686, and #690 changes.
label: Trust Model
---

## Abstract

GAIA describes how trustworthy an agent skill is using two things people can actually reason about: the **stars** a skill has earned, and the **Evidence Grades** of the demonstrations behind it. This report sets out the full methodology — why a single Evidence Class letter and a 0–100 "trust score" were rejected, how provenance (Evidence Type) and quality (Evidence Grade) were split into orthogonal axes, how a skill's **Overall Trust Grade** accumulates from its evidence, and how a starless capability reference passes shared evidence down to each named implementation that builds on it. It closes with the rollout status and the open recalibration question.

## The Case Against a Single Number

A registry that ranks skills invites a tempting shortcut: reduce every skill to one 0–100 number and sort. GAIA deliberately does not do this. A single score conflates unrelated questions — *where did the evidence come from?*, *how strong is it?*, and *how much of it is there?* — into a figure that looks precise and is not. It also rewards score-chasing over genuine demonstration.

The model instead keeps the human-legible signal — a skill's **stars**, on the 0★–6★ maturity axis — as the headline, and grounds it in graded evidence. The internal **trust number** still exists, but only as the input a grade is derived from; it is never shown in copy. Surfaces display the **grade** the number yields, not the raw number.

## Two Standing Axes: Tier and Stars

Every skill sits on two orthogonal axes that predate the trust model and remain unchanged:

- **Tier** — the taxonomy of what a skill *is*: Basic, Extra, Unique, or Ultimate.
- **Stars** — verified maturity from 0★ to 6★, derived from evidence and never declared. Each star value has a **rank name** used only when paired (for example, "the Hardened rank"); the bare word is never used for the axis itself.

The trust model does not touch these axes. It governs the *evidence* that justifies a skill's stars, and the aggregate standing that evidence implies.

## Splitting Evidence: Type and Grade

The legacy schema carried a single **Evidence Class** letter (C, B, A) that quietly encoded two different things at once — roughly, provenance *and* quality. The #646 model splits that one letter into two independent axes. Evidence Class remains valid in the schema until the next major release, then is removed; new evidence carries a Type and a Grade instead. A standing warning applies throughout: **Class A/B are not Grade A/B** — the axes share letters but mean different things.

### Evidence Type — provenance

An **Evidence Type** records *where* a demonstration comes from, not how good it is. Values are kebab-case and list-driven from `meta.json` `evidence.types`, so new provenance kinds extend the list without a schema change. The initial set:

| Evidence Type | Provenance |
|---|---|
| `arxiv` | A paper or preprint |
| `repo` | A source repository or `SKILL.md` implementation |
| `github-stars` | Popularity signal from a repository's stars |

### Evidence Grade — quality

An **Evidence Grade** records *how strong* a single demonstration is, on an S / A / B / C axis presented as Platinum, Gold, Silver, and Bronze. The grade is derived from that demonstration's **trust number** against the thresholds in `meta.json` `evidence.gradeThresholds`:

| Grade | Label | Trust number |
|---|---|---|
| S | Platinum | ≥ 90 |
| A | Gold | ≥ 80 |
| B | Silver | ≥ 60 |
| C | Bronze | ≥ 40 |
| — | ungraded | < 40 |

A demonstration below the C threshold is **ungraded**: it stays on the record but counts toward no gate. Grading is mechanical; a repository link alone does not earn a high grade, which is why a separate editorial step (below) exists to award S where genuine demonstrations justify it.

## The Overall Trust Grade

A skill's **Overall Trust Grade** is its aggregate standing — the accumulation of its individual Evidence Grades that establishes the capability "beyond reasonable doubt." It is computed from the evidence inventory at build time and **never stored in a node**; it materialises only in the generated catalogs (`named-skills.json`, `docs/graph/gaia.json`). It is distinct from any single demonstration's Evidence Grade.

The current implementation takes the strongest grade in the evidence pool. Whether aggregate standing should instead require corroboration — several independent demonstrations rather than one strong one — is the open question reserved for the post-rollout recalibration review.

## Inheritance: the Starless Layer

Skills are organised under **starless** references — rank-less taxonomy nodes that carry no stars of their own and render as *generic* in italic, greyed styling. A starless reference holds the shared, capability-level evidence pool — the academic and general-purpose demonstrations of a capability. Its **named** implementations (its children) each inherit that pool and then add their own implementation-specific evidence, typically a repository demonstration. That implementation-specific layer is the *differentiator* between two named skills that share a parent.

The trust model honours this structure directly. A named skill's **effective evidence** is its own evidence unioned with the evidence inherited from its starless parent, and its Overall Trust Grade is computed from that combined pool. A child therefore inherits its parent's capability floor and can exceed it on the strength of its own demonstration — but never reports a weaker standing than the capability it implements.

This layering was the step that turned the model from correct-on-paper into correct-in-practice. Grading only the parent layer left every suite reading "0/3 components carry graded evidence," because component standing was being looked up by the wrong identity. Resolving each component to its *named* effective evidence fixed the gates to report real, actionable reasons.

## Suite Ultimates: the Pillar Gate

An **Ultimate**-tier skill that fuses a suite of components is held to a pillar rule, expressed in `meta.json` `evidence.ultimateGate`: at least **three** components carrying graded evidence, of which at least **one** is graded S and at least **two** are graded A or better, with **no** component below the C floor. The gate scores each component by its child effective grade, not the shared parent grade, so a suite's standing reflects the real strength of its implementations.

By design, mechanical backfill alone does not let any suite pass: clearing the gate requires at least one component graded S, and awarding S is an editorial judgement reserved for a 4★+ Verifier reviewing a genuine demonstration. A gate that has not yet been cleared now reports an accurate gap (for example, "needs one component graded S") rather than a lookup artifact.

## Tenure and Verification

Two further signals sit alongside grading, each orthogonal to it.

**Tenure** measures how long a skill has held its current stars, derived from its timeline `rank_up` and `demote` events and rendered as "held the *[rank name]* rank since *[date]*." It is computed, never stored, and is display-only — it never inflates or regresses standing.

**Verification** is the state of a single evidence entry: unverified by default, **verified** once confirmed by a 4★+ Verifier, or **disputed**. Verification attests that a demonstration is *real*; grading measures how *strong* it is. The two never substitute for each other — a verified Bronze is still Bronze, and an unverified Platinum still counts toward gates while inviting scrutiny.

## Auditability and the Programmatic-First Discipline

Every change to graded evidence flows through the CLI (`gaia dev evidence`), never a hand-edit, and each grading writes an `evidence_graded` event to the skill's timeline. The schema's timeline action enum admits that event, so the registry's own validator (`gaia validate`) treats a graded history as well-formed. The result is that a skill's present standing is always explained by an auditable trail of events, and the build pipeline — not a human typing into a node — is the only thing that ever computes an Overall Trust Grade or a gate status.

## Rollout Status

The methodology shipped in three reviewed stages, all on `main`:

- **Schema (#659)** — the `evidenceEntry` gains `type`, `grade`, and `trustNumber`; `meta.json` gains the grade thresholds and the pillar `ultimateGate`; Evidence Class is marked deprecated.
- **Grading pipeline (#686)** — `gaia dev evidence` derives a grade from a trust number, grade colours join the shared design tokens, and the Overall Trust Grade aggregation lands in the build step.
- **Backfill and inheritance (#690)** — the in-place re-grade path and the `evidence_graded` enum; the backfill of 220 starless and 173 named evidence entries; and the inheritance layer that gives named skills an effective grade and fixes the suite gates. After this stage, 182 of 183 named skills carry an Overall Trust Grade and all six suite ultimates report real component standing.

What remains: the actionable per-skill reports that surface this model to readers, and a recalibration review — opened roughly a month after the gate has lived against real grade distributions — to revisit both the pillar thresholds and whether the Overall Trust Grade should demand corroboration rather than a single strongest demonstration.

## References

[1] GAIA Registry. (2026). *Trust Model RFC v2* (issue #646). Internal handover, `handovers/TRUST_MODEL_RFC.md`.
[2] GAIA Registry. (2026). *Evidence Type + Grade + trustNumber schema split* (PR #659).
[3] GAIA Registry. (2026). *Grading pipeline* (PR #686).
[4] GAIA Registry. (2026). *Grade layering & inheritance for named skills and suite ultimates* (PR #690, issue #689).
[5] GAIA Registry. *CONTEXT.md* — vocabulary source of truth for tier, stars, Evidence Type, Evidence Grade, Overall Trust Grade, tenure, verification, and the starless layer.
