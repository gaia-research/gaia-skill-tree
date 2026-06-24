---
name: gaia-trace-timeline
description: Audit and repair Gaia user-tree timelines so every skill's current rank is explained by its Hero's Journey. Use when a skill's rank changed (especially a demotion) but the contributor profile timeline/chart still shows the old rank, when the user asks to "trace what happened" to a skill's rank, or to backfill missing demote/rank_up events before a release.
version: 1.0.0
---

# gaia-trace-timeline

The profile **Hero's Journey** (rank chart + event list) is rendered from the
contributor's **user tree** (`skill-trees/<owner>/skill-tree.json`) — its
`timeline[]` and `unlockedSkills[]`. Rank changes are often applied on the
**registry node** (`registry/named/<contrib>/<skill>.md` `timeline:`, via
`gaia dev calibrate` / `reclassify`) and never mirrored onto the user tree, so a
skill silently charts at its old rank (e.g. a 3★→1★ demotion that never shows).

This skill audits that drift and backfills the missing events so each timeline
**explains** the current rank.

## When to use

- "Semantic-cache is 1★ now but the timeline never shows the demotion."
- "Trace what happened to `<handle>/<skill>`."
- "Check `<contributor>`'s timeline for the 1★ skills."
- Before a release, to clear `validate_timelines` failures.

## Workflow

1. **Find the drift.** The CI gate is the source of truth:
   ```bash
   python scripts/validate_timelines.py
   ```
   It lists every owned named skill whose `unlockedSkills` level or latest
   level-bearing timeline event disagrees with the **current registry level**
   (from `registry/named-skills.json`).

2. **Trace one skill (dry-run).** Inspect the registry node's documented
   level-change events before writing anything:
   ```bash
   python scripts/trace_timeline.py <handle>/<slug>
   ```
   It prints each `demote`/`rank_up` it would append, labelled
   `(from registry node)` when the `.md` records it, or `(reconciled)` when the
   change was applied with **no source event** anywhere (an undocumented
   registry-side recalibration) — in which case it synthesizes one clearly
   labelled event dated just after the skill's latest existing event.

3. **Apply.** Mutating `gaia dev` flows need Verifier auth; in CI/automation set
   `GAIA_OPERATOR_OVERRIDE=1`.
   ```bash
   # one skill
   GAIA_OPERATOR_OVERRIDE=1 python scripts/trace_timeline.py <handle>/<slug> --apply
   # or every drifting skill at once
   GAIA_OPERATOR_OVERRIDE=1 python scripts/trace_timeline.py --all --apply
   ```
   This appends the missing events (with `previousValue`/`newValue` so the rank
   chart plots them), sets each `unlockedSkills` level to the current registry
   level, and rebuilds its `levelHistory` from the full event run.

   For a single hand-authored event, the CLI is equivalent:
   ```bash
   gaia dev timeline <handle>/<slug> --user <owner> --action demote \
     --timestamp 2026-06-02T23:48:18Z --notes "Star-Bar hard reset (META §2.4): …"
   ```
   (The CLI has no flag for `previousValue`/`newValue`; `trace_timeline.py`
   fills them so the chart renders — prefer it for level changes.)

4. **Regenerate & verify.**
   ```bash
   GAIA_OPERATOR_OVERRIDE=1 gaia docs build      # regenerate profiles/charts
   python scripts/validate_timelines.py           # must print ✓
   ```

## Tracing the *reason* (for the event note)

When you want an accurate note, cross-reference git history — demotions usually
land in a sweep commit:

```bash
git log --oneline -- registry/named/<handle>/<slug>.md
git log --oneline --all | grep -iE "demot|star-bar|calibrat|reclassif"
```

Common causes, with the META reference to cite:
- **Star-Bar hard reset (META §2.4):** a 3★+ skill lost / never had a verified
  GitHub **blob** link → hard reset to 1★.
- **Reclassification / registry-only:** `installable: false` or type change
  (e.g. Unique→Basic) caps the rank.
- **Evidence rot / dead link:** broken evidence demerit.

## Guardrails

- Only a contributor's **own** named skills (`<owner>/slug`) are audited — the
  ones whose history their profile presents.
- Never hand-edit the `timeline[]` to fabricate ranks; let `trace_timeline.py`
  mirror the registry record or write a **labelled** reconciliation event.
- Keep the registry node (`.md`) and the user tree consistent; the `.md`
  timeline is the authoritative source the tool reads.
- After applying, `git checkout` the timestamp-only churn in `registry/gaia.json`,
  `docs/graph/gaia.json`, `registry/gaia.gexf`, `docs/css/tokens.css` (per the
  CLAUDE.md "isolate generated artifacts" rule) before committing.
