# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the right-hand column to match whatever vocabulary you actually use.

## Priority — `P0`–`P4`

One ladder for the whole repo. `/gaia-triage`, `/gaia-meta-audit`, `/gaia-meta-sweep`, and `/gaia-issue-resolver` all mean the same thing by each rung; do not introduce a second priority vocabulary.

| Label | Meaning                                                                                | Behaviour   |
| ----- | -------------------------------------------------------------------------------------- | ----------- |
| `P0`  | Critical integrity violation or active breakage (unsupported top-rank claim, secrets in a diff, site dark, `main` red) | Interrupts  |
| `P1`  | Structural correctness — dead evidence links, Star Bar gaps, broken contracts, lockstep drift | Schedules   |
| `P2`  | Attribution and sourcing issues; upgrades to working surfaces                            | Queues      |
| `P3`  | Registry hygiene, duplicate clusters, backlog enhancements                               | Queues      |
| `P4`  | Documentation cleanup, placeholder bodies, generated-output drift                        | Queues      |

## Impact size

| Label  | Blast radius |
| ------ | ------------ |
| `XS`   | Trivial fix, single config value |
| `S`    | Minor scoped adjustment, isolated touch-up |
| `M`    | Standard scoped task — one command, one field, one workflow |
| `L`    | Cross-component change, non-trivial backfill |
| `XL`   | Architecture-level refactor, substantial registry debt |
| `XXL`  | Core schema, authorization, or site-wide parity |
| `Epic` | Umbrella spanning multiple sub-issues across domains |

Size labels are applied as plain strings in the triage matrix today; they are not yet declared in `.github/labels.yml`, so **do not apply them with `gh issue edit`** until they are (see the warning below).

## Wayfinder — cartography labels

| Label                 | Meaning |
| --------------------- | ------- |
| `wayfinder:map`       | The map issue for one too-big effort; its tickets are child issues |
| `wayfinder:research`  | Ticket (AFK) — surface a fact a decision waits on |
| `wayfinder:prototype` | Ticket (HITL) — build a cheap rough artifact to react to |
| `wayfinder:grilling`  | Ticket (HITL) — conversation; the default type |
| `wayfinder:task`      | Ticket — manual work that unblocks a decision |

Every wayfinder ticket carries exactly one `wayfinder:<type>` label, and may stack ordinary repo labels (`tech-debt`, `trust-model`, a priority) on top. See `.agents/skills/wayfinder/SKILL.md`.

## `.github/labels.yml` is authoritative — a label not in it gets deleted

`.github/workflows/labels-sync.yml` reconciles the tracker's labels from `.github/labels.yml` on every push to `main` that touches that file, with `skip-delete: false`. **Any label not declared there is deleted off live issues at the next sync.**

So: to add a label, add it to `.github/labels.yml` in a PR. Never `gh label create` an ad-hoc label and assume it survives — `wayfinder:map`, `wayfinder:research`, and `wayfinder:task` were created that way, carried live issues for a week, and were one labels.yml push away from being wiped before they were declared (2026-09-01).
