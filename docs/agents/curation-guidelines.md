# Curation Guidelines

Refer to [DEV.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/DEV.md) for local environment setup, testing, and CI troubleshooting. Keep these curation-specific rules in mind.

All meta shifts route through `gaia dev add` / `gaia dev merge` / `gaia dev split` / `gaia dev evidence` (Programmatic-First Policy) rather than hand-edits.

## 1. `links.github` URL must use `blob/` not `tree/`
`src/gaia_cli/install.py::_parse_github_url` only recognises `https://github.com/owner/repo/blob/branch/subpath`. A bare repo URL (`https://github.com/owner/repo`) installs to the repo root and makes the skill undiscoverable (symlink has no `SKILL.md` at top level). GitHub's directory-view URLs use `tree/` — convert them to `blob/` manually.

## 2. Only `links.github` is read by the installer
The install pipeline reads `meta.get("links", {}).get("github")` and nothing else. Wrong keys seen in the wild and their fixes:
| Wrong key | Fix |
|---|---|
| `links.repo:` | rename to `links.github:` |
| `links.docs:` | rename to `links.github:` (strip any `#fragment`) |
| `links.arxiv:` | add `links.github:` alongside (keep arxiv) |
| `origin: https://...` | move URL to `links.github:`, set `origin: false` |

## 3. Suites never need `links.github` — do not flag them as uninstallable
Any skill with `suiteComponents` (e.g. `mattpocock/skills`, `garrytan/gstack`) installs by iterating its components. It has no installation directory of its own and does not need `links.github`. Only **non-suite** individual skills need `links.github`.
For non-suite skills at 2★ or below with no known public repo: mark `installable: false` in frontmatter and do not re-research on repeated audit passes. See **CONTRIBUTING.md §12** for the full exempt list and the 3★+ demotion rule.

## 4. Suite component links need subpaths
A suite skill (has `suiteComponents`) whose `links.github` is a bare repo root will install symlinks pointing to the repo root. Every component must have a `blob/branch/subpath` URL pointing to its actual skill directory.

## 5. Canonical source URL by evidence type

Each Stage-1 evidence type has one canonical URL shape. Using the wrong shape
either breaks the type's own scoring inputs or collides with same-source
dedup (`(type, url)`-keyed — see §6 below) in unintended ways.

| Type | Canonical URL | Notes |
|---|---|---|
| `repo-own` | `https://github.com/owner/repo` | Repo root — commits/contributors counted from the repo API. |
| `github-stars-own` | `https://github.com/owner/repo/blob/branch/subpath/SKILL.md` | Use the specific blob URL, not the repo root, in a multi-skill (suite) repo — one `github-stars-own` row per skill at its own blob URL avoids every skill in the suite colliding on the same `(type, url)` dedup key. |
| `proxy-containment` | URL of the external project bundling the skill | Not the skill's own repo — the *container* project's URL. |
| `verifier-attestation` | URL to the attestation record (PR review, issue comment, signed statement) | |
| `benchmark-result` | URL to the published benchmark leaderboard/results page | Requires a `percentile` field alongside the URL — see §6 below. |
| `arxiv` | `https://arxiv.org/abs/XXXX.XXXXX` | Abstract page, not the PDF. |
| `peer-review` | URL to the written critique/review record | See #1418 multi-target peer-review partitioning for one URL covering several skills. |
| `self-attestation` | Skill's own repo or a contributor declaration URL | Max 1 entry per skill; flat 10 magnitude regardless of URL content. |
| `social-signal` | URL to the specific video/post | Not a channel/profile URL — the individual piece of content. |
| `npm-downloads` | `https://www.npmjs.com/package/<name>` | Package page; download counts fetched via the npm registry API, not scraped from this URL. |
| `fusion-recipe` | N/A (structural) | Auto-derived for fused/Ultimate skills; never hand-added. |

## 6. Evidence pipeline — Trust Magnitude learnings (I11, 2026-06-20)

Key facts for evidence curation that affect computed TM scores:

**Same-source dedup is `(type, url)`-keyed — cross-type never collapses** (`_dedupeSameSource` in `trustMagnitude.py`): two rows only collapse into one when they share BOTH the same evidence `type` AND the same canonical URL; the highest-magnitude entry wins and the rest are recorded in `_collapsedSources`. A `repo-own` row and a `github-stars-own` row at the identical URL are DIFFERENT keys (different type) and both count independently — they do NOT dedupe against each other. Dedup only bites when you add a *second row of the same type* at a URL already carrying one (e.g. two `repo-own` entries at the same repo, or two `github-stars-own` entries at the same URL after a rename) — in that case only the higher-scoring one counts.

**github-stars-own mothership discount formula**: `artifact_score = (stars/1000) / skill_count_in_repo * weight`. For large suites (34+ skills), per-skill contribution is tiny. Prefer `social-signal` or `peer-review` for high-impact additions.

**peer-review is the highest-impact type for science skills**: `reviewers=3` gives magnitude=75, weight=1.2, so artifact_score≈90. One published NAR/Nature paper lifts a skill from TM=10 to TM=100+ (A grade) immediately.

**benchmark-result requires `percentile` field**: The magnitude formula uses `row.get("percentile", 0)`. Without it, score=0. Without a percentile score, use `peer-review` type instead.

**rm-evidence --source removes ALL entries at that URL**: If two entries share the same source URL (e.g. `repo` and `github-stars-own`), `--source URL` removes both. Inspect indices first.

**CLI run path in worktrees**: In worktrees, `python3 -m gaia_cli` may resolve to the installed system version, not the worktree source. Use `PYTHONPATH=/path/to/worktree/src python3 -m gaia_cli` to ensure branch-local CLI (e.g. when testing a new flag from a pending branch).

**social-signal view floor**: views < 1000 → score = 0. Formula: `log10(views) * 8.0`. 10K views ≈ 32 score; hard-capped at 80 per skill.

**firecrawl-search as WebSearch fallback**: When WebSearch API is down, use `firecrawl search "<query>" -o .firecrawl/result.json --json`. Always write to `.firecrawl/` directory.
