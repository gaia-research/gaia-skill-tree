# RFC 1419 — Registered Benchmarks and Generic Applicability

Status: approved shape, implementation in progress
Owner: Marcus Rafael B. Tiongson
Prime example: Firecrawl Research Index / alphaXiv ArXivQA

## Summary

Gaia benchmarks are capability-scoped. A benchmark source is recognized against the generic capability it measures; a benchmark result is evidence for a named skill that ran or was reported on that benchmark.

This separates two questions that were previously tangled:

1. **Benchmark applicability:** Which generic capability bucket does this benchmark evaluate?
2. **Benchmark evidence:** Which named implementation has a specific, reproducible score on that benchmark?

The benchmark catalog answers the first question. `benchmark-result` evidence rows answer the second.

## Core model

Registered benchmark source:

```text
/literature-search
  recognizes benchmark source: alphaxiv-arxivqa@v1.0
```

Named benchmark result:

```text
firecrawl/firecrawl-research-index
  may later carry score evidence for alphaxiv-arxivqa@v1.0
```

A registered benchmark source is not itself Trust Magnitude evidence. It is the cataloged benchmark definition that future named skills can be evaluated against.

## Catalog shape

Benchmark catalog entries may declare generic applicability:

```json
{
  "id": "alphaxiv-arxivqa@v1.0",
  "name": "alphaXiv ArXivQA Retrieval",
  "status": "registered",
  "mode": "external",
  "unit": "pct",
  "appliesToGenericSkillRefs": ["literature-search"],
  "scoring": {
    "scoresTrustMagnitude": false,
    "allowedProvenance": ["pending"],
    "requiredFields": []
  },
  "push": {
    "enabled": false,
    "aliases": []
  }
}
```

`appliesToGenericSkillRefs` means: skills mapped to these generic capabilities may use this benchmark ID when they later provide valid benchmark-result evidence.

It does **not** mean:

- all skills under that generic inherit a score,
- the benchmark contributes to Trust Magnitude by existing,
- a named skill has passed the benchmark,
- or a vendor-reported score is verified.

## Status semantics

- `candidate`: discovered lead; not yet accepted as a benchmark source.
- `registered`: accepted as a real benchmark source for one or more generic capabilities, but not reproducible/verified enough for Trust Magnitude scoring.
- `mirrored`: external leaderboard snapshot or score table copied for citation/display; excluded from Trust Magnitude.
- `verified`: benchmark source eligible for scoring when a named evidence row also carries allowed provenance and all reproducibility fields.
- `retired` / `rejected`: must not be used for new scoring.

For the first wave of benchmark curation, `registered` is the normal landing state. It lets Gaia remember the benchmark and its generic applicability while keeping scoring gates strict.

## Evidence row rule

A `benchmark-result` row belongs on a named skill only when the row can honestly provide the benchmark evidence contract:

- `benchmarkId`
- `score`
- `unit`
- `runAt`
- `provenance`
- `attestor`
- `datasetHash`
- `benchmarkInputHash`
- `percentile` when it should affect Trust Magnitude

Do not invent hashes from a blog post. `datasetHash` must identify the raw dataset used for evaluation. `benchmarkInputHash` must identify the dataset plus prompt/template/harness configuration.

If those fields are missing, register the benchmark source but do not ingest a named `benchmark-result` row.

## Prime example: Firecrawl Research Index / alphaXiv ArXivQA

Firecrawl issue #741 proposed the Research Index benchmark claim later folded into RFC #1419:

- arXivQA recall: 53.3% at $0.32/task
- next best: 45.4%
- MRR: 0.750
- benchmarked on roughly 200 alphaXiv ArXivQA queries, each labeled with up to 10 ground-truth arXiv IDs
- target named skill: `firecrawl/firecrawl-research-index`
- applicable generic capability: `literature-search`

This is a real, useful benchmark lead and should be cataloged as a registered benchmark source for `literature-search`.

It should not yet produce a scoring evidence row for Firecrawl because Gaia does not yet have the raw dataset hash, benchmark input hash, public reproducible harness, CI reproduction, or verifier attestation.

## Frontend posture

For now, the frontend may show existing evidence and benchmark-source metadata conservatively. Rich benchmark comparison surfaces can come later as curation adds more registered/verified benchmarks.

Initial display rule:

- show registered benchmarks as recognized sources for their generic capability when a surface supports it;
- do not display them as named-skill scores unless a `benchmark-result` row exists;
- do not imply Trust Magnitude impact unless `scoresTrustMagnitude` is true and the named row is scoring-eligible.

## Evidence pipeline posture

The evidence pipeline should treat benchmark source handling as a two-step gate:

1. **Generic applicability gate:** Does this benchmark source belong to one or more generic capability buckets?
2. **Named evidence gate:** Does a named skill have a reproducible/verifiable score row for that benchmark?

Phase 2B classifies both benchmark-source candidates and existing benchmark-result rows. After Phase 2B, Phase 3 adversarial audit, and Phase 4 link validation, humans may approve catalog registration. Scoring evidence ingestion remains a separate human gate through `/gaia-ingest-batch`.

Machines classify. Humans promote.
