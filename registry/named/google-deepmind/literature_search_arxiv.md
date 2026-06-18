---
id: google-deepmind/literature_search_arxiv
name: Literature-Search-Arxiv
contributor: google-deepmind
origin: false
genericSkillRef: literature-search
status: awakened
level: 2★
description: Search for scientific papers, preprints, and publications on arXiv. Extract
  metadata, abstracts, and download full-text PDFs or HTML versions of papers. Use
  when the user asks to find research papers, literature, or specific arXiv IDs.
createdAt: '2026-05-23'
updatedAt: '2026-06-14'
links:
  github: https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_arxiv/SKILL.md
evidence:
- class: B
  source: https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_arxiv/SKILL.md
  evaluator: unknown
  date: '2026-05-23'
  notes: Official Google DeepMind literature_search_arxiv science-skill implementation.
    (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:33Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_arxiv/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:16Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
trustMagnitude: 0.0
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
trustMagnitudeInputHash: 028a063469f070705a49fa9ed3e7b0be1f611c82c012e609eed756462c7240e9
---

# arXiv Search and Retrieval

## Prerequisites

1.  **`uv`**: Read the `uv` skill and follow its Setup instructions to ensure
    `uv` is installed and on PATH.
2.  **User Notification**: If LICENSE_NOTIFICATION.txt does not already exist in
    this skill directory then (1) prominently notify the user to check the terms
    at https://info.arxiv.org/help/api/index.html and to always check the
    license of the papers retrieved by the skill for any restrictions, then (2)
    create the file recording the notification text and timestamp.

## Core Rules

-   **Terms of Use**: You MUST respect arXiv's Terms of Use.
    -   Maximum 1 request every 3 seconds.
    -   The provided utility scripts handle rate limiting automatically. Always
        use these scripts rather than writing your own curl/python requests.
-   If this skill is used, ensure this is mentioned in the output AND list the
    URLs of all papers that were used in producing the output.

## Utility Scripts

**1. Search and Extract Metadata**

Search arXiv and return a clean JSON array of matching papers.

```bash
uv run scripts/search_arxiv.py --query "au:einstein AND ti:relativity" \
  --max_results 5 2>/dev/null > /tmp/arxiv_search_results.json
```

> **Important**: The tool outputs a large JSON result to stdout. Requesting 100+
> results will produce a massive JSON that might exceed your context length.
> Limit `--max_results` (e.g., 5-10) or paginate carefully using `--start`.
> Always redirect output to a file and parse it separately, otherwise terminal
> output will be truncated.

*Returned Metadata:* JSON results include `id`, `title`, `summary`, `published`,
`authors`, `pdf_url`, `primary_category`, `doi`, `journal_ref`, and `comment`.
Note: the `doi` field only contains DOI information in case the paper has an
external DOI and if only an arXiv-issued DOI exists, this is DOI is not
returned.

*Options:*

-   `--query`: Search string. See
    [references/query_syntax.md](references/query_syntax.md) for advanced
    syntax.
-   `--id_list`: Comma-separated list of arXiv IDs to fetch directly (e.g.,
    `1706.03762v5`).
-   `--start`: Pagination offset (default 0).
-   `--max_results`: Number of results to return (default 10).
-   `--sort_by`: `relevance`, `lastUpdatedDate`, or `submittedDate`. (Use
    `--sort_by submittedDate --sort_order descending` for the most recent
    papers).
-   `--sort_order`: `ascending` or `descending`.

**2. Download Paper (PDF or HTML)**

Download the full text of a paper to your local workspace for reading.

```bash
uv run scripts/download_paper.py --id 1706.03762 --format pdf --output attention.pdf
```

*Options:*

-   `--id`: The arXiv ID (e.g., `1706.03762` or `1706.03762v5`).
-   `--format`: `pdf` or `html`. Note: HTML is only available for newer papers.
-   `--output`: Filepath to save the downloaded document.

> **Important**: when downloading papers, make sure you download them to a
> location where you do not overwrite other files and do not clutter existing
> directory structure.

**3. Download Paper Source (tar.gz)**

Download the LaTeX source files of a paper to your local workspace. Note that
not all papers have source available.

```bash
uv run scripts/download_paper_source.py --id 2010.11645 --output source.tar.gz
```

*Options:*

-   `--id`: The arXiv ID (e.g., `2010.11645`).
-   `--output`: Filepath to save the downloaded tar.gz file.

> **Caution**: Care should be exercised when untar'ing the downloaded file for
> security and to avoid cluttering your filesystem, as archives may contain many
> files or unexpected directory structures.
>
> **Safe Extraction Requirements**: NEVER extract directly into your working
> directory! Always extract into a dedicated new directory: `bash mkdir
> paper_source && tar -xzf source.tar.gz -C paper_source`

## Reference

-   **Advanced Query Syntax**: See
    [references/query_syntax.md](references/query_syntax.md) for prefixes (au,
    ti, abs), booleans, and date filtering.

## Workflow

1.  Search for papers using `search_arxiv.py`. Review the JSON summaries.
2.  If full text is needed, use `download_paper.py` to fetch the PDF or HTML.
3.  If downloading a PDF, verify the PDF is not empty or corrupted.
4.  Read the downloaded file using standard file reading tools.
