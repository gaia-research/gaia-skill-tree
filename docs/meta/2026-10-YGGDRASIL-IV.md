---
title: "Yggdrasil IV: A Challenge Must Be Earned, and Standing Can Recover"
author: "Gaia Research"
date: "2026-10-31"
summary: "Yggdrasil IV makes trust challenge-driven and reversible. Four real challenger cases ran in October and none was admitted. The 701-record Meta re-audit and the approved calibrations are summarized here, with results through 2026-10-31T23:59:59Z."
abstract: |
  Yggdrasil IV changes how trust in the Gaia Skill Tree can go down and come back up. A skill's standing can now be questioned only through a challenge that has been discovered, evaluated, independently verified and admitted through a trusted receipt issuer with founder approval. Elapsed time, a dead link, or the mere existence of a newer competitor is a reason to look, never a penalty. In October we ran four real challenger cases through that pipeline. None was admitted: one ended in a tie, two were inconclusive and one was rejected at triage. We report those negatives as the mechanism working as designed. This report also summarizes the October Meta re-audit of all 701 registry records, the upstream and intake reconciliation, and the adjudication and calibration decisions the founder approved, and it lists what is deferred to November. Results run through 2026-10-31T23:59:59Z, and figures from before the cutoff refresh are provisional.
label: "Meta Report"
---

## Abstract

Yggdrasil IV is challenge-driven, reversible trust governance. Yggdrasil III settled how Trust Magnitude (TM) is computed. Yggdrasil IV settles who may question a skill's standing, what counts as proof, and how a skill recovers. It changes no TM weight, cap, threshold or grade boundary.

## Cutoff and provisional figures

**Results through 2026-10-31T23:59:59Z; figures before the cutoff refresh are provisional.**

The baseline October snapshot was taken at registry revision `43797a441` and labelled `provisional-2026-10-28`. After the `2026-10-31T23:59:59Z` cutoff, the same pipeline re-ran the upstream release sync (`<= 2026-10-31T23:59:59Z`), the deterministic pre-pass (`prepass-final-2026-10-31.json`, revision `525f3c937`), and the liveness and +72h witness checks, relabelling the October record final while preserving the frozen provisional snapshot untouched.

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

An October with no admitted challenge is a correct result, not an empty one. The pipeline's job is to keep weak or unfair comparisons from touching anyone's standing, and here it did that four times, publicly and with receipts. All four review records, each with its bundle digest and a plain disclosure that it has no effect on standing, are on the [Trust Challenges page](../../trust/challenges/). The same records are in the raw files `/api/v1/challenges/reviews.json` (four held review records) and `/api/v1/challenges/index.json` (`sourceStatus: unavailable`, `subjects: []`). The second file lists admitted challenges, and it remains empty through the October cutoff.

## The October Meta re-audit

The October re-audit read every record in the registry against the Yggdrasil III engine and the Yggdrasil IV doctrine. It was read-only: every finding is a proposal, and the sweep changed nothing in the registry.

