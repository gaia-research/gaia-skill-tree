# Install-parity harness

## Run it (TL;DR)

```bash
# One skill, ~30s — start here to see what the output looks like
python scripts/install_parity.py --only garrytan/health

# One contributor, a few minutes — the usual working loop
python scripts/install_parity.py --contributor mattpocock

# Everything, ~40-60 min and ~2 GB of clones — the periodic health read
python scripts/install_parity.py --json generated-output/parity/report.json
```

Needs `git`, `node`, `npm`, and network. Nothing is written outside gitignored
`generated-output/`. Read the closing **`VERDICT`** block first — it tells you
whether the next pass is a data pass, a CLI pass, or a decision.

---

`scripts/install_parity.py` sweeps every named skill in the registry, installs
each one twice — once with `gaia install`, once with the `skills` npm CLI
(`npx skills add`) — and diffs the result.

**It is a standalone operator tool, not a CI gate.** It lives in `scripts/`, is
never collected by pytest (`pyproject.toml` sets `testpaths = ["tests"]`), and
must not be wired into a workflow. It is network-bound, hits ~53 upstream repos,
and its verdicts move when *upstream* changes — none of which belongs in a
merge gate.

## What it proves

That a named skill in the Gaia Skill Tree delivers the *same skill* the wider
ecosystem's installer delivers. If gaia silently ships different bytes, a
wrongly-named directory, or nothing at all, this is the only thing that says so.

## What parity means here

The two installers are structurally different by construction, so byte-identical
*layouts* are impossible and are not the test:

| | `gaia install` | `npx skills add` |
|---|---|---|
| what lands | **symlink** → `$GAIA_HOME/skills/<contrib>/<repo>/<subpath>` | **real copied files** |
| dir name from | registry slug (`id.split("/")[1]`) | `sanitizeName(frontmatter.name)` |
| target dir | `.agents/skills/<name>` | `.claude/skills/<name>` when a single agent is named |
| manifest | `.gaia/install-manifest.json` | `skills-lock.json` |

Parity is judged on two things only:

1. **Delivered content** — every file's relative path and SHA256 must match.
   Skips exactly what the npm CLI skips: `.git`, `__pycache__`, `__pypackages__`,
   and `metadata.json`.
