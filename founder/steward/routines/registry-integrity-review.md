# Routine — Registry integrity review

| | |
|---|---|
| **Policy rule** | `registry-integrity-review` |
| **Debt kind** | `registry_integrity_failed` |
| **Authority** | Class B — bounded autonomous repair |
| **Sensor** | `registry-integrity` (wired) |
| **Cadence** | Every scan. The daily Class A pulse already observes it; dispatch only when debt is open. |
| **Routine catalog** | #11 — Registry Structure and Installability Examiner |

---

## What it is for

The registry is a graph with rules: every node validates against
`registry/schema/skill.schema.json`, filenames match ids, ids are unique,
prerequisite and derivative references resolve, the prerequisite graph is
acyclic, and each type meets its prerequisite floor from
`registry/schema/meta.json`.

When one of those breaks, the failure is **objective** — the sensor reports the
exact path and the exact violation. What is *not* objective is the correction:
a missing prerequisite reference might be a typo, a renamed node, or a node that
should never have been merged. That gap is why this is Class B and not Class A.

## When it is worth looking

Event-driven. Integrity debt is either open or it is not — there is no
freshness window here, and no value in a scheduled sweep. The daily pulse
observes it; you dispatch when something is actually broken.

If this debt appears immediately after a curation PR merges, prefer reverting
that PR over dispatching a repair. A routine is for drift nobody is holding, not
for a change that is still warm.

## Get the prompt

```bash
gaia steward scan
gaia steward dispatch <debt-id> --prompt
```

## Envelope

Fixed by `POLICY.yaml`; the prompt carries the authoritative copy.

- **May write:** `scripts/**`, `tests/**`
- **Never writes:** `registry/**`, `.agents/skills/**`, `.gaia/steward/**`, `.github/**`, `docs/**`, `founder/**`, `skill-trees/**`
- **May run:** `python scripts/validate.py`, `python scripts/sync_bundled_schemas.py --check`, `python -m pytest`

**`registry/**` is forbidden on purpose, and that is the whole shape of this
routine.** Canonical registry nodes are mutated only by a Verifier running
`gaia dev` verbs (Programmatic-First Policy), which is also what keeps the
timeline honest. So the dispatch does not produce a registry diff — it produces
a *diagnosis plus the exact verb sequence* a Verifier should run, with the
violation reproduced and proof attached. An agent that could edit
`registry/nodes/` directly would be routing around the audit trail the tool
exists to write.

## Stop conditions

1. Fresh local evidence does not reproduce the packet violation.
2. The correction needs a write outside the allowed paths.
3. The correction needs a Class C product or governance decision.
4. The correction cannot be expressed as a `gaia dev` verb sequence.
5. Validation, coverage, or independent proof is incomplete.

Condition 3 is the common one and the important one. "Which generic should this
map to?", "should this node exist at all?", and "does this deserve its rank?"
are all Class C. They go to `gaia steward founder`, never into the diff.

Condition 4 is the CLI-gap escape hatch: if no verb can express the correction,
that gap is the finding. File it as `CLI` + `tech-debt` rather than working
around it.

## Done means

- Every packet violation reproduced from local state before anything changed
- A diff confined to the allowed paths (often empty — that is fine)
- The exact `gaia dev` verb sequence stated for a Verifier to run
- `python scripts/validate.py` clean after that sequence is applied
- Independent review before integration

## Founder notes

- Running the proposed verbs needs Verifier authorization, and CI bots need
  `GAIA_OPERATOR_OVERRIDE=1`. That gate is deliberate: the dispatch proposes,
  a Verifier disposes.
- A Class S regeneration (`gaia dev docs`) is a separate human-gated commit.
  Do not let a repair dispatch quietly regenerate site artifacts.
