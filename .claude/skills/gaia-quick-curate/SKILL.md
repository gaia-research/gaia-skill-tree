---
name: gaia-quick-curate
description: >-
  Fully automated single-URL Gaia curation pipeline gated by just 2 human
  checkpoints. Given one repo/skill URL, it runs discovery, evidence
  verification, Trust Magnitude appraisal, star calibration, ingest, and PR
  merge as a 25-state machine — pausing only at Gate 1 (confirm the proposed
  generic mapping) and Gate 2 (approve the evidence + proposed stars). Use when
  you have exactly one source URL and want end-to-end automation with minimal
  interaction. Trigger phrases: "/gaia-quick-curate", "quick curate <url>",
  "automate curation from this URL", "curate and merge this repo", "2-gate
  curation", "run the automated pipeline on <url>". For batch/multi-page runs
  use gaia-curate-dynamic; for crawler branches use gaia-bot-curate; for pending
  intake proposals use gaia-draft-curate.
version: 1.0.0
argument-hint: "<url> [--generic] [--discover] [--resume] [--status]"
---

# gaia-quick-curate

The **automated** counterpart to the manual pipeline. One URL in, one merged PR
out, with exactly **two human gates**. Everything between the gates runs without
prompting. This skill drives a 25-state machine that checkpoints to disk after
every transition, so any run is resumable.

> **Prefer to drive each phase by hand?** Use [/gaia-full-pipeline](../gaia-full-pipeline/SKILL.md)
> (routing) or [/gaia-consult](../gaia-consult/SKILL.md) (command lookup). This
> skill is the *automated* path; those are the *manual* path.

---

## Command syntax

```
gaia curate <url> [--generic] [--discover] [--resume] [--status]
```

| Flag | Effect |
|---|---|
| `<url>` | The single source page or repo URL to curate. Required unless `--resume`/`--status`. |
| `--generic` | Treat the target as a new provisional **generic** skill rather than a named implementation. |
| `--discover` | Run the optional evidence-discovery phase (Firecrawl search for benchmarks/papers/social signal) before verification. Requires `FIRECRAWL_API_KEY`; skips gracefully when absent. |
| `--resume` | Resume the most recent (or specified) run from its last checkpointed state. |
| `--status` | Print the current state, gate status, and control-panel link for a run, then exit without mutating anything. |

---

## Gate 1 — confirm the proposed mapping (terminal UX)

After discovery + normalization the machine halts at `AWAIT_GATE1_MAPPING` and
prints the proposed mapping for your confirmation:

```
┌─ GATE 1 · PROPOSED MAPPING ─────────────────────────────────────┐
│ Candidate : owner/repo · SKILL.md @ 3f9a1c2                      │
│ Source     : https://github.com/owner/repo/blob/main/SKILL.md   │
│ Content SHA: sha256:9b1e…c7                                      │
│                                                                  │
│ Proposed mapping →  generic:  pdf-form-filling  (existing)      │
│                     named:    owner/pdf-form-filling            │
│                     type:     basic                             │
│                                                                  │
│ Alternatives: [1] document-extraction  [2] NEW_GENERIC          │
└──────────────────────────────────────────────────────────────────┘
Confirm this mapping?  [Y] yes  [n] reject  [e] edit  [d] defer  ›
```

- **Y / yes** — accept the mapping and advance to evidence verification.
- **n / reject** — mark `NOT_A_SKILL` / rejected; the run terminates cleanly.
- **e / edit** — choose an alternative generic, switch to `NEW_GENERIC`, or edit
  the named identity / upstream URL, then re-present.
- **d / defer** — checkpoint as `DEFERRED`; resume later with `--resume`.

---

## Gate 2 — approve evidence + proposed stars (approval screen)

After the evidence lake is verified and Trust Magnitude appraised, the machine
halts at `AWAIT_GATE2_APPROVAL` and prints the full appraisal:

```
┌─ GATE 2 · EVIDENCE & CALIBRATION ───────────────────────────────┐
│ Skill: owner/pdf-form-filling                                    │
├──────────────┬──────────┬───────┬───────────────────────────────┤
│ Evidence Type│ Grade    │ Live? │ Source                        │
├──────────────┼──────────┼───────┼───────────────────────────────┤
│ repo-own     │ B        │  ✓    │ github.com/owner/repo         │
│ github-stars │ B (1.2k) │  ✓    │ github.com/owner/repo         │
│ arxiv        │ A        │  ✓    │ arxiv.org/abs/2401.01234      │
│ social-signal│ C        │  ✓    │ youtube.com/watch?v=…         │
├──────────────┴──────────┴───────┴───────────────────────────────┤
│ Trust Magnitude : 41.7   →  Grade B                              │
│ Proposed stars  : ★★★☆☆  (3★)   [current: unranked]             │
└──────────────────────────────────────────────────────────────────┘
Approve this evidence set and 3★ calibration?  [Y] yes  [n] no  ›
```

