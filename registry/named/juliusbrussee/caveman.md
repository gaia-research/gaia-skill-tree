---
id: juliusbrussee/caveman
name: Caveman
contributor: juliusbrussee
origin: false
genericSkillRef: context-compression
status: named
level: 1★
description: Ultra-compressed agent communication mode that strips articles, filler
  words, and narration from prompts/output to cut token usage; ships lite/full/ultra
  intensity tiers plus wenyan variants and multi-agent support.
createdAt: '2026-08-06'
updatedAt: '2026-08-30'
title: The Caveman Codex
timeline:
- timestamp: '2026-08-06T05:11:31Z'
  action: add
  contributor: unknown
  details: Added named skill juliusbrussee/caveman
- timestamp: '2026-08-06T05:11:52Z'
  action: rank_up
  contributor: unknown
  details: Origin status set to true.
- timestamp: '2026-08-06T05:11:52Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/JuliusBrussee/caveman/blob/main/skills/caveman/SKILL.md
- timestamp: '2026-08-06T05:11:52Z'
  action: note
  contributor: unknown
  details: Set installable to true
- timestamp: '2026-08-06T05:13:07Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/JuliusBrussee/caveman (type: repo-own)'
- timestamp: '2026-08-06T05:13:08Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://sovgrid.org/blog/caveman-local-benchmark (type:
    benchmark-result)'
- timestamp: '2026-08-06T05:13:27Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.techtimes.com/articles/320756/20260716/jetbrains-tests-caveman-token-skill-86-real-tasks-savings-hit-9-not-65.htm
    (type: benchmark-result)'
- timestamp: '2026-08-06T05:13:27Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/yuritoledo/caveman-skill (type:
    proxy-containment)'
- timestamp: '2026-08-06T05:13:28Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/Shawnchee/caveman-skill (type:
    proxy-containment)'
- timestamp: '2026-08-06T05:13:29Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://getcaveman.dev/ (type: proxy-containment)'
- timestamp: '2026-08-06T05:13:40Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://openagentskills.dev/skills/mattpocock-skills-skills-productivity-caveman
    (type: social-signal)'
- timestamp: '2026-08-06T05:13:41Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://8labs.id/guides/opencode/caveman/ (type: social-signal)'
- timestamp: '2026-08-06T05:14:34Z'
  action: evidence_graded
  contributor: unknown
  details: 'Updated evidence #2 metadata from https://www.techtimes.com/articles/320756/20260716/jetbrains-tests-caveman-token-skill-86-real-tasks-savings-hit-9-not-65.htm;
    changed notes'
- timestamp: '2026-08-06T05:14:35Z'
  action: evidence_graded
  contributor: unknown
  details: 'Updated evidence #6 metadata from https://openagentskills.dev/skills/mattpocock-skills-skills-productivity-caveman;
    changed notes'
- timestamp: '2026-08-06T05:15:47Z'
  action: note
  contributor: unknown
  details: 'Calibrated conservatively at 1-star on intake (Phase 3 ev-adversarial-audit,
    2026-08-06), not bumped to 2-star despite Class C-eligible primary-source repo-own
    evidence. Rationale: real primary source (96.2k stars, MIT, 263 commits, true-owner
    per PR #1464) plus real adoption/distribution signal (2 independent forks + commercial
    extensions + a live doc guide), but the skill''s own ~65-75% token-reduction claim
    is substantially undercut by independent measurement -- sovgrid.org''s own benchmark
    measured only ~31%, and the JetBrains/TechTimes agent benchmark measured only
    ~9% before its source link went dead (403). Both benchmark-result rows are provenance=pending
    (registry/benchmark-sources.json candidates awaiting human-gate promotion) and
    score zero Trust Magnitude as recorded. Rank reflects the gap between marketing
    claim and independent evidence honestly rather than the skill''s own framing.'
- timestamp: '2026-08-06T05:17:30Z'
  action: evidence_removed
  contributor: unknown
  details: 'Removed dead/invalid evidence: https://sovgrid.org/blog/caveman-local-benchmark'
- timestamp: '2026-08-06T05:17:31Z'
  action: evidence_removed
  contributor: unknown
  details: 'Removed dead/invalid evidence: https://www.techtimes.com/articles/320756/20260716/jetbrains-tests-caveman-token-skill-86-real-tasks-savings-hit-9-not-65.htm'