- **Coverage.** 701 records: 400 named records (48 of them awakened) and 301 generic nodes, plus 874 evidence rows, across 13 survey dimensions.
- **Adversarial verification.** 930 raw findings went to three independent verification lenses. A finding survived only if at least two of the three upheld it. 817 survived: 2 at P0, 90 at P1, 312 at P2, 354 at P3 and 59 at P4.
- **Deterministic counts.** The workflow's own model-written summary reported 810 surviving findings. We replaced it with a deterministic replay of the run journal, which gives 817. The published counts come from the replay.
- **Liveness sweep.** 962 baseline evidence and implementation URLs were probed. The first pass ran into GitHub rate limits, so the whole set was re-probed at low concurrency (`concurrency: 3`): 903 alive, 59 dead, none unknown, plus all 73 newly curated October L4 skill blob URLs verified live. A dead URL is review debt with bounded probes at t0, +24h and +72h. It is never a demotion.
- **Upstream and pull-request reconciliation.** 313 items (pull requests, branches, intake issues, upstream releases and evidence records) were each traced to a disposition: 111 verified in the integration branch, 53 already equivalent, 99 waiting for curation, 9 held for governance, 13 duplicates, 27 not applicable, 1 needing action, and none rejected. The October upstream sync brought 15 named skills to their current upstream releases (PR #2197). 38 stale intake issues were closed.
- **Intake triage.** 90 intake items were triaged (PR #2199): 59 ready for curator review, 17 needing more information, 7 duplicates, 6 already covered by the upstream sync, and 1 rejected. No intake was admitted by triage.
- **Curator topology review.** The founder reviewed and ratified 76 topology choices as the curator: 53 approved as proposed (covering 59 concrete skills including the seven parked drafts, with `k-dense-ai/pymc` already registered), 10 routed to new generic or fusion skills (4 basic, 6 fusion), 5 remapped to the closest existing generic, and 8 declined as support material rather than skills (PR #2273). All 73 net-new named skills and 10 new generic nodes are now in the registry, `grill-me` was renamed to the vendor-neutral `interview-me`, and the 8 declined support intake issues were closed.

## Adjudication and calibration approved in October

The adjudication ledger turned surviving findings into 190 candidate decisions. 65 came with numbers recomputed by Gaia's own engine, and 125 needed a ruling. Every approval below is a founder ruling recorded verbatim in the campaign record and bound deterministically in `adjudication/approvals.json`: across the 190 candidates, 51 are approved, 89 are superseded by automatic Origin derivation, 42 remain proposed, 5 are held on bounded probes or evidence gathering, and 3 are deferred to November. Registry changes went through the CLI, each with a timeline event, and code changes went through reviewed pull requests.

The first independent Meta audit of this calibration batch returned **FAIL**. Thirty-seven skills had picked up shared host-repository evidence without being linked to their suite, so they escaped the 50 TM per-component suite cap. The batch was corrected across all ten required items (`C1`–`C10`), and a fresh independent Meta re-audit (`verification/CALIBRATION-REVERIFICATION.md`) returned **PASS**.

### Freezes for removed upstream skills

Twelve `heygen-com/hyperframes` components were dropped from the upstream repository at v0.8.209. They are frozen: no longer installable, links kept, star ratings unchanged. `heygen-com/general-video` was frozen for the same reason, and so was `leonxlnx/output-skill`, which was removed upstream. Where a skill had moved or been superseded instead of removed, its links were repointed to its new home instead. That includes nine leonxlnx skills that moved to new repositories and `leonxlnx/redesign-skill`, which was folded into another skill. A frozen skill keeps its Trust Magnitude and grade, and no batch calibration or closeout touches it.

### Origin is automatic and goes to the highest merit

Origin is the mark of the highest-merit named implementation in a generic skill. It is no longer assigned by hand. The founder ruled:

- Origin is computed automatically from merit. Manual Origin adjudication ends.
- A frozen skill competes with its locked Trust Magnitude and grade, and it can beat a live one.
- If two or more implementations tie at the top, they all hold Origin. With TM a real number, that should be rare.
- Origin has no star requirement. A 1★ implementation can hold Origin. It is simply not yet Named.

This replaces the manual "Origin transfer" path described in the Yggdrasil IV ratification. Before automation landed, four skills received Origin as the clear merit winners of their buckets: `vercel-labs/vercel-react-best-practices`, `addy-osmani/code-simplification`, `ayghri/i-have-adhd` and `dietrichgebert/ponytail`. Automatic merit-based Origin derivation (`src/gaia_cli/origin.py`, PR #2271) is now live across all 223 active buckets, with 28 buckets sharing Origin among tied top contenders and `1★`/`awakened` Origin holders projected with handle redaction preserved in `originStandings`.

### Star changes and corrected rules

- **latent-spaces/brag rises from 3★ to 4★.** TM 144.54 (A), a live pinned link, the Unique branch and sole Origin of its bucket. The 4★ Unique gate passes.
- **google-deepmind/workflow-skill-creator is Named** as *Workflow-to-Skill Distiller*. Its strongest evidence row was a bare repository filed as a peer review. It was retyped honestly, and its TM went from 100.82 (A) to 59.65 (B). Its stored 4★ stays as review debt, not a demotion. Under the grade clamp it is displayed at 3★, the B ceiling, across the named index, skills API, trust ledger and leaderboard until that debt is settled (PR #2251, PR #2259).
- **safishamsi/graphify stays at 5★.** An earlier rule had required a 5★ Unique skill to hold Origin on one of its generic skill's prerequisites. That requirement was borrowed from the Suite gate and never ratified for Uniques. A Unique needs to be its bucket's Origin and to clear the TM gate, and graphify does both (TM 318.14, S). The demotion proposed during the audit was reverted, and `checkUniqueBranchGate` in `src/gaia_cli/promotion.py` was corrected in PR #2271 so 5★ Unique Ultimate skills require only own-bucket Origin and Grade S (TM >= 250).
- **panniantong/agent-reach** had its evidence re-derived: TM 53.86 (B) went to 260.83 (A), and it stays at 3★.

### Evidence corrections

- **Evidence is deduplicated within its type.** Two rows of different types at the same URL now both count, and two rows of the same type at the same URL count once (PR #2257).
- **mattpocock/skills:** an arXiv citation count recorded as 500 was corrected to 2. TM moved from 374.99 to 280.39 and stays S, so the 5★ is unchanged. One supporting witness URL (`frontendmastery.com`) returned HTTP 404 across its bounded t0, +24h and post-deadline +72h (`2026-11-01T16:40Z`) probes, with no Wayback snapshot; under Yggdrasil IV it remains recorded review debt with no automatic demotion.
- **Thirty-seven skills that had been added with no evidence** received verified host-repository evidence and were linked to their parent suites (`addy-osmani/agent-skills`, `garrytan/gbrain` and `obra/superpowers`, PR #2251). Thirty-six sit at the 50.0 TM (B) suite-component cap, and `obra/test-driven-development` sits at 59.0 TM (B) with its inherited generic peer-review evidence.
- **Stale caches refreshed:** the apex cache of `obra/superpowers` and 70 Trust Magnitude caches, with no value changes.

### The grade clamp, shown the same way everywhere

A skill's displayed stars cannot exceed what its Overall Trust Grade supports: S up to 6★, A up to 4★, B up to 3★, C up to 2★, ungraded 1★. The named-skill pages and the skills API already applied this clamp. The trust ledger and the leaderboard showed the stored value instead, so the same skill could show two different ratings. They now apply the same clamp. Stored values are not edited, and the ledger shows both `storedStars` and the grade-clamped `currentStars` (PR #2259; 9 skills in the post-cutoff ledger display a clamped star rating below their stored frontmatter level).

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

Yggdrasil IV changed no Trust Magnitude weight, cap, threshold, grade boundary or Fusion Score rule. The within-type deduplication fix corrects how an existing rule was implemented. It is not a new rule. No October challenge changed anyone's standing. Every star, grade and Origin change in this report comes from an approved decision, not from a challenge, a dead link or the passage of time. At the final October cutoff (`525f3c937`), the registry holds **784 records**: **311 generic capability nodes** (156 basic, 155 fusion) and **473 named skill records** (426 classified entries across 223 buckets plus 47 awakened entries) across **77 contributors** in the public directory, with **342 trust-ledger rows** and **335 non-redacted skills across 52 contributors** in the public v1 API.

## References

[1] Gaia Skill Tree. [Yggdrasil IV founder ratification: trust degradation, challenge and recovery](https://github.com/gaia-research/gaia-skill-tree/blob/main/founder/YGGDRASIL%5FIV%5FRATIFICATION%5F2026-10-25.md). 2026-10-25.

[2] Gaia Skill Tree. [RFC #2148: trust degradation, deterministic downward recalculation and governance](https://github.com/gaia-research/gaia-skill-tree/issues/2148).

[3] Gaia Skill Tree. [EPIC #2189: Yggdrasil IV launch readiness, October Meta re-audit, challenges and release](https://github.com/gaia-research/gaia-skill-tree/issues/2189).

[4] Gaia Skill Tree. [Challenger case bundles C1 to C4, with Meta verification records](https://github.com/gaia-research/gaia-skill-tree/tree/main/evidence/frontier-challenges). PR #2234.

[5] Gaia Skill Tree. [Trust Challenges page](../../trust/challenges/).

[6] Gaia Skill Tree. [META.md: evidence methodology and merit-based Origin](https://github.com/gaia-research/gaia-skill-tree/blob/main/META.md).

[7] Gaia Skill Tree. [GOVERNANCE.md: approval, challenges and appeals](https://github.com/gaia-research/gaia-skill-tree/blob/main/GOVERNANCE.md).

[8] Gaia Research. [Yggdrasil III: Structural Provenance Is Not Trust](2026-08-29-yggdrasil-iii-structural-provenance-is-not-trust.html). 2026-08-29.
