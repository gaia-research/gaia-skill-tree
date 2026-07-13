---
title: "Curation Report: Firecrawl Suite and Origin Recalibration"
author: "Marcus Rafael Tiongson, Curator"
summary: "Five named Firecrawl components plus a capstone enter the registry; five buckets recalibrate to a single origin each; gaia dev fuse timeline bug fixed."
label: "Suite Curation"
abstract: |
  Curation of firecrawl/firecrawl-skills adds five named components and one capstone anchored to 150,087 GitHub stars. The pass also enforces the one-origin-per-bucket rule across five capability buckets, reclassifies the generic fusion anchor from Ultimate to Extra, ships two CLI-only ingestion skills, and corrects an invalid timeline action emitted by gaia dev fuse.
---

## Abstract

This note records the curation of the Firecrawl suite into the registry and the origin recalibrations it triggered across five capability buckets. All figures below are the values written to the registry at curation time. Grade cutoffs are Trust Magnitude S≥250, A≥100, B≥50, C≥20.

## Suite composition

Six nodes were added under the `firecrawl` contributor namespace: five named components and one capstone that anchors the suite.

| Node | Rank | Grade | Trust Magnitude | Capability |
|------|------|-------|-----------------|------------|
| `firecrawl/firecrawl-skills` | 4★ | A | 223.52 | Suite capstone |
| `firecrawl/firecrawl-build-scrape` | 4★ | A | 133.54 | Web scraping to LLM-ready markdown |
| `firecrawl/firecrawl-build-search` | 4★ | A | 107.14 | Web search via the Firecrawl API |
| `firecrawl/firecrawl-build-interact` | 2★ | B | 73.52 | JS/SPA browser interaction |
| `firecrawl/firecrawl-build-onboarding` | 2★ | B | 73.52 | API key and auth setup |
| `firecrawl/firecrawl-research-index` | 2★ | B | 73.52 | Academic literature retrieval |

The generic fusion anchor was reclassified from Ultimate to Extra via `gaia dev reclassify`. The suite is an Extra-tier fusion, not an Ultimate; the taxonomy now matches the component count and the fusion structure.

## Origin recalibration

The one-origin-per-bucket rule allows exactly one canonical origin per capability bucket. Firecrawl curation forced five buckets to converge. The table records the state before and after this pass.

| Bucket | Origin before | Origin after |
|--------|---------------|--------------|
| `web-scrape` | `garrytan/scrape` | `firecrawl/firecrawl-build-scrape` |
| `web-search` | — | `firecrawl/firecrawl-build-search` (sole entry) |
| `browser-control` | `garrytan/browse` | `browser-use/browser-harness` |
| `agent-environment-setup` | — | `firecrawl/firecrawl-build-onboarding` |
| `literature-search` | — | `google-deepmind/literature_search_openalex` |

Two `garrytan/*` origins were removed as part of the convergence. In the `browser-control` bucket, `browser-use/browser-harness` measured 103.59 (Grade A) and ranked up from 3★ to 4★ when it took the origin position.

## What the Trust Magnitude numbers mean for the suite

The capstone sits at 223.52 — Grade A, short of the S≥250 gate. The suite does not clear the S bar on current evidence, and the taxonomy reclassification to Extra reflects that. The two Grade A scrape and search components (133.54, 107.14) carry the suite's signal; the three Grade B components (73.52 each) sit above the B≥50 floor but below the A≥100 line, consistent with their 2★ ranks.

The three identical 73.52 values are not a placeholder. They are the same base evidence apportioned across the interact, onboarding, and research-index components, which share the suite's repository signal without independent per-component adoption data. That is the expected shape for a suite whose primary evidence is one repository: two components draw direct capability signal, three inherit suite standing.

## Evidence

The suite is anchored to `firecrawl/firecrawl`: 150,087 GitHub stars, 5,714 commits, 155 contributors at curation time. YouTube engagement was scraped live through the Firecrawl CLI — likes and comments were pulled and reduced to an engagement ratio rather than recorded as a raw view count, so the signal reflects interaction rather than impressions.

## CLI and infrastructure changes

- `gaia dev fuse` emitted an invalid `note` timeline action. It now emits `fuse`, matching the schema-valid action set.
- Two agent skills ship for post-`ev-pipeline` ingestion: `/gaia-ingest` performs a single-row, CLI-only evidence write, and `/gaia-ingest-batch` coordinates multiple rows by wrapping `/gaia-ingest`.
- The `review/meta` branch scope now permits changes under `skill-trees/`, required for the rank-change timeline events this pass generates.
- The `trust-methodology-consult` skill now references the Star Bar gates in `META.md §2`.

## References

[1] Firecrawl repository: https://github.com/firecrawl/firecrawl
[2] Registry origin nodes: `firecrawl/firecrawl-build-scrape`, `firecrawl/firecrawl-build-search`, `firecrawl/firecrawl-build-onboarding`, `browser-use/browser-harness`, `google-deepmind/literature_search_openalex`.
[3] Addy Osmani suite curation report: https://github.com/gaia-research/gaia-skill-tree/blob/main/docs/meta/reports/2026-07-03-curation-report-addy-osmani-7-skill-suite-integration.html
