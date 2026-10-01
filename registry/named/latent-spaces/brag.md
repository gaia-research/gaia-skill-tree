---
id: latent-spaces/brag
name: brag
contributor: latent-spaces
origin: true
genericSkillRef: project-launch-video-production
status: named
level: 3★
description: Turn the current project website into a short, polished, shareable launch
  video using Hyperframes. Use when someone says "/brag", "let's brag about this",
  "make a launch video", "turn this into a video", or wants to share what they built.
  Reads the project code directly — no live URL or screenshots needed.
createdAt: '2026-09-27'
updatedAt: '2026-09-27'
title: Project Launch Director
links:
  github: https://github.com/latent-spaces/brag/blob/c893c5ed52aed84e3e2ee56787de869fccdae6b0/skills/brag/SKILL.md
timeline:
- timestamp: '2026-09-26T16:33:46Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill latent-spaces/brag
- timestamp: '2026-09-26T16:34:05Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from generated-output/curate-discovery/brag-20260925/installation.md'
- timestamp: '2026-09-26T16:34:12Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/latent-spaces/brag/blob/c893c5ed52aed84e3e2ee56787de869fccdae6b0/skills/brag/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-09-26T16:34:19Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/latent-spaces/brag (type: repo-own)'
- timestamp: '2026-09-26T16:45:10Z'
  action: rank_up
  contributor: mbtiongson1
  details: Origin status set to true.
- timestamp: '2026-09-26T16:45:10Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from generated-output/curate-discovery/brag-20260925/installation.md'
- timestamp: '2026-09-26T16:45:15Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 3★
evidence:
- source: https://github.com/latent-spaces/brag/blob/c893c5ed52aed84e3e2ee56787de869fccdae6b0/skills/brag/SKILL.md
  updatedAt: '2026-10-01'
  evaluator: mbtiongson1
  date: '2026-09-27'
  type: github-stars-own
  notes: GitHub REST stargazers at verification; upstream /brag SKILL.md is one of
    two distinct skill files in the repo.
  stars: 12621
  skillCountInRepo: 2
  sourceStartedAt: '2026-06-16'
  grade: A
- source: https://github.com/latent-spaces/brag
  evaluator: mbtiongson1
  date: '2026-09-27'
  type: repo-own
  notes: GitHub GraphQL default-branch history count and REST contributor count; host-repository
    maintenance, not independent quality evidence.
  commits: 34
  contributors: 7
  skillCountInRepo: 2
  sourceStartedAt: '2026-06-16'
  grade: B
verification:
  firstEvidenceAt: '2026-09-26T16:34:12Z'
---

## Installation
Install the upstream `/brag` skill from [latent-spaces/brag](https://github.com/latent-spaces/brag):

```bash
npx skills add https://github.com/latent-spaces/brag --skill brag
```

Or in Claude Code:

```text
/plugin marketplace add latent-spaces/brag
/plugin install brag@brag
```

Run `/brag` inside a project. The full workflow requires Node.js 22+, FFmpeg on `PATH`, Hyperframes (`npx hyperframes doctor`), and its companion skills (`hyperframes-core`, `hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`, `hyperframes-cli`). On Claude Opus 5.5, `/brag` defaults to the bundled `/brag-slim`; request `/brag --full` to use the Hyperframes workflow. [Upstream instructions](https://github.com/latent-spaces/brag/blob/c893c5ed52aed84e3e2ee56787de869fccdae6b0/README.md).
