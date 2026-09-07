---
id: heygen-com/hyperframes
name: HyperFrames
contributor: heygen-com
origin: false
genericSkillRef: video-composition
status: named
level: 4★
description: 'Suite orchestrator and router for HyperFrames: programmatic video composition
  framework compiling HTML, CSS, JavaScript, WebGL, WebGPU, and Canvas into production
  videos.'
createdAt: '2026-09-06'
updatedAt: '2026-09-07'
title: HyperFrames
links:
  github: https://github.com/heygen-com/hyperframes/blob/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/skills/hyperframes/SKILL.md
timeline:
- timestamp: '2026-09-06T15:29:17Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill heygen-com/hyperframes
- timestamp: '2026-09-06T15:29:26Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/heygen-com/hyperframes/blob/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/skills/hyperframes/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-09-06T15:29:29Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/heygen-com/hyperframes (type: repo-own)'
- timestamp: '2026-09-06T15:29:31Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/heygen-com/hyperframes/blob/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/skills/hyperframes/SKILL.md
    (type: self-attestation)'
- timestamp: '2026-09-06T15:30:00Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 3★
- timestamp: '2026-09-06T16:21:13Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: 'Updated via `gaia dev fuse`: suiteRef=heygen-com/hyperframes, suiteComponents+=[''heygen-com/hyperframes-core'',
    ''heygen-com/hyperframes-cli'', ''heygen-com/hyperframes-animation'', ''heygen-com/embedded-captions''].'
- timestamp: '2026-09-06T16:21:50Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 3★ to 4★
- timestamp: '2026-09-06T16:48:08Z'
  action: evidence_graded
  contributor: mbtiongson1
  details: 'Updated evidence #0 metadata from https://github.com/heygen-com/hyperframes/blob/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/skills/hyperframes/SKILL.md;
    changed notes, sourceStartedAt'
- timestamp: '2026-09-06T17:24:15Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: 'Updated via `gaia dev fuse`: suiteRef=heygen-com/hyperframes, suiteComponents+=[''heygen-com/hyperframes-keyframes'',
    ''heygen-com/hyperframes-creative'', ''heygen-com/hyperframes-audio'', ''heygen-com/hyperframes-registry'',
    ''heygen-com/media-use'', ''heygen-com/motion-graphics'', ''heygen-com/music-to-video'',
    ''heygen-com/pr-to-video'', ''heygen-com/product-launch-video'', ''heygen-com/remotion-to-hyperframes'',
    ''heygen-com/slideshow'', ''heygen-com/talking-head-recut'', ''heygen-com/faceless-explainer'',
    ''heygen-com/figma''].'
- timestamp: '2026-09-06T17:25:44Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to heygen-com/hyperframes
- timestamp: '2026-09-06T17:44:42Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: 'Updated via `gaia dev fuse`: suiteRef=heygen-com/hyperframes.'
- timestamp: '2026-09-06T17:47:41Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 163.63, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-06T18:00:36Z'
  action: installation_updated
  contributor: mbtiongson1
  details: 'Replaced ## Installation section from /data/data/com.termux/files/usr/tmp/hyperframes-install.j4kT8q/hyperframes.md'
evidence:
- source: https://github.com/heygen-com/hyperframes/blob/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/skills/hyperframes/SKILL.md
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: github-stars-own
  notes: Host repository stars for heygen-com/hyperframes
  stars: 44308
  skillCountInRepo: 20
  grade: A
  sourceStartedAt: '2025-06-16'
- source: https://github.com/heygen-com/hyperframes
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: repo-own
  notes: Live verified repository metrics for heygen-com/hyperframes
  commits: 4199
  contributors: 57
  skillCountInRepo: 20
  grade: B
- source: https://github.com/heygen-com/hyperframes/blob/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/skills/hyperframes/SKILL.md
  evaluator: mbtiongson1
  date: '2026-09-06'
  type: self-attestation
  notes: Upstream orchestrator and router entry point SKILL.md
  grade: C
verification:
  firstEvidenceAt: '2026-09-06T15:29:26Z'
suiteComponents:
- heygen-com/embedded-captions
- heygen-com/faceless-explainer
- heygen-com/figma
- heygen-com/hyperframes-animation
- heygen-com/hyperframes-audio
- heygen-com/hyperframes-cli
- heygen-com/hyperframes-core
- heygen-com/hyperframes-creative
- heygen-com/hyperframes-keyframes
- heygen-com/hyperframes-registry
- heygen-com/media-use
- heygen-com/motion-graphics
- heygen-com/music-to-video
- heygen-com/pr-to-video
- heygen-com/product-launch-video
- heygen-com/remotion-to-hyperframes
- heygen-com/slideshow
- heygen-com/talking-head-recut
trustMagnitude: 163.63
overallTrustGrade: A
trustMagnitudeInputHash: 121fc2097a60cc4a77facdf6a9cca5474518053ba003a0930980deade4d443f0
---

## Installation

Initialize a HyperFrames project with the upstream CLI:

```bash
npx hyperframes init
```

To install or update the upstream HyperFrames entry skill:

```bash
npx skills add heygen-com/hyperframes --skill hyperframes
```

The entry skill is documented in the pinned upstream [SKILL.md](https://github.com/heygen-com/hyperframes/blob/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/skills/hyperframes/SKILL.md).
