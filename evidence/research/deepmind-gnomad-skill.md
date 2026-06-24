[Skip to content](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md#start-of-content)

You signed in with another tab or window. [Reload](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md) to refresh your session.You signed out in another tab or window. [Reload](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md) to refresh your session.You switched accounts on another tab or window. [Reload](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md) to refresh your session.Dismiss alert

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

[History](https://github.com/google-deepmind/science-skills/commits/main/skills/gnomad_database/SKILL.md)

Open commit details

[View commit history for this file.](https://github.com/google-deepmind/science-skills/commits/main/skills/gnomad_database/SKILL.md) History

73 lines (57 loc) · 3 KB

/

# SKILL.md

Copy path

Top

## File metadata and controls

- Preview

- Code

- Blame


73 lines (57 loc) · 3 KB

[Raw](https://github.com/google-deepmind/science-skills/raw/refs/heads/main/skills/gnomad_database/SKILL.md)

Copy raw file

Download raw file

Outline

Edit and raw actions

| name | gnomad-database |
| description | Query the Genome Aggregation Database (gnomAD). Use when determining the rarity or allele frequency of specific genetic variants, retrieving gene constraint metrics (pLI, LOEUF) to assess loss-of-function intolerance, finding variants in a genomic region or gene, or querying structural variants. Don't use for analyzing individual patient genomes, tracking somatic mutations in cancer (use COSMIC), or requesting raw sequencing reads (use ENA). |

# gnomAD Database

[Permalink: gnomAD Database](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md#gnomad-database)

## Prerequisites

[Permalink: Prerequisites](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md#prerequisites)

1. **`uv`**: Read the `uv` skill and follow its Setup instructions to ensure
`uv` is installed and on PATH.
2. **User Notification**: If LICENSE\_NOTIFICATION.txt does not already exist in
this skill directory then (1) prominently notify the user to check the terms
at [https://gnomad.broadinstitute.org/policies](https://gnomad.broadinstitute.org/policies) and
[https://gnomad.broadinstitute.org/data#api](https://gnomad.broadinstitute.org/data#api), then (2) create the file
recording the notification text and timestamp.

## Core Rules

[Permalink: Core Rules](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md#core-rules)

- **Use the Wrapper**: ALWAYS execute the provided helper scripts to query the
database rather than accessing the database directly. The scripts
automatically enforce the gnomAD API rate limits gracefully.
- **Notification**: If this skill is used, ensure this is mentioned in the
output.

## Utility Scripts

[Permalink: Utility Scripts](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md#utility-scripts)

All scripts are located in the `scripts/` subdirectory of this skill's
installation directory. When running them, use the full absolute path to the
script (e.g. `/path/to/gnomad_database/scripts/get_variant_frequency.py`).

**1\. Variant Frequency.** Retrieves global and ancestry-specific allele
frequencies, homozygote counts, and **Grpmax Filtering AF** (faf95/faf99) for
exome, genome, and total (exome+genome combined) data. The filtering allele
frequency (FAF) is the maximum credible genetic ancestry group AF (lower bound
of the 95% or 99% CI). Variant ID format must be `chrom-pos-ref-alt` (e.g.,
`1-55516888-G-GA`). Alternately, you may provide an `rsID`.

```
# By variant ID:
uv run scripts/get_variant_frequency.py --variant_id {variant_id} [--dataset {dataset}] --output variant_frequency.json

# By rsID (e.g., rs1800562):
uv run scripts/get_variant_frequency.py --rsid {rsid} [--dataset {dataset}] --output variant_frequency.json
```

**2\. Gene Constraint.** Retrieves constraint metrics for a gene. The response
will explicitly contain `pli`, and the LOEUF score is represented by
`oe_lof_upper`.

```
uv run scripts/get_gene_constraint.py --gene {gene_symbol} --output {gene_symbol}_constraint.json
```

**3\. Region/Gene Variant Search.** Finds all variants in a region or gene.

```
# By region:
uv run scripts/search_variants.py --chrom {chrom} --start {start} --end {end} --output region_variants.json
# By gene:
uv run scripts/search_variants.py --gene {gene_symbol} --consequence {pLoF|missense} --output {gene_symbol}_variants.json
```

## References

[Permalink: References](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md#references)

Further documentation on the data: [https://gnomad.broadinstitute.org/data#api](https://gnomad.broadinstitute.org/data#api)
More general database documentation: [https://gnomad.broadinstitute.org/help](https://gnomad.broadinstitute.org/help)

You can’t perform that action at this time.