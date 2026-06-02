# Meta Audit Sweep

**Branch**: `review/meta/sweep`
**Date**: 2026-06-01

## P1: Liveness Heartbeat Failures
37 evidence URLs are dead. Most point to `https://github.com/gaia-registry/gaia/blob/main/docs/evidence/...`. These need to be re-evidenced or removed.
*Suggested action: Run `gaia dev evidence` with fresh links or `gaia dev calibrate <id> 2★` if evidence is lost.*

## P1: Brand-Coupled Generic IDs
Generics containing 'gaia':
- (None found! The `gaia` instances were cleaned up in upstream patches. `agent` is a valid term and is no longer flagged.)

## P1: Missing `links.github` (for 3★+ skills, excluding suites)
- `stanfordnlp/dspy` (3★)
- `sickn33/mcp-builder` (3★)
- `openai/self-consistency` (4★)
- `openai/few-shot-learning` (4★)

*Suggested action: Provide a valid installable GitHub URL or mark `installable: false` / demote.*

## P1: Link Casing / Missing SKILL.md
Many URLs point to raw repos or directories instead of `SKILL.md` (or `skill.md`). Examples:
- `langgenius/backend-code-review.md` -> `.../backend-code-review`
- `devin-ai/autonomous-swe.md` -> `.../cognition-labs/devin`
- `firecrawl/firecrawl.md` -> `.../firecrawl`
- `ruvnet/*` (Many points to `.../ruflo` instead of `.../ruflo/blob/main/.../SKILL.md`)

*Suggested action: Edit YAML `links.github` to append `/SKILL.md` or correct target.*

## P1: Invalid Evidence (Seed URLs)
- (None found! No remaining seed URLs matching `gaia-registry/gaia/blob/main/docs/evidence` in the actual named skill evidence arrays.)

## P2: Mis-attributed origin (Highest rated should be origin)
- `tool-creation`: `anthropic/skill-creator.md` (Level 2) is origin, but max level is 3.
- `document-editing`: `anthropic/pptx.md` (Level 2) is origin, but max level is 4.
- `vertical-slice-planning`: `mattpocock/to-issues.md` (Level 3) is origin, but max level is 5.
- `design-system-extraction`: `Manavarya09/design-extract.md` (Level 2) is origin, but max level is 4.
- `performance-tuning`: `ruvnet/performance-analysis.md` (Level 2) is origin, but max level is 3.
- `web-scrape`: `firecrawl/firecrawl.md` (Level 2) is origin, but max level is 3.
- `write-report`: `glincker/readme-generator.md` (Level 2) is origin, but max level is 3.
- `finishing-a-development-branch`: `obra/finishing-a-development-branch.md` (Level 2) is origin, but max level is 4.
- `systematic-debugging`: `obra/systematic-debugging.md` (Level 3) is origin, but max level is 4.
- `ux-audit`: `martin-stepanoski/nielsen-heuristics-audit.md` (Level 2) is origin, but max level is 4.
- `browser-control`: `browser-use/browser-harness.md` (Level 2) is origin, but max level is 3.

*Suggested action: Flip `origin: false` on the lower-level skill, and `origin: true` on the highest-rated skill in the generic bucket.*

## P4: Placeholder Bodies
~19 skills have placeholder `## Installation\nAdd installation instructions here.` bodies.
*Suggested action: Backfill actual descriptions into the Markdown body.*