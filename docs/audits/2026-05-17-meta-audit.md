# Gaia Meta Audit: 2026-05-17

**Date:** 2026-05-17
**Auditors:** META Agent
**Scope:** Scan Gaia registry and real-skill catalog entries for candidates that may need review because they are outdated, superseded, overpromoted, weakly sourced, stale, duplicate, or incorrectly mapped.

## Summary of Findings

During the meta-audit scan, multiple red flags were identified:

1.  **Seed Evidence Drift on 4★+ Skills:** Several high-level skills (Extra and Ultimate) are still using old `gaia-registry/gaia` placeholder URLs that no longer exist, rather than concrete community usage evidence.
2.  **Repo-Root Catalog Entries:** Multiple high-profile entries in `real-skills.json` (such as `karpathy-autoresearch`, `devin-ai-autonomous-swe`) map to generic repository roots instead of specific `SKILL.md` or playbook files.
3.  **Heavyweight Dependencies:** Several skills (`agentic-workflow-design`, `deployment-automation`, `stealth-browser-interaction`, `voice-agent`) have known heavyweight dependencies that act as demerits, but this was verified as structurally sound in the schema.

## Prioritized Audit Queue

| Priority | Target | Why review | Suggested audit action | Source files |
|---|---|---|---|---|
| P0 | `autonomous-research-agent` (6★ Ultimate) | Uses `gaia-registry/gaia` seed evidence (`docs/evidence/seed.md`) which resolves as missing. | Require live, composable evidence before retaining 6★ apex confidence. Replace seed evidence with current primary evidence. | `registry/nodes/ultimate/autonomous-research-agent.json` |
| P0 | `recursive-self-improvement` (5★ Ultimate) | Uses `gaia-registry/gaia` seed evidence (`docs/evidence/seed.md`) which resolves as missing. | Require live, composable evidence before retaining 5★. | `registry/nodes/ultimate/recursive-self-improvement.json` |
| P0 | `multi-agent-orchestration-v` (5★ Ultimate) | Uses `gaia-registry/gaia` seed evidence (`docs/evidence/seed.md`) which resolves as missing. | Require live, composable evidence before retaining 5★. | `registry/nodes/ultimate/multi-agent-orchestration-v.json` |
| P1 | `autonomous-debug` (4★ Extra) | Uses `gaia-registry/gaia` seed evidence (`docs/evidence/autonomousDebug.md`) which resolves as missing. | Replace with live evidence or demote below Hardened. | `registry/nodes/extra/autonomous-debug.json` |
| P1 | `ghostwrite` (4★ Extra) | Uses `gaia-registry/gaia` seed evidence (`docs/evidence/ghostwrite.md`) which resolves as missing. | Replace with live evidence or demote below Hardened. | `registry/nodes/extra/ghostwrite.json` |
| P1 | `knowledge-harvest` (4★ Extra) | Uses `gaia-registry/gaia` seed evidence (`docs/evidence/knowledgeHarvest.md`) which resolves as missing. | Replace with live evidence or demote below Hardened. | `registry/nodes/extra/knowledge-harvest.json` |
| P1 | `plan-and-execute` (4★ Extra) | Uses `gaia-registry/gaia` seed evidence (`docs/evidence/planAndExecute.md`) which resolves as missing. | Replace with live evidence or demote below Hardened. | `registry/nodes/extra/plan-and-execute.json` |
| P2 | `karpathy-autoresearch` (Real Skill) | Source URL is a repository root (`https://github.com/karpathy/autoresearch`) instead of a specific `SKILL.md` or playbook. | Update to specific documentation file, or downgrade status. | `registry/real-skills.json` |
| P2 | `devin-ai-autonomous-swe` (Real Skill) | Source URL is a repository root (`https://github.com/cognition-labs/devin`) instead of a specific `SKILL.md` or playbook. | Update to specific documentation file, or downgrade status. | `registry/real-skills.json` |
