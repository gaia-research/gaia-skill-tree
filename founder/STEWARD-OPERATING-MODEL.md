# GAIA STEWARD — OPERATING MODEL

**Status:** Blueprint  
**Purpose:** Define freshness, debt, authority, sensors, receipts, dispatch, and founder escalation for Gaia Steward.

---

# 1. Core Loop

Every Steward cycle follows the same lifecycle:

```text
WAKE
 │
 ▼
COLLECT OBSERVATIONS
 │
 ▼
NORMALIZE
 │
 ▼
RECONCILE WITH CURRENT STATE
 │
 ▼
CREATE / UPDATE / RESOLVE DEBT
 │
 ▼
PRIORITIZE
 │
 ▼
AUTHORIZE
 │
 ├── no work ───────────────▶ RECEIPT → STOP
 │
 ├── Class A ───────────────▶ deterministic repair
 │
 ├── Class B ───────────────▶ bounded Tree Keeper dispatch
 │
 └── Class C ───────────────▶ founder decision queue
 │
 ▼
VERIFY
 │
 ▼
RECORD RECEIPT
 │
 ▼
STOP
```

A cycle must have a finite work budget.

Steward is not an infinite autonomous loop.

---

# 2. Freshness Registry

Freshness belongs to observation classes.

Initial policy:

| Observation | Suggested freshness | Expiry consequence |
|---|---:|---|
| canonical identity | none | never expires by time |
| generic/fusion topology | none | re-evaluate only from triggering evidence |
| upstream release | 24h | refresh |
| source commit/hash | event or 24h–7d | refresh |
| component manifest | release-triggered | refresh |
| installability | 7d | probe |
| evidence URL liveness | 7d | verify |
| GitHub stars | 30d | refresh |
| repo activity metrics | 30d | refresh |
| social evidence | 30–90d | refresh if decision-relevant |
| dependency/security state | 7d or event-driven | inspect |
| generated projections | source-triggered | regenerate |
| benchmark receipt | environment-versioned | never silently reinterpret |
| HH profile | benchmark-version dependent | mark coverage/freshness explicitly |
| editorial description | none | human/editorial trigger only |

These values are policy defaults, not ontology.

They should eventually live in a machine-readable Steward policy file.

---

# 3. Debt Record

Canonical conceptual shape:

```yaml
schemaVersion: steward-debt-v1

id: debt:<kind>:<subject>:<semantic-key>

kind: upstream_release_advanced
subject:
  type: named-skill
  id: mattpocock/grill-me

state:
  current:
    version: v1.4.0
  observed:
    version: v1.5.0

observation:
  source: upstream-watcher
  observedAt: 2026-08-09T00:00:00Z
  confidence: 1.0
  provenance:
    url: ...
    sha: ...

freshness:
  policy: upstream-release
  ageSeconds: 1320
  stale: false

priority:
  importance: 0.8
  decisionImpact: 0.4
  exposure: 0.9
  uncertainty: 0.0
  expectedCost: 0.1
  score: ...

authority:
  class: B
  reason: version reconciliation is bounded but may affect canonical provenance

status: open

routing:
  preferredRoutine: 11
  preferredExecutor: tree-keeper
```

Debt records should be reproducible from observations where possible.

---

# 4. Debt Status

Allowed lifecycle:

```text
open
queued
in_progress
blocked
awaiting_verification
awaiting_founder
resolved
superseded
invalid
```

No debt item may disappear without a final disposition.

Resolution must leave a receipt.

---

# 5. Semantic Deduplication

Workflows must not create one issue per detection event.

Debt identity should be based on the unresolved condition.

Example:

```text
evidence URL X is dead
```

detected on Monday, Tuesday, and Wednesday remains one debt item.

New observations update:

```text
lastObservedAt
observationCount
confidence
severity
```

rather than generating three maintenance objects.

If the URL recovers, the debt resolves.

---

# 6. Authority Registry

Every debt kind should have an explicit default authority classification.

Example:

```yaml
upstream_release_detected:
  class: A

upstream_version_reconcile:
  class: B

github_stars_refresh:
  class: A

dead_evidence_quarantine:
  class: B

trust_promotion:
  class: C

generic_mapping_ambiguous:
  class: C

generated_projection_drift:
  class: A

exact_agent_skill_mirror_drift:
  class: A

schema_change:
  class: C
```

A runtime may downgrade authority automatically.

It may never upgrade authority automatically.

Example:

```text
A → B because deterministic proof failed
B → C because topology impact was discovered
```

but never:

```text
C → B because Sol seems confident
```

---

# 7. Sensor Contract

Every sensor emits observations, not commands.

Minimum conceptual interface:

```yaml
sensor:
  id:
  version:

observation:
  kind:
  subject:
  observedAt:
  payload:
  provenance:
  confidence:
  cost:
```

Sensors must not independently decide:

- founder escalation;
- canonical promotion;
- model selection;
- PR policy;
- auto-merge eligibility.

Those belong to Steward.

---

# 8. Initial Sensors

## Upstream Watcher

Owns:

- latest release detection;
- component delta;
- source link liveness;
- release provenance.

Stops owning:

- independent issue policy;
- independent approval workflow philosophy.

## Evidence Health

Owns:

- URL status;
- timeout/error classification;
- evidence liveness observation.

Steward decides whether the consequence is:

- refresh;
- quarantine;
- discount;
- agent review;
- no action.

## Stargazer Heartbeat

Owns:

- source-native GitHub star observation.

It should eventually stop being a special direct-write workflow and feed the same authority mechanism as everything else.

## Source Curation

Owns:

- capability/source discovery observations;
- source provenance;
- deterministic mapping prefill;
- discovery packets.

