# GAIA STEWARD — EVOLUTION ARCHITECTURE

**Status:** PROPOSED — not ratified. This document governs nothing until a founder ruling adopts it, in whole or in part.
**Date:** 2026-10-27, written against `main` at `b0f6d9e` and the remote refs listed in §16.
**Canonical goal:** [`ENDGAME.md`](ENDGAME.md). This document neither amends nor replaces it.
**Current authority, unchanged by this document:**
- [`STEWARD.md`](STEWARD.md)
- [`STEWARD-OPERATING-MODEL.md`](STEWARD-OPERATING-MODEL.md)
- [`steward/POLICY.yaml`](steward/POLICY.yaml)
- [`YGGDRASIL_IV_RATIFICATION_2026-10-25.md`](YGGDRASIL_IV_RATIFICATION_2026-10-25.md)
- the Gaia Frontier ruling of 2026-10-26 (#2148; its file reaches `main` with Yggdrasil IV)

**Implementation handover:** [`handovers/2026-10-27-steward-evolution-post-yggdrasil-iv.md`](handovers/2026-10-27-steward-evolution-post-yggdrasil-iv.md). Implementation starts only after Yggdrasil IV lands and `main` is verified.

---

# 0. How to read this document

Each claim carries one of five markers.

| Marker | Meaning |
|---|---|
| **VERIFIED** | Read from code, a workflow, a git ref or a merged founder document on the date stated. |
| **RATIFIED** | Already decided in a founder document. Restated here, not changed. |
| **PROPOSED** | Recommended here. Binding only after a founder ruling (§17). |
| **POINT-IN-TIME** | A measurement dated 2026-10-27. Re-verify it before acting on it. |
| **OPEN** | Undecided. The resolving test is named. Do not invent an answer. |

Unmarked prose in §§2–15 is PROPOSED.

**How a proposal becomes binding.** Merging this document as PROPOSED ratifies nothing. A ruling binds only when the founder records it, in one of two ways:
- a founder-approved change that marks that ruling RATIFIED in §17;
- a decision record under `steward/decisions/`.

Rulings are adopted one at a time; adopting one adopts nothing else.

---

# 1. The proposal on one page

1. **One runtime, many domains.** Gaia Steward's existing runtime becomes the shared execution mechanism:
   - the zero-model runner;
   - the compare-and-swap ledger with leases;
   - sensors, debt and the rolling lane;
   - verification and landing;
   - the founder desk.

   Authority is *not* shared. Each **domain** keeps its own charter, policy, ledger and founder gates. One shared execution mechanism does not mean one universal governing authority. (SE-1)
2. **The Tree domain is unchanged.** The Gaia Skill Tree Steward keeps STEWARD.md, POLICY.yaml, the Yggdrasil IV clauses and the Frontier ruling as they are. Nothing here widens its charter. (SE-1)
3. **A second domain, Ecosystem, is proposed.** It covers Gaia's own opted-in repositories, starting with a public pilot cohort. It has two lanes (SE-2):
   - **Lane A, Ecosystem Health:** reactive.
   - **Lane B, Endgame Progress:** forward work the founder has authorized.
4. **Hosting follows capability and isolation, not ambition.**
   - Observation runs on the existing public host.
   - Write-capable driving runs only where its credential is confined.
   - A private host is created only when a concrete trigger fires (§8.4). (SE-3)
5. **Authorization is a record, never an inference.**
   - An issue is a candidate. A label is not authorization.
   - Work runs only under a founder-signed authorization record that is bound to the content, expires and can be revoked. (SE-4)
6. **Authority contracts automatically and expands only by ruling.**
   - Autonomy advances through envelopes E0–E5, by founder ruling on measured evidence.
   - Any boundary breach demotes to observe-only at once. (SE-5)
7. **Coordinators and executors are adapters, chosen by probe.** A durable agent may act as the proactive *coordinator*: waking, continuing authorized work and handling exceptions under one capability contract (§5.6). It never becomes an authority or a second ledger. Admission stays deterministic. No product is assumed to work until a go/no-go probe passes. (SE-6)
8. **The observer is itself observed.** A zero-model watchdog on a separate host checks Steward's own liveness. (SE-7)
9. **Existing threads are re-scoped, not duplicated.** (SE-8)
   - #2158 becomes the Admit stage.
   - #2001 becomes the Learn stage.
   - gaia-research#311 stays the umbrella.
   - #2175 is a precondition.
   - gaia-skill-heaven#216 is the first Lane A outcome candidate.
10. **Pre-existing ledger state is reconciled, not reset.** The operator's disposition of 2026-10-27 is respected. Anything older is re-observed before it is adopted. (SE-9)
11. **Lane B's classification contract is defined here and applied nowhere** until it is ratified and evaluated. (SE-10)

---

# 2. Purpose

**RATIFIED (STEWARD.md §15):**

> Gaia can observe change, measure its own maintenance debt, resolve what it is authorized to resolve, spend intelligence only where needed, and escalate only decisions worthy of governance.

**PROPOSED extension:** the same sentence, applied to every Gaia repository the founder opts in, plus one clause:

> …and advance founder-authorized work toward the endgame without being re-prompted between steps it is already permitted to take.

## What the evolution is for

- **Shrinking detection latency on the edges between repositories.** Each POINT-IN-TIME incident in §16.4 went unseen because no observer read its signal:
  - a daily cross-repository sync red for 95 consecutive runs;
  - a weekly evidence-link check red for 26 runs;
  - a retrieval index 50 days stale.
- **Turning founder-authorized work into verified outcomes** with fewer founder interventions per outcome.
- **Leaving every decision where it is decided today.**

## What does not change

- Gaia's ontology.
- Yggdrasil's trust model, including Yggdrasil IV.
- Arbor's behavioral model.
- The Frontier, Meta, Steward and Governance separation (§15).
- ENDGAME.md, Roadmap v5, and every RATIFIED Tree rule.

## What this is not

- **Not a second source of authority.** It does not decide product direction, ontology, prestige, trust or evidence.
- **Not an outward-facing scanner.** That is Frontier's role.
- **Not an evaluator.** That is Meta's role.
- **Not a decision-maker.** That is Governance's role.
- **No new defaults.** It is not a new product, brand, ledger format or control repository by default.
- **Not proof of unattended autonomy.** An orchestration that works once is a working mechanism, nothing more.

---

# 3. Runtime and domains

## 3.1 Terms

| Term | Meaning |
|---|---|
| **Runtime** | The mechanism. Today that is `src/gaia_cli/steward/` (`fullrun.py`, `ledger.py`, `lane.py`, `verification.py`, `landing.py`, `receipts.py`, the sensor modules, desk and digest) and `scripts/steward_drive.py`. **VERIFIED** on `main` `b0f6d9e`. |
| **Domain** | A unit of authority: a charter, a policy file, a ledger ref, a desk section, and the founder gates that apply. |
| **Lane** | A kind of work inside a domain: Lane A (health) or Lane B (endgame progress). |
| **Host** | Where a domain instance runs and keeps its state. |
| **Coordinator** | The proactive host that wakes, works the authorized backlog through the runner, revisits blockers and asks for decisions (§5.6). It holds no authority and no state of its own. |
| **Driver** | The one privileged process that performs the runner's external effects (branch, pull request, comment) and records them. |
| **Executor** | Whatever performs the runtime's agent actions (`agent.build`, `agent.verify`). It holds no write credential. |

## 3.2 Domains

| | Tree domain | Ecosystem domain |
|---|---|---|
| **Status** | **RATIFIED** (STEWARD.md, POLICY.yaml) | **PROPOSED** (SE-2) |
| **Charter** | STEWARD.md. The Frontier ruling makes it the "reactive governor of tree-related observations, verified challenges and authorized maintenance". | The operational health (Lane A) and founder-authorized forward work (Lane B) of opted-in Gaia repositories |
| **Writes to** | gaia-skill-tree only | Its onboarded repositories, never gaia-skill-tree |
| **Reads** | gaia-skill-tree | Its onboarded repositories, plus gaia-skill-tree as a *producer* of cross-repository contracts |
| **Initial cohort** | — | gaia-research, gaia-skill-heaven, skill-cost, skill-scout-fleet, skill-fuse, skill-ci-churn, skill-context-diet, skill-image-tuner. **VERIFIED** public on 2026-10-27. |
| **Policy** | `founder/steward/POLICY.yaml` | Its own domain policy file, named at Stage 1 |
| **Ledger** | `refs/heads/steward/ledger` | Its own ref, never the Tree's |
| **Desk** | The existing founder desk | The same desk, in a separate section and debt namespace |

Four rules apply to every domain:

- **One governing Steward domain per repository.** Only the domain whose charter covers a repository writes to it *as Steward*. When a stale contract is consumed *by* gaia-skill-tree, the Ecosystem domain reports the edge, and the fix is Tree-domain debt.

  The rule does not stop other writers. Repository-owned workflows, maintainers and founder-directed orchestrator campaigns keep writing. Contention with them is handled at the last privileged effect (§5.4).
- **A contract edge belongs to its consumer's domain.** The consumer pins the contract and refreshes it. A producer is never edited to satisfy a consumer.
- **Domains are created and retired only by founder ruling.** A retired domain's ledger stays readable and is never deleted.
- **Repositories outside Gaia are out of scope.** Repositories of other owners and organizations belong to their own domains. They are never observed from a public Gaia host.

## 3.3 What the runtime owns and what a domain owns

| Concern | Runtime (shared mechanism) | Domain (separate authority) |
|---|---|---|
| Sensor protocol; unknown is never healthy | Owns | Which sensors run, and on what inputs |
| Debt identity, dedupe, lifecycle | Owns | Debt kinds and their authority class |
| Ledger: CAS, leases, attempts, receipts | Owns the code | Its own ref and records |
| Lane caps (in-flight, attempts, cooldown) | Hard ceilings, in code | Values within the ceilings |
| Routing; recording model and effort | Owns | The route table and budgets |
| Verification protocol (verifier ≠ builder) | Owns | Verifier requirements per route |
| Landing adapters, which fail closed | Owns | The per-repository rules (§9) |
| Founder desk rendering | Owns | Which items reach the founder |
| Authority classes A/B/C | The definitions | Which debt gets which class |
| Charter | — | Owns |

The runtime never decides anything. It enforces what a domain's records have decided.

## 3.4 Why this shape, and not the alternatives

- **Not a wider Tree charter (v3, decision D1).** The Frontier ruling (LOCKED 2026-10-26) fixes the Tree Steward as the governor of *tree-related* observations. Stretching that charter across other repositories would amend a founder ruling made on 2026-10-26 by implication. A separate domain needs no such stretch.
- **Not a new engine or fleet platform (v2).**
  - The runtime already has the hard parts:
    - leases and adoption of expired runs;
    - idempotency keys;
    - a verifier-identity check that defeats case and zero-width tricks;
    - landing that fails closed.
  - They passed eight rehearsal scenarios against bare remotes (**VERIFIED**: [`handovers/2026-10-21-steward-full-founder-report.md`](handovers/2026-10-21-steward-full-founder-report.md) §5).
  - A second engine would duplicate those properties and then drift.
- **Not a new control repository now.** Every repository in the initial cohort is public (**VERIFIED** 2026-10-27), so observing them needs no secret and leaks nothing. A private host is justified only by the triggers in §8.4.
- **Not "Auto Ops" as a product.** gaia-research#311 uses "Ecosystem operations" or "Auto Ops" as a name for the work programme. It is not a runtime, ledger, brand or authority. It is not a lexicon entry until the oracle makes it one.

## 3.5 Extraction rule

"Steward Core" is a role, not a package.
- The runtime stays in `src/gaia_cli/steward/` until a second domain actually runs on it.
- A seam is extracted only when two real domains need it and the extraction leaves both green.
- No abstraction is built for hypothetical callers.

## 3.6 Each new component, and the requirement it answers

| Component | Concrete requirement | Evidence |
|---|---|---|
| Domain policy file and repository records | Landing rules differ per repository, and unknown rules must fail closed | **VERIFIED:** gaia-skill-heaven squashes and keeps drafts as drafts; gaia-skill-tree has squash disabled |
| Typed contract registry | Each repository's CI is offline by design (D6), so drift between producer and consumer is invisible to both | **POINT-IN-TIME:** #216 stale for 50 days; craft data frozen since 2026-08-13 |
| Silence and trust-ramp detection | A red or silent schedule has no reader | **POINT-IN-TIME:** 0 of 95 and 26 of 26 red runs (§16.4) |
| A ledger ref per domain | State must not mix authorities | **VERIFIED:** Yggdrasil IV writes challenge `operations` into the Tree ledger (§7) |
| Authorization records | Anyone can open an issue in a public repository, labels carry no authority, and merge authorization is already an open P0 | **VERIFIED:** #2175 |
| Durable build packets | A resume failed because its packet lived in ephemeral local state | **VERIFIED:** the ledger abandon reason, 2026-10-27 (§16.2) |
| Independent watchdog | Steward's own stall went unseen for six days | **VERIFIED:** ledger history 2026-10-21 → 2026-10-27 |
| Classification records | Lane B needs an ENDGAME trace without mutating issues | The mission brief: "An issue is a candidate, not authorization or commitment" |

**Not built:**
- a fleet platform, a second engine or a new ledger format;
- a control repository, until a §8.4 trigger fires;
- an app spanning several owners;
- any model in the observation path;
- an extracted Core package, until two domains run;
- new labels.

---

# 4. Lanes

## 4.1 Lane A — Ecosystem Health (reactive)

Lane A observes the following and repairs them, within authority:
- **Scheduled workflows** that fail repeatedly, never pass their trust ramp, or fall silent.
- **Typed producer-to-consumer contracts that drift.** These include pinned snapshots, vendored code, schema or branch pins, and version floors. Intentionally frozen pins act as quiet negative controls.
- **Stale generated artifacts.** Also release or deploy readback that does not match.
- **The domain's own pull requests:** red CI, review requested, conflicts.

Proposed debt kinds:
- `automation_broken`
- `automation_silent`
- `contract_stale`
- `contract_unknown`
- `readback_mismatch`
- `obligation_open`

Lane A works only from observations. It never reads an issue as an instruction.

## 4.2 Lane B — Endgame Progress (proactive, within authorized work)

Lane B advances founder-authorized forward work: a missing feature, a benchmark, a runtime contract, a behavioral observation or a cross-product integration.

1. **An issue is a candidate, not authorization or commitment.**
2. Lane B selects an item only when all three hold:
   - it has a valid authorization record (§6.3);
   - its dependencies are resolved;
   - its repository profile allows the work.
3. **Every Lane B item carries an alignment record (§14.1).** The record is either `direct`, quoting the ENDGAME sentence, or `indirect`, with a traceable path through an approved dependency. A `none` or `unknown` item cannot enter Lane B, but it may still be legitimate Lane A maintenance or ordinary backlog.
4. **Some surfaces are never Lane B's.** These go to Class C:
   - surfaces owned by Yggdrasil IV: challenge, degradation, recovery, trust, evidence, stars and Origin;
   - surfaces owned by Meta: evaluation and ranking;
   - surfaces owned by Governance: L4 intake, schema, policy and release.
5. **Lane B items are Class B at most:** bounded, verified, delivered as a draft pull request. Forward work is never Class A, because it is not deterministic repair.

## 4.3 Rules shared by both lanes

1. **One item, one lane.** Sometimes an issue and an observation describe the same subject. For example, gaia-skill-heaven#216 and the stale retrieval-index contract are the same subject. The observation's debt is then the item, and the issue is its human-visible handle.
2. **Lane A outranks Lane B in the same repository** when Lane A debt would block Lane B's verification. A red CI blocks forward work.
3. **The lanes share the domain's budget and in-flight cap.** Neither may starve the other: while Lane A has admissible work, admission keeps at least one in-flight slot for it (PROPOSED default).

---

# 5. The operating pipeline

## 5.1 Stages

```text
Discover → Normalize → Align → Prioritize → Authorize → Admit → Lease
        → Execute → Verify → Reconcile → Learn → Continue or Stop
```

| # | Stage | What it does | Record written | Failure becomes | Reuses (VERIFIED) |
|---|---|---|---|---|---|
| 1 | **Discover** | Lane A: sensor observations. Lane B: candidate issues in onboarded repositories. The repository list itself (§9.1). | Observation receipt | `unknown` coverage, never "healthy" | Sensor modules; sensor contract (operating model §7) |
| 2 | **Normalize** | Assigns a stable identity, dedupes against the ledger and rejects malformed input | Debt or candidate record | `invalid`, with a reason | `debt.py`; semantic dedupe (operating model §5) |
| 3 | **Align** | Lane B: classify the item and anchor it to ENDGAME (§14.2). Lane A: tag it `maintenance`. | Classification record | `none` (not eligible for Lane B) | — (new) |
| 4 | **Prioritize** | Scores the item by policy weights | Priority on the record | — | `POLICY.yaml` weights; `routing.py` |
| 5 | **Authorize** | Sets the authority class, checks for a standing or item authorization, and checks that it is still fresh | Authority verdict | `awaiting_founder` (Class C); `authorization_stale` | `policy.py`; `steward-decision-v1` records |
| 6 | **Admit** | Checks dependencies, budget and quota, the repository profile and the domain exclusions (Yggdrasil IV, Meta, Governance). Picks an explicit model and effort from the route. | Admission record, with a budget reservation | `blocked` (dependency); `deferred` (budget or quota); refusal | Lane caps in `lane.py`; #2158, re-scoped |
| 7 | **Lease** | Takes a time-bound lease and records intent before any effect | Lease (ledger CAS) | Contention exits; it never waits | `ledger.py` leases: TTL 1800 s, adoption after expiry |
| 8 | **Execute** | Class A: deterministic repair. Class B: a builder with no write credential, inside the item's envelope. | Attempt record: model, effort, executor, cost | A stop condition escalates; a crash is resumable | `repairs.py`; `steward_drive.py`; `steward_agent_dispatch.py` (paused) |
| 9 | **Verify** | Runs repository checks and an independent verifier. A machine verdict alone never accepts. | Verification record | `rejected`: at most `maxAttempts`, then cooldown | `verification.py` |
| 10 | **Reconcile** | The driver lands the change through the repository adapter, never on a default branch. After integration it re-observes the production truth. | Landing and readback record | `readback_mismatch` (the item stays open) | `landing.py`; "resolve only after re-observation" |
| 11 | **Learn** | Records outcome, skill-cost spend and founder minutes; classifies misses with the #2001 retro taxonomy | Receipt; weekly retro | — | `receipts.py`; `/gaia-steward-retro` |
| 12 | **Continue or Stop** | Continues only while budget, caps and envelope allow and admissible work remains. Otherwise stops with a quiet receipt. | Run status | — | The runner's finite budget (operating model §1) |

## 5.2 Mapping to the existing core loop

**RATIFIED** loop (STEWARD-OPERATING-MODEL.md §1):

```text
WAKE → COLLECT OBSERVATIONS → NORMALIZE → RECONCILE WITH CURRENT STATE
     → CREATE / UPDATE / RESOLVE DEBT → PRIORITIZE → AUTHORIZE
     → Class A / B / C → VERIFY → RECORD RECEIPT → STOP
```

| Existing step | Pipeline stage |
|---|---|
| WAKE; COLLECT OBSERVATIONS | Discover |
| NORMALIZE; RECONCILE WITH CURRENT STATE; CREATE / UPDATE / RESOLVE DEBT | Normalize |
| — | Align (new; Lane B only) |
| PRIORITIZE | Prioritize |
| AUTHORIZE | Authorize |
| Implicit in the lane caps | Admit (made explicit) |
| Steward Full leases | Lease |
| Class A / B / C branches | Execute. Class C never executes; it queues. |
| VERIFY | Verify |
| "Resolve only after re-observation" | Reconcile (made explicit as post-integration readback) |
| RECORD RECEIPT | Learn |
| STOP | Continue or Stop |

"Reconcile" means two things in the two vocabularies:
- In the existing loop, "reconcile with current state" means deduping against known debt. Here that is part of **Normalize**.
- In this document, **Reconcile** always means post-integration readback.

## 5.3 Item states

Existing state names are reused. New states are added only where Lane B or admission needs them.

| State | Meaning | Existing equivalent |
|---|---|---|
| `candidate` | Lane B: an issue seen but not yet classified | — (new) |
| `classified` | Lane B: a classification record exists | — (new) |
| `open` | Lane A: debt observed and normalized | debt `open` |
| `awaiting_founder` | Needs a founder decision or authorization | debt `awaiting_founder` |
| `authorized` | A valid authorization bound to the current content | — (new) |
| `authorization_stale` | The bound content changed, or the authorization expired or was revoked | — (new) |
| `queued` | Admissible, waiting for a slot | debt `queued`; lane `queued` |
| `blocked` | Waiting on a dependency. Spends no attempts. | debt `blocked` |
| `deferred` | Waiting on budget or quota | — (new) |
| `dispatched` / `building` | Leased and executing | lane `dispatched`; work `building` |
| `awaiting_verification` | Built; the verifier is pending | debt `awaiting_verification` |
| `verified` | The verifier accepted it | work `verified` |
| `awaiting_merge` | A draft PR is open and waiting for its human merge. The item is *not* done, and its truthful status is "proposed". | — (new) |
| `landed` | Merged by its owner, or integrated into a Tree `dev/*` branch | work `landed` |
| `resolved` | Re-observation confirms the outcome | debt `resolved` |
| `rejected` | Verification failed. It may retry after cooldown, up to `maxAttempts`. | lane rejection |
| `escalated` | A stop condition fired, attempts ran out, or the nature of the problem changed | lane `escalated` |
| `superseded` / `invalid` | Final dispositions, each with a reason | debt `superseded` / `invalid` |

Transition invariants:

1. **No item disappears without a final disposition and a receipt.** (**RATIFIED**, operating model §4.)
2. **`resolved` comes only from re-observation.** A verifier verdict, a merge, an exit code or a receipt alone is never enough.
3. **A stale authorization sends the item back.**
   - The item goes from `authorized` to `authorization_stale` the moment the bound content changes, or the authorization expires or is revoked. From there it returns to `classified` or `awaiting_founder`.
   - A leased item re-checks its authorization before every external write.
4. **A `queued` item older than its freshness window is re-observed before admission.** (**POINT-IN-TIME** evidence: 99 lane entries queued on 2026-10-21 were still queued on 2026-10-27.)
5. **A Lane B item starts at `candidate`** and cannot skip `authorized`.
6. **Escalation never raises authority.** It moves the item to the founder desk.

## 5.4 Contracts that cross stages

### Identity and deduplication

- **Repositories:** a repository's identity is GitHub's numeric repository id. The `owner/name` is for display only. A rename keeps the identity; a transfer to another owner ends it (offboarding, §9.3).
- **Debt ids** keep today's shape, `debt:<kind>:<subject>:<hash>` (**VERIFIED** in the ledger). Ecosystem debt puts the repository id inside `<subject>`.
- **Lane B candidate ids:** `cand:<repo-id>:issue:<number>`.
- **Contract ids:** `contract:<producer-repo-id>:<artifact>-><consumer-repo-id>:<pin>`.
- **Dedupe on subject, not wording.** A second observation of the same subject updates the existing record and never creates a new one.

### Dependency-aware admission

- A record may declare `dependsOn` (stable ids) and version floors.
- Admission refuses an item whose dependency is not `resolved`. The item waits in `blocked` and spends no attempts.
- A dependency cycle is a Class C question. The runtime never breaks a cycle itself.
- A dependency on another repository, such as a consumer waiting on a producer release, is read from the producer's published release. It is never assumed.

### Budgets, quotas, model and effort

- **Each domain has a budget per period.** It covers:
  - model calls and tokens;
  - dollars, measured by skill-cost;
  - wall-clock minutes;
  - items in flight.
- **Code caps stay the ceiling.** Today they are `maxDispatchesPerRun` 1, `maxInFlight` 2, `maxAttempts` 2 and `cooldownSeconds` 3600 (**VERIFIED**, `POLICY.yaml` `routing`).
- **Unknown is not unlimited.** When remaining quota or budget is unknown, nothing is admitted.
- **A subscription window shared with interactive use keeps a reserve** for the founder. Admission stops at the reserve.
- **Packets stay model-free.** (**RATIFIED**, STEWARD.md §9, amendment of 2026-08-13: a packet names no model and no harness.)
  - The route picks model and effort at admission, and each attempt records them.
  - `default` and `inherit` are refused (**VERIFIED**: the runner refuses both).
- **No model is escalated automatically.** A route may declare a model ladder only by founder ruling. Otherwise a rejected item retries on the same model and effort, then escalates to the desk.
- **Cost comes from skill-cost, with provenance.** An unmeasured cost is `null`, never `0`.

### Idempotency, interrupted writes, stale authorization

- **Every external effect carries its attempt's idempotency key** in a durable, observable marker: the branch name or the pull-request body. A resumed run can then see whether the effect happened.
- **Intent is recorded before the effect, and the outcome after it.** A resume re-observes external state before deciding anything.
- **After an ambiguous partial write, the run halts and escalates.** It never asks a model to guess what happened.
- **Everything a resume needs is as durable as the ledger.** On 2026-10-27 the operator abandoned the 2026-10-21 run because its builder packet had been lost with the ephemeral local `.gaia/` directory (**VERIFIED**, §16.2). A packet must be stored with the ledger, or be reproducible from ledger content plus a pinned commit.
- **Authorization is re-checked three times:** at lease, before execution, and before each external write.
- **Contention with other writers.** If the target branch or touched paths changed after the attempt's base commit, the attempt is invalidated rather than merged over.
  - The item re-observes and re-queues from the new HEAD.
  - A pull request already open is re-verified against the new base before it is marked ready.
  - If a human or another workflow resolved the subject meanwhile, the item is `superseded` on re-observation.

### Verification and post-integration readback

- **The verifier is a different identity and never sees the builder's reasoning.**
  - **RATIFIED** doctrine.
  - **VERIFIED** in rehearsal: the runner refused the builder's own id, case-shifted or with a zero-width character inserted, offered as the verifier (founder report §5, scenario C).
- **For Lane B, the verifier comes from a different model family** where one is available. This guards against correlated errors.
- **Deterministic gates prove consistency, not usefulness.** A route records any calibration or threshold it relies on. It never changes one.
- **Readback reads what is actually served or consumed:**
  - deployed bytes, hashed against git;
  - the consumer's pin;
  - the published release.

  Readback never trusts a token, a status code or an apply receipt.

### Per-repository merge, release and deploy gates

Landing goes through one adapter per repository, generated from that repository's record (§9.2). An unknown rule means `observe` only.

| Repository | Merge verb | Drafts | What a merge deploys | Adapter ceiling, once its record is complete |
|---|---|---|---|---|
| gaia-skill-tree | merge commit; squash disabled | — | GitHub Pages from `main:/docs` | Tree domain only: `dev/*` integration branch |
| gaia-research | merge commit | — | site deploy on merge: unverified | `draft-pr`; the maintainer merges |
| gaia-skill-heaven | squash; a ruleset blocks merge commits | stay drafts until the owner marks them ready | Pages on push to `main` | `draft-pr` |
| skill-cost | unknown | — | — | `draft-pr` for code; its existing price-refresh job is left alone |
| other `skill-*` | unknown | — | installers read `main` | `draft-pr` |

The merge verbs are **VERIFIED** on 2026-10-27 from the gaia-skill-tree and gaia-skill-heaven agent instructions (the latter also states gaia-research's verb). An "unknown" row stays at `observe` until the repository's record states the rule.

**Always, in every repository:**
- Never merge to a default branch.
- Never tag, release, publish or deploy.
- Never edit `.github/**` or secrets.
- Never apply authorization labels.
- Never use another agent's signature or an auto-merge label.

### Quiet operation and measured cost

- **A quiet tick makes zero model calls**, writes one receipt and adds nothing to the desk. (**RATIFIED** for the Tree: "no-change runs invoke no model", operating model §18.)
- **Cadence is a ceiling on attention**, not a clock that creates work.
- **Everything is metered.**
  - Every tick records its API calls and Actions minutes.
  - Every attempt records its model, its effort and its skill-cost dollars.

## 5.5 Continue or Stop

A run stops when any of these holds:
- no admissible work remains;
- a budget, quota or in-flight cap is reached;
- an envelope boundary would be crossed;
- coverage of a required input is unknown;
- the watchdog reports the domain unhealthy.

Stopping is a normal, quiet outcome.

## 5.6 Coordinator contract and provider probe

**Requirement:** the goal is proactive continuation and exception handling between founder touchpoints, not just a model that accepts build jobs. The runner stays the deterministic authority on admission, leases and state transitions. A coordinator is a host that drives it.

A coordinator may be a scheduled routine, a durable bot, or another long-lived agent. Every candidate meets the same contract:

| Capability | Contract |
|---|---|
| Wake | On a schedule or an event. Every wake starts by reading state; it never starts from memory. |
| Read | Only authorized backlog and state: the domain ledger, policy, authorization records and desk |
| Lease | Only through the runner's CAS lease. Never holds work the runner did not grant. |
| Resume | After lost context, rebuilds solely from the ledger plus durable packets (§5.4). Never from its own transcript. |
| Revisit | Re-checks `blocked`, `deferred` and `awaiting_founder` items on each wake. Re-raises nothing the desk already holds. |
| Ask | Puts decisions on the desk, using the runner's desk format. Never decides them. |
| Fan out | Only within the admitted budget and in-flight cap. Every worker gets explicit model and effort. |
| Record | Every action is recorded through the runner. A coordinator keeps no ledger, queue or memory that others must trust. |
| Hand back | Ends each wake with the run's receipt. Stops on a kill switch, budget exhaustion or an unknown. |

Model-driven coordination is optional and bounded. It may choose *among* admissible actions and draft desk text. It never admits, authorizes, escalates authority or resolves an item.

**Provider probe (go/no-go).** No coordinator or executor is used until it passes every check below in a sandbox repository. Product availability, subscription features and integration compatibility count as **unverified until probed**. Nothing platform-specific is built ahead of a probe, and no candidate is locked in.

| Probe | Pass condition |
|---|---|
| Wake / schedule | Fires on the cadence. A missed fire is visible to the watchdog (§10). |
| Permissions | Holds exactly the declared GitHub scopes. A write outside them is refused by GitHub, not merely avoided. |
| Context loss | Kill mid-run, cold-start, resume: no step repeats and no write is guessed |
| Dispatch / verify | One leased build plus one independent verify, end to end. Model and effort recorded; cost measured by skill-cost. |
| Quota exhaustion | The item goes to `deferred`. Nothing degrades silently onto a weaker model. |
| Kill switch | Disabling stops the next wake and any in-flight effect before its next write |
| Deprovisioning | Removing the host leaves no credential, schedule or state behind, and the ledger shows the release |

---

# 6. Authority model

## 6.1 Three authorities, intersected

Work proceeds only inside the intersection of three authorities:

1. **Domain authority:** what the domain's charter and policy allow.
   - Tree: STEWARD.md, POLICY.yaml, Yggdrasil IV and the Frontier ruling.
   - Ecosystem: its charter, once ratified.
2. **Repository authority:** how changes may land in that repository. This comes from:
   - the repository's own agent instructions;
   - branch protection and rulesets;
   - its merge verb;
   - its human-gated paths.
3. **Item authorization:**
   - a *standing* authorization covers a class of debt, such as one contract's refresh;
   - an *item* authorization covers one Lane B item.

Anything outside the intersection goes to the desk.

Strategy (ENDGAME, Roadmap v5) informs priority but never grants authority. Resemblance to the endgame is not permission.

## 6.2 Classes by lane

| | Lane A | Lane B |
|---|---|---|
| **Class A** (machine-owned) | Deterministic refresh under a ratified standing authorization, such as re-vendoring a contract | Never |
| **Class B** (bounded) | Bounded repair, as a draft PR, checked by an independent verifier | One authorized item, as a draft PR, checked by an independent verifier |
| **Class C** (founder) | Anything touching workflows, secrets, thresholds or policy | Anything unanchored; anything owned by Yggdrasil IV, Meta or Governance; anything needing product judgement |

**RATIFIED** failure policy (operating model §17), unchanged, for both lanes:

| Situation | Action |
|---|---|
| Ambiguity | Escalate A → B → C |
| Missing provenance | Block |
| Failed proof | Do not integrate |
| Scope expansion | Stop and reclassify |
| Sensor failure | Mark coverage unknown |

## 6.3 Authorization records

PROPOSED shape. It reuses the `steward-decision-v1` record and the `founder/steward/decisions/` location; field names are fixed at Stage 1.

| Field | Purpose |
|---|---|
| `id` | Stable id |
| `kind` | `standing` (a debt class or a contract), `item` (one Lane B candidate), or `mandate` (a future Lane B envelope; see below) |
| `subject` | Stable subject id: a contract id or a `cand:` id |
| `contentDigest` | Item kind: sha256 of the issue body and acceptance criteria at the moment of authorization |
| `envelope` | Lane, class, repository, adapter ceiling, allowed paths, budget |
| `authorizedBy`, `authorizedAt` | Founder identity and time |
| `expiresAt` | Required. Item authorizations never run indefinitely. |
| `revoked` | Revocation flag, with a reason |

Rules:

- **Only a record authorizes.** A label, comment, assignee or project field never authorizes on its own; at most it points to a record.
- **Agents may draft a record, never put one into effect.** A record takes effect only once the founder has merged it.
- **Staleness is immediate.** A change to the bound content, an expiry or a revocation makes the authorization stale at once.
- **No `ao:*` label is ratified (VERIFIED, 2026-10-27).** Using labels as pointers to records would need its own ruling.

**OPEN, as part of SE-4:** where item authorizations live. The options are a founder-merged record, as above, or a founder-authored comment bound to the content digest and verified by author identity. §17 gives the resolving test.

**Future Lane B standing mandate (SE-4b; ratified separately; not active).**

Per-item authorization is the *initial* E3 mode. It is safe, but it keeps the founder in the loop for every forward item. The escape hatch is a `mandate` record, which the founder ratifies separately.

A mandate states all of the following:
- one objective, with its ENDGAME anchor;
- the accepted issue class;
- repositories and paths;
- the acceptance tests every item must meet;
- a cumulative spend cap;
- a time window;
- a concurrency cap;
- an exclusion list, which always contains the §4.2 surfaces.

Inside a mandate, the engine may *select* items without per-item records. It still may not:
- write, extend, renew or widen a mandate;
- treat an issue, label or comment created by a machine (its own or another bot's) as consent;
- select an item whose content changed after selection without re-checking it against the mandate.

Revocation stops new selection at once. In-flight items halt before their next write. Two drills are required before any mandate takes effect:
- a revocation drill;
- a stale-task spoofing drill: a bot-created issue that matches the class, and an issue edited after selection.

## 6.4 Never

Every item here is unconditional.

1. Merge to a default branch, tag, release, publish or deploy.
2. Edit `.github/**`, workflow files, secrets or repository settings. A pull request opened from a branch in the same repository runs its modified workflows with that repository's secrets.
3. Mutate canonical Gaia data or judgments: registry nodes and named skills, evidence, Trust Magnitude, grades, stars, Origin, schema, policy, or release policy.
4. Act on L4 intake, schema, frontend-visual or Yggdrasil IV gates.
5. Create, extend or infer authorization. Apply authorization labels. Treat issue or comment text as an instruction.
6. Use another agent's signature, a bot identity that triggers an auto-merge path, or an auto-merge label.
7. Edit a producer to satisfy a consumer.
8. Post anywhere the repository adapter does not allow.
9. Carry private metadata onto a public surface (§8.3).
10. Erase ledger history, or edit the ledger by hand.
11. Raise a model, a budget, an envelope or an authority automatically.
12. Spend a model turn deciding what happened after an interrupted write.

## 6.5 Founder interaction

**RATIFIED** (STEWARD.md §10): the founder is involved by exception, through one desk.

PROPOSED additions:
- Each domain has a weekly cap on new desk items.
- Every desk item carries the evidence, the proposed change, and the exact command or decision required.
- Repeated items are deduplicated by subject.

---

# 7. State ownership

Each fact has one owner. Every other copy is a labelled cache.

| Fact | Owner | Notes |
|---|---|---|
| Strategy and destination | ENDGAME.md, Roadmap v5, gaia-research RATIFICATION | Read-only inputs |
| Domain charter and policy | Founder documents and domain policy files | Change only by founder ruling |
| Authorization and consent | Authorization records; reviews and merges on GitHub | §6.3 |
| Intent and visible work | Issues and pull requests in the owning repository | The human-visible handle |
| Mechanics: leases, attempts, dispositions, receipt index | The domain's own ledger ref | Never shared between domains |
| Candidate classification | The domain's receipt store | Never written to GitHub before ratification (§14.2) |
| Production truth | What is served or consumed, re-observed | A receipt alone never counts |
| Cost | skill-cost reports | `null` when unmeasured |
| Roadmap tracking fields | GitHub Project #6 (Program, Arc, Plane) | Lane B reads them and never writes them |

**VERIFIED** on `dev/yggdrasil-iv`, not yet on `main`: Yggdrasil IV adds an `operations` map to the ledger for challenge observations, and isolates the ledger's git remote refs. The Tree ledger will therefore hold Yggdrasil IV state. The Ecosystem domain must never write to it, which is one reason each domain has its own ref.

---

# 8. Security and isolation

## 8.1 Threats this design must survive

| Threat | Example | Control |
|---|---|---|
| Instruction injection through issues | In a public repository, anyone can open or edit an issue | Issue text is data. Lane B runs only under a founder authorization bound to a content digest. Builders hold no credentials. |
| A workflow edit that reaches secrets | A pull request from a same-repository branch runs its modified workflow with that repository's secrets | Never edit `.github/**`. A workflow fix goes to the desk with a diagnosis. |
| A bot merge path | Codex- or Jules-signed pull requests of under 20 files can auto-merge to `main` (#2175, **OPEN**) | #2175 resolved and verified before any unattended writer. Never use those identities or labels. |
| Consent forged by Gaia's own agents | An agent writes text that reads like approval | Only founder-merged records authorize, and agents cannot put a record into effect |
| Private metadata leaks | A private repository's name, issue title or finding reaches a public log, artifact or digest | §8.3 |
| Credential sprawl | One credential spans many repositories or owners | Least-privilege credentials per domain and per host. No app spanning several owners. |
| Ephemeral state lost | The 2026-10-21 builder packet was lost with the local `.gaia/` directory | §5.4: resumable state is as durable as the ledger |
| Supply-chain risk during verification | Checks run a repository's own code | Sandboxed. No secrets in builder or verifier environments. |

## 8.2 Credentials

- **Builders and verifiers hold no repository write credential.** The driver performs writes after verification. The paused GitHub Agentic Workflow path had this property (**VERIFIED**, decision record `steward-agent-agnostic-execution`).
- **That is a required property, not proof.** Only the driver's privileged step may create a branch, a pull request or a comment.
  - It runs as a separate process or job from any model.
  - It shares no environment, filesystem or tool handle with the model.
  - It takes only the verified artifact and the attempt record as input.
- **Revalidation at the last privileged effect.** Immediately before each write, the driver re-checks:
  - the policy digest;
  - the authorization record and its content digest;
  - the target repository's HEAD;
  - the changed paths, against the envelope.

  Any mismatch aborts the write.
- **Adversarial confinement test**, required before E2 alongside #2175's effective protections:
  - a hostile issue and a hostile worktree try to make a coordinator or builder reach the driver's credential, print it to logs or tool output, or trigger a write;
  - every attempt must fail, and a canary token must never appear in any output.
- **Unknown host capability means no write.**
- **Each host has its own credentials**, scoped to its domain's repositories and actions.
- **Observing public repositories needs no special credential.**

## 8.3 Private-metadata isolation

- **Classify every output channel** as `public` or `private`, from its host and the repository's visibility.
- **Private subjects stay on private hosts.** An item whose subject lives in a private repository is processed only by a domain instance on a private host.
- **Public channels never carry:**
  - private repository names;
  - issue titles, paths or findings;
  - digests of private content. A short private string's hash can be brute-forced.
- **The Tree ledger lives in a public repository.** It can never hold private-scope state.
- **Canary test**, which must pass before any private repository is onboarded:
  1. Plant a unique synthetic string in a private fixture.
  2. Run the full pipeline.
  3. Search every public output for the string: logs, artifacts, pull-request bodies, ledger refs and the desk.

  Any hit fails the onboarding.

This document follows its own rule. The organization has private repositories. None is named here, because this repository is public.

## 8.4 Hosting

**PROPOSED (SE-3).** Hosting is split by capability.

| Capability | Where it runs |
|---|---|
| Observation of public repositories (read-only, zero-model, default token) | The existing public host: gaia-skill-tree Actions, with the domain's own ledger ref |
| Attended execution (envelopes E2–E4) | An attended driver session with the founder present, using its existing authorization |
| Unattended writing across repositories (E5) | Only a host where the write credential is confined |
| Anything in private scope | A private host |

A **write credential is confined** when no workflow outside the domain's own can read it.
- A cross-repository write token stored as a secret in gaia-skill-tree fails that test.
- Any workflow there can be edited by a pull request opened from a branch in the same repository.
- While #2175 is open, a bot-signed pull request can merge without the founder.

A **private host** is created with the same runtime code, its own ledger and its own credentials, as soon as any of these triggers fires:
1. a private repository is onboarded;
2. a needed write credential cannot be confined on the public host;
3. receipts or desk items would carry private metadata;
4. the watchdog cannot be independent on the public host (§10).

A new repository is never a goal in itself.

---

# 9. Repository lifecycle

## 9.1 Discovery

- **Discovery is read-only.** It enumerates the organization's repositories, plus any others explicitly listed, and produces `candidate` repository records.
- **Discovery never observes private content, writes, or onboards.**

## 9.2 Onboarding: explicit and opt-in

A repository joins a domain only through a repository record approved by the founder, and by the repository's maintainer where that is someone else.

| Field | Meaning |
|---|---|
| `repoId`, `fullName` | The numeric id (the identity) and the display name |
| `visibility` | `public` or `private`. Private requires a private host. |
| `role` | What the repository is for |
| `profile` | `observe` (default), `draft-pr`, or `integration-land` (Tree only) |
| `mergeVerb`, `draftsStayDraft`, `integrationBranches` | The landing rules |
| `mergeDeploys` | Whether a merge deploys anything, and what readback proves it |
| `requiredChecks` | The repository's own fast checks |
| `humanGatedPaths` | Paths that need human review whatever their class |
| `forbiddenPaths` | Always includes `.github/**` and secrets |
| `budget` | The repository's share of the domain budget |
| `completionProof` | Which re-observation closes an item |

Onboarding steps:
1. The record is merged.
2. A first observe run reports every unknown.
3. The founder reviews it.
4. The profile may be raised later, by ruling.

An unknown field means `observe`.

## 9.3 Offboarding

- **Removing the record stops observation at the next tick.**
  - Leases are released.
  - Open pull requests stay with their owners and appear once on the desk.
  - Ledger history is kept.
- **Archival, deletion or transfer offboards automatically.** It is detected by numeric id and the desk is notified. A transfer is never followed.

---

# 10. Observer independence

**The requirement, with evidence:**
- **Unread red schedules (POINT-IN-TIME).** A daily cross-repository sync was red for 95 runs, and a weekly check for 26 runs. Nobody read either.
- **A six-day stall (VERIFIED).** A Steward run sat awaiting action from 2026-10-21 until an operator abandoned it on 2026-10-27.

Steward cannot be the last line of defence for its own liveness.

**PROPOSED (SE-7):** a zero-model watchdog that:
- **runs on a separate host and scheduler** from the domains it watches, such as a scheduled workflow in another public Gaia repository;
- **reads only public, durable signals that exist today**, which work even while daily observation uses `--ledger local`:
  - the Actions run list for `steward.yml`: its schedule, run times and conclusions;
  - the run's uploaded artifacts `steward-full` and `steward-receipts` (30-day retention, **VERIFIED** in `steward.yml`), as the receipt heartbeat;
  - for full runs only, the ledger ref's commit time, generation, leases and item ages;
- **alerts through a channel that does not depend on the observer:** one issue in its own host repository, edited in place;
- **stays silent while everything is healthy.**

**Three signals, never equated.** Each answers a different question, and each alerts on its own:

| Signal | Question it answers | Alert when (PROPOSED) |
|---|---|---|
| **Run presence** | Did the observer run at all? | No `steward.yml` run within twice its cron cadence: a missed schedule, a disabled workflow, or an Actions outage |
| **Receipt** | Did the run observe with full coverage? | The run is green, but its receipt artifact is missing, malformed, or reports unknown or partial coverage. A green workflow is not coverage. |
| **Ledger progress** | Is leased work moving? | A run `awaiting-action`, or an item `building`, older than 24 h. That is the runner's own threshold, `STUCKBUILDINGSECONDS` (**VERIFIED**, `fullrun.py`). Also: a lease past expiry by more than one TTL. |

**Shared failure domain.** A watchdog in another Gaia repository is independent of the observed *workflow and repository*, but not of the GitHub platform:
- an Actions-wide outage, an organization-level Actions or billing stop, or a revoked token can silence both at once;
- the watchdog therefore also alerts on its *own* missed run, through the issue it edits, so its silence is visible on the next run;
- a heartbeat outside GitHub is **OPEN** (§18). No new service is built ahead of evidence that a platform-wide silence went unnoticed.

**Drills:**
- **Missed schedule:** disable the observed workflow. The watchdog alerts within twice the cadence, and clears after recovery.
- **Green but blind:** a run that uploads no receipt. The watchdog alerts on the receipt signal.
- **Stuck item:** a sandbox ledger with an item `building` past the threshold. The watchdog alerts on progress only.

**OPEN:** across the 2026-10-23 and 2026-10-27 resumes, the runner's 24-hour stuck escalation did not move the item off `building`. That may be by design, because adoption re-offers the same idempotency key, or it may be a defect. The handover's Stage 1 settles which.

---

# 11. Economics

**RATIFIED doctrine** (STEWARD.md §11), in order of preference:
1. Deterministic.
2. Cheap classification.
3. Bounded agent.
4. Strong verifier.
5. Founder.

**PROPOSED extensions:**

- **Detection is the cheapest win.** Every POINT-IN-TIME incident in §16.4 was detectable with zero model tokens. Most of its cost was latency.
- **Spend follows verified value.**
  - Admission ranks admissible items by priority × estimated probability of verified success ÷ expected cost.
  - Once enough history exists, expected cost is the measured `E[cost | verified]` for each route. Until then, conservative fixed caps apply.
- **Premium context is spent only on synthesis.** Cheap workers sweep and diagnose. The driver is zero-model.
- **Budgets are hard.** Exhausting a budget stops the domain. It never borrows from the next period or from another domain.

**Weekly measures, per domain:**

| Measure | What is counted |
|---|---|
| Verified outcomes | Lane A items `resolved`; Lane B items merged and re-observed, split into `direct` and `indirect`. Objectives advanced are counted separately from items closed. |
| Reliability | Verifier overturn rate; readback failures; rollbacks; hours of unknown coverage |
| Cost | skill-cost dollars per verified outcome; model cost of quiet ticks (target 0) |
| Founder load | Founder minutes per verified outcome (self-reported); desk items; re-prompts between steps already permitted (target 0) |
| Latency | Time to detect; time from detection to a verified outcome |

**Objective.** Maximise verified endgame progress and Lane A reliability, subject to:
- floors on reliability;
- ceilings on cost;
- ceilings on founder load.

No single scalar is optimised, because a single scalar invites gaming.

---

# 12. Autonomy progression

**Principle:** authority contracts automatically, and expands only by founder ruling on measured evidence.

| Envelope | Allowed | Entry conditions (measurable) | Failure boundary (automatic demotion) |
|---|---|---|---|
| **E0** Foundation | Reconcile state and define records. No new runtime behaviour. | Yggdrasil IV is on `main`; `main` is verified | — |
| **E1** Observe | Zero-model, read-only observation; desk only | Records validated; canary and drills defined | Any model call, or any write beyond the domain's own receipts and ledger |
| **E2** Attended execution | One Lane A item at a time, as a draft PR, with the founder present; the maintainer merges | #2175 resolved and verified; provider probe (§5.6) and confinement test (§8.2) passed; one standing authorization | Any boundary breach: back to E1 |
| **E3** Attended progress | Adds one Lane B item at a time, under item authorization. Selection inside a standing mandate (§6.3) needs its own ruling and drills. | Classification contract ratified and evaluated; E2 definition of done met | Fabricated anchor, an item owned by Yggdrasil IV admitted, or a stale authorization acted on: back to E1 |
| **E4** Generalised | A second repository or host onboarded with no engine change | E3 definition of done met; canary passed for any private scope | Engine fork needed, or any leak: back to E1 |
| **E5** Unattended | Scheduled operation of the E2–E4 envelopes without the founder present. Draft PRs only; never merge. | Promotion window met; watchdog live; credentials confined | Any breach; a watchdog alarm unresolved for twice the cadence; a budget overrun: back to E1 |

**Promotion window for E5.** These defaults change only by ruling. Over four consecutive weeks at E3 or E4, all of the following must hold:
- no unauthorized writes;
- no private-metadata leaks;
- no readback failure left open;
- a verifier overturn rate below 10 %, over at least ten verified outcomes;
- quiet ticks at zero model cost;
- no re-prompt between steps already permitted;
- every watchdog drill passed.

Demotion is automatic and immediate. Re-promotion needs a new ruling.

**"Draft PRs only; never merge" is the *current* autonomy ceiling, not a permanent law.**

If the long-term goal ever needs end-to-end permissions, they arrive only through a separate, founder-gated ruling that is:
- narrow: per repository, per debt class, with a rollback path;
- grounded in E5 evidence;
- conditional on #2175-grade merge authorization being bound to the head SHA.

Nothing in this document grants them.

---

# 13. Governed self-improvement

**RATIFIED basis:** #2001's weekly rhythm and its retro taxonomy.

**PROPOSED rules:**
- **At most one improvement pull request** per domain per week.
- **An improvement needs evidence:** three occurrences of the same class of miss, or one high-impact miss.
- **Improvements to sensors, routes and tests land as ordinary reviewed pull requests.** Changes to policy, budgets, caps, envelopes or authority are Class C.
- **The improvement lane can never change its own limits or authority.**

**Worked examples** (POINT-IN-TIME; class names as #2001 used them on 2026-10-27):

| Miss | #2001 class | Improvement |
|---|---|---|
| The cross-repository sync failure | `missed_transport_or_schedule` | An automation-health sensor |
| The stale retrieval index | `missed_no_sensor` | A contract-freshness sensor |
| Skill Heaven's `stale: true` flag was emitted and never read | A signal with no consumer | Consume the flag |

---

# 14. Endgame alignment and the Lane B classification contract

## 14.1 Alignment rule

**ENDGAME.md sets the direction.**

- **A `direct` item names the ENDGAME section it advances and quotes the sentence.** Cite it as `ENDGAME §<n> <heading>`, using ENDGAME's own sections:

  | ENDGAME section | Heading |
  |---|---|
  | §2 | The Gaia Primitive: Identity, Structure, Indices, Observations, Frontend Projections, Prestige |
  | §3 | Tree One: Yggdrasil |
  | §4 | Tree Two: Arbor I |
  | §5 | The Hell-Heaven Model |
  | §6 | Hell-Heaven Index |
  | §7 | Arbor Nodes |
  | §8 | Arbor Edges |
  | §9 | Skill Heaven (umbrella), Skill Zero (launcher), Arbor (axis) |
  | §10 | Gaia CLI |
  | §11 | Gaia Skill Tree Frontend |
  | §12 | Future Trees |
  | §13 | The End-State Gaia Model |

  No new identifiers are coined.
- **Alignment has three modes.** Enabling work counts, but its path must be traceable:

  | Mode | Meaning | Required evidence |
  |---|---|---|
  | `direct` | The item itself advances an ENDGAME objective | `ENDGAME §<n>` and the quoted sentence |
  | `indirect` | The item is an indispensable dependency, such as a contract, test harness or foundational capability, of an *approved* item that is `direct` | The dependency chain as stable ids, each link a recorded `dependsOn` on an approved item, ending at a `direct` item |
  | `none` / `unknown` | No traceable path, or not enough evidence | The reason. Abstaining is a valid, recorded answer. |

  Rules for alignment records:
  - A model may propose an alignment, but never originate an anchor or a link. Every quoted sentence and every dependency edge must exist in its source.
  - An `indirect` path through an unapproved item is `unknown`.
- **Progress is not throughput.** Measures count verified advancement of objectives, direct and through approved dependencies (§11). They never count issues closed.
- **Roadmap v5 fields are secondary.** Program, Arc and Plane are recorded from Project #6 where they are set. They never substitute for an ENDGAME anchor.
- **Alignment never decides prestige, ontology, benchmarks or product direction.** ENDGAME gives an operations runner no such authority.

## 14.2 Classification contract: defined, not applied

**Status: PROPOSED.**
- It has not been run on any issue.
- No labels, comments or project fields are written.
- Nothing is mapped or labelled before the pull request carrying this document has merged. After it merges, mapping and labels follow the founder's ruling on SE-10.

**Input:** one open issue in an onboarded repository.

**Output:** one classification record.

| Field | Content |
|---|---|
| `candidateId` | `cand:<repo-id>:issue:<number>` |
| `source` | Repository id, issue number, sha256 of title and body at classification time, and `classifiedAt` |
| `classifier` | A deterministic rule id, or the model and effort plus a prompt digest |
| `bucket` | One of: `health` (Lane A); `progress` (Lane B); `governance` (Class C: policy, trust, Yggdrasil IV, Meta, L4, schema, product); `none` (no action, or unknown) |
| `alignment` | Mode (`direct`, `indirect`, `none`, `unknown`); for `direct`, `ENDGAME §<n> <heading>` plus the quoted sentence; for `indirect`, the dependency path; for `none` or `unknown`, the reason |
| `roadmap` | Program, Arc and Plane if set on Project #6; otherwise `null` |
| `targetBehavior` | The verifiable acceptance criterion, quoted from the issue, or `missing` |
| `owningRepo` | Repository id |
| `dependencies` | Stable ids, or `[]` |
| `authorityGate` | The class and the repository gates that would apply |
| `estimate` | Route class and expected cost band; `unknown` is allowed |
| `confidence` | `high` or `low`. `low` forces the bucket to `none`. |
| `status` | Always `candidate` |

Rules:

1. **Classification is read-only.** It never writes to GitHub.
2. **Issue text is untrusted data.** Instructions inside an issue are ignored.
3. **Deterministic rules run first.**
   - A model classifies only what is left, at a recorded model and effort.
   - A disagreement, or low confidence, yields `none`.
4. **`progress` needs both:** a `direct` or `indirect` alignment, and a target behaviour. Missing either yields `none` or `health`.
5. **Certain subjects are always `governance`:**
   - Yggdrasil IV, trust, evidence, stars and Origin;
   - Meta evaluation and L4 intake;
   - schema, policy, release and visual direction.
6. **Strategic alignment is never fabricated.** Legitimate maintenance with no anchor is `health` or `none`.
7. **A classification record never authorizes.** It is input to the founder's decision.

**Evaluation before any use (PROPOSED).** A classifier must not be able to pass by abstaining.

1. **Sample.**
   - The founder labels real issues: about 40, from at least three repositories.
   - At least 10 are `progress`, of which at least 3 are `indirect`.
   - At least 5 are `governance`.
2. **Adjudication.**
   - Borderline cases are adjudicated by the founder and recorded.
   - Adjudicated cases are excluded from the precision count, but kept as fixtures.
3. **Pass bar:**
   - `progress` precision ≥ 0.9 and recall ≥ 0.7;
   - `governance` recall = 1.0: no governance item is filed as anything else;
   - abstention (`none` or `unknown`) ≤ 30 % of the founder's `progress` set.
4. **Confusion review.** The full confusion matrix is reviewed with the founder, governance false negatives first.

Below that bar, Lane B stays at E1. This PR performs no bulk mapping or labelling.

---

# 15. Relationships

| Party | Role (**RATIFIED** unless marked) | Interface with Steward |
|---|---|---|
| **Gaia Frontier** | Discovers outside the ecosystem (Frontier ruling) | The Ecosystem domain never scans outside Gaia's own repositories. Verified challenges reach the Tree domain as Yggdrasil IV defines. |
| **Gaia Meta** | Evaluates: triage, appraisal, focused verification | Lane B never evaluates. Items Meta owns are `governance`. |
| **Governance** | Decides: L4 intake, Yggdrasil IV gates, founder rulings | Owns all Class C items and all authorization records |
| **Yggdrasil IV** | Challenge, degradation and recovery: reversible trust governance | Ecosystem work consumes only released, ratified Yggdrasil IV contracts. It never edits `dev/yggdrasil-iv`. Neither side's acceptance tests depend on the other. |
| **Tree domain** | Steward for gaia-skill-tree | A peer domain on the same runtime, and the governing Steward domain for gaia-skill-tree |
| **Skill Heaven programme** | Runtime products | A cohort repository. Steward never changes its merge rules or floors. |
| **gaia-orchestrator** | Founder-directed multi-PR campaigns | PROPOSED: a campaign may use the runtime's admission, leases and verification, and keeps its own authority from the founder's mission. See the SE-2 alternative. |

---

# 16. Evidence reconciliation

## 16.1 Sources

- **Canon on `main` at `b0f6d9e`:**
  - STEWARD.md, STEWARD-OPERATING-MODEL.md, `steward/POLICY.yaml`;
  - ENDGAME.md, Roadmap v5 and the Yggdrasil IV ratification;
  - the Steward Full architecture handover (2026-10-20) and founder report (2026-10-21);
  - `steward/decisions/`.
- **The Frontier ruling:** #2148, LOCKED 2026-10-26. Its file is on `dev/yggdrasil-iv`.
- **Remote refs read on 2026-10-27:** `steward/ledger`, `dev/steward-integration` and `dev/yggdrasil-iv`.
- **Reports:**
  - architecture reports v2 and v3 (2026-10-27; session artifacts, not committed);
  - the external proposal "Gaia Steward: Ecosystem Evolution Proposal" (2026-10-27).
- **Issues, read on 2026-10-27:** gaia-research#311, gaia-skill-tree#2158, #2001 and #2175, and gaia-skill-heaven#216.

## 16.2 Corrections to earlier findings

| Earlier claim | Correction | Status |
|---|---|---|
| v1–v3: `refs/heads/steward/ledger` was never pushed | It exists: generation 72 at `33af04c` (2026-10-27T14:58:56Z), with 72 commits since 2026-10-21. The error came from a truncated listing. | VERIFIED |
| v3: "no executor ever picked up the build" | **The executor existed.** GitHub Agentic Workflow builders and verifiers for four engines arrived in `dbdf986` (2026-10-21). **It was paused the same day.** The founder paused it in `ecb6cfa` with the note "subscription-driven Claude routine replaces gh-aw GitHub inference". **Whether that replacement exists is unverified.** | VERIFIED / OPEN |
| Ledger runs record `trigger: scheduled` | **This is only the CLI flag**, not proof that a schedule fired. **The only live schedule is `steward.yml`**, daily at 07:10 UTC. It runs `--observe --ledger local` and never writes the remote ledger. **The later writes came from unidentified CLI hosts:** the ledger writes on 2026-10-23 and 2026-10-27 came from CLI invocations whose host is unknown. | VERIFIED / OPEN |
| The stuck run | Run `run-20261021T174049Z-36e4510c` waited on one `agent.build` from 2026-10-21. An operator abandoned it at 2026-10-27T14:58:56Z, recording: "builder task packet lost with ephemeral .gaia/ and its Class C desk superseded by merged PR #2147". The work item is left `building` on purpose, for adoption by the next run. 99 lane entries are still `queued` from 2026-10-21. | VERIFIED |
| Decision ledger: "no PR in this table is merged" | The decision-7 implementation (`steward-full.yml` plus eight compiled agent workflows) is on `main`, paused. The decision ledger's lifecycle columns are stale. | VERIFIED |
| v3: "nine repositories, all public" | The nine are public. The organization has 17 repositories, 5 of them private and 1 of those archived. The nine are a pilot cohort, not the boundary. | VERIFIED |
| v2: the control plane "must live in a private repository" | That premise came from observing private repositories across several owners. The public cohort doesn't need it. The real triggers are credential confinement and private scope (§8.4). | Resolved here |
| v3 D1: widen the Tree Steward's charter | It conflicts with the Frontier ruling's tree-related scope. A separate domain replaces it (SE-1, SE-2). | Resolved here |
| Ledger schema | Yggdrasil IV adds `operations` to the ledger and isolates its remote refs. This is on `dev/yggdrasil-iv`, not yet on `main`. Every domain design starts from the post-IV ledger. | VERIFIED |
| v3: "Steward watches only one node", taken to mean no detection at all | The Tree already has a `ci_failure` sensor fed by `gh run list` on `main` (`sensors_ci.py`, `scripts/steward_collect_ci_runs.py`). What it lacks is detection of **silence** and **failed trust ramps**, any coverage of other repositories, and a consumer for Class B debt while the lane has no executor. | VERIFIED |

## 16.3 Contradictions between v2 and v3

| Question | v2 | v3 | Resolution |
|---|---|---|---|
| Who owns ecosystem observation | A thin fleet layer separate from Gaia Steward | Gaia Steward, with its charter widened | Neither. A shared runtime with a separate Ecosystem domain (SE-1, SE-2). **Test:** the second domain runs without an engine fork (Stage 5). |
| Where it runs | A private control repository | Inside `steward.yml` | Split by capability. Observation runs on the public host; write-capable driving runs where credentials are confined; a private host is created on a trigger (SE-3). **Test:** the credential-confinement check and the canary (§8). |
| Scope | 30 repositories across several owners | 9 public repositories | The Gaia ecosystem is the set of opted-in Gaia repositories, with the nine as the pilot cohort. Other owners' repositories form other domains and are never observed from a public Gaia host. |
| Executor | A pull-based subscription executor | A scheduled Claude Code cloud task | The executor is an adapter, chosen by probe (SE-6). The existing gh-aw adapter is paused, not deleted. **Test:** one leased build and one verify complete end to end on the candidate, with explicit model and effort recorded. |
| Observer liveness | "Steward observes Steward" | automation-health also covers the Tree's own workflows | Both are needed and neither is enough. Add an independent watchdog (SE-7). **Test:** the disable drill (§10). |

## 16.4 Point-in-time findings (2026-10-27; re-verify before use)

| Finding | Source | Verification |
|---|---|---|
| gaia-research `craft-registry-resync`: 0 of 95 runs green since 2026-07-27, failing at the gaia-skill-tree checkout | v3 | Verified by the reviewer |
| gaia-skill-tree `verify-evidence`: 26 consecutive red runs | v3 | Latest runs verified; the streak was reported by a helper |
| gaia-skill-heaven retrieval index: pinned to Tree v8.4.1 and refreshed by hand. 51 skills cannot be summoned; 7 removed skills are still ranked. | gaia-skill-heaven#216 | Verified |
| gaia-skill-heaven `arbor-identity.json`: 129 of 354 content hashes differ from upstream | v3 | Reported by a helper |
| The vendored `check-lexicon.ts` in gaia-skill-tree is behind its upstream | v3 | Verified |
| gaia-research `generate-templates.ts` pins a deleted branch and silently falls back | v3 | Verified |
| 5 of the 6 `skill-*` repositories have no CI; their installers read `main` | v3 | Reported by a helper |
| Healthy pattern: Skill Heaven CI validates its emitted ledger records against gaia-research's live `ledger.ts` | v3 | Verified |

## 16.5 Issue map

| Issue | Role in this architecture |
|---|---|
| gaia-research#311 (Gaia AO EPIC and RFC) | The umbrella. Its phases map to the stages: G0 safety → Foundation; G1 observe → Observation; G2 one governed action → Execution; G3 expand → Progress and Generalization; G4 improve → Autonomy, with governed self-improvement. |
| gaia-skill-tree#2158 (economic orchestration) | Re-scoped as the Admit stage: envelopes, budgets, quota reserve, explicit model and effort, telemetry. Its deterministic coordinator is the existing zero-model runner. |
| gaia-skill-tree#2001 (weekly rhythm, retro taxonomy) | The Learn stage, and governed self-improvement (§13) |
| gaia-skill-tree#2175 (harden bot PR merge authorization) | A precondition for E2 and above |
| gaia-skill-heaven#216 (stale retrieval index) | The first Lane A outcome candidate at E2, if the index is still stale |

---

# 17. Proposed founder rulings

Each ruling below gives the proposal, the alternatives, the test that decides between them, and the default that applies until the ruling is made.

### SE-1 — Shared runtime, separate domain authority

- **Proposal:**
  - The Steward runtime is a shared mechanism.
  - Authority lives in domains.
  - The Tree domain is unchanged.
- **Why:** the Frontier ruling scopes the Tree Steward. Duplicating the runtime would duplicate its hardest-won properties.
- **Alternatives:** (a) widen the Tree charter (v3 D1); (b) build a separate engine or fleet platform (v2).
- **Resolving test:** a second domain runs on the runtime with configuration-only changes (Stage 5). If it needs an engine fork, revisit this ruling.
- **Default until ratified:** nothing changes. The Tree Steward continues as ratified.

### SE-2 — Ecosystem domain charter

- **Proposal:** a domain over opted-in Gaia repositories:
  - it writes only to its eight cohort repositories, and reads gaia-skill-tree only as a producer;
  - Lanes A and B, with a Class B ceiling on forward work;
  - no outward scanning, no evaluation, no canonical decisions;
  - it is the governing Steward domain in its repositories (other writers continue; §3.2).
- **Alternatives:**
  - (a) Lane B stays outside Steward. Founder-directed campaigns (gaia-orchestrator) use the runtime's admission, leases and verification, and Steward runs Lane A only.
  - (b) No Ecosystem domain. Each repository grows its own CI checks for its contracts.
- **Resolving test:** at Stage 4, compare founder interventions per verified Lane B outcome with the same measure for a comparable orchestrator-run campaign. If Lane B does not reduce founder load at equal reliability, adopt (a).
- **Default until ratified:** no Ecosystem domain. Only the reconciliation and Tree-scoped observation in the handover's first mission go ahead.

### SE-3 — Hosting by capability (§8.4)

- **Alternatives:** (a) a private control repository from day one (v2); (b) everything inside gaia-skill-tree (v3).
- **Resolving test:**
  - **Credential confinement:** list every workflow that can read each write-capable credential on the host. Any reader outside the domain fails the host.
  - **Canary:** the private-metadata canary must pass.
- **Default until ratified:** observation only.

### SE-4 — Authorization records (§6.3)

- **Proposal:**
  - Standing authorizations are founder-merged decision records.
  - Item authorizations are founder-merged records, unless the alternative below passes its test.
- **Alternative (OPEN):** item authorizations as a founder-authored comment, bound to the content digest and verified by author identity.
- **Resolving test:**
  - A spoofing drill must be refused in every case: a non-founder account, a comment edited after the fact, and an issue body changed after authorization.
  - Founder minutes per authorization are measured for both forms.
- **Default until ratified:** no Lane B execution.
- **SE-4b, future and ratified separately:** a Lane B standing mandate (§6.3). It is proposed only after E3 succeeds in per-item mode. Its resolving test is the revocation drill plus the stale-task spoofing drill, followed by measured founder minutes per verified forward outcome compared with per-item mode.

### SE-5 — Autonomy ratchet and promotion window (§12)

- **Alternatives:** time-based promotion; envelopes set per repository only.
- **Resolving test:** run E2–E4 for the window. If the measures cannot be collected, the window cannot be passed.
- **Default until ratified:** no promotion beyond E1.

### SE-6 — Coordinators and executors chosen by probe (§5.6)

- **Proposal:**
  - The coordinator contract and the runtime's `agent.build` and `agent.verify` actions are the only interfaces.
  - Every host is an adapter behind them, with no vendor lock-in. Candidates include GitHub Agentic Workflows (paused), a scheduled agent routine, a durable chat-platform bot and a Pi harness (#2158).
- **Resolving test:** the full provider probe in §5.6, run on the candidate.
- **Default until ratified:** attended execution only.

### SE-7 — Independent watchdog (§10)

- **Alternative:** rely on the Tree Steward's own sensors. They cannot detect a run that never happens.
- **Resolving test:** the three drills in §10.
- **Default until ratified:** no independent liveness check, as today.

### SE-8 — Re-scope existing threads (§16.5)

- **Default until ratified:** the threads continue as written. This document only links them.

### SE-9 — Pre-existing ledger state

- **Facts (VERIFIED, 2026-10-27):**
  - The stuck run was abandoned by operator disposition.
  - One Class B trust-calibration work item stays `building` for adoption by the next run.
  - 99 lane entries have been queued since 2026-10-21: 50 trust-calibration and 49 unused-import.
- **Proposal:**
  - Respect the operator's disposition.
  - Before the next run adopts anything, re-observe each subject on post-Yggdrasil-IV `main`, and rebuild any packet from that fresh observation.
  - Supersede, with a reason, every entry the fresh observation does not reproduce.
  - The trust-calibration route only prepares commands for human approval and never writes to the registry (**VERIFIED**, `POLICY.yaml`). It is adopted only if its envelope is unchanged after Yggdrasil IV.
  - Never erase history.
- **Alternative:** adopt and build as recorded.
- **Resolving test:** a fresh observe on post-IV `main` either reproduces each queued debt or does not.
- **Default until ratified:** follow the operator's disposition, plus the freshness invariant in §5.3.

### SE-10 — Lane B classification contract (§14.2)

- **Alternative:** no automated classification; the founder hand-picks items.
- **Resolving test:** the founder-labelled sample.
- **Default until ratified:** not applied.

---

# 18. Open questions

1. **Who invoked the ledger runs on 2026-10-23 and 2026-10-27?** The actor is `cli` and the host is unidentified. Does a subscription-driven routine exist, and where is it defined? Answer this before adding any schedule.
2. **Is the paused gh-aw executor path to be retired, or kept as one adapter?** The Frontier ruling authorizes cleanup of superseded adapters within Yggdrasil IV.
3. **Where should item authorizations live?** See the SE-4 alternatives.
4. **Is Lane B a Steward lane, or an orchestrator capability that uses the runtime?** See the SE-2 alternative.
5. **Should any private repository be observed, and when?** (§8.4)
6. **Where should daily observation results live?** Should `steward.yml`'s daily observe write a ledger ref, or stay `--ledger local` with a separate receipt store?
7. **Which §16.4 findings still hold** after Yggdrasil IV lands?
8. **Do the post-Yggdrasil-IV versions of STEWARD.md, POLICY.yaml or the ledger code change any contract in §§5–7?**
9. **Why did the 24-hour stuck escalation not fire?** Across the 2026-10-23 and 2026-10-27 resumes it left the item on `building`. Is that by design or a defect? (§10)
10. **Is a heartbeat outside GitHub needed?** It would cover platform-wide silence. Decide from evidence, not in advance. (§10)
