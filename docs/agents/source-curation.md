# Source Curation Pipeline

> **Status:** Dry-run only. Auto-PR publishing is NOT implemented.
> **Bot identity:** `nova-gaia`
> **Issue:** [#762](https://github.com/gaia-research/gaia-skill-tree/issues/762)
> **EPIC:** [#855 Sprint B](https://github.com/gaia-research/gaia-skill-tree/issues/855)

## Overview

The source-curation pipeline automates the discovery of evidence sources for
named skills in the Gaia registry. It replaces the manual `/ev-pipeline`
orchestration loop with a scheduled crawler that produces **proposal reports**
-- structured JSON files describing discovered evidence sources, pre-validated
against the `sourceProposal.schema.json` contract.

**Current scope (Phase 1):** The pipeline emits dry-run reports only. No
registry mutation occurs. No auto-PRs are opened. Reports are written to
`generated-output/source-curation/<run-id>/report.json` and reviewed by a
human or the adversarial gate before any action is taken.

## Architecture

```
  Scheduled trigger (cron / manual)
         |
         v
  +-----------------+
  | Crawler Runner  |  <-- Tool-agnostic: dispatches to configured backends
  +-----------------+
         |
         v
  +-----------------+
  | Source Discovery |  <-- Firecrawl, GitHub API, YouTube, arXiv, etc.
  +-----------------+
         |
         v
  +--------------------+
  | Proposal Generator |  <-- Validates against sourceProposal.schema.json
  +--------------------+
         |
         v
  +--------------------+
  | Dedup + Confidence |  <-- Drops duplicates and below-floor proposals
  |     Filter         |
  +--------------------+
         |
         v
  +----------------------------+
  | Dry-Run Report             |  <-- sourceProposalReport.schema.json
  | (generated-output/         |      dryRun: true (enforced by schema)
  |  source-curation/<run-id>/ |
  |  report.json)             |
  +----------------------------+
         |
         v  (FUTURE -- not yet implemented)
  +---------------------+
  | Adversarial Gate    |  <-- 3-skeptic refute pass
  +---------------------+
         |
         v  (FUTURE -- not yet implemented)
  +---------------------+
  | Human Review Gate   |  <-- Reviewer approves before merge
  +---------------------+
         |
         v  (FUTURE -- not yet implemented)
  +---------------------+
  | Auto-PR (ingestion) |  <-- gaia dev evidence + PR
  +---------------------+
```

## Schemas

| Schema | Path | Purpose |
|---|---|---|
| Source Proposal | `registry/schema/sourceProposal.schema.json` | Single evidence source proposal |
| Proposal Report | `registry/schema/sourceProposalReport.schema.json` | Batch of proposals from one crawl run |

### Key constraints enforced by the schemas

- **`dryRun: true` (const):** The report schema enforces `dryRun` as a const
  `true` value. This is a hard stop: no report can be generated with
  `dryRun: false` until the const constraint is relaxed in a future release.

- **`generatedBy: "nova-gaia"` (const):** Only the `nova-gaia` bot identity
  is authorized to generate reports. This is enforced at the schema level.

- **`additionalProperties: false`:** Both schemas reject unknown fields.
  A crawler cannot sneak mutation instructions (e.g. `autoMerge`,
  `secretMutation`) into a proposal.

- **`confidence` range [0, 1]:** Proposals must self-report confidence.
  Proposals below the configurable `confidenceFloor` (default 0.3) are
  dropped before report inclusion.

- **`rationale` minLength 10:** Every proposal must explain why the source
  is relevant, in enough detail for an adversarial reviewer to evaluate
  without visiting the URL.

- **`skillId` pattern enforces named-skill format:** `contributor/skill-name`,
  not a bare generic ID. Proposals target named skills only.

- **`existingEvidenceCheck`:** Idempotency guard. Crawlers must check for
  duplicates against the current registry state before proposing.

## Bot Identity: `nova-gaia`

`nova-gaia` is the bot identity for automated source curation. It is:

- **Read-only in Phase 1:** `nova-gaia` can discover sources and write
  proposal reports to `generated-output/`. It cannot mutate
  `registry/nodes/`, `registry/named/`, or any canonical registry file.

- **Not a GitHub App (yet):** `nova-gaia` does not have GitHub API
  credentials or PR-creation permissions in Phase 1. It is a logical
  identity used in `discoveredBy` and `generatedBy` fields.

- **Not added to meta-guard allowlist:** The `meta-guard.yml` CI workflow
  gates registry mutations by actor identity. `nova-gaia` is intentionally
  NOT in the bot allowlist (`*[bot]`, `jules`, `codex`, `claude-bot`,
  `gemini-bot`). When auto-PR publishing is implemented, `nova-gaia` will
  need to be added to the allowlist -- that decision requires a separate
  review.

## Tool-Agnostic Design

The proposal contract does not prescribe which tools a crawler uses. The
`crawlerBackend` field records which tool produced each proposal, but the
schema accepts any string value. Known backends include:

| Backend | API | Evidence types it can discover |
|---|---|---|
| `github-api` | GitHub REST/GraphQL | `github-stars-own`, `repo-own`, `proxy-containment` |
| `youtube-data-api` | YouTube Data API v3 | `social-signal` |
| `arxiv-api` | arXiv OAI-PMH | `arxiv` |
| `firecrawl-search` | Firecrawl Search | `social-signal`, `peer-review`, `benchmark-result` |
| `firecrawl-scrape` | Firecrawl Scrape | Any (page content analysis) |
| `haunt` | Haunt API | Any (TBD -- tool choice undecided) |
| `puppeteer` | Puppeteer/Playwright | Any (browser automation) |
| `hackernews-algolia` | HN Algolia API | `social-signal` |
| `semantic-scholar` | Semantic Scholar API | `arxiv` |

New backends can be added without schema changes. The `crawlerVersion`
field is optional but recommended for reproducibility.

## Quota and Cost Placeholders

The `quotaCost` (per-proposal) and `quotaSummary` (per-report) fields are
structural placeholders. They carry no enforcement logic in Phase 1.

When budget enforcement is implemented, these fields will be consumed by a
quota manager that:

1. Tracks cumulative spend per backend per billing cycle.
2. Defers crawl runs when budget is exhausted.
3. Prioritizes low-grade skills (C/ungraded) over high-grade skills (A/S)
   for cost efficiency.

The rough cost model from #762:
- Firecrawl: ~$60/mo for 3,500 calls
- GitHub API: free tier (5k/hour authenticated)
- YouTube: free tier (10k units/day)
- Agent dispatch: ~$10/mo (2.1M tokens at Sonnet rates)
- **Estimated total: ~$70/mo for 249 skills**

These numbers are estimates. Actual costs will be tracked in `quotaSummary`
and refined after the first live crawl cycles.

## Adversarial Gate (Future)

The `adversarialReview` field in the proposal schema is designed for the
3-skeptic refute pass described in #762:

1. Each proposal is presented to 3 independent skeptic agents.
2. Each skeptic votes `accept` or `refute` with a reason.
3. Proposals with >=2 refute votes are dropped.
4. Proposals with >=2 accept votes proceed to human review.
5. Split votes (1-1-1, impossible with 3 skeptics) are `deferred`.

The adversarial gate is NOT implemented in Phase 1. The schema supports it
structurally so that when it ships, proposals from older dry-run reports can
be retroactively reviewed without re-crawling.

## Reviewer Gate

**Every automated curation PR needs reviewer/spec-check before merge.**

This is a hard policy requirement. Even when auto-PR publishing is
implemented in a future phase:

1. `nova-gaia` opens a **draft** PR, never a ready-for-merge PR.
2. The PR body includes the proposal report summary and links to the
   dry-run report JSON for full audit.
3. A human reviewer (or the adversarial gate result) must approve before
   the PR can be merged.
4. `meta-guard.yml` enforces that `nova-gaia` is authorized for the
   mutation (requires adding to the allowlist -- separate decision).

## Output Location

Dry-run reports are written to:

```
generated-output/source-curation/<run-id>/report.json
```

This directory is gitignored. Reports are local artifacts consumed by
reviewers and the adversarial gate. They are NOT committed to the
repository or published to GitHub Pages.

Run the deterministic dry-run runner with:

```bash
python3 scripts/sourceCuratorRunner.py --run-id 20260702-dry-run --generated-at 2026-07-02T14:00:00Z
```

By default the runner uses fixture discovery only: no live network calls, no
registry mutation, `dryRun: true`, and `generatedBy: "nova-gaia"`. Pass
`--input seed.json` to supply a local JSON array or an object with a `seeds`
/ `proposals` array.

## Self-Bounding Rules

From #762, the pipeline enforces:

- **Max 5 proposals per skill per cycle:** Prevents flooding.
- **Idempotent:** Re-running on the same skill is a no-op for
  already-known sources (enforced by `existingEvidenceCheck`).
- **Configurable confidence floor:** Default 0.3. Proposals below this
  threshold are dropped before report inclusion.
- **Grade-based scheduling (future):** C/ungraded skills get monthly
  crawls; A-grade quarterly; S-grade annual.

## Testing

Schema validation tests live at:

```
tests/test_source_proposal_schema.py
```

Run with:

```bash
python3 -m pytest tests/test_source_proposal_schema.py -v
```

Test fixtures:

| Fixture | Purpose |
|---|---|
| `source_proposal_valid.json` | Social-signal proposal (YouTube) |
| `source_proposal_valid_github.json` | GitHub stars proposal |
| `source_proposal_valid_reviewed.json` | Proposal with adversarial review |
| `source_proposal_invalid_fields.json` | Bad field values |
| `source_proposal_invalid_missing.json` | Missing required fields |
| `source_proposal_invalid_extra_fields.json` | Extra fields (additionalProperties) |
| `source_proposal_report_valid.json` | Full report with 2 proposals |

## What This PR Does NOT Do

- **No network crawler implementation.** `scripts/sourceCuratorRunner.py` is dry-run fixture/seed driven only.
- **No GitHub Actions workflow.** No `.github/workflows/auto-source-curation.yml`.
- **No registry mutation.** The schemas and tooling cannot write to
  `registry/nodes/` or `registry/named/`.
- **No auto-PR publishing.** `dryRun: true` is enforced as a schema const.
- **No tool selection.** Firecrawl, Haunt, Puppeteer, etc. are all listed
  as potential backends but none is chosen or integrated.
- **No `nova-gaia` GitHub identity.** The bot is a logical name only.
- **No quota enforcement.** Cost fields are structural placeholders.
