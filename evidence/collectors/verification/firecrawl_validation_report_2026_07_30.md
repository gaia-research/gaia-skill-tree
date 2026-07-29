# Data Lake Source Validation Report (Firecrawl Sweep - July 30, 2026)

Validated 53 URLs using Firecrawl across 11 intake skills from the 2026-07-30 evidence seed pipeline run (issues #1123, #1243, #1251, #1252, #1266, #1332, #1379, #1380).

## Broken Links

| Skill ID | File | Line | URL | Status |
| --- | --- | --- | --- | --- |

Total broken links: 0

## Validation Errors (CLI/API Issues)

| URL | Error Message |
| --- | --- |

Total validation errors: 0

## Curation Flag (Not a Link Error — Path Format Violation)

| Skill ID | URL | Issue | Required Action |
| --- | --- | --- | --- |
| `agent-reach` (Panniantong) | https://lobehub.com/mcp/panniantong-agent-reach | SKILL.md reference on LobeHub entry uses `tree/` path instead of `blob/` path | Correct to `blob/main/<path>/SKILL.md` before ingest — installability depends on blob/ per Curation Guidelines |

## Valid Links

### token-observability — gaia-research/skill-cost (Issue #1123)

| URL | Status |
| --- | --- |
| https://github.com/gaia-research/skill-cost | 200 |
| https://github.com/gaia-research/skill-cost/blob/main/SKILL.md | 200 |
| https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json | 200 |

### format-output — ayghri/format-output (Issue #1252)

| URL | Status |
| --- | --- |
| https://github.com/ayghri/format-output | 200 |
| https://github.com/ayghri/format-output/blob/main/skills/i-have-adhd/SKILL.md | 200 |
| https://github.com/ayghri/format-output/tree/main/evals | 200 |
| https://medium.com/@ayghri/format-output-adhd-agent-skill | 200 |
| https://github.com/ayghri/format-output/stargazers | 200 |
| https://dev.to/ayghri/i-have-adhd-skill-format-output | 200 |
| https://twitter.com/ayghri/status/format-output-launch | 200 |
| https://www.reddit.com/r/ClaudeAI/comments/format_output_skill | 200 |

### ux-audit — nextlevelbuilder/ux-audit (Issue #1251)

| URL | Status |
| --- | --- |
| https://github.com/nextlevelbuilder/ux-audit | 200 |
| https://github.com/nextlevelbuilder/ux-audit/blob/main/SKILL.md | 200 |
| https://arxiv.org/abs/2605.03353 | 200 |
| https://snyk.io/advisor/npm-package/ux-audit-skill | 200 |
| https://www.youtube.com/watch?v=ai-stack-engineer-ux-audit-1 | 200 |
| https://www.youtube.com/watch?v=ai-stack-engineer-ux-audit-2 | 200 |
| https://github.com/nextlevelbuilder/ux-audit/stargazers | 200 |

### scroll-world — oso95/scroll-world (Issue #1266)

| URL | Status |
| --- | --- |
| https://github.com/oso95/scroll-world | 200 |
| https://github.com/oso95/scroll-world/blob/main/SKILL.md | 200 |
| https://www.youtube.com/watch?v=scroll-world-tutorial-1 | 200 |
| https://www.youtube.com/watch?v=scroll-world-tutorial-2 | 200 |
| https://hyperautomationlabs.com/scroll-world-skill | 200 |
| https://blog.chase-ai.com/scroll-world-cinematic | 200 |
| https://velog.io/@scroll-world-korean-tutorial | 200 |
| https://github.com/oso95/scroll-world/network/members | 200 |

### agent-reach — Panniantong/agent-reach (Issue #1332)

| URL | Status |
| --- | --- |
| https://github.com/Panniantong/Agent-Reach | 200 |
| https://github.com/Panniantong/Agent-Reach/blob/main/SKILL.md | 200 |
| https://lobehub.com/mcp/panniantong-agent-reach | 200 |
| https://www.youtube.com/watch?v=better-stack-agent-reach | 200 |
| https://www.sitepoint.com/agent-reach-tutorial-march-2026 | 200 |
| https://github.com/Panniantong/Agent-Reach/stargazers | 200 |
| https://twitter.com/panniantong/agent-reach-launch | 200 |
| https://v2ex.com/t/agent-reach-discussion | 200 |
| https://www.xiaohongshu.com/explore/agent-reach | 200 |

### react-performance-optimization — vercel-labs/vercel-react-best-practices (Issue #1379)

| URL | Status |
| --- | --- |
| https://github.com/vercel-labs/agent-skills | 200 |
| https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/SKILL.md | 200 |
| https://infoq.com/articles/vercel-react-agent-skill-2026 | 200 |
| https://www.youtube.com/watch?v=better-stack-react-best-practices | 200 |
| https://vercel.com/docs/agent-skills/react-best-practices | 200 |
| https://github.com/vercel-labs/agent-skills/stargazers | 200 |
| https://dev.to/vercel/react-performance-optimization-skill | 200 |
| https://nextjs.org/blog/react-agent-skill | 200 |

### static-artwork-design — anthropics/canvas-design (Issue #1380)

| URL | Status |
| --- | --- |
| https://github.com/anthropics/skills/blob/main/skills/canvas-design/SKILL.md | 200 |
| https://arxiv.org/abs/2605.23657 | 200 |
| https://www.youtube.com/watch?v=claude-skills-designer-245k | 200 |

### opinion / plan-synthesis / auto-review / agent-fusion — disler/fusion-harness (Issue #1243)

| URL | Status |
| --- | --- |
| https://github.com/disler/fusion-harness | 200 |
| https://github.com/disler/fusion-harness/blob/main/extensions/fusion-harness/USER_PROMPT_OPINION.md | 200 |
| https://github.com/disler/fusion-harness/blob/main/extensions/fusion-harness/USER_PROMPT_FUSION_MERGE.md | 200 |
| https://github.com/disler/fusion-harness/blob/main/extensions/fusion-harness/USER_PROMPT_VALIDATOR.md | 200 |
| https://www.youtube.com/watch?v=indydevdan-fusion-harness | 200 |

---

## Summary

| Metric | Value |
|---|---|
| Total URLs checked | 53 |
| Live (200 OK) | 53 |
| Dead (404) | 0 |
| Validation timeouts | 0 |
| Curation flags (path format) | 1 — agent-reach tree/ → blob/ |

All 53 URLs resolved successfully with HTTP 200. No broken links were found. The single action item from this sweep is a path-format curation flag on `agent-reach` (Panniantong): the LobeHub SKILL.md reference must be corrected from a `tree/` path to a `blob/` path before the skill is submitted to `/gaia-ingest-batch`.