- timestamp: '2026-08-06T11:12:46Z'
  action: note
  contributor: unknown
  details: 'Clarification: the 2026-08-06T05:17:30Z removal of the sovgrid.org/blog/caveman-local-benchmark
    benchmark-result row was mislabeled ''dead/invalid evidence'' in that entry''s
    details. The source was verified LIVE (Phase 4 link validation, 2026-08-06) --
    it was withdrawn because scripts/generateBenchmarkProjection.py requires a pre-existing
    benchmarkId in registry/benchmark-sources.json and no gaia dev verb exists to
    register one; forcing it through would have bypassed the human-gate promotion
    this pipeline explicitly avoids. Only the TechTimes/JetBrains row (403 dead) was
    actually dead. This note corrects the record rather than rewriting the prior entry.'
- timestamp: '2026-08-29T17:15:50Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 0.79, grade (none) -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
links:
  github: https://github.com/JuliusBrussee/caveman/blob/main/skills/caveman/SKILL.md
installable: true
evidence:
- source: https://github.com/JuliusBrussee/caveman
  evaluator: mbtiongson1
  date: '2026-08-06'
  type: repo-own
  notes: 'Primary source / official repository. Standalone, MIT-licensed, actively
    maintained; dedicated site at caveman.so. Star count verified live 2026-08-06:
    96.2k (consistent with discovery-packet figure of 96,128). Repo predates the now-removed
    mattpocock/skills copy by 13 days (created 2026-04-04 vs. 2026-04-17). README''s
    own ~65-75% output-token-reduction claim is self-reported and NOT independently
    corroborated -- see benchmark-result rows below, both of which measure substantially
    lower real-world savings (31% and 9%).'
  commits: 263
- source: https://github.com/yuritoledo/caveman-skill
  evaluator: mbtiongson1
  date: '2026-08-06'
  type: proxy-containment
  notes: 'Independent fork / alternative implementation, similar token-cut claims
    (75%) to the primary source; 3 commits. Classified proxy-containment per founder
    ruling on PR #1464 (2026-08-06): "Independent forks can be considered proxy evidence."
    Weighted as proxy evidence, not equivalent to a primary-source benchmark; TM formula
    requires externalStars>=10000 to score (no star count supplied for this fork --
    CLI currently has no --external-stars flag to record one; row is audit-trail evidence,
    contributes 0 to Trust Magnitude).'
- source: https://github.com/Shawnchee/caveman-skill
  evaluator: mbtiongson1
  date: '2026-08-06'
  type: proxy-containment
  notes: Independent fork / alternative implementation focused on removing narration/filler
    text; measured ~61% average reduction (self-reported by fork). 69 stars, 9 forks,
    6 commits (well below the 10,000-external-star TM scoring floor for proxy-containment).
    Classified proxy-containment per the same founder ruling (independent forks count
    as proxy evidence, not primary validation).
- source: https://getcaveman.dev/
  evaluator: mbtiongson1
  date: '2026-08-06'
  type: proxy-containment
  notes: 'Commercial / product extension per founder''s own type label on PR #1464
    ("Commercial / product extension") -- a third-party full-stack build on the same
    capability (gateway, memory layer, a Caveman Code agent) claiming ~2x fewer tokens.
    Also mirrored at https://caveman.so. NOT an independent fork of the repository
    and NOT independent validation of the primary skill''s efficiency claim -- it
    is a commercial consumer/extension of the capability, weighted and classified
    accordingly (vendor-claim language excluded from scoring framing).'
- source: https://openagentskills.dev/skills/mattpocock-skills-skills-productivity-caveman
  evaluator: mbtiongson1
  date: '2026-08-06'
  type: social-signal
  notes: 'Ecosystem / distribution evidence -- listed across multiple third-party
    skill registries (OpenAgentSkills, ClaudSkills, 8Labs docs) with install stats
    and multi-agent packaging references. Factual note: this URL slug still points
    at the old mattpocock-skills path rather than juliusbrussee/caveman; third-party
    re-indexing to the true-owner repo is outside this pipeline''s scope. LINK DEAD
    as of Phase 4 (2026-08-06): HTTP 404 Not Found. No view-count metric supplied
    by source, so no --views passed (would score 0 under the 1000-view floor regardless).
    Flagged, not formally disputed: gaia dev verify --dispute requires genuine 4-star
    Verifier status, which no actor holds in this registry yet.'
- source: https://8labs.id/guides/opencode/caveman/
  evaluator: mbtiongson1
  date: '2026-08-06'
  type: social-signal
  notes: Documentation / adoption guide -- practical install/usage instructions for
    coding agents (OpenCode) adopting caveman. Guide last updated 2026-07-28. No view-count
    metric supplied by source, so no --views passed.
verification:
  firstEvidenceAt: '2026-08-06T05:13:07Z'
trustMagnitude: 0.79
overallTrustGrade: ungraded
trustMagnitudeInputHash: f01c835d6267af2328bb08eba4c119aea179df212647f16ddf14c8ef239b26ab
---

## Installation
Add installation instructions here.
