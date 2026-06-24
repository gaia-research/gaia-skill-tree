[Skip to content](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#start-of-content)

You signed in with another tab or window. [Reload](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md) to refresh your session.You signed out in another tab or window. [Reload](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md) to refresh your session.You switched accounts on another tab or window. [Reload](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md) to refresh your session.Dismiss alert

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

[History](https://github.com/google-deepmind/science-skills/commits/main/skills/pubmed_database/SKILL.md)

Open commit details

[View commit history for this file.](https://github.com/google-deepmind/science-skills/commits/main/skills/pubmed_database/SKILL.md) History

199 lines (159 loc) · 8.57 KB

/

# SKILL.md

Copy path

Top

## File metadata and controls

- Preview

- Code

- Blame


199 lines (159 loc) · 8.57 KB

[Raw](https://github.com/google-deepmind/science-skills/raw/refs/heads/main/skills/pubmed_database/SKILL.md)

Copy raw file

Download raw file

Outline

Edit and raw actions

| name | pubmed-database |
| description | Search PubMed for scientific literature, including published clinical trials. Fetch abstracts and full text. Link published research to biological databases (gene, protein, nucleotide, PubChem) to discover associations between papers and specific compounds or genes. Verify medical spelling, match raw citations, and cache result sets for bulk processing. Interfaces NCBI E-utilities and PMC BioC APIs. |

# PubMed API

[Permalink: PubMed API](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#pubmed-api)

## Prerequisites

[Permalink: Prerequisites](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#prerequisites)

1. **`uv`**: Read the `uv` skill and follow its Setup instructions to ensure
`uv` is installed and on PATH.
2. **User Notification**: If LICENSE\_NOTIFICATION.txt does not already exist in
this skill directory then (1) prominently notify the user to check the terms
at [https://pubmed.ncbi.nlm.nih.gov/disclaimer/](https://pubmed.ncbi.nlm.nih.gov/disclaimer/) and
[https://www.ncbi.nlm.nih.gov/home/about/policies/](https://www.ncbi.nlm.nih.gov/home/about/policies/) and to always check the
license of the papers retrieved by the skill for any restrictions, then (2)
create the file recording the notification text and timestamp.
3. **`.env` file**: Make sure the `.env` file exists in your home directory.
Create one if it does not exist.
4. **`NCBI_API_KEY`** (optional): Raises the NCBI E-utilities rate limit from 3
to 10 requests/second. The skill works without it, but a key is recommended
if the user plans many queries or encounters a 429 error. The user can
obtain one for free by registering at
[https://www.ncbi.nlm.nih.gov/account/settings/](https://www.ncbi.nlm.nih.gov/account/settings/)
5. **`USER_EMAIL`** (optional but recommended): Identifies the caller to NCBI
(recommended by their Terms of Use).

If the variables are missing from `.env`, do NOT ask the user to paste them into
the chat (this would leak keys into the agent's context). Instead, give the user
these commands — **substituting `ENV_FILE` with the resolved literal path to the**
**`.env` file**:

```
printf "Enter NCBI API key (typing hidden): " && read -s key && echo && echo "NCBI_API_KEY=$key" >> "ENV_FILE" && echo "Saved."
```

```
printf "Enter contact email: " && read email && echo "USER_EMAIL=$email" >> "ENV_FILE" && echo "Saved."
```

The scripts load credentials automatically via `dotenv`. **NEVER** read,
print, or inspect the `.env` file or its variables (e.g. no `cat`, `grep`,
`echo`, `printenv`, or `os.environ.get` on keys). Credentials must stay
out of the agent's context.

This skill provides CLI access to the NCBI PubMed and PubMed Central APIs via
`scripts/pubmed_api.py` — a single CLI with 10 functions covering search, fetch,
linking, full text, spelling, discovery, citation matching, and caching.

## Core Rules

[Permalink: Core Rules](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#core-rules)

- **API Use**: Always use the provided wrapper `scripts/pubmed_api.py` which
manages rate limits automatically and prevents API abuse. Setting the
`NCBI_API_KEY` environment variable raises the rate limit from 3 to 10
requests/second. Querying the API any other way (e.g. via curl, wget, or
hand-written code) is strictly forbidden.
- **JSON Processing**: Use `jq` to filter and transform JSON output (or python
equivalents if `jq` is not available) to prevent hallucinations and context
overflow.
- **Temporary Files**: To avoid polluting the working directory with JSON
files, use a temporary directory inside the current directory. When running
multiple agents or tasks in parallel, ensure each uses a unique subdirectory
name (e.g., `tmp_$TASK_ID/`) to avoid file collisions.
- **Notification**: If this skill is used, ensure this is mentioned in the
output AND list the URLs of all papers that were used in producing the
output.

## Structure of the skill folder

[Permalink: Structure of the skill folder](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#structure-of-the-skill-folder)

- `SKILL.md` \- This file
- `scripts/pubmed_api.py` \- The skill CLI
- `references/`\- Directory with detailed function specifications

  - `advanced-linking.md`
  - `advanced-search.md`
  - `bulk-workflows.md`
  - `citation-matching.md`
  - `cross-database-linking.md`
  - `fetch-and-resolve.md`
  - `search-and-discovery.md`
  - `utilities.md`

## CLI Usage

[Permalink: CLI Usage](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#cli-usage)

```
uv run scripts/pubmed_api.py <output_file> <function_name> <required_args> [--flag value ...]
```

- **Positional Arguments**: Arguments are positional; list arguments are
passed as comma-separated strings without spaces (e.g.
`"35113657,31234568"`).
- **Flag Options**: Optional arguments can be passed as `--flag value` instead
of positional args.
- **Output Handling**: On success, JSON is written to `output_file`. On error,
the process exits with a non-zero code and no output file is written.

### Example Usage

[Permalink: Example Usage](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#example-usage)

```
uv run scripts/pubmed_api.py ./search_results.json search_pubmed "BRCA1" --max_results 5
cat ./search_results.json | jq '.[]' -r
uv run scripts/pubmed_api.py ./abstracts.json fetch_article_abstracts "35113657"
cat ./abstracts.json | jq '.[0].title' -r
```

## Essential Recipes

[Permalink: Essential Recipes](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#essential-recipes)

**Join PMIDs for the next call (most common chaining pattern):**

```
cat ./search_results.json | jq -r 'join(",")'
```

**Slim abstracts to essential fields and truncate long abstracts:**

```
cat ./abstracts.json | jq '[.[] | {pmid, title, snippet: (.abstract // "")[:500]}]'
```

**Filter by keyword (null-safe):**

```
cat ./abstracts.json | jq '[.[] | select((.title // "") | contains("Review"))]'
```

### Context Management & Accuracy

[Permalink: Context Management & Accuracy](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#context-management--accuracy)

When processing larger result sets (>10 abstracts):

1. **Filter Early**: Use `jq` to verify keywords in abstracts _before_ reading
the full JSON into context.
2. **Slimming**: Extract only `title` and `abstract` fields unless explicitly
instructed otherwise. Author lists and metadata contribute to noise.
3. **Bulk Operations (N > 10)**: Avoid fetching or processing IDs one-by-one.
The API and History Server are designed for bulk retrieval. Fetch all data
in a **single turn** and use shell pipelines to slim the results before
reading into context. This prevents turn exhaustion and context overflow.
4. **Grounding**: Never use internal knowledge to provide specific identifiers
(PMIDs, CIDs, Gene IDs) if no results are found. Report the tool's output
accurately to ensure results are grounded in the current database state.
5. **Search Termination**: When asked to find papers that may not exist, limit
exploration to 3–5 high-quality, varied search queries. If no results match
after these attempts, conclude that no papers meet the criteria rather than
continuing to iterate — unless explicitly instructed to be thorough.

## Functions

[Permalink: Functions](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#functions)

> **⚠️ MANDATORY**: You **MUST** read the linked reference file for a function
> group **before calling any function** in that group. The tables below only
> describe _what_ each function does — not _how_ to call it. Argument names,
> argument order, flags, and output schemas are **only** documented in the
> reference files. **Do NOT guess or infer arguments from function names.** If
> you call a function without first reading its reference, you **will** produce
> incorrect invocations.

### [Search](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/references/search-and-discovery.md)

[Permalink: Search](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#search)

- `search_pubmed`: Find PMIDs matching a free-text or structured NCBI query.
- `global_database_discovery`: Count how many records match a query across
every NCBI database.

### [Fetch & Resolve](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/references/fetch-and-resolve.md)

[Permalink: Fetch & Resolve](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#fetch--resolve)

- `fetch_article_abstracts`: Retrieve metadata and abstracts for a batch of
PMIDs.
- `get_full_text_pmc`: Retrieve open-access full text from PMC.
- `fetch_database_summary`: Resolve opaque UIDs from any NCBI database into
human-readable metadata.

### [Cross-Database Linking](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/references/cross-database-linking.md)

[Permalink: Cross-Database Linking](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#cross-database-linking)

- `find_linked_biological_data`: Find records in other NCBI databases linked
to a source record.
- `discover_available_links`: List all available ELink linknames for a given
record.

### [Bulk Workflows](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/references/bulk-workflows.md)

[Permalink: Bulk Workflows](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#bulk-workflows)

When working with **more than ~10 PMIDs**, avoid processing IDs one-by-one.
Upload them to the NCBI History Server via `cache_results_history` to get a
session handle (`webenv` \+ `query_key`), then pass that handle to
`fetch_article_abstracts` or `find_linked_biological_data` for a single bulk
call. Chain with `jq` shell pipelines to slim results before reading into
context. This prevents turn exhaustion and context overflow. See the reference
for complete workflow recipes (search→fetch, cross-db exploration, citation
resolution, and bulk retrieval with data slimming).

- `cache_results_history`: Upload PMIDs to the NCBI History Server for bulk
retrieval.

### [Utilities](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/references/utilities.md)

[Permalink: Utilities](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md#utilities)

- `verify_medical_spelling`: Spell-check biomedical terms before searching.
- `match_raw_citations`: Resolve incomplete bibliographic citations to PMIDs.

You can’t perform that action at this time.