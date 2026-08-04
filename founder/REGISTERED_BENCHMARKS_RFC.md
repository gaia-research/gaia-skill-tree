# RFC 1419 — Benchmark Evidence Lanes

Status: approved shape, implementation in progress
Owner: Marcus Rafael B. Tiongson
Prime example: Firecrawl Research Index / alphaXiv ArXivQA

## Summary

Benchmarks are normal Gaia evidence with a small lane multiplier. The registry should not make benchmark evidence harder to land than social, repo, or paper evidence. If a public source reports a benchmark score and a human accepts it during the evidence pipeline, Gaia may count it. If the benchmark is later found bogus, an audit can reject it and remove or zero the row.

The model has three lanes:

| Lane | Meaning | Benchmark multiplier |
| --- | --- | ---: |
| `verified` | CI reproduced or verifier-attested benchmark evidence | `2.0x` |
| `reported` | Publicly claimed or mirrored benchmark evidence accepted by the human gate | `1.0x` |
| `rejected` | Not approved, disputed, bogus, retired, or blacklisted | `0x` |

No extra evidence fields are needed. Trust Magnitude computes the final benchmark score internally from the row score and lane multiplier.

## Core model

Benchmark source:

```text
/literature-search
  recognizes benchmark source: alphaxiv-arxivqa@v1.0
```

Named benchmark result:

```text
firecrawl/firecrawl-research-index
  reports score evidence for alphaxiv-arxivqa@v1.0
```

The benchmark catalog answers which benchmark IDs Gaia approves and which generic capabilities they apply to. Named `benchmark-result` rows answer which specific implementation scored what.

## Catalog shape

Benchmark catalog entries may declare generic applicability:

```json
{
  "id": "alphaxiv-arxivqa@v1.0",
  "name": "alphaXiv ArXivQA Retrieval",
  "status": "reported",
  "mode": "external",
  "unit": "pct",
  "appliesToGenericSkillRefs": ["literature-search"],
  "scoring": {
    "scoresTrustMagnitude": true,
    "requiredFields": []
  },
  "push": {
    "enabled": false,
    "aliases": []
  }
}
```

`appliesToGenericSkillRefs` means skills mapped to these generic capabilities may use this benchmark ID when adding named benchmark-result evidence.

It does **not** mean every skill under that generic inherits a score. Scores still belong to named evidence rows.

## Evidence row shape

A reported benchmark row can be light:

```yaml
- type: benchmark-result
  source: https://www.firecrawl.dev/blog/research-index-launch
  evaluator: mbtiongson1
  date: '2026-08-03'
  benchmarkId: alphaxiv-arxivqa@v1.0
  score: 53.3
  unit: pct
  provenance: reported
  attestor: https://www.firecrawl.dev/blog/research-index-launch
  notes: >-
    Firecrawl-reported ArXivQA recall: 53.3% at $0.32/task versus
    45.4% next best; MRR 0.750.
```

A verified benchmark row may also carry reproducibility details such as `runAt`, `datasetHash`, `benchmarkInputHash`, `harnessUrl`, and `percentile`, but those are not required for reported evidence. They are how a row earns the stronger `verified` lane.

Do not persist a `finalScore`. `trustMagnitude.py` computes it.

## Trust Magnitude rule

For benchmark-result evidence, Trust Magnitude computes:

```text
baseBenchmarkScore = normalized row score
laneMultiplier = 2.0 for verified, 1.0 for reported, 0.0 for rejected
finalBenchmarkScore = baseBenchmarkScore × laneMultiplier
```

The normal benchmark evidence type weight and freshness rules then apply.

Legacy provenance terms normalize into the three lanes:

- `ci-reproduced` and `verifier-attested` normalize to `verified`.
- `mirrored` normalizes to `reported`.
- `pending`, unknown, rejected, retired, and blacklisted benchmark IDs normalize to `rejected`.

## Blacklist rule

The benchmark catalog is the blacklist surface. A catalog entry with `status: rejected` is not Gaia-approved and contributes zero Trust Magnitude. Phase 2B should flag rows that reference rejected or unknown benchmark IDs. Curators may remove the named row or leave it as rejected audit history, but it does not score.

This lets Gaia admit useful benchmark evidence quickly while preserving a simple audit escape hatch.

## Prime example: Firecrawl Research Index / alphaXiv ArXivQA

Firecrawl issue #741 proposed the Research Index benchmark claim later folded into RFC #1419:

- arXivQA recall: 53.3% at $0.32/task
- next best: 45.4%
- MRR: 0.750
- benchmarked on roughly 200 alphaXiv ArXivQA queries, each labeled with up to 10 ground-truth arXiv IDs
- target named skill: `firecrawl/firecrawl-research-index`
- applicable generic capability: `literature-search`

This should land as reported benchmark evidence. It is not verified by Gaia yet, but it is source-backed and can be removed or rejected if an audit disputes it.

## Frontend posture

For now, `docs/benchmarks` should show registered/reported benchmark source metadata and existing benchmark-result rows plainly. Rich benchmark comparison surfaces can wait until more benchmarks are curated.

Display rule:

- show benchmark lane (`verified`, `reported`, `rejected`),
- show the source and score when a named row exists,
- do not imply CI/verifier verification for `reported` rows,
- rejected benchmarks are blacklisted and score zero.

## Evidence pipeline posture

The evidence pipeline should stay simple:

1. Phase 2B classifies benchmark rows by lane and checks catalog status.
2. Human gate approves reported benchmark evidence or rejects/blacklists it.
3. Trust Magnitude applies the lane multiplier.

Machines classify. Humans approve or reject.
