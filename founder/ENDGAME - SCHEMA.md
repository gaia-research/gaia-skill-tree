# GAIA MULTI-TREE SCHEMA ARCHITECTURE

**Status:** Target Schema Direction  
**Purpose:** Define the modular data architecture supporting Yggdrasil, Arbor, and future Gaia Trees.

# 1. Architectural Law

The schema must separate:

```text
Identity
Structure
Observations
Indices
Projections
Prestige
```

No single Skill document should become the authoritative container for every dimension.

The schema should prefer references and generated projections over duplicated state.

---

# 2. Canonical Data Flow

```text
AUTHORED / OBSERVED DATA
        │
        ▼
canonical identities
relations
observations
        │
        ▼
INDEX ENGINES
        │
        ├── TrustMagnitude
        ├── Hell-Heaven Index
        └── future indexes
        │
        ▼
MATERIALIZED INDEX RESULTS
        │
        ▼
TREE PROJECTIONS
        │
        ▼
frontend / CLI / API
```

A derived value should be regenerable whenever possible.

---

# 3. Target Registry Shape

A possible long-term organization:

```text
registry/
│
├── entities/
│   ├── generic/
│   └── named/
│
├── relations/
│   ├── yggdrasil/
│   │   ├── prerequisites/
│   │   ├── suites/
│   │   └── origins/
│   │
│   └── arbor/
│       └── behavioral/
│
├── observations/
│   ├── evidence/
│   ├── benchmarks/
│   ├── runtime/
│   ├── attestations/
│   └── adoption/
│
├── indexes/
│   ├── trust/
│   └── hell-heaven/
│
└── projections/
    ├── yggdrasil/
    └── arbor/
```

This is a target architecture, not a requirement for an immediate filesystem migration.

---

# 4. Identity Schema

The canonical named Skill should trend toward representing identity rather than computed standing.

Example:

```yaml
id: mattpocock/grill-me
name: Grill Me
contributor: mattpocock
genericSkillRef: critique
status: named

description: >
  ...

links:
  github: ...

tags:
  - critique

createdAt: ...
updatedAt: ...
```

Changing an HH formula should not require changing this identity.

Changing TrustMagnitude should not require changing this identity.

---

# 5. Observation Schema

Observations record what happened or what evidence exists.

They should avoid embedding conclusions that belong to indexes.

A Gaia benchmark receipt may resemble:

```yaml
schema: gaia.benchmark-receipt/v1

id: benchmark/run/abc123

subject:
  type: named-skill
  ref: mattpocock/grill-me

benchmark:
  id: critique-v2
  version: 2.1

environment:
  model: ...
  harness: ...
  skillPopulation: ...
  posture: hell
  horizon: standard

inputs:
  taskSetHash: ...
  seedSetHash: ...

measurements:
  trajectorySpread: ...
  outcomeQuality: ...
  recoverability: ...
  churn: ...
  tokens: ...

provenance:
  runner: ...
  artifacts: ...
  attestors: ...

verification:
  lane: verified
```

The receipt is the canonical experiment.

---

# 6. Shared Receipt, Multiple Interpretations

The same benchmark receipt may be referenced by both indexes.

```text
benchmark/run/abc123
        │
        ├──▶ HH Index
        │      behavioral interpretation
        │
        └──▶ TM Index
               verified evidence contribution
```

The receipt must not be duplicated into separate HH and TM versions.

---

# 7. Index Envelope

Every Gaia index should share a common outer contract.

Example:

```yaml
schemaVersion: 1

index:
  id: hell-heaven
  version: 2026-Q4

subject:
  type: named-skill
  ref: mattpocock/grill-me

computedAt: ...
inputDigest: ...

sources:
  - benchmark/run/abc123
  - benchmark/run/def456

result:
  ...
```

This allows CLI, frontend, APIs, and validators to understand an Index generically while leaving the result payload index-specific.

---

# 8. TM Index Result

Conceptually:

```yaml
index:
  id: trust-magnitude

result:
  magnitude: 137.2
  overallGrade: A
  evidenceDiversity: ...
  verificationTier: ...
  apexGateStatus: ...
```

Yggdrasil may consume this result when determining prestige.

Evidence remains in the Yggdrasil/TM lane.

---

# 9. Hell-Heaven Index Result

