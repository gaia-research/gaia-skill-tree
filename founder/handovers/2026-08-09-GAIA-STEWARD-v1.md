# GAIA STEWARD V1 — IMPLEMENTATION HANDOVER

**Status:** Ready for implementation planning  
**Primary objective:** Build the smallest real Gaia Steward that can measure maintenance debt and autonomously close one safe class of it.

---

# 1. Do Not Build the Final System

V1 should prove four things:

1. Gaia can normalize maintenance signals from different subsystems.
2. Gaia can distinguish observation freshness from canonical correctness.
3. Gaia can make deterministic no-work decisions.
4. Gaia can safely close a bounded Class A maintenance loop.

Do not implement:

- all 17 routines;
- a general-purpose agent scheduler;
- Arbor;
- benchmark governance;
- contributor `gaia sync`;
- autonomous canonical curation;
- a large dashboard;
- a new service;
- a database unless demonstrated necessary.

Start inside the existing Gaia Skill Tree repository.

---

# 2. Proposed File Shape

Prefer a narrow package:

```text
src/gaia_cli/steward/
├── __init__.py
├── models.py
├── policy.py
├── sensors.py
├── debt.py
├── priority.py
├── authority.py
├── receipts.py
└── controller.py
```

Optional sensor adapters:

```text
src/gaia_cli/steward/sensors/
├── upstream.py
├── evidence.py
├── stars.py
└── repository.py
```

Schemas:

```text
registry/schema/
├── stewardObservation.schema.json
├── stewardDebt.schema.json
└── stewardReceipt.schema.json
```

Fixtures:

```text
tests/fixtures/steward/
```

Tests:

```text
tests/steward/
```

Founder policy:

```text
founder/steward/
├── POLICY.yaml
└── README.md
```

Do not create routine packages in V1.

---

# 3. Policy File

Initial conceptual form:

```yaml
version: 1

freshness:
  upstream_release:
    maxAge: 24h

  evidence_url:
    maxAge: 7d

  github_stars:
    maxAge: 30d

  installability:
    maxAge: 7d

authority:
  github_stars_refresh: A
  generated_projection_drift: A
  exact_mirror_drift: A

  upstream_reconcile: B
  cli_contract_drift: B
  knowledge_contradiction: B

  generic_mapping: C
  fusion_topology: C
  trust_promotion: C
  schema_change: C

budgets:
  maxDebtSelectedPerRun: 10
  maxAgentDispatchesPerRun: 1
  maxFounderItemsPerDigest: 10
```

Machine-enforce this file.

Do not rely on prompt text as the authority system.

---

# 4. Phase 1 — Debt Scanner

Implement:

```bash
gaia steward scan
```

Requirements:

- read current repository state;
- invoke sensor adapters;
- normalize observations;
- reconcile against current trusted state;
- emit deterministic debt;
- deduplicate debt;
- calculate authority class;
- calculate an initial priority score;
- write a receipt;
- make no repository mutation.

Suggested output:

```text
Steward scan

Observations      314
New debt            8
Existing debt       6
Resolved debt       3

Class A             9
Class B             4
Class C             1

Model dispatches    0
Cost                $0
```

First milestone should require **zero LLM calls**.

---

# 5. Initial Sensors

Integrate existing logic rather than rewriting it.

## Sensor A: Stargazer

Extract observation generation from the existing heartbeat.

Output:

```text
skill
observed star count
observed timestamp
source
```

Do not mutate registry in scan mode.

## Sensor B: Evidence Health

Reuse existing verification behavior.

Output:

```text
evidence id/url
HTTP status
classification
observed timestamp
```

Do not open an issue directly from the sensor.

## Sensor C: Upstream

Reuse upstream watcher detection.

Output:

```text
skill id
current known release
latest observed release
component delta
link state
```

Scheduled mode must perform real observation rather than fixture-only observation where credentials/cost permit.

## Sensor D: Repository

Start with cheap deterministic checks:

```text
generated projection drift
.agent/.claude exact mirror drift
validator failures
```

Do not add broad static analysis yet.

---

# 6. Persistence

Avoid introducing infrastructure prematurely.

V1 acceptable options:

```text
generated-output/steward/
```

for ephemeral run data and:

```text
.steward/
```

or another clearly classified repository-local state location for durable debt only if necessary.

Before choosing persistence, determine whether debt can be reproduced cheaply from canonical state plus recent observations.

Prefer reproducibility over accumulated mutable state.

Durable founder/governance decisions may eventually need tracked state.

Ephemeral polling observations probably do not.

---

# 7. Phase 2 — Class A Closed Loop

Choose exactly one initial Class A repair category.

Recommended first candidate:

## Generated / exact mirror drift

Why:

- deterministic;
- local;
- reversible;
- zero external semantic interpretation;
- strong validators;
- no TrustMagnitude or topology consequence;
- inexpensive oracle fixtures.

Alternative:

## Stargazer refresh

Only if the current canonical mutation and timeline/provenance rules clearly support fully automatic integration without contradicting repository governance.

Do not select both for the first experiment.

Class A flow:

```text
detect
→ debt
→ allowed deterministic command
→ diff scope check
→ validator
→ second deterministic reproduction
→ integration eligibility
→ receipt
```

Initially allow:

```text
repair-ready
```

without auto-merge.

Then enable automatic integration only after fixture and live evidence demonstrates safety.

---

# 8. Phase 3 — Class B Packet Generation

