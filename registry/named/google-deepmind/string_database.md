---
id: google-deepmind/string_database
name: String-Database
contributor: google-deepmind
origin: false
genericSkillRef: proteomic-data-retrieval
status: awakened
level: 3★
description: Query the STRING database for protein-protein interactions (PPIs), functional
  enrichment, and homology. Use when the user asks about interactions between specific
  proteins, interaction evidence, confidence scores, protein interaction partners,
  or pathway enrichments.
createdAt: '2026-05-23'
updatedAt: '2026-06-21'
links:
  github: https://github.com/google-deepmind/science-skills/blob/main/skills/string_database/SKILL.md
evidence:
- class: B
  source: https://github.com/google-deepmind/science-skills/blob/main/skills/string_database/SKILL.md
  evaluator: unknown
  date: '2026-05-23'
  notes: Official Google DeepMind string_database science-skill implementation. (backfilled
    — class-to-type migration)
  type: repo
  trustNumber: 70.0
  commits: 6
  contributors: 3
  grade: C
- source: https://academic.oup.com/nar/article/51/D1/D638/6825349
  evaluator: unknown
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Szklarczyk et al. 2022 NAR: STRING database in 2023 — protein-protein association
    networks. 7,077 citations (Semantic Scholar 2026-06-19).'
  reviewers: 2
  grade: A
timeline:
- timestamp: '2026-06-14T12:32:38Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/google-deepmind/science-skills/blob/main/skills/string_database/SKILL.md
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
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:39Z'
  details: TM 0.0 -> 10.82, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T14:29:23Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://academic.oup.com/nar/article/51/D1/D638/6825349
    (type: peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:31:46Z'
  details: TM 10.82 -> 70.82, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:32:17Z'
  details: TM 70.82 -> 70.82, grade B -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:27Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 3★ per G7 final rankings calibration.
trustMagnitude: 70.82
overallTrustGrade: B
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
  firstEvidenceAt: '2026-06-19T14:29:23Z'
trustMagnitudeInputHash: fa66fd3a3d2dbb922d22fa817610d12cdb19c4926ffe4194edb8af901dfeb6eb
---

# STRING Database Skill

This skill allows you to query the STRING database programmatically using a
bundled Python CLI wrapper.

## Prerequisites

1.  **`uv`**: Read the `uv` skill and follow its Setup instructions to ensure
    `uv` is installed and on PATH.
2.  **User Notification**: If LICENSE_NOTIFICATION.txt does not already exist in
    this skill directory then (1) prominently notify the user to check the terms
    at https://string-db.org/cgi/access, then (2) create the file recording the
    notification text and timestamp.

## Core Rules

1.  **MANDATORY: Ask for Species First:** The STRING API requires NCBI Taxon
    IDs. **You MUST NOT guess or assume a species.** If the user does not
    explicitly state a species or Taxon ID, you MUST stop and ask: "Which
    species are you interested in? I need the NCBI Taxon ID to proceed." Even
    for well-known proteins like TP53, BRCA1, or MDM2 that are commonly
    associated with human studies, you MUST still ask — do not default to Human.
2.  **Never print output to stdout:** The `--output <file.tsv>` is required.
    Never read large outputs into context. Instead use jq, python or file
    operations (`grep`, `head`) to process large output.
3.  **Map Identifiers first:** If you only have common gene names (e.g.,
    'TP53'), map them to STRING IDs first as this guarantees much faster server
    responses. Use the `map` command for this.
4.  **Notification**: If this skill is used, ensure this is mentioned in the
    output.

## Tool Execution

The CLI is at `scripts/string_cli.py` and should be run using `uv run`:

```bash
uv run scripts/string_cli.py <command> [options] --output /tmp/out.tsv
```

## Feature Domains (Progressive Disclosure)

Read the following reference files based on the user's request:

*   **[Mapping Identifiers](references/mapping.md)** - Map common protein names
    to STRING IDs.
*   **[Interactions & Network](references/interactions.md)** - Find interacting
    proteins, network topologies, mediators, homology, and visual network
    images.
*   **[Enrichment & Functional Annotations](references/enrichment.md)** -
    Analyze pathway enrichment (GO, KEGG, Pfam), PPI significance, or find all
    proteins associated with a specific term (e.g. Melanoma).
*   **[Values/Ranks Enrichment](references/valuesranks.md)** - Submit full
    experimental datasets (e.g., logFC, p-values) for rank-based enrichment
    analysis using the async background API.

To begin, read the reference file most appropriate to the current task to
discover the correct CLI command.
