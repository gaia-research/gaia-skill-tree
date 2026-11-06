---
title: "Yggdrasil IV: A Challenge Must Be Earned, and Standing Can Recover"
author: "Gaia Research"
date: "2026-10-31"
summary: "Yggdrasil IV makes trust challenge-driven and reversible. Four real challenges ran in October and none was admitted. Explore every rating that moved, every skill that changed, and the audit behind it."
abstract: |
  Until October, a skill's rating in the Gaia Skill Tree could be earned but not seriously questioned. Yggdrasil IV changes that, in both directions. A skill's standing can now be challenged, but only by a challenge that has been tested, independently re-checked and admitted. And anything that goes down can come back. Time, a broken link or a newer competitor is a reason to look, never a penalty. This report shows what happened in October instead of describing it: four real challenges and why none was admitted, the new rules at work on real skills, every rating that moved, the audit of all 701 records, and a searchable changelog of every change made to every skill during the closeout. Results run through the October 31 cutoff, the final November 2 ledger and one November 3 correction to frozen skills.
label: "Meta Report"
---

## Abstract

Yggdrasil IV is challenge-driven, reversible trust governance. It changes who may question a skill's standing and how a skill recovers. It changes no Trust Magnitude weight, cap, threshold or grade boundary.

## October at a glance

Yggdrasil IV was ratified on October 25. Its premise is that Gaia is a long-lived trust registry, not a fast-moving leaderboard. Time invites scrutiny. Counterevidence justifies a drop. Only an approved decision moves a rating.

{{fig: hero}}

In practice that means four things:

- **Signals are not penalties.** An old benchmark, a built-in feature that overlaps a skill or an unreachable link can open an investigation. None of them lowers a score by itself.
- **A drop needs counterevidence.** It takes independently verifiable proof that is relevant to the skill's actual claim.
- **Recovery works the same way in reverse.** A fix, a new release or a new independent benchmark can win a rating back, with no bonus for coming back.
- **History is kept.** Challenges, outcomes and recoveries stay linked on the public record.

## How a challenge works, shown on four real cases

A challenge is a claim that something else does the same job as a ranked skill, as well or better. Every challenge goes through the same five steps. A case that fails a step stops there. Pick a case to see where it stopped.

{{fig: lab}}

Four real cases ran in October. Three ran a full test and one was turned away before any test. None was admitted, and the founder accepted that result. This is the system working as designed: unfair or weak comparisons never touched anyone's rating, and each one is on the public record with a plain note that it has no effect on standing. Admitted challenges and these held reviews are on the [Trust Challenges page](../../trust/challenges/).

A contributor whose skill faces an admitted challenge has 14 days to respond with a rebuttal, an equivalent test or an upstream improvement. An unanswered challenge never causes an automatic demotion. Automated challenge watching stays off this month, so every October case was opened and run deliberately.

## The new calculations, on real skills

### A ceiling on stars

A skill's displayed stars cannot go higher than its Trust Grade supports. The named-skill pages and the API already worked this way. The trust ledger and leaderboard did not, so one skill could show two different ratings. All surfaces now agree. The one exception is a frozen skill: it keeps the stars it was frozen at, and the ceiling never lowers it. Try it:

{{fig: clamp}}

### A score is the sum of its evidence

Every Trust score is built from evidence, one slice per type. Evidence is counted once per type per source, so repeating the same link does not inflate a score. Two corrections this month show how the slices move the total:

{{fig: evidence}}

### Origin goes to merit, automatically

Origin marks the highest-merit implementation in a skill family. It is no longer awarded by hand. The founder's rulings:

- Origin is computed from merit. Manual Origin decisions end.
- A frozen skill competes with its locked score and grade, and it can beat a live one.
- Ties share Origin. Twenty-eight families currently do.
- Origin has no star requirement. A 1★ skill can hold it, and is simply not yet named.

Four skills received Origin as clear merit winners this month: `vercel-labs/vercel-react-best-practices`, `addy-osmani/code-simplification`, `ayghri/i-have-adhd` and `dietrichgebert/ponytail`. Explore all families:

{{fig: origin}}

