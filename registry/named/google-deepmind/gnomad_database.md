---
id: google-deepmind/gnomad_database
name: Gnomad-Database
contributor: google-deepmind
origin: false
genericSkillRef: genomic-data-retrieval
status: awakened
level: 3★
description: Query the Genome Aggregation Database (gnomAD). Use when determining
  the rarity or allele frequency of specific genetic variants, retrieving gene constraint
  metrics (pLI, LOEUF) to assess loss-of-function intolerance, finding variants in
  a genomic region or gene, or querying structural variants. Don't use for analyzing
  individual patient genomes, tracking somatic mutations in cancer (use COSMIC), or
  requesting raw sequencing reads (use ENA).
createdAt: '2026-05-23'
updatedAt: '2026-07-16'
links:
  github: https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md
evidence:
- class: B
  source: https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md
  evaluator: unknown
  date: '2026-05-23'
  notes: Official Google DeepMind gnomad_database science-skill implementation. (backfilled
    — class-to-type migration)
  type: repo
  trustNumber: 70.0
  commits: 6
  contributors: 3
  grade: C
- source: https://www.nature.com/articles/s41586-020-2308-7
  evaluator: unknown
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Karczewski et al. 2020 Nature: The mutational constraint spectrum quantified
    from 141,456 humans. 8,320 citations (Semantic Scholar 2026-06-19).'
  reviewers: 3
  grade: S
timeline:
- timestamp: '2026-06-14T12:32:31Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:16Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:57Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:39Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T14:29:19Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.nature.com/articles/s41586-020-2308-7
    (type: peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:31:46Z'
  details: TM 10.82 -> 100.82, grade ungraded -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:32:17Z'
  details: TM 100.82 -> 100.82, grade A -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:25Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 4★ per G7 final rankings calibration.
- timestamp: '2026-07-16T08:36:43Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''genomic-data-retrieval'' type: basic (unchanged; Yggdrasil
    II taxonomy migration #997)'
- timestamp: '2026-07-16T08:36:43Z'
  action: demote
  contributor: mbtiongson1
  previousValue: 4★
  newValue: 3★
  details: 'Yggdrasil II recalibration: 4★ unique-branch gate failed (unique-branch
    origin=False TM=100.8 (≥ 100.0)) — demoted to 3★ Evolved'
trustMagnitude: 100.82
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
verification:
  firstEvidenceAt: '2026-06-19T14:29:19Z'
trustMagnitudeInputHash: 27923e8b16fa85da1591afd2f703975961102b66632f8a8a7be54ec482ed5aea
---

# gnomAD Database

## Prerequisites

1.  **`uv`**: Read the `uv` skill and follow its Setup instructions to ensure
    `uv` is installed and on PATH.
2.  **User Notification**: If LICENSE_NOTIFICATION.txt does not already exist in
    this skill directory then (1) prominently notify the user to check the terms
    at https://gnomad.broadinstitute.org/policies and
    https://gnomad.broadinstitute.org/data#api, then (2) create the file
    recording the notification text and timestamp.

## Core Rules

-   **Use the Wrapper**: ALWAYS execute the provided helper scripts to query the
    database rather than accessing the database directly. The scripts
    automatically enforce the gnomAD API rate limits gracefully.
-   **Notification**: If this skill is used, ensure this is mentioned in the
    output.

## Utility Scripts

All scripts are located in the `scripts/` subdirectory of this skill's
installation directory. When running them, use the full absolute path to the
script (e.g. `/path/to/gnomad_database/scripts/get_variant_frequency.py`).

**1. Variant Frequency.** Retrieves global and ancestry-specific allele
frequencies, homozygote counts, and **Grpmax Filtering AF** (faf95/faf99) for
exome, genome, and total (exome+genome combined) data. The filtering allele
frequency (FAF) is the maximum credible genetic ancestry group AF (lower bound
of the 95% or 99% CI). Variant ID format must be `chrom-pos-ref-alt` (e.g.,
`1-55516888-G-GA`). Alternately, you may provide an `rsID`.

```bash
# By variant ID:
uv run scripts/get_variant_frequency.py --variant_id {variant_id} [--dataset {dataset}] --output variant_frequency.json

# By rsID (e.g., rs1800562):
uv run scripts/get_variant_frequency.py --rsid {rsid} [--dataset {dataset}] --output variant_frequency.json
```

**2. Gene Constraint.** Retrieves constraint metrics for a gene. The response
will explicitly contain `pli`, and the LOEUF score is represented by
`oe_lof_upper`.

```bash
uv run scripts/get_gene_constraint.py --gene {gene_symbol} --output {gene_symbol}_constraint.json
```

**3. Region/Gene Variant Search.** Finds all variants in a region or gene.

```bash
# By region:
uv run scripts/search_variants.py --chrom {chrom} --start {start} --end {end} --output region_variants.json
# By gene:
uv run scripts/search_variants.py --gene {gene_symbol} --consequence {pLoF|missense} --output {gene_symbol}_variants.json
```

## References

Further documentation on the data: https://gnomad.broadinstitute.org/data#api
More general database documentation: https://gnomad.broadinstitute.org/help