A canonical HH result should be a profile, not merely a scalar.

Example:

```yaml
index:
  id: hell-heaven

result:
  polarity:
    value: -0.72
    label: heaven-native

  behavior:
    convergenceGain: 0.61
    explorationGain: -0.08
    trajectorySpreadDelta: -0.31
    outcomeStability: 0.93
    recoverability: 0.91
    churnDelta: 0.07

  regimes:
    heaven:
      effectiveness: 0.84

    hell:
      effectiveness: 0.66
      safety: 0.92

    ultra:
      endurance: null
      status: untested

  coverage:
    benchmarkRuns: 28
    taskFamilies: 4
    harnesses: 2
    models: 3
```

Human-friendly badges are derived from this profile.

---

# 10. Arbor Edge Result

Arbor behavioral relationships require their own schema.

Example:

```yaml
schema: gaia.arbor-edge/v1

from: brainstorm
to: grill-me

relation: stabilizes

effect:
  outcomeQualityDelta: 0.14
  trajectorySpreadDelta: -0.22
  recoveryDelta: 0.31

conditions:
  posture: hell
  populationBand: 8-16
  taskFamily: software-design

sources:
  - benchmark/run/abc123

status: observed
```

Possible lifecycle:

```text
observed
characterized
ratified
deprecated
```

This prevents a single noisy experiment from immediately becoming canonical graph truth.

---

# 11. Structural Edge versus Behavioral Edge

Never overload Yggdrasil prerequisites.

These statements are different:

```text
A ── prerequisite ──▶ B
```

means B structurally incorporates capability A.

```text
A ── stabilizes ──▶ B
```

means A empirically improves B's runtime behavior under defined conditions.

A Skill pair may possess both relationships.

The schemas must preserve the distinction.

---

# 12. Projection Manifest

A Tree should eventually be describable independently from its source indexes.

Conceptually:

```yaml
tree:
  id: arbor
  version: 1

nodes:
  source: hell-heaven

edges:
  source: arbor-behavioral

layout:
  primaryAxis: polarity

visualMappings:
  nodeSize: behavioralEffect
  nodeOpacity: benchmarkCoverage
  trustRing: trust-magnitude.grade
```

Yggdrasil may have its own projection manifest:

```yaml
tree:
  id: yggdrasil
  version: 2

structure:
  prerequisites: true
  suites: true

visualMappings:
  rank: stars
  branch: membership
  prestige: trust
```

This is what eventually makes frontend switching a projection change rather than a separate application.

---

# 13. Ownership Rules

The following should be enforced conceptually and eventually in CI.

## Authored

Humans or curated tools may author:

- identity
- source links
- structural declarations where applicable
- benchmark definitions

## Observed

Experiments and external systems produce:

- benchmark receipts
- adoption events
- runtime observations
- attestations
- evidence artifacts

## Computed

Machines produce:

- TrustMagnitude
- HH profiles
- HH labels
- grades
- coverage
- behavioral scores

## Governed

Curators or ratified processes determine:

- promotion
- prestige
- ratified edge semantics
- schema changes
- index formula versions

A contributor should never simply write:

```yaml
hellSafe: true
```

and have Gaia believe it.

---

# 14. Index Independence Rule

No index may recursively depend on another index unless explicitly ratified as a higher-order composite index.

Therefore:

```text
HH Index ─X─▶ TrustMagnitude ─X─▶ HH Index
```

is forbidden.

Instead:

```text
raw observation ──▶ HH
raw observation ──▶ TM
```

Frontend projections may freely join their outputs.

---

# 15. Versioning

Indexes evolve independently.

Example:

```text
Yggdrasil II
TM Index 2026 Q3
Arbor I
HH Index 2026 Q4
Benchmark Spec 1.2
```

Gaia ecosystem roadmap versions should not force lockstep schema versions.

Every computed artifact should record:

```text
schema version
index version
benchmark version
source digest
computation timestamp
```

---

# 16. Core Invariant

The architecture succeeds if Gaia can perform the following operation safely:

```text
delete all generated HH Index artifacts
recompute them from benchmark receipts
produce the same Arbor projection
```

Likewise for TrustMagnitude wherever historical governance semantics permit deterministic regeneration.

That is the standard for keeping Gaia modular rather than accumulating hidden state.