2. **Installed directory name** — the registry slug must equal the name the
   ecosystem installer chooses. A mismatch means the same skill answers to two
   different names depending on how you installed it. Settled by
   [issue #1446](https://github.com/gaia-research/gaia-skill-tree/issues/1446)
   (Option A): the registry slug is authoritative — `install.py` is unchanged,
   and a mismatch is curation debt fixed with `gaia dev rename <old-id> <new-id>`.

Link-vs-copy and lockfile shape are recorded as KPIs, never as failures.

### The npm CLI is not always a valid oracle

A `REPO_ROOT` link points at a repo that **groups** skills — it is not itself a
single-skill repo. The npm CLI may legitimately find nothing there, or find N
skills under names of its own choosing, and neither says anything about whether
Gaia works. So `REPO_ROOT` is judged **purely on the gaia side**: did
`gaia install` produce a real directory containing a `SKILL.md`? Whatever the
npm CLI did is captured in `npxNote` and `npxDiscovered` for information only.

`ruvnet/*` is the reference case. The comparison is still run and reported —
that is how you learn whether the npm CLI copes with grouped-skill repos — but
it can never fail a skill.

## Categories

Every skill is classified before it runs, because the four kinds are not
comparable the same way:

| Category | What it is | How it's judged |
|---|---|---|
| `STANDARD` | `links.github` has `/blob/` or `/tree/` | dir name **and** full content diff |
| `REPO_ROOT` | bare `github.com/owner/repo` | **gaia-side only.** Does `gaia install` produce a real directory with a `SKILL.md`? The npm CLI's result is recorded, never failed on — see below |
| `SUITE` | `suiteComponents` non-empty | no content diff — instead, **every** component must install |
| `NO_SOURCE` | no `links.github` | must fail, and fail with the right message. An install that *succeeds* is the failure |

## Running it

```bash
python scripts/install_parity.py                       # full sweep
python scripts/install_parity.py --list                # what would run, no installs
python scripts/install_parity.py --only garrytan/health --keep
python scripts/install_parity.py --contributor mattpocock
python scripts/install_parity.py --category STANDARD --limit 25 --jobs 4
python scripts/install_parity.py --json generated-output/parity/report.json
```

Exit codes: `0` full parity, `1` at least one failure, `2` precondition failure
(missing `git`/`node`/`npm`, unreachable npm registry, no registry index).

Useful flags: `--keep` retains sandboxes for inspection, `--jobs 1` forces serial
for clean timing, `--timeout` guards very large repos, `--npx-version` pins the
comparison tool, `--gaia-bin` tests an installed `gaia` instead of this checkout.

Requires `git`, `node`, and `npm`, plus network. Everything it writes goes to
gitignored `generated-output/parity/<runid>/` and is removed unless `--keep`.

**Budget for a full sweep:** ~40–60 minutes at `--jobs 8`, and roughly **2 GB**
of clone cache across the ~53 source repos. `--keep` leaves all of it on disk —
delete `generated-output/parity/` when finished inspecting. Narrow with
`--contributor`, `--category`, or `--only` for day-to-day work; the full sweep
is for a periodic health read, not an inner loop.

## Reading the output

Findings print one line each, grouped under the origin that owns the fix:

```
FINDINGS (2 across 2 skill(s))
==============================================================================
DATA — registry curation; fix registry/named/<contributor>/<slug>.md  [2]
==============================================================================
* stanfordnlp/dspy  NOT_A_SKILL_DIR  gaia exited 0 but installed a non-directory: .../dspy/__init__.py
  google-deepmind/chembl_database  DIRNAME_MISMATCH  gaia:'chembl_database' npx:'chembl-database'
    fix: gaia dev rename google-deepmind/chembl_database google-deepmind/chembl-database
```

and the run closes with the verdict:

```
VERDICT — what the next pass actually is
  data updates      2 skill(s) need a registry edit (gaia dev verbs)
  cli updates       0 skill(s) blocked by an installer defect
```

### Findings are grouped by where the fix belongs

A flat list of failures is a wall; the same list split by origin is a work plan.
Every finding carries one of five origins, and the report groups by them:

| Origin | Means | Fix in |
|---|---|---|
| `DATA` | the registry entry describes the wrong thing | `registry/named/<contributor>/<slug>.md` — via `gaia dev` verbs, per the Programmatic-First Policy |
| `CLI` | gaia accepted or produced a state it should have rejected | `src/gaia_cli/install.py` |
| `POLICY` | **reserved** — a whole failure class turns on one undecided ruling | decide first, then act once |
| `UPSTREAM` | the source repo moved, went private, or vanished | nothing here — re-link or freeze the skill |
| `HARNESS` | measurement noise | re-run, or raise `--timeout` |

`POLICY` exists so the report never overstates undecided work — a class whose
fix depends on a ruling nobody has made yet should not be counted as N separate
curation edits. `DIRNAME_MISMATCH` used to be the archetype: the registry slug
and the upstream skill name disagreed, and it was unclear whether the fix was
renaming the slug or having the installer adopt the upstream name. Issue #1446
settled it (Option A, registry slug wins), so `DIRNAME_MISMATCH` is now plain
`DATA` — no `POLICY` findings are currently mapped to any failure code, but the
origin stays defined for the next open question. **Count the class, decide,
then act.**

### Keeping slugs in sync

Option A is a standing obligation, not a one-time cleanup: whenever an
upstream `SKILL.md` changes its frontmatter `name`, the registry slug can
drift out of sync again and the next parity run will report a fresh
`DIRNAME_MISMATCH`. `docs/agents/upstream-watcher.md` is the natural place to
catch this going forward — an upstream rename is exactly the kind of event it
already opens tracking issues for.

The run ends with a `VERDICT` block that states this directly: how many skills
need a registry edit, how many are blocked by an installer defect, how many
findings a single ruling would clear, and what to ignore.

Findings marked `*` are **dual-origin**: a bad link caused them, *and* gaia
installed it without complaint. Fixing the data clears the finding; hardening
the installer stops the next one landing silently. Worth filing both.

### Failure codes

| Code | Origin | Meaning |
|---|---|---|
| `NOT_FOUND` | DATA | ref did not resolve in the registry |
| `AMBIGUOUS_REF` | DATA | duplicate slug; `resolve_named_skill_reference` raised `ValueError` |
| `NO_SOURCE_LINK` | DATA | no `links.github` (expected only for `NO_SOURCE`) |
| `NOT_A_SKILL_DIR` | DATA\* | gaia exited 0 having installed a file, not a directory |
| `NO_SKILL_MD` | DATA\* | the installed tree contains no `SKILL.md` |
| `DIRNAME_MISMATCH` | DATA | the two installers named the directory differently; fix with `gaia dev rename` (issue #1446) |
| `NPX_NO_SKILL_DISCOVERED` | DATA | the npm CLI found no skill at that URL |
| `NPX_FAN_OUT` | DATA | a `blob`/`tree` link resolved to more than one skill |
| `SUITE_COMPONENT_FAILED` | DATA | named components did not install |
| `CONTENT_MISSING_FILE` / `CONTENT_EXTRA_FILE` / `CONTENT_BYTES_DIFFER` | DATA | tree diff — usually the link points at a near-miss directory |
| `DANGLING_SYMLINK` | DATA\* | `links.github` points at a path that no longer exists upstream; gaia reported success anyway |
| `GAIA_INSTALL_FAILED` | CLI | gaia exited nonzero for another reason, or wrote no manifest entry |
| `UNEXPECTED_SUCCESS` | CLI | a `NO_SOURCE` skill installed anyway |
| `GIT_CLONE_FAILED` | UPSTREAM | 404, private, or network — captured `git` stderr |
| `TIMEOUT` | HARNESS | either side exceeded `--timeout` |
| `NPX_INSTALL_FAILED` | HARNESS | the npm CLI itself exited nonzero |

Checks run in dependency order, so a skill stops at its first real problem: a
broken gaia install is not also reported as a content diff.

### KPIs

- **`gaia cold` vs `gaia warm`** — the headline timing. Cold is the first skill
  of each source repo and includes the `git clone`; warm reuses the cache. Only
  warm reflects what a user with a primed cache experiences.
- **Dirname mismatches** — registry slugs that disagree with the ecosystem name.
  Expected zero after issue #1446; any nonzero value is new curation debt from
  an upstream rename, fixed with `gaia dev rename`.
- **Dangling symlinks** — a pure gaia-installer health number. Should be zero.
- **Suite component coverage** — `installed/total` overall and per suite.
- **Repo-root fan-out** — how many skills gaia installs as one versus how many
  the npm CLI finds in the same repo.
- **Findings by origin** — how much is curation work versus installer work.

## Design notes for anyone editing it

- **Skill list comes from `docs/graph/named/index.json`**, not
  `list_available()`. `registry/named-skills.json` is Class P and gitignored, so
  on a clean checkout `list_available()` falls back to scanning frontmatter —
  which loses `suiteComponents` for suites declared under `registry/suites/`,
  misclassifying the exact skills that need suite handling.
- **Source URLs come from `gaia_cli.install._parse_github_url`**, imported
  rather than reimplemented, so the harness cannot drift from what the
  installer actually resolves.
- **Concurrency shards by source repo**, one repo per worker. gaia's clone cache
  is shared across the run, so two workers on the same repo would race two
  `git clone`s into one destination. Sharding removes the race without locking,
  and gives the natural cold-then-warm ordering the timing KPI depends on.
- **The npm CLI's `HOME` and `XDG_STATE_HOME` are per skill**, not per run —
  it writes a global `.skill-lock.json` that concurrent workers would corrupt.
  `DO_NOT_TRACK=1` suppresses its telemetry POSTs.
- **A timed-out or failed clone purges its cache dir.** gaia treats any existing
  directory as a valid cache and only runs `git pull` on it, ignoring the exit
  status — so a partial clone would silently poison every later skill from that
  repo.
