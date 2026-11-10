# Removal record: gaiabot/repo-docs-before-pr

Audit record only. This does NOT restore a live skill: `registry/named/gaiabot/repo-docs-before-pr.md` is deleted and must stay deleted.

## Founder ruling (verbatim)

> Remove from the skill tree: "`gaiabot/repo-docs-before-pr`". This is not a skill.

Source: founder rulings batch 1, 2026-11-06, relayed for #2283. Decision record: `founder/steward/decisions/steward-remove-gaiabot-repo-docs-before-pr.json` (branch `dev/steward-campaign-2026-11-05`). Steward debt: `debt:trust_calibration_drift:gaiabot-repo-docs-before-pr:8e51b0cf3b86a8c9`.

## Final state before removal

Taken from the deleted file at `origin/main` 956b684fe: `status: awakened`, `level: 1★`, `genericSkillRef: write-report`, `trustMagnitude: 36.0`, `overallTrustGrade: C`, `installable: false`, one B-grade `repo` evidence row (https://github.com/gaia-research/gaia-skill-tree, 90 commits, 10 contributors, TM 70.0).

## Preserved named-skill timeline (verbatim frontmatter, 8 events)

This is the `timeline:` block of the deleted file (base lines 34-65), byte for byte:

```yaml
timeline:
- timestamp: '2026-06-10T05:38:16Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/gaia-research/gaia-skill-tree
- timestamp: '2026-06-14T12:32:18Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/gaia-research/gaia-skill-tree
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:36Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-08-06T04:54:21Z'
  action: note
  contributor: unknown
  details: Set installable to false
- timestamp: '2026-09-05T00:00:00Z'
  action: demote
  author: mbtiongson1
  notes: "Demoted from 2★ to 1★ Awakened (status is awakened; 2★+ requires status: named per CONTEXT.md) (#1699)"
  previousValue: 2★
  newValue: 1★
```

## Removal commands (each run with `GAIA_OPERATOR_OVERRIDE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m gaia_cli.main dev ...`)

1. `timeline gaiabot/repo-docs-before-pr --user gaiabot --action demote --previous-value "1★" --notes "..." --no-build` appended a `demote` event to `skill-trees/gaiabot/skill-tree.json`.
2. Direct JSON edit of `skill-trees/gaiabot/skill-tree.json` (CLAUDE.md "Known CLI gap": no `gaia remove-skill`) removed the `unlockedSkills` entry and set `stats.totalUnlocked` from 6 to 5. The user-tree `register` and `demote` events and the new `demote` event remain.
3. `rm gaiabot/repo-docs-before-pr --reason "Removed by founder ruling 2026-11-06 (#2283): not a skill." --yes --no-build`
4. `docs` (regenerates the Class S artifacts and registry-driven mirrors).

Removal PR: #2319 (`review/meta/remove-gaiabot-repo-docs-before-pr`).
