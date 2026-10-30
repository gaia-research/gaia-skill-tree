---
title: "Yggdrasil IV: A Challenge Must Be Earned, and Standing Can Recover"
author: "Gaia Research"
date: "2026-10-31"
summary: "Yggdrasil IV makes trust challenge-driven and reversible. In October four real challenger cases went through the new pipeline and none was admitted. This report also covers the 701-record Meta re-audit and the calibrations the founder approved. Results run through 2026-10-31T23:59:59Z."
abstract: |
  Yggdrasil IV changes how trust in the Gaia Skill Tree can go down and come back up. A skill's standing can now be questioned only through a challenge that has been discovered, evaluated, independently verified and admitted through a trusted receipt issuer with founder approval. Elapsed time, a dead link, or the mere existence of a newer competitor is a reason to look, never a penalty. In October we ran four real challenger cases through that pipeline. None was admitted: one ended in a tie, two were inconclusive and one was rejected at triage. We report those negatives as the mechanism working as designed. This report also summarizes the October Meta re-audit of all 701 registry records, the upstream and intake reconciliation, and the adjudication and calibration decisions the founder approved, and it lists what is deferred to November. Results run through 2026-10-31T23:59:59Z, and figures from before the cutoff refresh are provisional.
label: "Meta Report"
---

## Abstract

Yggdrasil IV is challenge-driven, reversible trust governance. Yggdrasil III settled how Trust Magnitude (TM) is computed. Yggdrasil IV settles who may question a skill's standing, what counts as proof, and how a skill recovers. It changes no TM weight, cap, threshold or grade boundary.

## Cutoff and provisional figures

**Results through 2026-10-31T23:59:59Z; figures before the cutoff refresh are provisional.**

The October snapshot was taken at registry revision `43797a441` and labelled provisional-2026-10-28. After the cutoff, the same pipeline reruns the upstream sync, the deterministic pre-pass and the liveness re-probe, and the snapshot is relabelled final. The frozen provisional snapshot is not rewritten. [[VERIFY: cutoff refresh ran and the snapshot was relabelled final / founder/reports/yggdrasil-iv-october-2026/HANDOVER.md step 9 on dev/yggdrasil-iv-launch / git log origin/dev/yggdrasil-iv-launch --oneline -5]]

## What Yggdrasil IV is

The founder ratified Yggdrasil IV on 2026-10-25. Its premise is that Gaia is a long-lived trust registry, not a fast-moving leaderboard. Time invites scrutiny, counterevidence justifies degradation, and only adjudication authorizes a canonical change.

In practice that means four things:

- **Signals are not penalties.** Elapsed time, a stale benchmark, a new built-in agent capability or a temporarily unreachable URL can open a bounded investigation. None of them lowers a published TM or star rating on its own.
- **Degradation needs counterevidence.** A confirmed degradation requires independently verifiable, materially relevant evidence, for example a newer capability that demonstrably does the same specified task better under comparable conditions. A competitor's existence or a description claim is not proof.
- **Recovery is symmetric.** A later release, a fixed implementation or a new independent benchmark can defeat even a formerly correct challenge. Any score that comes back does so only through the same deterministic recomputation of eligible evidence. There is no comeback bonus.
- **History is kept.** Challenges, consequences, remediation and recovery stay linked on the public record. No valid historical achievement is silently erased.

## How a challenge works

The challenger mechanic is the October highlight. Every step leaves a committed record, and a step can stop the case.

- **Frontier discovers.** A lead names a challenger (a tool, a built-in platform feature or another skill), the specific claim it challenges, the named skill it is compared against, and the exact versions involved. Each lead is matched against the registry and checked for duplicates.
- **Meta evaluates.** Meta triages the lead. If it is worth testing, a protocol with a written decision rule is committed before anything runs, so the result cannot be fitted afterwards. The experiment then runs and produces a receipt bound to that protocol.
- **An independent verification is recorded.** A separate session re-executes or re-checks the case and writes a Meta verification record that upholds, downgrades or rejects the runner's outcome. Independence is declared, not cryptographically authenticated, and every record says so.
- **Admission goes only through the trusted receipt issuer.** A case can become an admitted challenge only through the authenticated challenge-receipt issuer, and the founder approves each admission individually. Approving the issuer did not admit anything.
- **Only an admitted challenge can make a skill contested.** Nothing that stops before admission is labelled contested. The prominent Origin-contested marker is reserved for an unresolved admitted challenge that is material to the skill's current Origin.
- **A held review has no effect on standing.** Review records for cases that were not admitted are published for transparency. They change no Trust Magnitude, star, grade, Origin or ranking. Even after admission, numbers change only through an approved decision.

