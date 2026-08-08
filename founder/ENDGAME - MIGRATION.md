# GAIA EVOLUTION AND GOVERNANCE DOCTRINE

**Status:** Founder Migration Doctrine  
**Purpose:** Define how Gaia moves toward the multi-Tree end state without unnecessary rewrites, benchmark explosions, or ontology churn.

# 1. Preserve Before Replacing

Existing Gaia systems should not be rewritten merely because a cleaner end state has been identified.

Yggdrasil II remains the active prestige schema.

TrustMagnitude remains the active trust index.

The current Gaia CLI remains the ecosystem shell.

Existing domains and canonical Skill URLs remain stable unless a migration provides clear user value.

New architecture should emerge through clean boundaries around established systems.

---

# 2. Arbor Begins Beside Yggdrasil

Arbor I should initially be introduced as a new independent lane.

Do not immediately move TrustMagnitude out of existing records.

Do not redesign Yggdrasil II merely to accommodate Arbor.

First prove Arbor.

Initial shape:

```text
YGGDRASIL II               ARBOR I
     │                          │
Evidence                   Benchmarks
     │                          │
TM Index                    HH Index
     │                          │
Prestige                    Behavior
```

They meet through shared Skill identity and cross-referenced observations.

---

# 3. Recommended Evolution Sequence

## Phase 0: Ratify the conceptual model

Freeze:

- one capability universe
- multiple Trees
- Yggdrasil owns prestige
- Arbor owns behavior
- TM and HH are independent indexes
- benchmark receipts may feed both
- behavioral edges do not equal fusion edges
- no mandatory ranking system for Arbor

## Phase 1: Arbor sidecar

Introduce experimental locations such as:

```text
registry/indexes/hell-heaven/
registry/observations/benchmarks/
```

No destructive schema migration.

Produce early HH profiles for a small reference set.

## Phase 2: Benchmark receipt contract

Ratify a canonical Gaia capability benchmark receipt.

Make receipt provenance strong enough that:

- Arbor can compute behavioral interpretation
- Yggdrasil/TM can recognize verified benchmark evidence

## Phase 3: Arbor node model

Calibrate:

- polarity
- convergence
- exploration
- stability
- recovery
- churn
- coverage

Only then ratify consumer labels.

## Phase 4: Arbor behavioral edges

Begin with experimentally important pairs.

Allow unknown relationships.

Do not attempt complete pairwise coverage.

## Phase 5: Frontend projection

Add:

```text
Yggdrasil | Heaven ↔ Hell
```

to Gaia Skill Tree.

Use the same canonical Skill identities.

Let the geometry change dramatically.

## Phase 6: Multi-index substrate

After Arbor has demonstrated that two Trees genuinely need shared infrastructure, consider the deeper identity / observations / indexes / projections schema separation.

This may become Yggdrasil III if scoped to the existing lineage, or a broader Gaia meta-schema evolution if the architecture has transcended Yggdrasil itself.

---

# 4. Benchmark Strategy

Gaia must never require exhaustive benchmarking.

The combinatorial space grows approximately with:

```text
skills
× skill pairs
× tasks
× models
× harnesses
× postures
× horizons
× repetitions
```

Comprehensive coverage is economically impossible and scientifically unnecessary.

Gaia should optimize for:

> **expected information gain per token spent**

---

# 5. Benchmark Pyramid

## L0: Static Validation

Near-zero inference cost.

Validate:

- schema
- installation
- hashes
- dependencies
- topology
- provenance

Run broadly.

## L1: Probe

Tiny cheap behavioral test.

Question:

> Does this capability appear to produce a measurable effect?

Most Skills need nothing beyond this until demand emerges.

## L2: Characterization

For promising or important Skills.

Estimate:

- Heaven behavior
- Hell behavior
- safety
- recovery

## L3: Promotion / Decision Benchmark

Spend serious resources only when evidence may materially alter:

- TrustMagnitude
- verification status
- an important composition decision
- a contested claim
- a meaningful capability classification

## L4: Frontier Benchmark

Reserve expensive models and long horizons for:

- important high-prestige Skills
- Ultra readiness
- disputed claims
- high-impact behavioral edges
- frontier capability characterization

Expensive certainty should concentrate where the decision value is highest.

---

# 6. Never Benchmark Every Edge

Behavioral edge testing should be triggered by evidence of relevance.

A pair enters the queue when:

- Yggdrasil structurally connects them
- a Suite contains both
- Skill Heaven observes frequent co-activation
- runtime variance suggests interaction
- a contributor claims synergy
- either Skill has high exposure
- uncertainty blocks an important composition decision

Otherwise:

```text
relationship: unknown
```

is completely valid.

Unknown is better than fabricated certainty and cheaper than useless certainty.

---

# 7. Sequential Evaluation

Benchmarks should stop as soon as sufficient evidence exists.

```text
3 runs
 │
 ├── obvious null effect ──▶ stop
 │
 ├── obvious strong effect ▶ characterize provisionally
 │
 └── uncertain ────────────▶ run more
```

Fixed large sample counts should be reserved for high-value verification.

---

# 8. Cache Experimental Controls

Stable environment cells should produce reusable baseline receipts.

Example:

```text
model
harness
benchmark version
task-set hash
seed-set hash
baseline posture
```

Experimental arms may reuse the baseline while all invariants remain unchanged.

This prevents repeatedly paying for identical control runs.

