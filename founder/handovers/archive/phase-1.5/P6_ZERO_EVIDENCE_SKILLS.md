# P6 — Skills with Zero Evidence Array (Invisible to Scorer)

**Generated:** 2026-06-19  
**Source:** Registry audit — 62 named skills have NO `evidence:` array in frontmatter. Zero TM contribution regardless of any inherited evidence.

These are candidates for a future manual curation pass. For each: verify publicly accessible evidence exists before adding any row.

---

## Priority A — High-value, evidence clearly exists

| Skill | Stars / Signal | Recommended type | Notes |
|---|---|---|---|
| `safishamsi/graphify` | 68,766 stars, arxiv 2408.03910, YT video | `github-stars-own` + `arxiv` + `social-signal` | No evidence array at all — biggest gap |
| `stanfordnlp/dspy` | ~20k stars, arxiv 2310.03714 (700+ citations) | `arxiv` + `repo-own` | arxiv in body prose only |
| `openai/few-shot-learning` | GPT-3 paper, `links.arxiv` set | `arxiv` | `links.arxiv` field exists but inert |
| `openai/self-consistency` | arxiv 2203.11171, `links.arxiv` set | `arxiv` | Same |
| `pexp13/sentiment-analysis` | 8-row evidence table in body text | `arxiv` + `peer-review` | Body table has SemEval/AAAI refs |
| `browserbase/stagehand` | ~10k+ stars likely | `github-stars-own` | Verify star count first |

## Priority B — Medium-value, needs star count verification

| Skill | Contributor | Note |
|---|---|---|
| `huggingface/huggingface-papers` | huggingface | HuggingFace papers hub — social signal candidate |
| `huggingface/hf-cli` | huggingface | HF CLI repo |
| `huggingface/semantic-cache` | huggingface | proxy-containment evidence in data lake |
| `huggingface/pr-agent` | huggingface | Codium PR-Agent, high stars |
| `google-deepmind/protein_sequence_similarity_search` | google-deepmind | Has 2 evidence rows already (richest generic) |
| `devin-ai/autonomous-swe` | devin-ai | Benchmark result + arxiv in data lake |
| `nexu-io/open-design` | nexu-io | shadcn-ui proxy-containment 116k stars in data lake |

## Priority C — Low-value or installable: false

The following 49 skills have no evidence array. Most are suite components (sub-skills of garrytan/gstack, obra/superpowers, ruvnet/*) that will inherit from their parent suite's fusion-recipe once I3 lands. No action needed on these individually — they gain evidence through suite inheritance.

**garrytan/gstack components (no evidence array, inherits from suite):**
- garrytan/browse, garrytan/canary, garrytan/careful, garrytan/codex, garrytan/connect-chrome, garrytan/cso, garrytan/design-consultation, garrytan/design-html, garrytan/design-review, garrytan/design-shotgun, garrytan/devex-review, garrytan/document-generate, garrytan/document-release, garrytan/freeze, garrytan/gstack-upgrade, garrytan/guard, garrytan/investigate, garrytan/land-and-deploy, garrytan/learn, garrytan/office-hours, garrytan/plan-ceo-review, garrytan/plan-design-review, garrytan/plan-devex-review, garrytan/plan-eng-review, garrytan/qa, garrytan/qa-only, garrytan/retro, garrytan/review, garrytan/setup-browser-cookies, garrytan/setup-deploy, garrytan/setup-gbrain, garrytan/ship, garrytan/unfreeze

**obra/superpowers components (no evidence array, inherits from suite):**
- obra/caching-patterns, obra/error-handling, obra/feature-flags, obra/logging-monitoring, obra/performance-testing

**Misc (installable: false or too small):**
- `0xdarkmatter/pytest-patterns` (263 stars, below floor)
- `safishamsi/graphify-v2` (suite component)
- `gooseworks/notte-browser` (736 stars, below 10k floor for stars-own)
- `martin-stepanoski/automcp` (small, no public star data)
- `changkun/evolve-ai` (no public data found)
- `glincker/glasskube` (check star count)
- `yundu-ai/n8n-workflow-generator` (needs verification)

---

## How to add evidence

Use the CLI — never direct frontmatter edit:

```bash
# Example: add repo-own evidence
gaia dev evidence safishamsi/graphify \
  --source "https://github.com/safishamsi/graphify" \
  --class A \
  --type github-stars-own \
  --evaluator mbtiongson1 \
  --notes "68,766 GitHub stars as of 2026-06-19 (verified via firecrawl validation report)"
```

**Always verify the source URL is live** (check `founder/sources/collectors/verification/firecrawl_validation_report_2026_06_19.md`) before adding.