Discovery does not imply canonical intake.

## Repository Sensors

Potential signals:

- generated drift;
- mirror mismatch;
- validator failures;
- CLI help drift;
- dependency drift;
- test flakes;
- broken links;
- stale agent instructions.

---

# 9. Class A Execution

Class A work must satisfy:

1. deterministic input;
2. deterministic intended state;
3. no unresolved semantic ambiguity;
4. bounded writable paths;
5. reversible change;
6. machine-verifiable proof.

Preferred execution:

```text
sensor
→ Steward debt
→ deterministic command
→ validator
→ policy check
→ integration
→ receipt
```

Initial candidates:

```text
GitHub star refresh
generated Class S synchronization
exact mirror synchronization
source hash refresh
selected link-status metadata
cache/index regeneration
```

Do not begin with every possible Class A category.

Prove the lane with a deliberately small set.

---

# 10. Class B Dispatch

A Tree Keeper packet must be generated before agent invocation.

Example:

```yaml
dispatchId: steward-run-...
debtIds:
  - ...

authority: B

routine:
  id: 6
  name: CLI and Runtime Contract Steward

objective:
  Repair confirmed help/discovery drift.

facts:
  - ...
  - ...

allowedPaths:
  - src/gaia_cli/**
  - tests/**
  - docs/cli/**

allowedCommands:
  - pytest ...
  - gaia --help
  - gaia dev ...

forbidden:
  - registry/named/**
  - registry/nodes/**
  - schema mutation
  - release
  - main push

stopIf:
  - compatibility policy is ambiguous
  - schema change becomes necessary
  - unrelated failures appear
  - proof cannot be reproduced

proof:
  - exact contract test
  - CLI smoke test
  - clean repository status
```

The agent may not broaden its own authority envelope.

---

# 11. Independent Verification

Builder confidence is not proof.

Class B should eventually separate:

```text
builder
from
verifier
```

The verifier should receive:

- original debt;
- original authority;
- proposed diff;
- proof contract;
- generated receipts.

The verifier asks:

```text
Was the finding real?
Did the patch solve it?
Did scope expand?
Were guards weakened?
Did new debt appear?
Is the original authority class still valid?
```

The verifier does not redesign the patch unless explicitly dispatched as a new repair job.

---

# 12. Founder Queue

Class C debt should be aggressively deduplicated and compressed.

Bad:

```text
17 issues
8 workflow failures
4 PR comments
3 bot reports
```

Good:

```text
Founder Decision #C-018

Question:
Should capability X map to generic A or require new generic B?

Why now:
Three independent discoveries are blocked on this ruling.

Evidence:
...

Consequences:
A → ...
B → ...

Steward recommendation:
...

Confidence:
...

Affected debt:
7 items
```

One decision may unblock many debts.

---

# 13. Receipts

Every meaningful Steward action produces a receipt.

Conceptual schema:

```yaml
schemaVersion: steward-receipt-v1

runId:
startedAt:
finishedAt:

observationsCollected:
debtCreated:
debtUpdated:
debtResolved:

dispatches:
repairs:
founderEscalations:

models:
  - model:
    tokens:
    estimatedCost:

verification:
  checks:
  result:

result:
  status: no_change | repaired | partially_repaired | escalated | blocked
```

No-change receipts should remain cheap and quiet.

Large logs may remain ephemeral artifacts.

The durable receipt should be small.

---

# 14. User-Facing Health

Steward should eventually expose a compact health view.

Example:

```text
Gaia Steward

Canonical integrity       healthy
Observation freshness     94.2%
Upstream coverage         97.1%
Evidence health           91.8%
Installability coverage   86.4%

Open maintenance debt     18
  Class A                  11
  Class B                   5
  Class C                   2

Oldest high-priority debt  3d
Founder decisions           2
```

This is more useful than treating repository age as Tree staleness.

---

# 15. CLI Direction

Initial commands:

```text
gaia steward scan
gaia steward status
gaia steward debt
gaia steward inspect <debt-id>
gaia steward run
gaia steward receipt <run-id>
```

Later:

```text
gaia steward repair
gaia steward verify
gaia steward founder
gaia sync
```

Avoid overbuilding the CLI before the debt model is proven.

The first useful product is:

```text
gaia steward scan
```

---

# 16. Routine Routing

The 17 engineering routines remain available as repair strategies.

Initial routing examples:

```text
generated drift
→ Routine 12

CLI contract drift
→ Routine 6

knowledge contradiction
→ Routine 17

flake evidence
→ Routine 5

evidence/trust inconsistency
→ Routine 9

registry structural inconsistency
→ Routine 11
```

Routine routing occurs only after debt exists.

Routine execution does not independently schedule itself.

---

# 17. Failure Policy

Steward fails closed.

On ambiguity:

```text
A → B
B → C
```

On missing provenance:

```text
block
```

On failed proof:

```text
do not integrate
```

On unexpected scope expansion:

```text
stop current dispatch
create/update debt
reclassify authority
```

On sensor failure:

```text
mark coverage unknown
```

Do not silently claim freshness when observation infrastructure is unavailable.

---

# 18. Initial Definition of Done

Steward V1 is successful when:

- one command produces normalized debt from multiple real sensors;
- repeated runs are idempotent;
- no-change runs invoke no model;
- at least one Class A debt can close itself with deterministic proof;
- at least one Class B debt can generate a bounded Tree Keeper packet;
- Class C debt appears in one founder-oriented queue;
- all actions leave receipts;
- existing canonical governance is not weakened.

The goal of V1 is not maximum automation.

It is one coherent maintenance nervous system.