Do not start by letting an agent roam the repository.

Implement:

```bash
gaia steward dispatch <debt-id>
```

which produces a complete Tree Keeper packet.

Example output:

```yaml
dispatchId:
debt:
routine:
authority:
objective:
facts:
allowedPaths:
allowedCommands:
forbiddenPaths:
stopConditions:
proof:
budget:
```

The packet should be independently inspectable and testable.

Only after this contract is stable should it be handed to Claude/Hermes/Codex automatically.

---

# 9. Tree Keeper V1

First agent-enabled candidate should be one of:

- Routine 12 — repository hygiene;
- Routine 6 — CLI/runtime contract;
- Routine 17 — knowledge/nomenclature.

The previous RFC model-routing work remains useful here.

But the model is selected **after**:

```text
debt
→ authority
→ routine
→ packet
```

not before.

Initial execution mode:

```text
report or draft patch only
```

No automatic Class B merge in first rollout.

---

# 10. Phase 4 — Verification

Implement verifier input as a separate artifact from builder context.

Verifier receives:

```text
original debt
authority
dispatch packet
patch/diff
proof output
```

Verifier emits:

```yaml
findingConfirmed:
scopeValid:
proofValid:
authorityStillValid:
guardsWeakened:
newDebt:
verdict:
```

Allowed verdicts:

```text
accept
reject
escalate
```

The verifier cannot silently widen scope.

---

# 11. Phase 5 — Founder Queue

Implement a compact view:

```bash
gaia steward founder
```

Output only Class C or escalated Class B matters.

Group by common decision.

Example:

```text
C-003 — Generic mapping ruling

Blocks:
  debt-14
  debt-22
  debt-31

Question:
Map implementations X/Y/Z to `context-compression`,
or ratify a new generic?

Evidence:
...

Recommendation:
...

No action has been taken.
```

Do not create one GitHub issue for each blocked observation.

---

# 12. Migration of Existing Workflows

Do not delete current automation immediately.

Migration sequence:

```text
existing workflow
      ↓
emit Steward-compatible observation
      ↓
run both old + new behavior temporarily
      ↓
compare receipts
      ↓
disable old side effect
      ↓
Steward becomes authority
```

Candidate migration order:

1. Stargazer Heartbeat
2. Evidence Health
3. Upstream Watcher
4. Source Curation

Source Curation should be migrated last because its governance surface is larger.

---

# 13. Routine RFC Integration

The existing routine RFC should be interpreted as infrastructure for Class B execution.

Retain:

- policy registry;
- semantic receipts;
- oracle fixtures;
- model floors;
- spend ceilings;
- clean worktree isolation;
- proof contracts;
- model evaluation;
- daily/weekly Claude lane where useful.

Supersede:

> Schedule the routine catalog itself.

New interpretation:

> Steward selects debt. Debt selects authority. Authority and evidence select a routine and executor.

---

# 14. Evaluation Fixtures

Build fixtures around **debt decisions**, not model personalities.

Minimum fixture classes:

```text
clean/no-debt
stale-but-low-value
Class A deterministic drift
Class B bounded repair
Class C governance dependency
sensor disagreement
failed proof
authority escalation
duplicate observation
recovered observation
```

Required properties:

- deterministic expected debt;
- deterministic authority class;
- deterministic no-model behavior where appropriate;
- no out-of-scope writes;
- no false canonical mutation.

---

# 15. Metrics

Measure the system by:

```text
founder interventions / month
maintenance debt age
Class A closure rate
Class B verifier acceptance rate
false-positive debt rate
no-op rate
LLM calls avoided
cost per resolved debt
unauthorized mutations
unexplained diffs
```

A high no-op rate is not failure.

It means Steward is not manufacturing work.

The critical metric:

> **How long can Gaia remain trustworthy without founder maintenance activity?**

---

# 16. Suggested First PR

One narrow PR:

## `feat(steward): introduce maintenance debt scanner`

Scope:

- Steward models;
- policy;
- observation/debt/receipt schemas;
- 2–3 deterministic sensors;
- `gaia steward scan`;
- fixtures;
- tests;
- report-only receipts.

Explicitly no:

- agent dispatch;
- auto-PR;
- auto-merge;
- canonical mutation;
- routine scheduling.

Acceptance criteria:

- deterministic;
- idempotent;
- zero model calls;
- repeated scans produce equivalent debt from equivalent state;
- debt deduplicates;
- authority classes are machine-enforced;
- no-change state produces a clean no-change receipt.

---

# 17. Suggested Second PR

## `feat(steward): close first Class A maintenance loop`

One repair category only.

Acceptance:

- known-clean fixture;
- positive drift fixture;
- failed-proof fixture;
- rollback/recovery behavior;
- exact writable path guard;
- repeat run becomes no-op;
- zero unexplained changes.

Only after this PR is trusted should Tree Keeper enter the architecture.

---

# 18. Later Roadmap

```text
V1
debt scanner

V1.1
first Class A loop

V1.2
Tree Keeper packet + report-only execution

V1.3
independent verifier

V1.4
bounded Class B rolling maintenance lane

V1.5
founder Class C digest

V2
observation substrate expansion

V2+
gaia sync / signed upstream receipts

future
Skill Heaven telemetry + benchmark debt
```

The implementation should remain deliberately boring until the authority model is proven.

The interesting intelligence belongs above a trustworthy control plane.