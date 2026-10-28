# Yggdrasil IV — Trust Degradation, Challenge, and Recovery

**Founder ratification:** 2026-10-25  
**Status:** Product doctrine ratified; implementation **not yet complete**.  
**RFC:** [#2148](https://github.com/gaia-research/gaia-skill-tree/issues/2148), [Argon/Opus whole-tree design and findings](https://github.com/gaia-research/gaia-skill-tree/issues/2148#issuecomment-6388789645), [D8 ruling](https://github.com/gaia-research/gaia-skill-tree/issues/2148#issuecomment-6388990961).  
**Canonical ownership:** `META.md` owns ranking/evidence methodology and **merit-based Origin**; `GOVERNANCE.md` owns approval and appeals; `founder/STEWARD.md` and its operating model own observations, debt and execution routing; this document records the Yggdrasil IV founder decisions.

> Gaia is a **long-lived trust registry, not a fast-moving leaderboard**. Time invites scrutiny; **counterevidence justifies degradation**; adjudication authorizes canonical change. A historically valid challenge can later be defeated by a new implementation. No valid historical achievement is silently erased.

## I. Policy boundaries

Yggdrasil III's evidence-backed additive Trust Magnitude (TM), separate informational Fusion Score, Evidence Type weights and caps, thresholds, diversity/witness gates, and branch topology **remain unchanged** until explicitly approved work implements a different rule. Yggdrasil IV supplies the **challenge/degradation/recovery lifecycle and authority**; it is not an extra penalty multiplier or an automatic rank-recalibration switch.

Potential decay is a **non-scoring review signal**. Elapsed time, a stale benchmark, a new built-in Claude/agent capability, altered source, or a temporary URL failure can trigger a bounded investigation. **No reduction of published TM or star rank follows from elapsed time alone.** Continue recording and shadow-evaluating the existing type-specific freshness rules at pinned `evaluationAtUTC` for comparison, but do not promote shadow decay to authoritative score or silently penalize stable/finished software. Code currently using temporal freshness for live calculations must be assessed for divergence in RFC #2148 before publication automation is authorized.

**Confirmed degradation** requires independently verifiable, materially relevant counterevidence: for example, a newer agent capability demonstrably supersedes a named skill **for a specified task under comparable conditions**. A newer competitor's existence or a description claim alone is not proof. An old benchmark remains historically true for its pinned version/task/environment, even if the *present-day claim of unique usefulness* becomes weaker. Interpretive conclusions and canonical consequences require Class C review.

**Recovery** is symmetric: a later upstream release, new working CLI, fixed implementation or independent benchmark may defeat even a formerly correct verified challenge. Reverify the same disputed behavior, version and comparator. A score may return partially, fully, or exceed its old value **only through canonical deterministic recomputation of eligible, revisioned evidence**, never an invented comeback bonus. Historical challenge, consequence, remediation, and recovery receipts remain linked.

## II. Challenge and evidence states

Keep **observations** distinct from **canonical assertions** and from **public challenge proceedings**:

| Layer | Target vocabulary | Meaning and authority |
| --- | --- | --- |
| Observation | `unknown`, `reachable`, `transient-failure`, `unavailable`, `changed` | Fallible probes held in Steward receipts; no canonical revocation or score mutation. |
| Evidence assertion | `active`, `suspended`, `revoked`, `superseded` | Versioned canonical truth under its separate governance gates; Class B cannot write these states. |
| Public challenge | `verified-pending`, `upheld`, `narrowed`, `technically-rebutted`, `resolved-by-upstream-improvement`, `rejected` | Public challenge proceeding; **Class B may close only objectively resolved technical cases** under the proof contract below. |
| Numeric consequence | `shadow`, `awaiting-approval`, `approved-published` | Proposed versus approved current TM/grade and rank eligibility; do not confuse with the challenge status. |

These are **proposed implementation vocabularies**, not claims that the current schemas or UI already expose them. Give evidence and its revisions stable identities (`evidenceId`, revision, `supersedes`, `decisionRef`); a refreshed metric replaces the previous current measurement rather than double counting it. Retain provenance, original observation time, source SHA/version, verifier/method, policy version and pinned evaluation time.

## III. Public transparency and contributor rights

**Verified challenges go public immediately after independent verification**, with an operational goal of publication within 24 hours and simultaneous contributor notice. Show challenged claim, source/version, task and comparison limits, evidence/independent verification, challenge status and response route. No unverified allegation is labeled a verified challenge. An honest single-benchmark advantage is **not** a verdict of global inferiority.

All verified challenges are discoverable in a public evidence/challenge history. A **scoped capability challenge** is distinct from prominent **Origin contested**. Only an unresolved **material** challenge that could affect present Origin qualification yields that prominent marker. Derived display must clear when the last qualifying challenge resolves; it is not a direct score/rank mutation.

Ordinary contributor response is **14 calendar days** for rebuttal, equivalent reproducible testing, or upstream improvement. The technical challenge may close earlier on complete Class B proof. An unanswered challenge does **not** cause automatic demotion. An availability-only concern receives bounded `t0 / +24h / +72h` probes before unavailability review debt, not a default penalty. Independently established urgent fraud/security risk may be expedited to Class C. Notices, extensions, outcomes and appeal evidence remain recorded.

When a Class B technical challenge clears while a previous approved score loss is still present, the UI must distinguish **“technical challenge resolved; trust recalibration pending”** from numeric recovery. Public index, ledger, leaderboard, API, profiles, and badges must reflect **one coherent approved snapshot**. Historical rank awards remain visible; canonical star changes must be explicitly approved and represented in both canonical and owner-tree timeline events (`previousValue → newValue`). Silent projection clamps are defects.

## IV. Current Origin is exactly one and merit-based

**`META.md` §4.1 is correct.** Current Origin belongs to the **most renowned qualified named implementation** in each **claimed** generic bucket, not necessarily the first person to claim it. There is **exactly one current Origin per claimed eligible generic node**, no vacancy merely because its incumbent is contested; unclaimed generic nodes do not require fabricating a named owner. A different qualifying named skill can win Origin through an **approved transfer at any time**; historical attribution to earlier Origin holders remains unchanged.

A verified material challenge can mark Origin **contested**, but **does not remove/transfer Origin**. A Class B technical resolution can clear its derived contested marker if no other material challenges remain, without transferring Origin. Claims that no eligible owner remains or that two claims conflict escalate to Class C rather than rewriting the one-Origin invariant.

Preserve `META.md`'s currently documented 0★ effective demerit floor over contradictory 1★ legacy prose. **`broken-evidence` cannot be auto-applied merely from an unavailable URL** under Yggdrasil IV; demerit consequences require a substantiated, approved decision. Any broader demerit model change needs its own review.

## V. Steward: challenge-driven, two-sided upstream watching

Reuse existing Upstream Watcher, Steward debt, sensors, receipts, and skills. A verified challenge triggers **bounded, targeted and release/event-driven** investigation of both the challenged skill and its comparator when traceable, particularly for **Unique-branch** named skills: upstream release/version/SHA, `SKILL.md`, executable behavior, new CLI support, installability, and the specific claimed benchmark or capability. Descriptions are scouting leads, **never sufficient proof by themselves**. On resolution, return to routine cadence; no endless costly monitoring or model-derived score authority.

**Class A:** deterministic observations, probes and debt creation only.

**Class B may autonomously close an objectively resolved technical challenge** as `technically-rebutted` or `resolved-by-upstream-improvement` **only if all hold**:
1. Challenge is narrow and testable, with a pinned behavior/test and comparison conditions.
2. Fix addresses **the same** challenged claim; new version/SHA, run environment, test version, original baseline, actual output and any comparator are captured.
3. **Independent** reproducible verification passes. Missing, partial, conflicting or model-only confidence is not sufficient.
4. A durable, public, linked resolution receipt and contributor notification are produced. The original challenge stays in history.
5. The closure changes **only public technical challenge status and its derived contested indicator** when no other material challenge remains. It does **not** change TM, Grade, stars, Origin, canonical evidence assertions, or meta/schema policy.

**Class C:** ambiguous/evaluative superiority, semantic replacement, inconsistent benchmarks or provenance, Origin change, canonical evidence assertion change, score/grade/rank mutation, policy/schema change, and uncertain or urgent security/fraud judgments. A Class B runner may **propose** a separate recovery calculation; it may not authorize or publish it. Any future reopening uses a linked new challenge rather than silently rewriting a resolved event.

## VI. Ratified decisions and implementation gates

Founder decisions **D1–D11** for RFC #2148 are ratified in principle, including D3's **counterevidence-triggered potential versus confirmed decay**, D7's **no-vacancy transferable Origin and reversible loss**, and D8's **immediately public verified challenges with bounded Class B technical closure**.

- **P0–P2 first:** final contract/documentation, deterministic **shadow-only** evaluator and Steward observation/proposal packets; no canonical score/evidence/rank changes.
- **P3–P4 require a second explicit founder gate:** evidence identity/schema and CLI mutation support, focused correctness fixes, independently verified pilot and rollback.
- **P5 requires separate approval:** wider registry rollout; no implicit mass recalibration or mass evidence gathering.
- **RFC closure requires explicit founder approval** after delivered and verified DoD, not merely merged policy docs.

**Four discovered correctness defects** must be isolated as `implementation-correction` receipts, not “decay” or new meta policy: source-only inheritance merge/order dependence; eligibility-before-dedup; component-before-suite Apex grade ordering; named-row grading context. Shadow-compare before allowing a corrected score to publish. Keep existing weights, caps, thresholds and Fusion Score frozen.

**Proposed proof fixtures:** reachable/temporary 404, repeated unavailable evidence, contradictory evidence, valid older benchmark, newer superior comparator, reversible updated CLI, partially successful response, two unresolved material challenges, technical resolution with recovery pending, revoked verifier, generic inheritance and suite capstone, cross-surface snapshot, pinned clock/policy version, dual timeline and rollback. An old 202-test pass does not prove unimplemented Yggdrasil IV behavior.

## VII. Agent-skill responsibilities

- `gaia-meta-audit`: triage and evidence/change queues, including material challenges and stale observations; **never** decide Origin via `createdAt` or mutate directly.
- `gaia-meta-sweep`: whole-tree **read-only comparison** of stored versus derived trust and eligibility until explicitly authorized; semantic reviewers are not numerical authorities.
- `gaia-audit`: focused independent verification; separate technical link failure from adjudicated evidence invalidity and never auto-demote on an HTTP error.
- `gaia-trace-timeline`: preserve both prior and recovered rank, and never fabricate an award, penalty or unapproved canonical mutation.
- `gaia-steward` / Upstream Watcher: bounded dual-sided challenge watch; Class B technical closure receipts only with the proof contract, Class C for all consequential canonical decisions.

**No production deployment or new challenge UI is claimed by this ratification.** See RFC #2148 for the engineering specification and approval progression.