A contributor whose skill faces an admitted challenge has 14 calendar days to respond with a rebuttal, an equivalent reproducible test or an upstream improvement. An unanswered challenge does not cause an automatic demotion.

Automated challenge watching remains switched off this month. Every October case was opened and run deliberately.

## October's challenger cases: four truthful negatives

Four real cases went through the pipeline in October. Three ran a pre-registered experiment, and one was rejected at triage before any experiment. **None was admitted.** The founder accepted the negative result.

| Case | Challenger | Compared against | Runner outcome | Meta verification | Admitted |
|---|---|---|---|---|---|
| C1 | Graphify 0.8.13 | `trailhq/graft` caller lookup | Contradicted (a tie) | Upheld: contradicted as a tie | No |
| C2 | Claude Code `permissions.deny` (2.1.312) | `mattpocock/git-guardrails-claude-code` | Supported, on a narrow fixture | Downgraded to inconclusive | No |
| C3 | `git log -L` (Git 2.56.0 documented, 2.50.1 executed) | `trailhq/graft` | Inconclusive | Inconclusive | No |
| C4 | ripgrep 15.1.0 | `trailhq/graft` caller lookup | Rejected at triage | Rejected at triage | No |

### C1: Graphify against graft

The task was finding the callers of five functions in Gaia's own Python source, scored against a reviewed ground truth of 27 call sites. The targets were picked by a mechanical rule committed in advance. The two tools returned identical caller sets: the same recall on all five targets, and all 22 callers each tool returned were correct. Under the pre-registered rule a tie counts as contradicted. That means Graphify showed no caller-lookup advantage here. It does not mean graft is better. Both tools missed the same five call sites, which points to a shared limit of static analysis. Graphify is already registered as `safishamsi/graphify`, and caller lookup is a narrow slice of what it does, so this case says nothing about its main capability.

### C2: Claude Code's native deny rules against git-guardrails

The question was whether Claude Code's built-in deny rules make an installed git-guardrails hook unnecessary. On 18 commands the native rules blocked 10 of 12 dangerous commands and allowed all 6 safe ones. The hook blocked 8 of 12 and allowed 5 of 6. The runner recorded that as supported. Meta re-ran the case, reproduced it exactly and still downgraded it to inconclusive. The fixture had been frozen after the runner had already seen the hook's results, so the evasions it contained were known hook misses. A wrapper form outside the fixture was blocked by the hook and missed by the native rules. The case is held pending a fixture written without knowledge of either side's outcome.

### C3 and C4

C3 compared `git log -L` with graft on tracing how one function changed over time. The two tools do different jobs, and the Git version that ran differed from the documented one, so the protocol allowed at most an inconclusive result, and that is what it returned. C4 proposed ripgrep, a regular-expression text search, as a challenger to graft's symbol-level caller lookup. ripgrep makes no caller-resolution claim, so the lead was rejected at triage and no experiment ran.

### Why the negatives matter

An October with no admitted challenge is a correct result, not an empty one. The pipeline's job is to keep weak or unfair comparisons from touching anyone's standing, and here it did that four times, publicly and with receipts. All four review records, each with its bundle digest and a plain disclosure that it has no effect on standing, are on the [Trust Challenges page](../../trust/challenges/). The same records are in the raw files `/api/v1/challenges/reviews.json` and `/api/v1/challenges/index.json`. The second file lists admitted challenges, and it is empty this month. [[VERIFY: still no admitted challenge at the cutoff (sourceStatus unavailable, 4 reviews) / docs/graph/challenges/index.json and reviews.json / python3 -c "import json;print(json.load(open('docs/graph/challenges/index.json'))['sourceStatus'], len(json.load(open('docs/graph/challenges/reviews.json'))['reviews']))"]]

