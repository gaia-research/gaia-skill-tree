---
id: google-deepmind/literature_search_openalex
name: Literature-Search-Openalex
contributor: google-deepmind
origin: false
genericSkillRef: literature-search
status: awakened
level: 4★
description: Query the OpenAlex scholarly database for research papers, authors, institutions,
  topics, sources, publishers, funders, geo-locations, and keywords. Use when searching
  academic papers, resolving DOIs, downloading open-access PDFs, finding an author's
  publications, aggregating bibliometric data (citation counts, h-index, impact factor),
  exploring the research taxonomies, or performing DOI lookups.
createdAt: '2026-05-23'
updatedAt: '2026-06-21'
links:
  github: https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_openalex/SKILL.md
evidence:
- class: B
  source: https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_openalex/SKILL.md
  evaluator: unknown
  date: '2026-05-23'
  notes: Official Google DeepMind literature_search_openalex science-skill implementation.
    (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  commits: 6
  contributors: 3
  grade: C
- source: https://openalex.org/about
  evaluator: unknown
  date: '2026-06-20'
  type: peer-review
  trustNumber: 78.0
  grade: S
  notes: OpenAlex — fully open catalog 200M+ scholarly works; Priem & Heather 2022;
    replaces Microsoft Academic
  reviewers: 3
  sourceStartedAt: '2022-01-01'
timeline:
- timestamp: '2026-06-14T12:32:34Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_openalex/SKILL.md
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
- timestamp: '2026-06-19T17:06:49Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://openalex.org/about (type: peer-review)'
- timestamp: '2026-06-19T17:06:49Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://openalex.org/about as B (trustNumber: 78.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:02Z'
  details: TM 10.82 -> 100.82, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:25Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 4★ per G7 final rankings calibration.
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
trustMagnitudeInputHash: 0bd8ed800e255c7aa45f871f228c1e54c3c0adda5f7c9b582c110be21b80d513
verification:
  firstEvidenceAt: '2026-06-19T17:06:49Z'
---

# OpenAlex Skill

## Prerequisites

1.  **`uv`**: Read the `uv` skill and follow its Setup instructions to ensure
    `uv` is installed and on PATH.
2.  **User Notification**: If LICENSE_NOTIFICATION.txt does not already exist in
    this skill directory then (1) prominently notify the user to check the terms
    at https://developers.openalex.org/ and to always check the license of the
    papers retrieved by the skill for any restrictions, then (2) create the file
    recording the notification text and timestamp.
3.  **`.env` file**: Make sure the `.env` file exists in your home directory.
    Create one if it does not exist.
4.  **`OPENALEX_API_KEY`** (optional but recommended): Enables the OpenAlex
    Premium API with higher rate limits. The skill works without it (using the
    free "polite pool"). If the variable is missing from `.env`, do NOT ask the
    user to paste it into the chat (this would leak the key into the agent's
    context). Instead, give the user this command — **substituting `ENV_FILE`
    with the resolved literal path to the `.env` file**:

    ```bash
    printf "Enter OpenAlex API key (typing hidden): " && read -s key && echo && echo "OPENALEX_API_KEY=$key" >> "ENV_FILE" && echo "Saved."
    ```

    The scripts load credentials automatically via `dotenv`. **NEVER** read,
    print, or inspect the `.env` file or its variables (e.g. no `cat`, `grep`,
    `echo`, `printenv`, or `os.environ.get` on keys). Credentials must stay out
    of the agent's context. See the [Rate Limits section](#rate-limits) for more
    details.

## Core Rules

1.  **List Sources.** If this skill is used, ensure this is mentioned in the
    output AND list the URLs of all papers that were used in producing the
    output.
2.  **Resolve before filter.** NEVER filter by name. Always `resolve` a name to
    an ID first, then use that ID in `--filter`.
3.  **Use the CLI only.** Never call the API via `curl`/`urllib`. The CLI
    handles retries and rate limiting.
4.  **No fabrication.** Never invent OpenAlex IDs or DOIs. Use `resolve`/`get`
    to look them up. Report empty results accurately.
5.  **API key.** If a command returns 401/429 or you need high-volume queries,
    follow the prerequisite instructions above to help the user add
    `OPENALEX_API_KEY` to the `.env` file. Keys are at OpenAlex.org → account
    settings.
6.  **Keep output small.** Always use `--select` and `--per-page 5–10` for
    overview queries. Pipe `filter` output to a file (`> results.json`), then
    slim with `jq` before reading into context.

## Rate Limits

-   **With key:** ~10 req/s, $1/day free budget.
-   **Without key:** Very limited, $0.01/day budget.

Operation              | Cost
---------------------- | -------
Singleton `get`        | Free
`filter`               | $0.0001
`--search` / `resolve` | $0.001
`download-pdf`         | $0.01

## CLI Reference

```
uv run scripts/openalex_cli.py [--api-key KEY] <command> [flags]
```

Entity types (shared across commands): `works`, `authors`, `sources`,
`institutions`, `topics`, `domains`, `fields`, `subfields`, `sdgs`, `countries`,
`continents`, `languages`, `keywords`, `publishers`, `funders`, `work-types`,
`source-types`, `institution-types`, `licenses`

### Commands

**resolve** `<entity> <query>` — Name → ID candidates. Returns `id`,
`display_name`, `hint`. Use `--per-page N` for more candidates.

**get** `<entity> <id>` — Full metadata for one entity. Accepts short ID
(`W2741809807`), full URL, or DOI URL. Use `--select` to limit fields.

**filter** `<entity>` — Search/filter entities. Key flags are:

-   `--search <query>`: Full-text search (10× cost of `--filter`)
-   `--filter <expr>`: Filter expressions. Use `,` for AND and `|` for OR.
-   `--sort <field:dir>`: Sort results (e.g., `cited_by_count:desc`)
-   `--select <fields>`: Limit the fields returned in the output.
-   `--group-by <field>`: Aggregate results by a specific field.
-   `--per-page <N>`: Number of results per page (default 25, max 100).
-   `--page <N>`: Specify the page number to retrieve.
-   `--sample <N>`: Get a random sample of up to 10,000 results.
-   `--seed <N>`: Seed for reproducible sampling.

**download-pdf** `<work-id> <output-path>` — Download PDF (requires API key).
Falls back to alternative `pdf_url` locations if primary fails. Whenever you
download a PDF, verify it is not empty or corrupted.

**rate-limit** — Check current rate limit status (requires API key).

### Search Tips

-   If `resolve` returns no matches, try alternate spellings or abbreviations.
-   If `--search` returns 0 results, try broader terms (max 3 retries).
-   If `resolve` returns multiple candidates, present them to the user with
    `display_name` and `hint` for manual selection.

## Entity References

Consult `references/` for valid filter, sort, and group-by fields per entity:

-   [Works](references/works.md) — [Authors](references/authors.md) —
    [Sources](references/sources.md)
-   [Institutions](references/institutions.md) — [Topics](references/topics.md)
    — [Taxonomy](references/taxonomy.md)
-   [Geo & Language](references/geo_and_language.md) —
    [Publishers & Funders](references/publishers_funders.md)
-   [Type Values](references/type_values.md)

## Common Workflows

```bash
# Author's works (resolve → filter)
uv run scripts/openalex_cli.py resolve authors "Geoffrey Hinton"
uv run scripts/openalex_cli.py filter works \
  --filter "authorships.author.id:A5108093963" \
  --sort "cited_by_count:desc" --per-page 10 > papers.json
cat papers.json | jq '[.results[] | {id, title: .display_name, year: .publication_year, citations: .cited_by_count}]'

# DOI lookup
uv run scripts/openalex_cli.py get works "https://doi.org/10.1038/s41586-021-03819-2"

# Bulk DOI lookup (up to 100)
uv run scripts/openalex_cli.py filter works \
  --filter "doi:10.1234/a|10.1234/b|10.1234/c" --per-page 100 > results.json

# Institutional impact by year
uv run scripts/openalex_cli.py resolve institutions "MIT"
uv run scripts/openalex_cli.py filter works \
  --filter "authorships.institutions.id:I63966007" \
  --group-by "publication_year" > mit_by_year.json

# Random sample
uv run scripts/openalex_cli.py filter works \
  --filter "publication_year:2023,is_oa:true" \
  --sample 100 --seed 42 > results.json
```

## Error Handling

Code | Meaning             | Action
---- | ------------------- | ------------------------------------------------
401  | Unauthorized        | Help user add API key to `.env` (see prereqs)
403  | Plan upgrade needed | Inform user; see https://openalex.org/pricing
404  | Not found           | Verify ID; try `resolve` first
429  | Rate limited        | Wait and retry; suggest adding API key to `.env`

Known premium-only filters: `from_updated_date`, `to_updated_date`.

Never fabricate results on empty responses — report accurately and suggest
alternate search terms.
