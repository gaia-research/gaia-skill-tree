---
id: google-deepmind/unibind_database
name: Unibind-Database
contributor: google-deepmind
origin: false
genericSkillRef: genomic-data-retrieval
status: awakened
level: 2★
description: Queries the UniBind database for experimentally validated transcription
  factor (TF) binding sites. Use when retrieving direct TF-DNA interaction datasets,
  downloading binding site coordinates (BED/FASTA) for local analysis, or listing
  available datasets by species, cell line, or TF name. Don't use to query specific
  intervals, locations, genes, motif models or expression data.
createdAt: '2026-05-23'
updatedAt: '2026-06-14'
links:
  github: https://github.com/google-deepmind/science-skills/blob/main/skills/unibind_database/SKILL.md
evidence:
- class: B
  source: https://github.com/google-deepmind/science-skills/blob/main/skills/unibind_database/SKILL.md
  evaluator: unknown
  date: '2026-05-23'
  notes: Official Google DeepMind unibind_database science-skill implementation. (backfilled
    — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6
  contributors: 3
timeline:
- timestamp: '2026-06-14T12:32:39Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/google-deepmind/science-skills/blob/main/skills/unibind_database/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:57Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
trustMagnitude: 10.82
overallTrustGrade: ungraded
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 82fcba6670a541fe676377eb9e9a3b16aadf48cb0aef73aef6fcbe4a70ed5409
---

# UniBind Database Skill

UniBind is a database of direct TF–DNA interactions across 9 species,
integrating ChIP-seq peaks with JASPAR TF binding profiles via the DAMO
framework.

## Prerequisites

1.  **`uv`**: Read the `uv` skill and follow its Setup instructions to ensure
    `uv` is installed and on PATH.
2.  **User Notification**: If LICENSE_NOTIFICATION.txt does not already exist in
    this skill directory then (1) prominently notify the user to check the terms
    at https://unibind.uio.no/ and https://unibind.uio.no/api/overview, then (2)
    create the file recording the notification text and timestamp.

## Quick Start

Query commands print JSON to stdout by default. Most outputs are small enough to
read directly. For large outputs (`list_cell_lines`, `list_tfs`), pipe through
`jq` to extract only the fields you need.

```bash
uv run <SKILL DIR>/scripts/unibind_api.py list_species
```

The `download_tfbs` command writes BED/FASTA files to `--output-dir` instead.
You may optionally use `--output <path>` on any query command to save results to
a file if needed.

## Core Rules

-   **Use the Wrapper**: ALWAYS execute the provided helper scripts to query the
    database rather than accessing the database directly. The scripts
    automatically enforce the required rate limit gracefully.
-   **Output**: Query commands print JSON to stdout. Most responses are compact
    and can be read directly.
-   **Large Results**: `list_cell_lines` and `list_tfs` produce large output.
    Pipe these through `jq` to extract specific fields rather than reading the
    full output into context.
-   **Saving to File**: Use `--output <path>` when you need to reference the
    data later or when processing very large results with `jq`.
-   **Pagination**: Use `--page` and `--page-size` (max 1000) to chunk large
    result sets.
-   **Ordering**: Use `--order field_name` (prefix with `-` for descending) on
    any list command.
-   **Notification**: If this skill is used, ensure this is mentioned in the
    output.

## Utility Scripts

*Replace `<SKILL DIR>` with the absolute path to this skill's directory.*

### 1. List Species

```bash
uv run <SKILL DIR>/scripts/unibind_api.py list_species
```

### 2. List Collections

```bash
uv run <SKILL DIR>/scripts/unibind_api.py list_collections
```

### 3. List Cell Lines & TFs (large output — use `jp`)

These commands return large datasets. Use `uvx --from jmespath jp` to extract
only the fields you need.

```bash
uv run <SKILL DIR>/scripts/unibind_api.py list_cell_lines | uvx --from jmespath jp "results[].name"
uv run <SKILL DIR>/scripts/unibind_api.py list_tfs | uvx --from jmespath jp "results[].tf_name"
```

### 4. List and Filter Datasets (and Profile-Specific Datasets)

Filter datasets using the following arguments:

-   `--species` (e.g., "Homo sapiens")
-   `--tf-name` (e.g., "CTCF")
-   `--cell-line` (e.g., "mESC")
-   `--collection` (e.g., Permissive, Robust)
-   `--search` (a search term)
-   `--biological-condition` (biological condition or source)
-   `--data-source` (source of data, e.g., "ENCODE")
-   `--has-pvalue` ("true" or "false")
-   `--identifier` (e.g., "GSE60130")
-   `--jaspar-id` (JASPAR database profile matrix ID)
-   `--model` (prediction model)
-   `--summary` (summary filter)
-   `--threshold-pvalue` (p-value threshold)

Use `list_datasets` for standard datasets, or `list_specific_datasets` for
profile-specific queries.

```bash
uv run <SKILL DIR>/scripts/unibind_api.py list_datasets --species "Homo sapiens" --tf-name "CTCF" --data-source "ENCODE"
uv run <SKILL DIR>/scripts/unibind_api.py list_specific_datasets --species "Mus musculus" --cell-line "mESC"
```

### 5. Get Dataset Details

```bash
uv run <SKILL DIR>/scripts/unibind_api.py get_dataset "EXP047889.HMLE-Twist-ER_breast_cancer.SMAD3"
```

### 6. Download TFBS Files (BED / FASTA)

Downloads all TFBS files for a dataset to a local directory. Use `--format bed`
(default) or `--format fasta`.

```bash
uv run <SKILL DIR>/scripts/unibind_api.py download_tfbs "EXP047889.HMLE-Twist-ER_breast_cancer.SMAD3" --output-dir /tmp/tfbs --format bed
```

## Anti-Patterns

-   **DON'T** attempt to use the UniBind API to query specific genomic
    intervals, locations, or genes.
-   **DON'T** guess or hallucinate genome coordinates. Always use
    `ensembl-database` as an external check if you're pulling local BED tracks
    for offline bedtools intersection.
-   **DON'T** use for motif models (PFMs). Use the **jaspar-database** skill
    instead.
-   **DON'T** use for gene expression data. UniBind only stores binding events.
-   **DON'T** assume tissue-specific expression from dataset lists alone.
-   **DON'T** use `cat` to read large JSON output files into context. The output
    is too large. Use `jq` or write your own code to parse the output files.
