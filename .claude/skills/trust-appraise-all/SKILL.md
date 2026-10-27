---
name: trust-appraise-all
description: Compatibility alias for gaia-tm-inspect; explicitly inspect an existing named skill or request the TM leaderboard.
disable-model-invocation: true
version: "1.2.0"
genericSkillRef: registry-inspection
---

# Trust appraisal compatibility entry point

Read and follow [gaia-tm-inspect](../gaia-tm-inspect/SKILL.md), passing through the skill ID or `--leaderboard` and all other user context. For proposed skills or suites instead, use [trust-appraise](../trust-appraise/SKILL.md).
