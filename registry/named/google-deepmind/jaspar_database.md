---
id: google-deepmind/jaspar_database
name: Jaspar-Database
contributor: google-deepmind
origin: false
genericSkillRef: genomic-data-retrieval
status: awakened
level: 3★
description: Query the JASPAR database for Transcription Factor (TF) binding profiles.
  Use when retrieving Position Frequency Matrices (PFMs) or Position Weight Matrices
  (PWMs) for specific TFs, resolving gene symbols to JASPAR Matrix IDs, or getting
  TF metadata. Supports multiple output formats (MEME, TRANSFAC, PFM, JASPAR, YAML).
createdAt: '2026-05-23'
updatedAt: '2026-07-16'
links:
  github: https://github.com/google-deepmind/science-skills/blob/main/skills/jaspar_database/SKILL.md
evidence:
- class: B
  source: https://github.com/google-deepmind/science-skills/blob/main/skills/jaspar_database/SKILL.md
  evaluator: unknown
  date: '2026-05-23'
  notes: Official Google DeepMind jaspar_database science-skill implementation. (backfilled
    — class-to-type migration)
  type: repo
  trustNumber: 70.0
  commits: 6
  contributors: 3
  grade: C
- source: https://academic.oup.com/nar/article/52/D1/D174/7420101
  evaluator: unknown
  date: '2026-06-20'
  type: peer-review
  trustNumber: 85.0
  grade: S
  notes: JASPAR 2024 — NAR; largest open-access TF binding profile database; 8-organism
    TFBS tracks
  reviewers: 3
  sourceStartedAt: '2024-01-04'
timeline:
- timestamp: '2026-06-14T12:32:32Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/google-deepmind/science-skills/blob/main/skills/jaspar_database/SKILL.md
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
- timestamp: '2026-06-19T17:05:36Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://academic.oup.com/nar/article/52/D1/D174/7420101
    (type: peer-review)'
- timestamp: '2026-06-19T17:05:36Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://academic.oup.com/nar/article/52/D1/D174/7420101
    as A (trustNumber: 85.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:02Z'
  details: TM 10.82 -> 100.82, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:25Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 4★ per G7 final rankings calibration.
- timestamp: '2026-07-16T08:36:43Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''genomic-data-retrieval'' type: basic (unchanged; Yggdrasil
    II taxonomy migration #997)'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-16
- timestamp: '2026-07-16T08:36:43Z'
  action: demote
  contributor: mbtiongson1
  previousValue: 4★
  newValue: 3★
  details: 'Yggdrasil II recalibration: 4★ unique-branch gate failed (unique-branch
    origin=False TM=100.8 (≥ 100.0)) — demoted to 3★ Evolved'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-16
trustMagnitude: 100.82
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: true
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 61de340c0594b68b15ce13d359ff8ca7d43edd6f227038ac5e67f61306bebe84
verification:
  firstEvidenceAt: '2026-06-19T17:05:36Z'
---

# JASPAR Skill

JASPAR is the definitive open-access database for Transcription Factor (TF)
binding profiles, stored as Position Frequency Matrices (PFMs).

Use this skill to map abstract sequence motifs or genomic regions to specific
biological regulators (e.g., "what TFs bind here?" or "what is the motif for
CTCF?").

## Prerequisites

1.  **`uv`**: Read the `uv` skill and follow its Setup instructions to ensure
    `uv` is installed and on PATH.
2.  **User Notification**: If LICENSE_NOTIFICATION.txt does not already exist in
    this skill directory then (1) prominently notify the user to check the terms
    at https://jaspar.elixir.no/ and https://jaspar.elixir.no/api/, then (2)
    create the file recording the notification text and timestamp.

## Core Rules

**CRITICAL**: You MUST respect the JASPAR API Terms of Use by adhering to the
following:

-   **Use the Wrapper**: ALWAYS execute the provided helper scripts to query the
    database rather than accessing the database directly. The scripts
    automatically enforce the required rate limit gracefully.
-   **Maximum API Window Size**: The genomic window for a single API query MUST
    NOT exceed 100,000 bp (100kb). The `jaspar_api.py` script automatically
    chunks larger requests for you to bypass this limitation when querying
    larger regions.
-   **Valid Matrix IDs**: `get_tf_motif`, `get_tf_metadata`, and `get_tf_pwm`
    require a stable JASPAR Matrix ID (e.g., `MA0488.2`). If a user provides a
    gene symbol (e.g., `JUN`), you must resolve it first using `resolve_tf_id`.
-   **Taxonomy Required**: Resolving IDs requires a `tax_id` to ensure targeted
    searches. Common IDs: Human=9606, Mouse=10090.
-   **Notification**: If this skill is used, ensure this is mentioned in the
    output.

## Utility Scripts

Run all commands using the bundled Python script:

### 1. Resolve TF to Matrix ID

Maps a transcription factor name to a stable Matrix ID. Required step before
fetching motifs if only a gene name is provided.

```bash
uv run scripts/jaspar_api.py resolve_tf_id --name "JUN" --tax-id 9606
```

### 2. Get TF Motif (PFM)

Retrieves the raw Position Frequency Matrix for a specific TF. Supports
`--format` flag.

```bash
uv run scripts/jaspar_api.py get_tf_motif --matrix-id "MA0488.2"
uv run scripts/jaspar_api.py get_tf_motif --matrix-id "MA0488.2" --format meme
```

### 3. Get TF Metadata

Retrieves TF class, family, and links to external databases (e.g., UniProt).
Supports `--format` flag.

```bash
uv run scripts/jaspar_api.py get_tf_metadata --matrix-id "MA0488.2"
uv run scripts/jaspar_api.py get_tf_metadata --matrix-id "MA0488.2" --format yaml
```

### 4. Compute PWM (Position Weight Matrix)

Fetches the PFM for a matrix and converts it to log-odds scores (PWM).

```bash
uv run scripts/jaspar_api.py get_tf_pwm --matrix-id "MA0488.2"
uv run scripts/jaspar_api.py get_tf_pwm --matrix-id "MA0488.2" --pseudocount 0.1
```

### 5. Infer Matrix from Protein Sequence

Infers potential JASPAR matrix profiles from a raw transcription factor protein
sequence.

```bash
uv run scripts/jaspar_api.py infer_from_sequence --sequence "QAQLLPSHHVG"
```

### 6. Get TF Flexible Model (TFFM)

Retrieves metadata for a JASPAR TF Flexible Model. (Note: The JASPAR TFFM
endpoints occasionally experience 500 Internal Server errors).

```bash
uv run scripts/jaspar_api.py get_tffm --tffm-id "TFFM0001.1"
```

### Output Formats

The `get_tf_motif` and `get_tf_metadata` commands accept an optional `--format`
flag. Supported formats: `json` (default), `jsonp`, `jaspar`, `meme`,
`transfac`, `pfm`, `yaml`.

## Anti-Patterns

*   **DON'T** pass gene symbols (e.g., `JUN`) to `get_tf_motif`. You must pass
    the `MA...` Matrix ID.
*   **DON'T** forget the `--tax-id` when resolving a TF name.
*   **DON'T** use this skill for determining tissue-specific epigenetic
    availability (JASPAR shows *potential* binding, not *actual* tissue
    expression context).
*   **DON'T** use this skill to model how a specific protein mutation affects
    binding.