- **Y / yes** — ingest the evidence rows, write the calibration, build, validate,
  open + merge the PR, and close the intake issue.
- **n / no** — halt at `GATE2_REJECTED`; nothing is ingested. Re-run or defer.

Benchmark-result rows always require this explicit human gate — they never
auto-approve.

---

## The 25-state machine

```
 1  INIT
 2  FETCH_SOURCE
 3  RESOLVE_SKILL_MD
 4  PARSE_FRONTMATTER
 5  HASH_CONTENT
 6  LOAD_GENERIC_SNAPSHOT
 7  NORMALIZE_CANDIDATE
 8  DEDUPE
 9  PROPOSE_MAPPING
10  AWAIT_GATE1_MAPPING        ← human gate 1
11  GATE1_RESOLVED
12  WRITE_DISCOVERY_PACKET
13  PUSH_INTAKE
14  OPEN_DRAFT_PR
15  EV_DISCOVERY              (optional, --discover)
16  EV_COLLECTION
17  EV_STAR_VERIFICATION
18  EV_BENCHMARK_VERIFICATION
19  EV_ADVERSARIAL_AUDIT
20  EV_LINK_VALIDATION
21  APPRAISE_TM
22  AWAIT_GATE2_APPROVAL       ← human gate 2
23  INGEST_AND_CALIBRATE
24  MERGE_PR
25  CLOSE_INTAKE
```

Terminal off-ramps: `DEFERRED`, `GATE1_REJECTED`, `GATE2_REJECTED`, `FAILED`
(each checkpointed so a `--resume` can pick up or a human can inspect).

---

## Run state location

Every run persists its state to disk after each transition:

```
.gaia/runs/curate/<run-id>/state.json
```

The `state.json` records the current state name, the resolved mapping, the
verified evidence rows, the appraised TM, gate decisions, and the intake issue /
PR numbers. `gaia curate --status` reads this file; `--resume` restarts from it.

---

## Control-panel comment (on the intake issue)

When the run opens the intake issue (state `PUSH_INTAKE`), it posts a single
**control-panel** comment that it edits in place as the machine advances:

```markdown
### 🤖 gaia-quick-curate · control panel
**Run:** `curate/2f8c1a` · **State:** `EV_LINK_VALIDATION` (20/25)
**Source:** https://github.com/owner/repo/blob/main/SKILL.md

| Gate | Status |
|------|--------|
| Gate 1 · mapping   | ✅ confirmed → `pdf-form-filling` |
| Gate 2 · calibration | ⏳ awaiting approval |

**Draft PR:** #1234 · **Last update:** 2025-01-14T09:31Z
_Resume locally with:_ `gaia curate --resume curate/2f8c1a`
```

The comment is the single source of truth for anyone watching the issue; it is
rewritten (not appended) on each state change.

---

## When to use vs other curate skills

| Your input | Use |
|---|---|
| One repo / skill **URL** | **this skill** (`/gaia-quick-curate`) |
| A **batch** of pages / multi-source volume | [/gaia-curate-dynamic](../gaia-curate-dynamic/SKILL.md) |
| Crawler `bot/*` **branches** | [/gaia-bot-curate](../gaia-bot-curate/SKILL.md) |
| **Pending** intake proposals in `registry-for-review/` | [/gaia-draft-curate](../gaia-draft-curate/SKILL.md) |

For a manual, phase-by-phase walk-through of everything this skill automates, see
[/gaia-full-pipeline](../gaia-full-pipeline/SKILL.md).

---

## Implementation file locations

| Concern | Path |
|---|---|
| CLI command entry | `src/gaia/cli/commands/curate.py` |
| State machine + transitions | `src/gaia/curate/state_machine.py` |
| Gate 1 / Gate 2 terminal UX | `src/gaia/curate/gates.py` |
| Run state (per run) | `.gaia/runs/curate/<run-id>/state.json` |
| Control-panel comment renderer | `src/gaia/curate/control_panel.py` |
| Discovery packet schema/validator | `scripts/validate_discovery_packet.py` |
