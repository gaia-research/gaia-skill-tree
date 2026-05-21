# Meta-Audit Handover: Skill Rating Calibration

**Branch:** `review/meta/skill-rating-audit`
**Status:** Completed initial calibration pass; pushed to remote.

## Completed Work

### 1. Foundational Promotions (0★ → 3★/4★)
These skills were previously unranked but have significant evidence and named implementations:
- **UX Audit (`ux-audit`)**: 4★. Consolidated evidence from `martin-stepanoski/nielsen-heuristics-audit` (Origin) and `pbakaus/impeccable`.
- **Test-Driven Development (`test-driven-development`)**: 3★. Consolidated `addy-osmani/test-driven-development` (Origin) and `mattpocock/tdd`.
- **Skill Discovery (`skill-discovery`)**: 3★. Sourced from `vercel/find-skills`.
- **Question Answer (`question-answer`)**: 4★. Added `garrytan/office-hours` as evidence alongside SQuAD 2.0.
- **Gaia Audit (`gaia-audit`)**: 4★. Reflected its current 7-phase discipline and role in meta-auditing.

### 2. Pseudo-Ultimate Demotions (5★ → 3★)
These skills were overrated as Ultimates and have been reclassified as Extra Skills:
- `autonomous-research-agent` (Karpathy AutoResearch)
- `grill-with-docs` (Matt Pocock variant)
- `multi-agent-orchestration-v` (Ruflo Flow Nexus Swarm)
- `agentic-workflow-design` (Ruflo SPARC Methodology)
- `github-platform-mastery` (Ruflo GitHub Suite)

### 3. Structural Consolidation
- **Merged `mattpocock/tdd`** into the origin file `addy-osmani/test-driven-development.md` to eliminate double-canon entries.

## Remaining Items / Next Steps

1. **Verify Frontend Visuals:** The build pipeline has been run, but the visuals in the worktree `../gaia-frontend-investigation` should be manually verified to ensure 5-star glyphs are gone for the demoted skills.
2. **Audit remaining 4★ skills:** The original prompt suggested there are many 4-star skills that might be overrated. A follow-up `/gaia-meta-audit` should focus on:
    - `autonomous-web-research` (Currently 4★)
    - `dispatching-parallel-agents` (Currently 4★)
    - `tree-of-thought` (Currently 4★)
    - `ubiquitous-language` (Currently 4★)
3. **Registry Normalization:** Continue searching for generic skill IDs that are acronyms (like `tdd`) and ensure they are merged into their full-name counterparts (`test-driven-development`).

## How to Resume
1. Switch to branch `review/meta/skill-rating-audit`.
2. Run `gaia meta-audit` to identify the next batch of over-promoted candidates.
3. Use `gaia appraise <skillId>` to check evidence depth for current 4★ nodes.
