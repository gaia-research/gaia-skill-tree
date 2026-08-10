# GAIA STEWARD

**Status:** Founder Direction  
**Purpose:** Define the maintenance operating system that allows Gaia Skill Tree to remain current, trustworthy, and progressively improving without continuous founder supervision.

---

# 1. Thesis

Gaia Skill Tree should not require its founder to continuously watch the repository in order for the system to remain healthy.

The maintenance problem is not fundamentally a lack of engineering routines.

It is a lack of a unified mechanism for answering:

> **What has become stale, broken, uncertain, or newly relevant, and what is the cheapest authorized action that should happen next?**

Gaia Steward is that mechanism.

Steward is the maintenance governor for Gaia Skill Tree.

It does not replace existing validators, crawlers, watchers, routines, agents, or governance systems.

It coordinates them.

Conceptually:

```text
                     GAIA STEWARD

                         observe
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
     upstream            evidence           repository
      signals             signals             signals
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                    MAINTENANCE DEBT
                            │
                    score / classify
                            │
        ┌───────────────────┼────────────────────┐
        ▼                   ▼                    ▼
     automatic          agent repair          governance
      repair                                   decision
        │                   │                    │
        └───────────────────┼────────────────────┘
                            ▼
                         receipt
                            │
                            ▼
                     trusted state
```

Steward's job is not to manufacture work.

A healthy cycle may conclude:

```text
no valuable maintenance debt
→ no dispatch
→ no mutation
→ stop
```

---

# 2. The Tree Does Not Expire

Gaia must stop treating freshness as one property of the entire Tree.

The Tree does not become stale as a single object.

Individual observations and operational surfaces have different freshness characteristics.

Examples:

```text
canonical identity       effectively timeless
upstream release         fast-changing
GitHub stars             slowly changing
link liveness            periodically changing
installability           periodically changing
benchmark result         environment-bound
TrustMagnitude           derived from inputs
fusion topology          governed, not time-expiring
description              editorial, not mirrored upstream
```

Therefore:

> **Observations accrue freshness debt. Canonical identity does not.**

This changes the maintenance question from:

> Is Gaia Skill Tree up to date?

to:

> What maintenance debt currently exists, how important is it, and what authority is required to resolve it?

---

# 3. Observed Gaia and Canonical Gaia

Gaia should distinguish between two states of knowledge.

## Observed

Gaia has credible machine-readable evidence that something exists, changed, failed, or behaved a certain way.

Observed state may be created automatically.

Examples:

- a new upstream release exists;
- a source URL now returns 404;
- a repository gained stars;
- a component disappeared upstream;
- installation failed in a clean environment;
- a possible new capability was discovered;
- a benchmark generated a receipt;
- two skills were repeatedly co-activated.

Observed state is not automatically canonical truth.

## Canonical

Gaia has governed the claim into the authoritative capability system.

Canonical decisions may affect:

- identity;
- generic mapping;
- fusion topology;
- suite structure;
- prestige;
- TrustMagnitude;
- schema;
- lifecycle;
- permanent provenance.

Canonical state therefore carries a higher authority threshold.

The flow becomes:

```text
world
  ↓
observation
  ↓
Gaia knows something happened
  │
  ├── mechanically safe consequence
  │        ↓
  │     automatic maintenance
  │
  └── governed consequence
           ↓
       canonical decision
```

Gaia can therefore remain **current in awareness** without pretending that every observation has already received canonical governance.

---

# 4. Maintenance Debt

Steward represents unresolved maintenance as structured debt.

A debt item is not merely an issue or task.

It is a normalized statement that:

> The current trusted state and the latest relevant observation differ in a way that may warrant action.

Examples:

```text
upstream_release_advanced
evidence_source_dead
installability_failed
generated_projection_drift
mirror_mismatch
cli_contract_drift
dependency_risk_changed
knowledge_contradiction
benchmark_freshness_expired
unclassified_discovery
```

Every debt item should include at minimum:

```yaml
id:
kind:
subject:
observedAt:
source:
currentState:
observedState:
confidence:
importance:
freshness:
decisionImpact:
estimatedCost:
authorityClass:
status:
```

Debt must be deduplicated by semantic identity rather than by individual workflow execution.

Repeated observation of the same unresolved condition should strengthen or refresh one debt item, not create endless issues.

---

# 5. Priority

Steward should prefer expected maintenance value rather than frequency.

Conceptually:

```text
priority ∝

importance
× confidence
× decision impact
× exposure
× freshness need

÷ expected cost
```

Other modifiers may include:

- reversibility;
- blast radius;
- accumulated age;
- repeated failure;
- strategic relevance;
- availability of deterministic proof.

Uncertainty alone does not create work.

Age alone does not create work.

A scheduled wake-up does not imply model dispatch.

---

# 6. Authority Classes

Maintenance authority must be classified before model or harness selection.

A stronger model never receives stronger authority merely because it is more capable.

## Class A — Machine-Owned Maintenance

Objective, reversible, mechanically verifiable work.

Examples:

- source hashes;
- upstream release detection;
- GitHub star refresh;
- link liveness;
- deterministic generated projections;
- exact mirror synchronization;
- reproducible install probes;
- cache refresh;
- index recomputation from unchanged rules;
- deterministic formatting or generated-artifact repair.

Desired end state:

```text
detect
→ repair
→ verify
→ integrate
```

without founder involvement.

Class A should normally use zero LLM tokens.

## Class B — Bounded Autonomous Repair

Work that requires interpretation but has a narrow authority envelope and strong verification.

Examples:

- exact documentation drift;
- CLI contract repairs;
- deterministic test or flake repairs;
- narrow upstream reconciliation;
- repository hygiene with proven ownership;
- knowledge corrections where sources of truth do not conflict.

