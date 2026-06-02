# Meta Audit Sweep

**Branch**: `review/meta/sweep`
**Date**: 2026-06-01

## P1: Liveness Heartbeat Failures
37 evidence URLs are dead. Most point to `https://github.com/gaia-registry/gaia/blob/main/docs/evidence/...`. These need to be re-evidenced or removed.
*Suggested action: Run `gaia dev evidence` with fresh links or `gaia dev calibrate <id> 2★` if evidence is lost.*

## P1: Brand-Coupled Generic IDs
Generics containing 'agent' or 'gaia' (now that dify/gaia patches are in, these remain):
- `worker-agent-dispatch`
- `sequential-agent-pipeline`
- `agent-memory-platform`
- `multi-agent-debate`
- `agent-handoff`
- `conversational-agent`
- `voice-agent`
- `agentic-workflow-design`
- `dispatching-parallel-agents`
- `multi-agent-orchestration-v`
- `agent-eval`
- `agent-memory-learning`
- `subagent-driven-development`
- `agent-environment-setup`

*Suggested action: `gaia dev rename` to abstract noun phrases.*

## P1: Level Overshoots (Named > Generic)
Many named skills claim >0 stars but are mapped to 0-star generics. 
Example top offenders:
- `mattpocock/skills` (Named: 6★, Generic: 0)
- `mattpocock/engineering` (Named: 5★, Generic: 0)
- `ruvnet/ruflo` (Named: 6★, Generic: 0)
- `ruvnet/agentdb` (Named: 5★, Generic: 0)

*Suggested action: direct YAML edit to demote the named skill to the generic's level, or calibrate the generic to match (if evidenced).*

## P1: Missing `links.github` (for 3★+ skills)
- `mattpocock/engineering` (5★)
- `mattpocock/personal` (4★)
- `mattpocock/skills` (6★)
- `mattpocock/productivity` (4★)
- `stanfordnlp/dspy` (3★)
- `sickn33/mcp-builder` (3★)
- `openai/self-consistency` (4★)
- `openai/few-shot-learning` (4★)

*Suggested action: Provide a valid installable GitHub URL or mark `installable: false` / demote.*

## P1: Link Casing / Missing SKILL.md
Many URLs point to raw repos or directories instead of `SKILL.md`. Examples:
- `langgenius/backend-code-review.md` -> `.../backend-code-review` (Missing /SKILL.md)
- `devin-ai/autonomous-swe.md` -> `.../cognition-labs/devin`
- `firecrawl/firecrawl.md` -> `.../firecrawl`
- `ruvnet/*` (Many points to `.../ruflo` instead of `.../ruflo/blob/main/.../SKILL.md`)

*Suggested action: Edit YAML `links.github` to append `/SKILL.md` or correct target.*

## P2: Mis-attributed `origin: true`
- `tool-creation`: `anthropic/skill-creator.md` is origin but earliest is `mattpocock/write-a-skill.md`.
- `document-editing`: `anthropic/pptx.md` is origin but earliest is `mattpocock/edit-article.md`.
- `registry-entry-audit`: `mbtiongson1/gaia-audit.md` is origin but earliest is `mbtiongson1/gaia-curation-review.md`.
- `registry-curation`: `mbtiongson1/gaia-curate.md` is origin but earliest is `mbtiongson1/gaia-draft-curate.md`.
- `prompt-optimization`: `stanfordnlp/dspy.md` is origin but earliest is `garrytan/plan-tune.md`.
- `write-report`: `glincker/readme-generator.md` is origin but earliest is `spring-ai/readme-generate.md`.
- `agent-memory-learning`: `ruvnet/agentdb-learning.md` is origin but earliest is `ruvnet/reasoningbank-agentdb.md`.

*Suggested action: Flip `origin: false` on the mis-attributed skill, and `origin: true` on the earliest.*

## P4: Placeholder Bodies
~19 skills have placeholder `## Installation\nAdd installation instructions here.` bodies.
*Suggested action: Backfill actual descriptions into the Markdown body.*