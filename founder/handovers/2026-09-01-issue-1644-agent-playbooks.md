# Agent playbooks — replacing CLI-verb execution as the agent's method

**Status:** proposed method contract. No runtime, schema, registry, CLI, or frontend changes in this planning PR.
**Issue:** [#1644](https://github.com/gaia-research/gaia-skill-tree/issues/1644)
**Supersedes the issue as filed.** #1644 proposes wrapping the CLI in a typed tool/MCP layer. That is the wrong first move, for a reason the investigation below makes concrete: the tool layer would faithfully re-expose a method whose *instructions are wrong*. Transport is not the defect.

---

## 1. Stack baseline

This plan is stacked on the open restoration stack, in merge order:

1. [#1668](https://github.com/gaia-research/gaia-skill-tree/pull/1668) — `dev/yggdrasil-iii-newmeta` → `main`
2. [#1669](https://github.com/gaia-research/gaia-skill-tree/pull/1669) — `dev/steward-sensors-fleet` → `dev/yggdrasil-iii-newmeta`
3. [#1667](https://github.com/gaia-research/gaia-skill-tree/pull/1667) — `fix/trust-magnitude-full-recalibration` → `dev/steward-sensors-fleet`
4. [#1672](https://github.com/gaia-research/gaia-skill-tree/pull/1672) — `dev/yggdrasil-iii-fusion-score-plan` → `fix/trust-magnitude-full-recalibration`
5. This planning branch → `dev/yggdrasil-iii-fusion-score-plan`

Top of stack at time of writing: `294729658`.

---

## 2. The distinction being ratified

> **Human → CLI. Agent → playbook.**

The `gaia` CLI is not being deprecated, reduced, or hidden. It stays exactly what it is: the canonical, programmatic, schema-safe mutation interface, and the surface a human maintainer drives directly.

What changes is what an **agent** is handed. Today an agent is handed the same 36 `gaia dev` verbs a human gets, plus 65 skill documents describing when to use them. That is a *primitive* interface: it says what you *can* do and leaves *what you should do, in what order, with what proof* to be re-derived from prose on every run.

A playbook is the unit that carries the method. The CLI keeps carrying the mutation.

---

## 3. What already exists

Nothing in this plan is greenfield. Four assets already carry most of the weight, and the plan is mostly *generalization plus pruning*, not construction.

| Asset | Where | What it already gives us |
|---|---|---|
| **The Steward packet contract** | `founder/steward/POLICY.yaml`, `founder/STEWARD.md` | `objective`, `allowedPaths`/`allowedCommands`/`forbiddenPaths`, `stopConditions`, `proof`, `capability`. This is already a playbook schema — scoped to maintenance debt. |
| **Class A / B / C authority model** | `founder/STEWARD.md` §§ 260–340 | A = mechanical and reversible, closes itself, zero tokens. B = interpretation inside a narrow envelope with hard proof. C = governance, waits for the founder. |
| **The rolling lane** | `POLICY.yaml` `routing.lane`, `gaia steward lane` | `maxInFlight`, `maxAttempts`, `cooldownSeconds`, receipts, verdicts. An escalation target that actually exists. |
| **The routine library** | `founder/steward/routines/*.md` | Harness-neutral prose contracts with "What it is for" / "Envelope to grant" / "Stop conditions" / "Done means" / "Founder notes". |

Two rulings already on the books constrain the design and must not be re-litigated:

- **Capability is prose, never a gate** (founder ruling 2026-08-13, `STEWARD.md` § Amendment). A packet names no model and no harness. "A stronger model is never mistaken for a wider envelope." Authority is machine-enforced in policy; capability is a scheduling hint that gates nothing.
- **Cadence is a ceiling on attention, not a clock that creates work** (`routines/README.md`). A playbook that wakes, finds nothing, and stops has done its job perfectly.

---

## 4. Diagnosis — why agents stumble

Investigated with an 8-scout Haiku fan-out (`gaia-research/skill-scout-fleet`, Pareto ×2, read-only, RRF k=60). Every finding below was **re-verified by hand** against the live parser before being written down; two scout claims were wrong and are corrected in § 4.1.

RRF consensus hotspots (found independently by 3 scouts each): `META.md`, `src/gaia_cli/commands/dev/helpers.py`, `src/gaia_cli/commands/dev/calibrate.py` — exactly the calibration surface where failures were reported.

| # | Finding | Evidence | Why it breaks an agent |
|---|---|---|---|
| **D1** | The root agent contract teaches a command that cannot execute. | `CLAUDE.md:149` shows `gaia dev fuse <id> --name … --type ultimate --prereqs …`. `gaia dev fuse --help` accepts only `--name --description --prereqs --named-capstone --suite-components`. There is **no `--type` flag on fuse**, and valid types are `['basic','fusion']` (`registry/schema/meta.json`). | Every agent that reads CLAUDE.md inherits a broken invocation. A strong model recovers by reading `--help`; a weaker one copies the documented example and flails on `unrecognized arguments`. |
| **D2** | The word **grade** denotes two different scales ten lines apart in the same file. | `META.md:104` — Evidence Grade from a row's `trustNumber`: S ≥ 90, A ≥ 80, B ≥ 60, C ≥ 40. `META.md:114` — Overall Trust Grade from Trust Magnitude: S ≥ 250, A ≥ 100, B ≥ 50, C ≥ 20. `gaia dev evidence --help` states only the second. | An agent reading META.md:104 and passing `--trust 90` expecting S silently gets B. Mis-calibration with no error. This is the single most likely mechanism behind reported calibration failures. |
| **D3** | Stale flag taught as primary in agent-facing docs. | `--class` is `[DEPRECATED] Use --trust instead` in the parser and absent from live `dev evidence --help`. Still taught as the primary form in `DEV.md:95` and `.claude/skills/gaia-meta-audit/SKILL.md:91` (and its `.agents/` mirror). | Agents learn the retired spelling from the documents written for them. |
| **D4** | Authorization failures state the violation, not the remedy. | `commands/dev/verify.py:31-35`; gating at `commands/dev/__init__.py:912-942` over the mutating verb set. | "You are not a Verifier" is a dead end. Nothing says a 4★+ named skill is the path, or that CI allowlists bot actors. |
| **D5** | Preflights stop at the first failure. | `commands/dev/helpers.py::_run_dev_preflights` runs checks sequentially and returns on first error. | The agent fixes one thing, re-runs, hits the next, re-runs. It can never see the dependency set at once, so it cannot plan. Cost scales with the number of latent violations. |
| **D6** | Load-bearing invariants are enforced *after* the fact, by CI, not at write time. | Guard E (`docs-cohesion.yml`) requires `docs/graph/` regeneration whenever `registry/nodes/` or `registry/named/` changes; `branch-scope.yml`; `meta-guard.yml` verifier + apex gates; `validate_timelines.py`; `validate_redaction.py`. | An agent can complete a locally "successful" curation whose PR is structurally unmergeable. No CLI verb warns at the moment of the write. |
| **D7** | 65 skills, with large overlapping clusters and shipped aliases. | 7 curation variants (`gaia-curate{,-chain,-dynamic,-trending}`, `gaia-bot-curate`, `gaia-draft-curate`, `gaia-quick-curate`); 6 `ev-*` phases; 6 `fp-*` phases. `evidence-verification-pipeline` is an alias of `ev-pipeline`; `gaia-tm-inspect` of `trust-appraise-all` — both shipped as separate skills. | `gaia-full-pipeline` opens by asking the agent to choose strategy A–F from a 6-row table *before any work begins*. The first act is the least-informed decision in the run. |
| **D8** | The routine that would catch all of the above is not wired. | `founder/steward/routines/cli-contract-drift.md` header: *"(not wired — no sensor emits this debt yet)"*. `founder/MEMORY.md:188` already records the open debt: CLAUDE.md § CLI Shape lists four commands that no longer exist and omits two that do. | The drift-detector exists, has an envelope, and never runs. Drift accumulates into the documents agents read. |

| **D9** | Two live skills give **opposite instructions on merging** — the most consequential action in the repo. | `gaia-quick-curate` runs a 25-state machine ending at state `24 MERGE_PR`, described as "curate and merge this repo". `.claude/skills/gaia-review-meta-close/SKILL.md:180` states the final merge to `main` "is a human decision (this skill never merges)". | Whether an agent merges to `main` depends on which description matched first. `quick-curate`'s merge does follow a human Gate 2, but its state machine does not distinguish squash from merge commit — and `CLAUDE.md` forbids squash merges onto `main`. |

### 4.1 Scout claims corrected

Reported by scouts, **not** true, and not used in this plan:

- *"`--class` was removed in v7.0.0; agents get `unrecognized arguments`."* It is still parsed (`impl.py:3888`), explicitly marked deprecated. The defect is stale *guidance*, not a hard break.
- *"`gaia dev reclassify` is obsolete."* It is deprecated in the changelog but still registered and dispatchable. Treat as drift, not removal.

Recording these matters: a plan built on unverified scout output would itself become the next D1.

The underlying instrument limitation was filed upstream under the cross-repo rule: [skill-scout-fleet#1](https://github.com/gaia-research/skill-scout-fleet/issues/1) — cheap scouts fabricate consequences in the `signal` field, so scout output is a *localization hypothesis*, never a finding. Recall was excellent; every claim in § 4 was re-verified by hand against the live parser.

---

## 5. The thesis

> **"Only the strongest model can do curation reliably" is a measurement of instruction quality, not of task difficulty.**

A strong model succeeds here because it has the reserve capacity to notice that its instructions are wrong, re-read `--help`, reconcile two grade scales, and infer the ordering the preflights never showed it. It is paying a **correction tax** on every run. A weaker model has no reserve and fails.

That reframes the goal. The objective is not to route curation to a stronger reasoner — the founder ruling of 2026-08-13 already forbids treating capability as a gate, and a stronger reasoner never receives a wider envelope. The objective is to **lower the reasoning required until a modest reasoner completes the work correctly**, and to keep it there.

This yields the quality metric for the whole programme:

> **A playbook's quality is the weakest reasoner that completes it correctly, twice, from a cold start.**

Not prose elegance. Not coverage. That number, tracked over time.

Corollary, and the answer to "how do we keep control while granting agency": **agency belongs at the judgment points, control belongs at the sequence and the invariants.** An agent should be deciding *is this a duplicate*, *is this evidence independent*, *does this deserve 3★* — and should never be deciding *which of seven curation skills am I in*, *what order do these six verbs go in*, or *which artifacts must be committed together*. The second list is not judgment. It is the method, and the method should be carried by the playbook, not re-derived per run.

---

## 6. What a playbook is

A playbook is the Steward packet contract, generalized from maintenance debt to the whole agent-facing method, with one addition: **a machine-checked command spine.**

```yaml
id: curate-single-source
class: B                      # A | B | C — authority, machine-enforced
objective: >-
  Take one upstream SKILL.md URL to a review-ready discovery packet at L4.
capability: >-                # prose. names no model, no harness. gates nothing.
  Reading a source repository against a schema and deciding whether a capability
  already exists in the graph. The cheap answer — propose a new generic — is
  usually wrong.

preconditions:                # checked BEFORE step 1, all of them, reported at once
  - generic snapshot exists and its sha256 is recorded
  - actor authorization resolves (verifier | override | bootstrap)
  - branch prefix is one of review/meta, dev

steps:
  - id: snapshot
    run: gaia dev list --generic --json > {snapshot}
    proves: snapshot.sha256
  - id: prefill
    run: gaia dev prefill --source {url} --output {prefill}
    proves: prefill.mappingOptions[].matchTier
  - id: decide
    judgment: MAP | NEW_GENERIC | DUPLICATE | NOT_A_SKILL | DEFER
    rules: CURATION-CORE.md § bounded decision precedence
  - id: validate
    run: python scripts/validate_discovery_packet.py --generic-snapshot {snapshot} {packet}

stopConditions:
  - the decision requires a Class C ontology call (new generic capability)
  - the source is not a skill under the artifact gate
  - validation cannot be made to pass without editing the snapshot

proof:
  - packet validates against discovery-packet-v2
  - every mapped id exists in the recorded snapshot
  - the L4 packet shows similarity AND matchTier for each option

done: review-ready packet in registry-for-review/discovery-packets/. L4 is a hard stop.
```

Five properties make this a playbook rather than a long prompt:

1. **Preconditions are checked together, up front, and reported as a set.** This directly repairs D5. The agent sees the whole dependency graph before acting.
2. **The command spine is data, not prose.** Every `run:` is extractable, and therefore verifiable against the live argparse surface. This is what repairs D1/D3 permanently — see § 8.
3. **Judgment steps are explicitly marked and narrowly scoped.** The agent is asked one bounded question with an enumerated answer space, not "curate this."
4. **Stop conditions have somewhere to land.** A Class C stop goes to the founder queue; a failed Class B goes to the lane with `maxAttempts` and a cooldown. An escalation with nowhere to land is not an escalation.
5. **Proof is declared, not assumed.** "Done" is a checkable statement, not the agent's opinion that it finished.

---

## 7. Architecture

```text
                    HUMAN                              AGENT
                      │                                  │
                      │                                  ▼
                      │                         ┌──────────────────┐
                      │                         │    PLAYBOOK      │
                      │                         │  objective       │
                      │                         │  preconditions ──┼──► checked as a SET
                      │                         │  step spine      │    (repairs D5)
                      │                         │  judgment points │
                      │                         │  stopConditions ─┼──► lane │ founder queue
                      │                         │  proof           │
                      │                         └────────┬─────────┘
                      │                                  │
                      │                    ┌─────────────┴─────────────┐
                      │                    │   PLAYBOOK CONTRACT CHECK │  ◄── CI
                      │                    │  every `run:` parsed and  │      (repairs D1/D3/D8
                      │                    │  matched against the live │       permanently)
                      │                    │  argparse surface         │
                      │                    └─────────────┬─────────────┘
                      ▼                                  ▼
        ┌───────────────────────────────────────────────────────────┐
        │              gaia CLI — 36 dev verbs, unchanged            │
        │        canonical, programmatic, schema-safe mutation       │
        └───────────────────────────────┬───────────────────────────┘
                                        ▼
                            registry / skill-trees / docs
```

The CLI is untouched. The playbook layer sits above it, and a contract check sits between the playbook and the CLI so that a playbook can never drift away from the verbs it invokes.

---

## 8. How skills really happen — the mechanics this must respect

The founder's requirement: *if it is skills, the agent must know how skills really happen, so that what we actually do in this repo is maintained and order is maintained.* Four mechanics, and what each one forces.

**1. A skill is selected by its `description`, before its body is read.** Progressive disclosure means the frontmatter description is the entire basis on which a skill is chosen; the body is loaded only after. This is why D7 hurts so much — 7 curation descriptions competing for the same trigger phrases means selection is a coin flip made on partial information. *Forces:* descriptions must be **discriminative, not merely accurate**, and every cluster needs exactly one entry point.

**2. Triggering accuracy is measurable, and therefore must be measured.** `anthropic/skill-creator` ships the loop: draft → test prompts → run → evaluate → rewrite, plus a dedicated description-improver for triggering. *Forces:* each playbook ships with test prompts, and "does the right playbook fire?" becomes a CI-checkable number rather than a matter of opinion.

**3. Skills are prose; prose drifts silently.** Nothing about a `SKILL.md` fails when the CLI beneath it changes. That is the whole causal chain of D1→D3→D8. *Forces:* the command spine must be **extractable and executable-checkable**. A playbook whose `run:` lines no longer match the live parser fails CI — the same way `verify_lockstep.py` fails on manifest disagreement. This is the mechanism by which *order is maintained*.

**4. This repo mirrors skills into two trees.** `.claude/skills/` and `.agents/skills/` must stay byte-identical (`scripts/sync_agent_skill_mirror.py`; Steward repairs it as Class A). *Forces:* playbooks live in one canonical tree and are mirrored by the existing executor — never hand-copied, never authored twice.

---

## 9. The pruning

The user's expectation of heavy pruning is correct. 65 skills is not a library; it is a routing problem that every agent must re-solve on every run.

Target shape:

| Cluster | Today | Proposed | Rule applied |
|---|---|---|---|
| Curation | 7 variants + 2 routers | **1 playbook, parameterised** by batch size and source kind | Batch size and recoverability are *parameters*, not distinct methods. |
| Evidence | 8 (`ev-*` + alias) | **1 playbook, 5 declared phases** | The phases are already strictly ordered; ordering belongs in the spine, not in the agent's head. |
| Feature work | 7 (`fp-*` + router) | **1 playbook, phased** | Same. |
| Trust / audit | 6 | **2** — appraise (proposed) and inspect (existing) | The rest are aliases or scope variants. |
| Aliases | 2 shipped as separate skills | **0** | `evidence-verification-pipeline`, `gaia-tm-inspect` become description keywords on their canonical playbook. |

Rough order of magnitude: **65 → ~15**. The exact set is a Class C call and belongs to the founder, not to this plan.

D9 is the sharpest argument for the prune: a cluster large enough that two of its members disagree about whether an agent may merge to `main` is not a library, it is an unreviewed policy fork.

Pruning rule, stated so it can be applied without re-asking: *if two skills differ only in **how much** or **how fast**, they are one playbook with a parameter. If they differ in **what proof is required at the end**, they are different playbooks.*

---

## 10. Phasing

Deliberately ordered so the highest-value, lowest-risk repairs land first, and so nothing depends on a new runtime.

| PR | Scope | Class | Depends on |
|---|---|---|---|
| **P0 — this PR** | This plan document. No code. | C | — |
| **P1 — contract truth** | Fix D1/D2/D3 at source: correct `CLAUDE.md:149`, disambiguate the two grade scales in `META.md` (name them *Evidence Grade* and *Overall Trust Grade* wherever a threshold appears), retire `--class` from agent-facing docs and skills. | B | P0 |
| **P2 — wire the drift sensor** | Emit `cli_contract_drift` so the existing, already-scoped routine can actually run. Repairs D8, and prevents P1 from silently regressing. | B | P1 |
| **P3 — playbook schema + checker** | Define the playbook YAML front-section; ship `scripts/check_playbook_contract.py` that extracts every `run:` and validates it against the live argparse surface. Wire into `docs-cohesion.yml` as a new guard. | B | P1 |
| **P4 — batch preconditions** | Change `_run_dev_preflights` to evaluate all checks and report the full failing set, rather than returning on the first. Repairs D5. Additive; no behaviour change on success. | B | — |
| **P5 — first playbook** | Convert the curation cluster to one parameterised playbook. Ship test prompts and a triggering eval. | B | P3, P4 |
| **P6 — write-time invariant warnings** | Have registry-mutating verbs warn at write time about the CI invariants they have just put at risk (Guard E regeneration, branch scope, timeline events). Repairs D6. | B | P4 |
| **P7 — prune** | Collapse the remaining clusters per § 9. Founder-gated set selection. | C | P5 |

P1 and P4 are independently valuable and should land even if the rest of the programme is rejected.

---

## 11. How a playbook is proven

Every playbook ships with all four. A playbook missing any of them is not done.

| Layer | What it checks | Mechanism |
|---|---|---|
| **Contract** | Every `run:` in the spine matches the live CLI surface — verb exists, flags exist, choices are valid. | `scripts/check_playbook_contract.py`, CI guard (P3) |
| **Triggering** | The right playbook fires for a realistic request, and the wrong ones do not. | Test prompts per playbook; description-improver loop |
| **Execution** | The spine runs end to end on a fixture and produces the declared proof. | Dry-run against fixtures in `tests/` |
| **Floor** | The weakest reasoner that completes it correctly, twice, cold. | Recorded per playbook; the programme's headline metric |

---

## 12. Failure modes

| Risk | Severity | Mitigation |
|---|---|---|
| Playbooks become a second place where the method drifts — now in YAML instead of prose. | **critical** | The contract checker (P3) is the whole answer, and is why P3 precedes P5. A playbook that cannot be checked must not be written. |
| Over-constraining removes the judgment that makes curation valuable. | high | Judgment steps are explicit and enumerated. If a playbook has no `judgment:` step, it is a Class A script and should be code, not a playbook. |
| The 65→15 prune deletes a capability someone depends on. | high | Prune is P7, last, founder-gated, and keyed on the stated rule. Aliases fold into descriptions rather than disappearing. |
| `capability:` quietly becomes a model gate, violating the 2026-08-13 ruling. | high | Policy already refuses a capability line naming a model, provider, or harness. Extend that refusal to playbooks in P3. |
| Batching preconditions (P4) changes behaviour on success paths. | medium | Additive only: same pass/fail verdict, fuller failure report. Pinned by tests. |
| The floor metric gets gamed by simplifying tasks rather than instructions. | medium | Floor is measured against fixed end-to-end fixtures with declared proof, not against the playbook's own summary. |

---

## 13. NOT in scope

- **Removing, reducing, or hiding the CLI.** It stays the canonical mutation interface and the human surface. Every playbook `run:` is a `gaia` verb.
- **The MCP/tool-server layer of #1644 as filed.** Deferred, not rejected. Once playbooks exist and their spines are contract-checked, a typed tool layer becomes a mechanical projection of an already-correct method. Building it first would harden the current one.
- **Changing Trust Magnitude, the Star Bar, Apex predicates, or any scoring rule.** § 4 D2 is a *documentation disambiguation*, not a threshold change. No number moves.
- **Any registry, skill-tree, or frontend mutation.** This PR is a document.
- **Choosing the final pruned skill set.** Class C, founder's call, P7.

---

## 14. Open founder decisions

1. **Does the playbook layer live in `.agents/skills/` as a skill kind, or in `founder/steward/routines/` as a routine kind?** They are converging on the same contract from opposite ends. Recommendation: extend the routine contract, mirror into the skills trees, one canonical source.
2. **Is `capability:` retained on playbooks?** It gates nothing by ruling. Recommendation: keep — it is how a human decides what to hand over, and it is already policy-refused from naming a model.
3. **The 65→15 target set.** § 9 gives the rule; the list is yours.
4. **Does the floor metric become a release gate?** Recommendation: not initially. Measure for one sprint, then decide.
