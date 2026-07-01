---
name: gaia-trace-timeline
description: >
  Audit and repair Gaia user-tree timelines so every skill's current rank is
  explained by a chain of Hero's Journey events. Trigger this skill when:
  a contributor's profile chart shows a stale rank (e.g. still shows 3★ after
  a demotion to 1★); someone asks to "trace what happened" to a skill's rank;
  `validate_timelines.py` is failing in CI; you need to backfill missing
  `demote` or `rank_up` events before cutting a release; a skill was
  reclassified or Star-Bar-reset and the user tree was never updated; or any
  time the registry node and user tree disagree on a skill's current level.
  Uses `scripts/trace_timeline.py` (dry-run + apply) and
  `scripts/validate_timelines.py` (CI gate). Do NOT hand-edit `timeline[]`
  arrays — the script synthesises properly labelled events with
  `previousValue`/`newValue` so the rank chart plots correctly.
version: 1.0.0
---

# gaia-trace-timeline

The profile **Hero's Journey** (rank chart + event list) is rendered from the
contributor's **user tree** (`skill-trees/<owner>/skill-tree.json`) — its
`timeline[]` and `unlockedSkills[]`. Rank changes are typically applied to the
**registry node** (`registry/named/<handle>/<skill>.md`) via
`gaia dev calibrate` / `reclassify`, but that change is never automatically
mirrored into the user tree. The result: a skill silently charts at its old
rank — a 3★→1★ demotion that looks like it never happened.

This skill finds that drift and backfills the missing events so each timeline
**explains** the current rank.

## Workflow

### 1. Find the drift

The CI gate is the authoritative source of disagreements:

```bash
python scripts/validate_timelines.py
```

It lists every owned named skill whose `unlockedSkills` level or latest
level-bearing timeline event disagrees with the **current registry level**
in `registry/named-skills.json`. Run this first — it gives you the complete
work list so you do not miss any drifting skill.

### 2. Trace one skill (dry-run)

Before writing anything, inspect what events would be appended:

```bash
python scripts/trace_timeline.py <handle>/<slug>
```

The output labels each event `(from registry node)` when the `.md` records
the level change, or `(reconciled)` when no source event exists anywhere
(an undocumented registry-side recalibration). The reconciled case synthesises
a clearly labelled event dated just after the skill's latest existing event —
it does not invent history, it documents the gap honestly.

### 3. Apply

Set `GAIA_OPERATOR_OVERRIDE=1` so the mutating script clears the Verifier
auth gate (required in CI and any non-Verifier environment):

```bash
# Single skill
GAIA_OPERATOR_OVERRIDE=1 python scripts/trace_timeline.py <handle>/<slug> --apply

# All drifting skills at once
GAIA_OPERATOR_OVERRIDE=1 python scripts/trace_timeline.py --all --apply
```

Prefer `trace_timeline.py` over the raw CLI for level changes — the script
fills `previousValue`/`newValue` on each event so the rank chart plots
correctly. The CLI equivalent (`gaia dev timeline ... --action demote`) omits
those fields and produces a flat event line in the chart.

Use the raw CLI only for a one-off hand-authored note:

```bash
gaia dev timeline <handle>/<slug> --user <owner> --action demote \
  --timestamp 2026-06-02T23:48:18Z --notes "Star-Bar hard reset (META §2.4): …"
```

### 4. Regenerate and verify

```bash
GAIA_OPERATOR_OVERRIDE=1 gaia docs build   # regenerate profiles/charts
python scripts/validate_timelines.py        # must print ✓ for all skills
```

Before committing, discard timestamp-only churn in generated artifacts:

```bash
git checkout HEAD -- registry/gaia.json docs/graph/gaia.json \
  registry/gaia.gexf docs/css/tokens.css
```

These files get touched by `gaia docs build` even when the content is
unchanged — staging them inflates the diff and trips unrelated CI guards.

## Finding the reason for a demotion note

An accurate event note prevents future confusion. Cross-reference git history
— demotions usually arrive in a sweep commit:

```bash
git log --oneline -- registry/named/<handle>/<slug>.md
git log --oneline --all | grep -iE "demot|star-bar|calibrat|reclassif"
```

Common causes and the META reference to cite in the note:

| Cause | Note text |
|---|---|
| Star-Bar hard reset | `Star-Bar hard reset (META §2.4): no verified blob link` |
| Reclassification | `Type change (Unique→Basic) caps max rank` |
| Evidence rot / dead link | `Broken evidence demerit — link no longer resolves` |

## Guardrails

- Only audit a contributor's **own** named skills — the ones whose history
  their profile presents. Do not touch other users' trees.
- Never hand-edit `timeline[]` to fabricate ranks. Always route through
  `trace_timeline.py` so events carry the correct shape and `levelHistory`
  is rebuilt from the full event run.
- The registry `.md` timeline is the authoritative source the script reads;
  keep it and the user tree consistent.