---

# 9. Benchmark Controller

Gaia should eventually schedule benchmarking through a governed controller.

Conceptually:

```text
wake
 │
 ▼
scan benchmark debt
 │
 ▼
score candidate experiments
 │
 ├── nothing valuable enough
 │       └── produce no-change receipt
 │
 ▼
select highest-value experiment
 │
 ▼
choose cheapest adequate model
 │
 ▼
execute
 │
 ▼
record receipt
 │
 ▼
escalate only if evidence warrants it
```

Possible priority semantics:

```text
priority ∝
importance
× uncertainty
× decision impact
× usage exposure
× freshness need
÷ expected cost
```

Uncertainty alone must never create work.

---

# 10. Founder Economics

The founder should not become the permanent payer and executor of every capability benchmark.

Long term:

```text
Gaia defines benchmark
        │
Contributor executes
        │
signed receipt
        │
Gaia validates
        │
strategic verifier reproduces
```

Founder-funded work should concentrate on:

- reference baselines
- calibration
- important ecosystem gaps
- disputes
- protocol upgrades
- high-impact frontier evaluations

The founder's role evolves from **benchmark runner** toward **benchmark protocol governor**.

---

# 11. Skill Heaven and Benchmarking

Skill Heaven should eventually become a major producer of Arbor observations.

Runtime:

```text
Tree knowledge
    ↓
composition
    ↓
Skill Heaven execution
    ↓
telemetry
    ↓
uncertainty detection
    ↓
benchmark candidate
    ↓
receipt
    ↓
Arbor improves
```

This creates a learning loop without requiring every normal runtime session to become a formal benchmark.

Telemetry identifies questions.

Controlled benchmarks answer them.

---

# 12. CLI Doctrine

The existing `gaia` command remains the ecosystem doorway.

Do not create:

```text
gaia2
arbor-cli
hell-cli
ultra-cli
```

merely because the architecture expands.

The TUI may progressively expose distinct domains while preserving command compatibility.

A future top-level experience might visually group:

```text
Skill Tree
Skill Heaven
Benchmarks
Developer
```

Implementation boundaries may remain polyrepo.

Interface boundaries need not mirror repository boundaries.

---

# 13. Repository Doctrine

High-level products remain separate when they have independent lifecycles.

Conceptually:

```text
gaia-research/
├── gaia-skill-tree
├── skill-heaven
├── gaia-research
└── gaia-operator
```

Do not create separate repositories for:

```text
skill-hell
skill-ultra
HH-index
```

unless they become independently reusable systems with genuinely independent ownership and release requirements.

Heaven, Hell, and Ultra remain concepts within the execution product.

Arbor belongs to Gaia Skill Tree because it is a Tree and index over Gaia capability knowledge.

---

# 14. Web Doctrine

`gaiaskilltree.com` remains the canonical multi-Tree capability product.

The frontend grows lenses rather than new top-level sites for every index.

Conceptually:

```text
gaiaskilltree.com

Skill
 ├── Overview
 ├── Yggdrasil
 ├── Heaven ↔ Hell
 ├── Benchmarks
 └── Evidence
```

Skill Heaven may have its own product domain because it is an execution system rather than a knowledge projection.

Hell and Ultra should not require independent domains.

---

# 15. Prestige Doctrine

Prestige belongs to Yggdrasil unless explicitly changed by a future Meta Shift.

Arbor should avoid copying stars.

HH properties describe behavior:

```text
Heaven-native
Hell-native
Hell-safe
Dual-safe
Ultra-ready
```

They are not prestige titles.

A capability can therefore be:

```text
6★ Apex
S Trust
Hell-native
Dual-safe
Ultra-ready
```

without any of those dimensions pretending to mean the others.

---

# 16. Future-Tree Doctrine

A new Tree should exist only when a domain has:

1. a genuinely different question;
2. its own observations;
3. its own index semantics;
4. meaningful relations or topology;
5. a frontend projection worth seeing independently.

Do not create Trees merely because a new metric exists.

Possible future Trees include:

```text
Efficiency / Cost versus Capability
Security / Enterprise Readiness
```

Neither should be named or structurally frozen before sufficient observations exist.

---

# 17. Founder's Decision Test

When a future architectural question appears, ask:

### Identity

Does this change what the Skill *is*?

If not, keep it out of identity.

### Observation

Is this a raw fact or experiment?

Store it as an observation.

### Index

Is this a computed interpretation?

Put it in an index.

### Structure

Is this a relationship meaningful only under one Tree?

Keep it inside that Tree's structural vocabulary.

### Projection

Is this merely how the information should be visualized?

Do not promote it into schema truth.

### Prestige

Is Gaia making a governed status judgment?

That belongs in the prestige layer.

This test should prevent most future schema entanglement.

---

# 18. Permanent North Star

The desired end state is not:

> One perfect schema that describes everything about every Skill.

It is:

> **A stable capability identity surrounded by independently evolving structures, observations, indexes, and projections.**

Yggdrasil can evolve without rewriting Arbor.

Arbor can improve its behavioral science without changing star prestige.

A future Efficiency Tree can appear without either system knowing about it beforehand.

A benchmark can simultaneously strengthen behavioral knowledge and verified trust without forcing those two interpretations into one score.

And the user can move between Trees while remaining anchored to the exact same Skill.

That is the architecture Gaia should gradually converge toward.