One rule was corrected along the way. A 5★ Unique skill had been required to hold Origin on its skill family's prerequisites. That requirement was borrowed from the Suite rule and never ratified for Uniques. `safishamsi/graphify` was proposed for a drop on that basis and stays at 5★ (score 318.14, grade S). A Unique needs Origin in its own family and grade S.

### Thirty-seven skills, one cap

Thirty-seven skills had been added with no evidence of their own. They received verified evidence from their host repositories and were linked to their parent suites: `addy-osmani/agent-skills`, `garrytan/gbrain` and `obra/superpowers`. Shared host evidence is capped at 50 per component. Thirty-six sit at exactly 50 (grade B). `obra/test-driven-development` sits at 59 because it also inherits peer-review evidence from its generic skill.

The first independent audit of this batch returned **FAIL**: the 37 skills had picked up shared evidence without being linked to their suites, so they escaped the cap. The batch was corrected and a fresh independent audit returned **PASS**. The changelog below shows the escape and the correction on the same skills: a first score near 177, then 50.

## Every rating that moved

{{fig: movers}}

### The ratings that went down, and why

Nothing went down because of age, a dead link or a challenge. Each row below has a recorded reason:

| Skill | What changed | Why |
|---|---|---|
| `mattpocock/skills` | Score 374.99 → 280.39. Still S and 5★. | A paper's citation count had been logged as 500. The live count is 2. |
| `google-deepmind/workflow-skill-creator` | Score 100.82 → 59.65 (A → B). Stored 4★, displayed 3★. | Its strongest evidence was a bare repository filed as peer review. It was retyped honestly. The stored 4★ stays as recorded review debt. |
| Five October additions | Stored 2★, displayed 1★. | Ungraded, so the same ceiling applies: `kishorkukreja/inventory-optimization`, `cis2042/product-design-harness`, `jpoutrin/create-plugin`, `majiayu000/edge-model-compression`, `yylo-dev/plan-ledger-tasks-yylo`. |

Three frozen skills are not in this table because the ceiling does not apply to them. See “Frozen, not deleted” below.

### Going up

`latent-spaces/brag` rose from 3★ to 4★: score 144.54 (A), a live pinned link, and sole Origin of its family. `panniantong/agent-reach` and `browser-use/browser-harness` rose a grade (shown above). Two skills curated earlier in the month, `nvidia/accelerated-computing-cudf` and `wheresryan22/anatomy`, arrived at 4★.

## The shape of the tree now

{{fig: growth}}

{{fig: added}}

### Frozen, not deleted

Fourteen skills were removed from their source repositories, so they are frozen: no longer installable, links kept. They are twelve `heygen-com/hyperframes` components, `heygen-com/general-video` and `leonxlnx/output-skill`. A frozen skill keeps its record, its stars and its place in the Origin race, and the grade ceiling never lowers it. Three frozen skills show this: `heygen-com/general-video` keeps 2★ with no score, `mattpocock/personal` (frozen in August) keeps 3★, and `leonxlnx/output-skill` keeps 3★. `output-skill` had also lost an evidence row at its freeze, which dropped its score from 50 to 36 (B to C). The row was restored on November 3 and its score is back at 50 (B). The restored row's page no longer exists upstream. It stays because a frozen record keeps its evidence, and a frozen score is a lock, not a live re-check. A test now covers every frozen skill (23 today). It fails if one is un-frozen, is recalibrated or has its evidence changed after its freeze, or is shown with fewer stars than it holds. Where a skill moved instead of being removed, its links were repointed: nine `leonxlnx` skills moved to new repositories and `redesign-skill` was folded into another skill.

## The October audit

Every record was read against the current rules. The audit changed nothing in the registry by itself.

{{fig: audit}}

Alongside the audit, 313 pull requests, branches, intake issues, upstream releases and evidence records were each traced to an outcome. 111 were verified as already in place, 53 were equivalent to something in place, 99 are waiting for curation, 9 are held for governance, 13 were duplicates, 27 did not apply and 1 needs action. None was rejected. The upstream sync brought 15 named skills to their current releases and closed 38 stale intake issues. Ninety new intake items were triaged: 59 ready for curator review, 17 needing more information, 7 duplicates, 6 already covered by the sync and 1 rejected.