## The October Meta re-audit

The October re-audit read every record in the registry against the Yggdrasil III engine and the Yggdrasil IV doctrine. It was read-only: every finding is a proposal, and the sweep changed nothing in the registry.

- **Coverage.** 701 records: 400 named records (48 of them awakened) and 301 generic nodes, plus 874 evidence rows, across 13 survey dimensions.
- **Adversarial verification.** 930 raw findings went to three independent verification lenses. A finding survived only if at least two of the three upheld it. 817 survived: 2 at P0, 90 at P1, 312 at P2, 354 at P3 and 59 at P4.
- **Deterministic counts.** The workflow's own model-written summary reported 810 surviving findings. We replaced it with a deterministic replay of the run journal, which gives 817. The published counts come from the replay.
- **Liveness sweep.** 962 evidence and implementation URLs were probed. The first pass ran into GitHub rate limits, so the whole set was re-probed at low concurrency: 903 alive, 59 dead, none unknown. A dead URL is review debt with bounded probes at t0, +24h and +72h. It is never a demotion. [[VERIFY: liveness re-probe at the cutoff / sweep/liveness-reprobe on dev/yggdrasil-iv-launch / git show origin/dev/yggdrasil-iv-launch:founder/reports/yggdrasil-iv-october-2026/sweep/liveness-reprobe/evidence-health.md]]
- **Upstream and pull-request reconciliation.** 313 items (pull requests, branches, intake issues, upstream releases and evidence records) were each traced to a disposition: 111 verified in the integration branch, 53 already equivalent, 99 waiting for curation, 9 held for governance, 13 duplicates, 27 not applicable, 1 needing action, and none rejected. The October upstream sync brought 15 named skills to their current upstream releases (PR #2197). 38 stale intake issues were closed.
- **Intake triage.** 90 intake items were triaged (PR #2199): 59 ready for curator review, 17 needing more information, 7 duplicates, 6 already covered by the upstream sync, and 1 rejected. No intake was admitted by triage.
- **Curator topology review.** The founder reviewed 76 topology choices as the curator: 53 approved as proposed, 10 routed to new generic skills, 5 remapped to an existing generic, and 8 declined as support material rather than skills. These choices are approved but not yet executed. [[VERIFY: L4 batch executed, with final approved, new-generic, remapped and declined counts (the approve row for the 7 parked drafts counts once in 53) / CAMPAIGN.md L4 table and the L4 review/meta PR / gh pr list --search "L4 batch" --state all]]

## Adjudication and calibration approved in October

The adjudication ledger turned surviving findings into 190 candidate decisions. 65 came with numbers recomputed by Gaia's own engine, and 125 needed a ruling. Every approval below is a founder ruling recorded verbatim in the campaign record. Registry changes went through the CLI, each with a timeline event, and code changes went through reviewed pull requests. [[VERIFY: adjudication ledger regenerated with an approvals input; approved count no longer 0 / adjudication/LEDGER.md on dev/yggdrasil-iv-launch / git show origin/dev/yggdrasil-iv-launch:founder/reports/yggdrasil-iv-october-2026/adjudication/LEDGER.md]]

The first independent Meta audit of this calibration batch returned **FAIL**. Thirty-seven skills had picked up shared host-repository evidence without being linked to their suite, so they escaped the 50 TM per-component suite cap. The batch was corrected, and a fresh independent re-audit must pass before the batch reaches the public site. [[VERIFY: calibration re-audit verdict PASS / verification/CALIBRATION-REVERIFICATION.md on dev/yggdrasil-iv-launch / git show origin/dev/yggdrasil-iv-launch:founder/reports/yggdrasil-iv-october-2026/verification/CALIBRATION-REVERIFICATION.md]]

### Freezes for removed upstream skills

Twelve `heygen-com/hyperframes` components were dropped from the upstream repository at v0.8.209. They are frozen: no longer installable, links kept, star ratings unchanged. `heygen-com/general-video` was frozen for the same reason, and so was `leonxlnx/output-skill`, which was removed upstream. Where a skill had moved or been superseded instead of removed, its links were repointed to its new home instead. That includes nine leonxlnx skills that moved to new repositories and `leonxlnx/redesign-skill`, which was folded into another skill. A frozen skill keeps its Trust Magnitude and grade, and no batch calibration or closeout touches it.

### Origin is automatic and goes to the highest merit

Origin is the mark of the highest-merit named implementation in a generic skill. It is no longer assigned by hand. The founder ruled:

- Origin is computed automatically from merit. Manual Origin adjudication ends.
- A frozen skill competes with its locked Trust Magnitude and grade, and it can beat a live one.
- If two or more implementations tie at the top, they all hold Origin. With TM a real number, that should be rare.
- Origin has no star requirement. A 1★ implementation can hold Origin. It is simply not yet Named.

This replaces the manual "Origin transfer" path described in the Yggdrasil IV ratification. Before automation landed, four skills received Origin as the clear merit winners of their buckets: `vercel-labs/vercel-react-best-practices`, `addy-osmani/code-simplification`, `ayghri/i-have-adhd` and `dietrichgebert/ponytail`. [[VERIFY: Origin automation merged; count of buckets whose Origin changed and count of tied buckets / Origin automation PR on dev/yggiv-origin-automation / gh pr list --head dev/yggiv-origin-automation --state all]]

### Star changes and corrected rules

- **latent-spaces/brag rises from 3★ to 4★.** TM 144.54 (A), a live pinned link, the Unique branch and sole Origin of its bucket. The 4★ Unique gate passes.
- **google-deepmind/workflow-skill-creator is Named** as *Workflow-to-Skill Distiller*. Its strongest evidence row was a bare repository filed as a peer review. It was retyped honestly, and its TM went from 100.82 (A) to 59.65 (B). Its stored 4★ stays as review debt, not a demotion. Under the grade clamp it is displayed at 3★, the B ceiling, until that debt is settled. [[VERIFY: displayed star rating of workflow-skill-creator after the clamp alignment / docs/graph/named/index.json after #2251 and #2259 / gh pr view 2259]]
- **safishamsi/graphify stays at 5★.** An earlier rule had required a 5★ Unique skill to hold Origin on one of its generic skill's prerequisites. That requirement was borrowed from the Suite gate and never ratified for Uniques. A Unique needs to be its bucket's Origin and to clear the TM gate, and graphify does both (TM 318.14, S). The demotion proposed during the audit was reverted. [[VERIFY: Unique 5★ gate corrected in code (no prerequisite-Origin check) / src/gaia-cli promotion module after the Origin automation PR / gh pr list --head dev/yggiv-origin-automation --state all]]
- **panniantong/agent-reach** had its evidence re-derived: TM 53.86 (B) went to 260.83 (A), and it stays at 3★.

### Evidence corrections

- **Evidence is deduplicated within its type.** Two rows of different types at the same URL now both count, and two rows of the same type at the same URL count once (PR #2257).
- **mattpocock/skills:** an arXiv citation count recorded as 500 was corrected to 2. TM moved from 374.99 to 280.39 and stays S, so the 5★ is unchanged. One supporting witness URL returns 404. It is on bounded re-probes, the last due 2026-11-01T16:40Z, after the cutoff. [[VERIFY: +72h witness probe result for mattpocock/skills / registry/named/mattpocock/skills.md timeline / gh pr view 2251]]
- **Thirty-seven skills that had been added with no evidence** received verified host-repository evidence. Twelve addy-osmani skills were relinked to their suite and capped at 50.0 TM (B). Suite linking for the remaining 23 garrytan and 2 obra skills is automatic under the existing cap. [[VERIFY: the 25 garrytan and obra skills carry their suite link and sit at the capped TM (about 50.0 B) / registry/named/garrytan and registry/named/obra after #2251 / gh pr view 2251]]
- **Stale caches refreshed:** the apex cache of `obra/superpowers` and 70 Trust Magnitude caches, with no value changes.

### The grade clamp, shown the same way everywhere

A skill's displayed stars cannot exceed what its Overall Trust Grade supports: S up to 6★, A up to 4★, B up to 3★, C up to 2★, ungraded 1★. The named-skill pages and the skills API already applied this clamp. The trust ledger and the leaderboard showed the stored value instead, so the same skill could show two different ratings. They now apply the same clamp. Stored values are not edited, and the ledger shows both the stored and the displayed value. [[VERIFY: clamp alignment merged and the final number of skills whose ledger and leaderboard display changed / PR #2259 / gh pr view 2259 --json state,mergeCommit]]

## Deferred to November

The founder deferred these items to November. Each is tracked:

- **Intake for verified upstream contributors** ([#2261](https://github.com/gaia-research/gaia-skill-tree/issues/2261)): apply the recommended curator defaults, gather evidence, then run the Meta audit in the next cycle.
- **Three evidence corrections** ([#2262](https://github.com/gaia-research/gaia-skill-tree/issues/2262)): a vendor claim filed as a benchmark result on `ruvnet/ruflo`, 21 rows with no type or grade, and one mismatched arXiv citation on `knowledge-graph-build`.
- **An audit of the suite-component cap** ([#2263](https://github.com/gaia-research/gaia-skill-tree/issues/2263)): the 50 TM per-component cap on shared suite-repository evidence stays unchanged while it is audited.

## What changed on the site

These surfaces ship with Yggdrasil IV:

- **Trust lifecycle panel.** The panel now loads on every page that opens the Skill Explorer, where some pages used to show an empty space.
- **Evidence provenance.** Every evidence row is rendered by one component and says where it came from in the same way everywhere: type, source, evaluator and date, exactly as recorded.
- **Trust Challenges page** at [/trust/challenges/](../../trust/challenges/). It lists admitted challenges and, separately, review records under "Admission held, no effect on standing". It is linked from the Trust Methodology page and from the Skill Explorer's lifecycle panel.
- **Contested marks.** The leaderboard, the trust ledger and the Skill Explorer can mark a skill whose admitted challenge is unresolved, using a stronger mark when the challenge is material to Origin. Bar lengths and numbers stay exactly the same. **No skill is contested today**, because no challenge has been admitted.
- **Era stamp.** The navigation stamp and the meta-shift notes now read Yggdrasil IV and link to this report.

## What did not change

Yggdrasil IV changed no Trust Magnitude weight, cap, threshold, grade boundary or Fusion Score rule. The within-type deduplication fix corrects how an existing rule was implemented. It is not a new rule. No October challenge changed anyone's standing. Every star, grade and Origin change in this report comes from an approved decision, not from a challenge, a dead link or the passage of time. [[VERIFY: final counts at the cutoff: 301 generic skills, 352 named skills on the public record, 268 trust-ledger rows, 229 skills in the skills API, 59 contributors on the about-page tally / docs/index.html stats block, docs/graph/ledger/data.json, docs/api/v1/skills/index.json, docs/about.html / jq '.summary.total' docs/graph/ledger/data.json]]

## References

[1] Gaia Skill Tree. [Yggdrasil IV founder ratification: trust degradation, challenge and recovery](https://github.com/gaia-research/gaia-skill-tree/blob/main/founder/YGGDRASIL%5FIV%5FRATIFICATION%5F2026-10-25.md). 2026-10-25.

[2] Gaia Skill Tree. [RFC #2148: trust degradation, deterministic downward recalculation and governance](https://github.com/gaia-research/gaia-skill-tree/issues/2148).

[3] Gaia Skill Tree. [EPIC #2189: Yggdrasil IV launch readiness, October Meta re-audit, challenges and release](https://github.com/gaia-research/gaia-skill-tree/issues/2189).

[4] Gaia Skill Tree. [Challenger case bundles C1 to C4, with Meta verification records](https://github.com/gaia-research/gaia-skill-tree/tree/main/evidence/frontier-challenges). PR #2234.

[5] Gaia Skill Tree. [Trust Challenges page](../../trust/challenges/).

[6] Gaia Skill Tree. [META.md: evidence methodology and merit-based Origin](https://github.com/gaia-research/gaia-skill-tree/blob/main/META.md).

[7] Gaia Skill Tree. [GOVERNANCE.md: approval, challenges and appeals](https://github.com/gaia-research/gaia-skill-tree/blob/main/GOVERNANCE.md).

[8] Gaia Research. [Yggdrasil III: Structural Provenance Is Not Trust](2026-08-29-yggdrasil-iii-structural-provenance-is-not-trust.html). 2026-08-29.
