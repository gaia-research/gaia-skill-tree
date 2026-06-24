[Skip to content](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#start-of-content)

You signed in with another tab or window. [Reload](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md) to refresh your session.You signed out in another tab or window. [Reload](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md) to refresh your session.You switched accounts on another tab or window. [Reload](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md) to refresh your session.Dismiss alert

{{ message }}

[google-deepmind](https://github.com/google-deepmind)/ **[science-skills](https://github.com/google-deepmind/science-skills)** Public

- [Notifications](https://github.com/login?return_to=%2Fgoogle-deepmind%2Fscience-skills) You must be signed in to change notification settings
- [Fork\\
200](https://github.com/login?return_to=%2Fgoogle-deepmind%2Fscience-skills)
- [Star\\
2k](https://github.com/login?return_to=%2Fgoogle-deepmind%2Fscience-skills)


## Collapse file tree

## Files

main

Search this repository(forward slash)` forward slash/`

/

# SKILL.md

Copy path

Blame

More file actions

Blame

More file actions

## Latest commit

[![michaeloneill](https://avatars.githubusercontent.com/u/8782349?v=4&size=40)](https://github.com/michaeloneill)[michaeloneill](https://github.com/google-deepmind/science-skills/commits?author=michaeloneill)

[Initial public release of Science Skills](https://github.com/google-deepmind/science-skills/commit/d68809a6af09a2f18d8a30958450621f5cb53e1e)

last monthMay 19, 2026

[d68809a](https://github.com/google-deepmind/science-skills/commit/d68809a6af09a2f18d8a30958450621f5cb53e1e) · last monthMay 19, 2026

## History

[History](https://github.com/google-deepmind/science-skills/commits/main/skills/chembl_database/SKILL.md)

Open commit details

[View commit history for this file.](https://github.com/google-deepmind/science-skills/commits/main/skills/chembl_database/SKILL.md) History

282 lines (204 loc) · 11.2 KB

/

# SKILL.md

Copy path

Top

## File metadata and controls

- Preview

- Code

- Blame


282 lines (204 loc) · 11.2 KB

[Raw](https://github.com/google-deepmind/science-skills/raw/refs/heads/main/skills/chembl_database/SKILL.md)

Copy raw file

Download raw file

Outline

Edit and raw actions

| name | chembl-database |
| description | Query the ChEMBL database for bioactive molecules, drug targets, bioactivity data, approved drugs, and chemical structures. Use when the user asks about compounds, targets, IC50/Ki values, drug mechanisms, or structure searches. |

# ChEMBL Database Query

[Permalink: ChEMBL Database Query](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#chembl-database-query)

## Prerequisites

[Permalink: Prerequisites](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#prerequisites)

1. **`uv`**: Read the `uv` skill and follow its Setup instructions to ensure
`uv` is installed and on PATH.
2. **User Notification**: If LICENSE\_NOTIFICATION.txt does not already exist in
this skill directory then (1) prominently notify the user to check the terms
at [https://chembl.gitbook.io/chembl-interface-documentation/about](https://chembl.gitbook.io/chembl-interface-documentation/about), then (2)
create the file recording the notification text and timestamp.

## Core Rules

[Permalink: Core Rules](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#core-rules)

- \[!IMPORTANT\] **Use the Utility Scripts**: You MUST ALWAYS use the provided
utility script `scripts/chembl_api.py` for all ChEMBL API interactions,
including checking status. NEVER use `curl` or custom Python requests to
query the ChEMBL API directly. This ensures rate limit is enfoced and also
retries on network errors.

- **Output to File (Required)**: The `--output` flag is **required** for every
subcommand. All JSON results are written to the specified file. After
running the command, read the output file with jq or your own code to
extract the data. List results are typically wrapped in a JSON array keyed
by the endpoint name (e.g., `molecules`, `activities`).

- **Notification**: If this skill is used, ensure this is mentioned in the
output.


## Utility Script

[Permalink: Utility Script](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#utility-script)

All ChEMBL API queries use one script with subcommands:

```
uv run scripts/chembl_api.py <subcommand> --output <file> [options]
```

* * *

### 1\. Check API Status

[Permalink: 1. Check API Status](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#1-check-api-status)

```
uv run scripts/chembl_api.py status --output /tmp/status.json
```

* * *

### 2\. Molecule Queries

[Permalink: 2. Molecule Queries](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#2-molecule-queries)

**Fetch by ChEMBL ID:**`bash uv run scripts/chembl_api.py molecule --id CHEMBL25 --output /tmp/mol.json`

**Search by name:**`bash uv run scripts/chembl_api.py molecule --search "aspirin" --limit 3 --output /tmp/mol_search.json`

**Batch fetch:**`bash uv run scripts/chembl_api.py molecule --ids "CHEMBL25;CHEMBL1642" --limit 10 --output /tmp/mol_batch.json`

**Filter by properties:**`bash uv run scripts/chembl_api.py molecule --filter molecule_properties__mw_freebase__lte=500 --limit 5 --output /tmp/mol_filter.json`

**Filter by range:**`bash uv run scripts/chembl_api.py molecule --filter molecule_properties__mw_freebase__range=150,200 --limit 5 --output /tmp/mol_range.json`

**Download SDF structure file:**`bash uv run scripts/chembl_api.py molecule --id CHEMBL25 --dl_format sdf --output /tmp/aspirin.sdf`

> **Tip**: SDF/MOL files can be passed directly to tools like PyMOL or RDKit for
> 3D visualization and analysis.

* * *

### 3\. Target Queries

[Permalink: 3. Target Queries](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#3-target-queries)

**Search for targets:**`bash uv run scripts/chembl_api.py target --search "EGFR" --limit 5 --output /tmp/targets.json`

**Fetch by ID:**`bash uv run scripts/chembl_api.py target --id CHEMBL203 --output /tmp/egfr.json`

* * *

### 4\. Bioactivity Data

[Permalink: 4. Bioactivity Data](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#4-bioactivity-data)

**Fetch activity by ID:**`bash uv run scripts/chembl_api.py activity --id 31863 --output /tmp/act.json`

**Search activities:**`bash uv run scripts/chembl_api.py activity --search "EGFR" --limit 5 --output /tmp/act_search.json`

**Filter activities for a target:**`bash uv run scripts/chembl_api.py activity --filter target_chembl_id=CHEMBL203 standard_type=IC50 --limit 10 --output /tmp/egfr_ic50.json`

**Normalize bioactivity units to nM:**`bash uv run scripts/chembl_api.py activity --filter target_chembl_id=CHEMBL203 standard_type=IC50 --limit 5 --normalize --output /tmp/egfr_normalized.json`

> **Important**: Bioactivity values come in various units (nM, µM, pM). Use
> `--normalize` to convert all values to nM for consistent comparison. Each
> record will include `normalized_value_nM` and `normalization_note`.

* * *

### 5\. Drug Information

[Permalink: 5. Drug Information](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#5-drug-information)

**Fetch drug details:**`bash uv run scripts/chembl_api.py drug --id CHEMBL25 --output /tmp/drug.json`

**Drug indications:**`bash uv run scripts/chembl_api.py drug_indication --filter molecule_chembl_id=CHEMBL25 --limit 10 --output /tmp/indications.json`

**Filter indications by phase:**`bash uv run scripts/chembl_api.py drug_indication --filter molecule_chembl_id=CHEMBL25 max_phase_for_ind=4.0 --limit 10 --output /tmp/approved_indications.json`

**Drug warnings:**`bash uv run scripts/chembl_api.py drug_warning --limit 5 --output /tmp/warnings.json`

**Mechanisms of action:**`bash uv run scripts/chembl_api.py mechanism --filter molecule_chembl_id=CHEMBL25 --limit 5 --output /tmp/mech.json`

* * *

### 6\. Structure-Based Searches

[Permalink: 6. Structure-Based Searches](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#6-structure-based-searches)

> **Note**: Both similarity and substructure searches are performed
> **server-side** on ChEMBL's pre-indexed database. They do not require a local
> RDKit installation.

**Similarity search (SMILES + threshold):**`bash uv run scripts/chembl_api.py similarity --smiles "CC(=O)Oc1ccccc1C(=O)O" --similarity 85 --limit 5 --output /tmp/similar.json`

**Substructure search (SMILES):**`bash uv run scripts/chembl_api.py substructure --smiles "c1ccccc1" --limit 5 --output /tmp/substruct.json`

* * *

### 7\. Compound Image

[Permalink: 7. Compound Image](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#7-compound-image)

Download a 2D structure image (SVG by default, scalable for publication):

```
uv run scripts/chembl_api.py image --id CHEMBL25 --output /tmp/chembl25.svg
```

_Options:_

- `--dimensions`: Image size in pixels (max 500, default 500).
- `--engine`: Rendering engine (default: rdkit).
- `--img_format`: Output format — `svg` (default, vector) or `png` (raster).

* * *

### 8\. Cross-Referencing with Other Databases

[Permalink: 8. Cross-Referencing with Other Databases](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#8-cross-referencing-with-other-databases)

ChEMBL integrates with UniProt, Ensembl, PubChem, and other databases. Common
cross-referencing patterns:

**Find a ChEMBL target from a UniProt accession:**`bash uv run scripts/chembl_api.py target --filter target_components__accession=P00533 --limit 5 --output /tmp/uniprot_target.json`

**Resolve any ChEMBL ID to its entity type:**`bash uv run scripts/chembl_api.py chembl_id_lookup --id CHEMBL203 --output /tmp/lookup.json`

**Look up cross-reference sources:**`bash uv run scripts/chembl_api.py xref_source --limit 10 --output /tmp/xrefs.json`

> **Tip**: Use the `target_component` endpoint to find UniProt accessions, gene
> names, and protein sequences for any ChEMBL target.

* * *

### 9\. Pagination

[Permalink: 9. Pagination](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#9-pagination)

All list endpoints support `--limit` and `--offset` for pagination:

```
# First page: 2 results starting at offset 0
uv run scripts/chembl_api.py molecule --limit 2 --offset 0 --output /tmp/page1.json

# Second page: next 2 results starting at offset 2
uv run scripts/chembl_api.py molecule --limit 2 --offset 2 --output /tmp/page2.json
```

The response includes `page_meta` with `total_count`, `limit`, `offset`, `next`,
and `previous` links. Use successive `--offset` values to page through large
result sets.

* * *

### 10\. Other Endpoints

[Permalink: 10. Other Endpoints](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#10-other-endpoints)

All remaining endpoints follow the same pattern:

```
uv run scripts/chembl_api.py <subcommand> --output <file> [--id ID | --ids ID1;ID2 | --search QUERY] [--limit N] [--offset N] [--filter KEY=VAL ...]
```

**Key subcommands at a glance:**

- `molecule` (searchable: true): Molecules/compounds — the primary entry point
- `target` (searchable: true): Drug targets (proteins, organisms, etc.)
- `activity` (searchable: true): Bioactivity data (IC50, Ki, EC50, etc.)
- `drug` (searchable: false): Approved drugs
- `mechanism` (searchable: false): Mechanisms of action
- `assay` (searchable: true): Assay descriptions
- `similarity` (searchable: false): Similarity search (special)
- `substructure` (searchable: false): Substructure search (special)
- `image` (searchable: false): Compound image download (special)

**Full subcommand list:**

- `activity_supp` (searchable: false): Supplementary activity data
- `assay_class` (searchable: false): Assay classifications
- `atc_class` (searchable: false): ATC drug classifications
- `binding_site` (searchable: false): Binding site information
- `biotherapeutic` (searchable: false): Biotherapeutic molecules
- `cell_line` (searchable: false): Cell line details
- `chembl_id_lookup` (searchable: true): ChEMBL ID resolution
- `chembl_release` (searchable: false): Database release info
- `compound_record` (searchable: false): Compound records
- `compound_structural_alert` (searchable: false): Structural alerts
- `document` (searchable: true): Literature documents
- `document_similarity` (searchable: false): Document similarity
- `drug_indication` (searchable: false): Drug indications
- `drug_warning` (searchable: false): Drug safety warnings
- `go_slim` (searchable: false): GO slim terms
- `metabolism` (searchable: false): Metabolism data
- `molecule_form` (searchable: false): Molecule forms (salts/parents)
- `organism` (searchable: false): Organisms
- `protein_classification` (searchable: true): Protein classifications
- `source` (searchable: false): Data sources
- `target_component` (searchable: false): Target protein components
- `target_relation` (searchable: false): Target relationships
- `tissue` (searchable: false): Tissue types
- `xref_source` (searchable: false): Cross-reference sources
- `status` (searchable: false): API status check (special)

## Common Options

[Permalink: Common Options](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#common-options)

- `--output FILE`: **Required.** Output file path for JSON results.
- `--id ID`: Fetch a single record by ID.
- `--ids ID1;ID2;...`: Batch fetch multiple records.
- `--search QUERY`: Free-text search (only for searchable endpoints, marked
✓).
- `--limit N`: Max results to return (default: 5).
- `--offset N`: Pagination offset.
- `--filter KEY=VAL`: Filter parameters (can specify multiple).
- `--normalize`: (activity only) Normalize values to nM.
- `--dl_format sdf|mol`: (molecule only) Download structure file.

## Reference

[Permalink: Reference](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#reference)

- **API Endpoints Reference**: See
[references/api\_endpoints.md](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/references/api_endpoints.md) for the full list
of endpoints and filter operators.

## Workflow

[Permalink: Workflow](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md#workflow)

1. Use `status --output /tmp/status.json` to verify the API is available.
2. Search for targets, molecules, or drugs using the relevant subcommand.
3. Read the output JSON file to extract IDs and data.
4. Use IDs from search results to fetch detailed records.
5. Query `activity` with filters to get bioactivity data for targets/molecules.
Use `--normalize` when comparing values across studies.
6. Use `similarity` or `substructure` for server-side structure-based queries.
7. Download compound images with `image` or structure files with `molecule --dl_format sdf`.
8. Use `target --filter target_components__accession=<UniProt>` to cross-
reference with UniProt.

You can’t perform that action at this time.