---
name: gaia-quick-curate
description: >-
  Inspect or exercise the paused gaia curate orchestration scaffold for one
  source URL. The command currently persists an INITIALIZED run ledger and
  reports status; its 25 named workflow states and transition methods are a
  design skeleton, not an implemented automated curation or merge pipeline.
  Use only for scaffold development, status inspection, or dry-run contract
  work. For live curation, use gaia-full-pipeline or gaia-consult. Trigger
  phrases: "/gaia-quick-curate", "inspect gaia curate", "curate scaffold",
  "quick curate status". For batch/multi-page runs use gaia-curate-dynamic;
  for crawler branches use gaia-bot-curate; for pending intake proposals use
  gaia-draft-curate.
version: 1.1.0
argument-hint: "<url> [--generic <id>] [--discover] [--dry-run] [--resume <run-id>] [--status]"
---

# gaia-quick-curate

`gaia curate` is currently a **paused orchestration scaffold**. It can create
and persist a run ledger, reload one with `--resume`, and print status. A fresh
run deliberately pauses at `INITIALIZED`; the non-executing transition method
stubs beyond that point were an orchestration skeleton, NOT working automation,
and have been pruned. The CLI does not perform automatic discovery, evidence
verification, ingest, calibration, GitHub issue/PR work, or merging.

Do not describe this skill as an automated two-gate pipeline, claim that it
will advance through all 25 states, or promise "one URL in, one merged PR out."
The state names record the intended workflow shape only.

> For an implemented, human-directed curation workflow, use
> [/gaia-full-pipeline](../gaia-full-pipeline/SKILL.md) for phase routing or
> [/gaia-consult](../gaia-consult/SKILL.md) for command guidance. For outward
> ecosystem intelligence and discovery leads, use [/gaia-frontier](../gaia-frontier/SKILL.md).

## Migration notice

Under the Founder Frontier Ruling (2026-10-26), the unimplemented future-transition
Python stubs in `CurationOrchestrator` were pruned as obsolete scaffolding, NOT
working automation:
- **Outward ecosystem discovery** is canonically owned by `/gaia-frontier`.
- **Manual, bounded L4-gated curation** remains valid and supported via `/gaia-full-pipeline` and `/gaia-consult`.
- **Status inspection and historical ledger loading** are preserved in `gaia curate` and this compatibility skill (`/gaia-quick-curate`).

## Current command surface

```text
gaia curate <url> [--generic <id>] [--discover] [--dry-run]
gaia curate --resume <run-id> [--status]
```

| Input | Current behavior |
|---|---|
| `<url>` | Creates a run ledger, pauses at `INITIALIZED`, and prints status. |
| `--generic <id>` | Records a suggested generic ID; it does not apply a mapping. |
| `--discover` | Records discovery intent; it does not run discovery yet. |
| `--dry-run` | Records dry-run intent; no curation transitions are implemented. |
| `--resume <run-id>` | Loads an existing ledger by run ID. |
| `--status` | Prints the loaded or newly created run's status. |

Run state is stored at:

```text
.gaia/curation/runs/<run-id>/state.json
```

The ledger currently starts in `INITIALIZED`. Although
`src/gaia_cli/curation/state.py` declares 25 intended state names, that list is
retained for historical runs and ledger compatibility, not evidence that an
automated workflow exists. `SCAFFOLD_PAUSE_STATES` in the orchestrator prevents
a fresh run from entering unimplemented transitions.

## Safety and merge authority

The scaffold has no authority to mutate the registry or GitHub today. If its
runtime is implemented later, all registry writes must still use the canonical
Gaia CLI mutation path, approval gates must be explicit and resumable, and the
final merge to `main` must remain founder-gated. This skill must never merge the
final PR to `main`; a human founder makes that decision after reviewing the
evidence, diff, and CI state.

## Live source locations

| Concern | Path |
|---|---|
| CLI command entry | `src/gaia_cli/commands/curate.py` |
| Run ledger and 25-state design skeleton | `src/gaia_cli/curation/state.py` |
| Pause guard and status inspector | `src/gaia_cli/curation/orchestrator.py` |
| URL-resolution helper | `src/gaia_cli/curation/url_resolver.py` |
| Run state | `.gaia/curation/runs/<run-id>/state.json` |

There is no live `src/gaia/curate/state_machine.py`, gate UI, or control-panel
comment renderer. Do not invent those paths or report future components as
implemented.

## When to use another skill

| Need | Use |
|---|---|
| Outward discovery and ecosystem intelligence | [/gaia-frontier](../gaia-frontier/SKILL.md) |
| Implemented phase-by-phase curation | [/gaia-full-pipeline](../gaia-full-pipeline/SKILL.md) |
| Curation command/reference lookup | [/gaia-consult](../gaia-consult/SKILL.md) |
| Batch or multi-source discovery | [/gaia-curate-dynamic](../gaia-curate-dynamic/SKILL.md) |
| Crawler `bot/*` branches | [/gaia-bot-curate](../gaia-bot-curate/SKILL.md) |
| Pending intake proposals | [/gaia-draft-curate](../gaia-draft-curate/SKILL.md) |