## Every change to every skill

This is the complete record of what happened to named skills during the closeout: scores recalculated, evidence added and removed, suites linked, upstream syncs, freezes and star changes.

{{fig: changelog}}

## Deferred to November

- **Intake for verified upstream contributors** ([#2261](https://github.com/gaia-research/gaia-skill-tree/issues/2261)).
- **Three evidence corrections** ([#2262](https://github.com/gaia-research/gaia-skill-tree/issues/2262)): a vendor claim filed as a benchmark on `ruvnet/ruflo`, 21 rows with no type or grade, and one mismatched paper on `knowledge-graph-build`.
- **An audit of the suite cap** ([#2263](https://github.com/gaia-research/gaia-skill-tree/issues/2263)). The 50 cap stays in place while it is audited.
- **One link under watch.** A supporting page for `mattpocock/skills` returned "not found" on every timed re-check. It stays on record as review debt, with no automatic drop.

## What did not change

Yggdrasil IV changed no Trust Magnitude weight, cap, threshold, grade boundary or Fusion Score rule. Counting evidence once per type corrects how an existing rule was applied. It is not a new rule. No October challenge changed anyone's standing. Every star, grade and Origin change in this report came from an approved decision.

The registry holds **784 records**: 311 generic skills (156 basic, 155 fusion) and 473 named skills (426 named and 47 awakened).

## How this report was checked

Every figure above was recomputed from the registry files and the closeout record. The comparison point is October 25, the day of ratification. Where an earlier draft disagreed with the data, the data won:

| Claim | Checked against | Result |
|---|---|---|
| Named skills added | Registry before and after | 75, not 73. 73 came from the curator review and 2 were curated earlier in the month. |
| New generic skills | Registry before and after | 12 new plus 1 rename, not 10. Two came with the earlier curations. |
| Origin families | Origin standings | 223 hold a named skill. 14 more hold only awakened skills. 237 in all. |
| Frozen skills keep their score and stars | Skill histories and ledger | Not at first. `output-skill` had lost an evidence row (score 50 → 36), and `general-video` and `personal` displayed fewer stars. Corrected on November 3: all 23 frozen skills now show their stored stars, and `output-skill` is back at 50. |
| Skills below their stored stars | Trust ledger | 6, down from 9. The three frozen skills are exempt from the ceiling. |
| Audit and reconciliation counts | Sweep, adjudication and reconciliation records | All match. |

{{include: 2026-10-YGGDRASIL-IV/data.frag}}
{{include: 2026-10-YGGDRASIL-IV/figures.frag}}

## References

[1] Gaia Skill Tree. [Yggdrasil IV founder ratification: trust degradation, challenge and recovery](https://github.com/gaia-research/gaia-skill-tree/blob/main/founder/YGGDRASIL%5FIV%5FRATIFICATION%5F2026-10-25.md). 2026-10-25.

[2] Gaia Skill Tree. [RFC #2148: trust degradation, deterministic downward recalculation and governance](https://github.com/gaia-research/gaia-skill-tree/issues/2148).

[3] Gaia Skill Tree. [EPIC #2189: Yggdrasil IV launch readiness](https://github.com/gaia-research/gaia-skill-tree/issues/2189).

[4] Gaia Skill Tree. [Challenge case records C1 to C4, with independent verification](https://github.com/gaia-research/gaia-skill-tree/tree/main/evidence/frontier-challenges).

[5] Gaia Skill Tree. [Trust Challenges page](../../trust/challenges/).

[6] Gaia Skill Tree. [META.md: evidence methodology and merit-based Origin](https://github.com/gaia-research/gaia-skill-tree/blob/main/META.md).

[7] Gaia Skill Tree. [GOVERNANCE.md: approval, challenges and appeals](https://github.com/gaia-research/gaia-skill-tree/blob/main/GOVERNANCE.md).

[8] Gaia Research. [Yggdrasil III: Structural Provenance Is Not Trust](2026-08-29-yggdrasil-iii-structural-provenance-is-not-trust.html). 2026-08-29.
