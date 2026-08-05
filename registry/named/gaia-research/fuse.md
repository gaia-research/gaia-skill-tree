---
id: gaia-research/fuse
name: Fuse
contributor: gaia-research
origin: false
genericSkillRef: skill-fusion
status: named
level: 2★
description: 'Composes multiple named skill implementations for a single contributor
  into a unified ultimate or suite skill node: collecting component IDs, verifying
  node existence, researching evidence, writing the ultimate node, back-linking derivatives
  on components, updating registry indexes, and opening a pull request.'
createdAt: '2026-07-08'
updatedAt: '2026-08-05'
timeline:
- timestamp: '2026-07-08T10:19:43Z'
  action: add
  contributor: unknown
  details: Added named skill gaia-research/skill-fuse
- timestamp: '2026-07-08T10:21:52Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gaia-research/gaia-skill-tree (type:
    repo-own)'
- timestamp: '2026-07-08T10:22:00Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gaia-research/gaia-skill-tree/blob/main/.agents/skills/gaia-fuse-full-suite/SKILL.md
    (type: self-attestation)'
- timestamp: '2026-07-08T10:22:20Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 2★ to 2★
- timestamp: '2026-07-08T10:22:40Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/gaia-research/gaia-skill-tree/blob/main/.agents/skills/skill-fuse/SKILL.md
- timestamp: '2026-07-08T20:47:22Z'
  action: name
  contributor: unknown
  details: Promoted from awakened to named.
- timestamp: '2026-07-08T20:47:37Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 2★ to 2★
- timestamp: '2026-08-03T15:11:27Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/gaia-research/skill-fuse/blob/main/SKILL.md
- timestamp: '2026-08-03T15:11:33Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gaia-research/skill-fuse (type:
    repo-own)'
- timestamp: '2026-08-03T15:11:47Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from _install_section.md'
- timestamp: '2026-08-05T06:29:04Z'
  action: rename
  contributor: unknown
  details: Renamed named skill from gaia-research/skill-fuse to gaia-research/fuse
evidence:
- source: https://github.com/gaia-research/gaia-skill-tree
  evaluator: unknown
  date: '2026-07-08'
  type: repo-own
  notes: gaia-skill-tree repo — 2884 commits, 24 contributors; skill-fuse SKILL.md
    added in intake PR
  commits: 2884
  contributors: 24
  grade: B
- source: https://github.com/gaia-research/gaia-skill-tree/blob/main/.agents/skills/gaia-fuse-full-suite/SKILL.md
  evaluator: unknown
  date: '2026-07-08'
  type: self-attestation
  notes: In production use — fuses contributor skill sets into ultimates/suites
  grade: C
- source: https://github.com/gaia-research/skill-fuse
  evaluator: unknown
  date: '2026-08-03'
  type: repo-own
  notes: Standalone skill-fuse repo (gaia-research org) — public, install.sh, SKILL.md,
    works without Gaia
  stars: 2
  commits: 10
  contributors: 1
verification:
  firstEvidenceAt: '2026-07-08T10:21:52Z'
links:
  github: https://github.com/gaia-research/skill-fuse/blob/main/SKILL.md
title: Skill Fusion
---

## Installation
Install into Claude Code, Cursor, Windsurf, or any harness that supports agent skill directories:

```bash
bash <(curl -sL https://raw.githubusercontent.com/gaia-research/skill-fuse/main/install.sh)
```

The installer auto-detects `.agents/skills/`, `.claude/skills/`, or `.cursor/rules/` and writes the skill there.

**Manual install:** clone or copy `SKILL.md` (and the `reference/` directory) from [gaia-research/skill-fuse](https://github.com/gaia-research/skill-fuse) into your target skills directory.

After install, trigger from any agent conversation:

```
/fuse shape + audit
```
