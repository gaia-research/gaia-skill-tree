---
name: gaia-quick-curate
description: >-
  Execute checkpointed pre-L4 CHAIN discovery for one exact SKILL.md URL or a
  declared inventory of one to five candidates. Produces discovery-packet-v2
  packets, advisory assessments and shared reconciliation, then stops for human
  L4 review. Does not submit, ingest, calibrate, promote or merge.
version: 1.1.0
argument-hint: "<blob-url> --named-identity <contributor/slug> | --inventory <path> | --resume <run-id> [--status]"
---

# gaia-quick-curate

Read [CURATION-CORE.md](../gaia-curate/CURATION-CORE.md). CHAIN uses the existing
source fetch, prefill, packet and assessment primitives with atomic local
checkpoints. This is **pre-L4 discovery execution**, not an automated downstream
curation or merge engine. Repository-wide source enumeration is not implemented;
provide an exact GitHub `SKILL.md` blob URL or an explicit bounded inventory.

## Commands

```bash
gaia curate <blob-url> --named-identity contributor/skill-name
gaia curate --inventory candidates.json
gaia curate --resume <run-id> --status
gaia curate --resume <run-id>
```

A declared inventory is a JSON array of one to five rows containing
`candidateId`, exact lowercase `namedIdentity` (`contributor/slug`), and
`sourceUrl`. Candidate identity is not the named identity or generic ID.
Immutable source revisions are retained when independently available; branch
URLs remain explicitly unresolved and require live freshness checks.

The runtime fetches and checkpoints source bytes, freezes the inventory and
generic snapshot before semantic processing, executes candidates sequentially,
persists owned digest-named packets and assessments, and reconciles the complete
inventory. Default prefill remains advisory: deferred packets are honestly shown
as deferred, never silently relabeled as approved mappings. Configured semantic
workers remain model-neutral.

## Recovery and L4

State lives at `.gaia/curation/runs/<run-id>/state.json`. Attempts are charged
before execution. Retries target the failed candidate; completed packets are
reused only after source, catalog, packet and assessment freshness checks.
Budget exhaustion preserves every remaining candidate as an explicit deferral.
Status inspection does not execute freshness checks or advance the workflow.

The complete L4 inventory includes review-ready, deferred, rejected and proven
duplicate outcomes. **Review-ready is not human-approved.** The runtime always
stops at `AWAITING_L4_REVIEW`; a local decision field cannot advance it.
Independent protected human authorization is required at the ratify/submission
boundary. If that ceremony is unavailable, the workflow remains pending; flags,
comments, reviewer metadata and operator override are not substitutes.

For an existing intake, supply `--batch-id`, `--intake-issue-number` and
`--intake-issue-url` when creating the run. Resume preserves these references.
Continue its existing evidence route; do not open another intake.

## Boundaries and related workflows

Neither CHAIN nor FAN-OUT mutates canonical registry data or creates intake
issues, promotion PRs, evidence rows, grades or calibration decisions.
FAN-OUT uses `curation/fanout.py` callable workers and the same
`curation/reconciliation.py` envelope; see
[gaia-curate-dynamic](../gaia-curate-dynamic/SKILL.md).

After authorized L4, the existing
[full pipeline](../gaia-full-pipeline/SKILL.md) controls intake, evidence
verification, ingestion and calibration. Final merge remains founder-gated.