Pattern:

```text
Steward debt packet
      ↓
builder
      ↓
candidate repair
      ↓
independent verifier
      ↓
policy
  ┌───┴────┐
safe     ambiguous
 │           │
integrate   escalate
```

Class B autonomy should expand only through measured evidence.

## Class C — Governance Decision

Changes whose correctness depends on product, ontology, prestige, or irreversible interpretation.

Examples:

- new generic capability;
- ambiguous generic mapping;
- fusion topology;
- suite semantics;
- Origin changes;
- promotions or demotions;
- prestige rules;
- TrustMagnitude policy;
- schema or meta shifts;
- irreversible provenance rulings;
- major release decisions;
- meaningful public visual direction.

Class C belongs in a deduplicated founder decision queue.

The founder should increasingly interact only with Class C.

---

# 7. Sensors

Existing automation should become sensors feeding Steward rather than independent maintenance philosophies.

Potential sensors include:

```text
Upstream Watcher
Evidence Health Check
Stargazer Heartbeat
Source Curation
installability probes
registry validators
generated-state checks
CI health
dependency/security checks
CLI contract checks
benchmark controller
Skill Zero launcher telemetry
```

A sensor observes.

It does not independently decide the governance model for its finding.

Sensors should emit normalized observations or debt candidates.

Steward decides what happens next.

---

# 8. Routines

`founder/ROUTINES.md` remains the catalog of engineering stewardship capabilities.

Routines are not clocks.

They are repair operators.

Incorrect model:

```text
Tuesday
→ Architecture Doctor runs
```

Correct model:

```text
dependency/coupling evidence
→ architecture debt
→ Steward selects Architecture Doctor
```

A routine should be invoked only because an existing finding maps to its stated outcome.

The routine must not create work merely to justify its own execution.

---

# 9. Tree Keeper

Steward may dispatch long-running agent work through a bounded role called **Tree Keeper**.

Tree Keeper does not receive the instruction:

> Maintain Gaia Skill Tree.

It receives:

> Resolve this Steward-selected debt inside this authority envelope.

A dispatch packet should contain:

```yaml
finding:
evidence:
authorityClass:

allowedPaths:
allowedCommands:

prohibitedChanges:

stopConditions:
proofContract:
escalationConditions:

budget:
model:
harness:
```

Tree Keeper may continue autonomously while:

- its authority remains valid;
- the task remains within scope;
- proof is obtainable;
- no stop condition fires.

It must stop and escalate when the nature of the problem changes.

---

# 10. Founder Interaction

Steward should optimize for founder attention as a scarce governance resource.

The desired founder experience is not:

```text
daily reports
weekly PR approval
monthly cleanup
periodic backlog triage
```

It is:

```text
Gaia resolved bounded maintenance autonomously.

Two governance decisions require founder judgment.
```

A founder digest should contain only matters whose outcome changes the constitution, ontology, prestige, product direction, or other Class C state.

Routine housekeeping must not become a recurring founder ritual.

---

# 11. Cost Doctrine

Maintenance should follow the same economic principle as Gaia benchmarking:

> **maximize expected information or maintenance value per token spent.**

Preferred order:

```text
deterministic code
      ↓
cheap classification
      ↓
bounded agent
      ↓
strong verifier
      ↓
founder
```

Do not use an agent to perform work that a hash comparison, API request, validator, graph algorithm, HEAD request, or deterministic test can answer.

Model intelligence should concentrate where ambiguity survives machinery.

---

# 12. Push Before Poll

Polling is necessary while Gaia does not control upstream systems.

It should not remain the only long-term maintenance architecture.

Gaia should eventually support contributor-generated maintenance receipts.

Conceptually:

```text
upstream skill repository
        ↓
      release
        ↓
gaia sync / Gaia Action
        ↓
signed maintenance receipt
        ↓
Gaia validates
        │
        ├── Class A consequence
        │       ↓
        │   automatic
        │
        └── governed consequence
                ↓
             review
```

Potential receipt contents:

```text
canonical skill identity
release version
commit SHA
SKILL.md hash
component manifest
installation contract
provenance
optional benchmark receipts
```

Polling then becomes fallback infrastructure for non-participating upstreams.

---

# 13. Relationship to Skill Heaven and Arbor

Steward is not merely repository maintenance infrastructure.

Its debt and observation architecture can become a shared pattern across the Gaia ecosystem.

Under the **Skill Heaven** runtime umbrella, the **Skill Zero** launcher may
eventually emit:

- runtime observations;
- benchmark candidates;
- capability interaction evidence;
- abnormal churn;
- failed compositions;
- recovery behavior.

These can enter the same general flow:

```text
observe
→ assess uncertainty/debt
→ prioritize
→ experiment or repair
→ receipt
→ update interpretation
```

Steward therefore moves Gaia toward the observation-driven architecture described in `ENDGAME.md` rather than away from it.

---

# 14. Success Condition

Steward succeeds when Gaia Skill Tree can be left unattended for meaningful periods while:

- volatile observations continue refreshing;
- deterministic drift repairs itself;
- bounded repair work progresses;
- stale or invalid evidence is surfaced honestly;
- unknowns remain explicitly unknown;
- no unauthorized canonical judgment occurs;
- founder decisions accumulate only when genuinely necessary.

The target is not zero maintenance.

It is **maintenance that knows who should perform it**.

---

# 15. North Star

Gaia Steward should turn maintenance from a founder activity into a property of the system.

The desired state is:

> **Gaia can observe change, measure its own maintenance debt, resolve what it is authorized to resolve, spend intelligence only where needed, and escalate only decisions worthy of governance.**

The Tree should keep growing even when its founder is building somewhere else.