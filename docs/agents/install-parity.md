# Install-parity harness

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
   different names depending on how you installed it.

Link-vs-copy and lockfile shape are recorded as KPIs, never as failures.

## Categories

Every skill is classified before it runs, because the four kinds are not
comparable the same way:

| Category | What it is | How it's judged |
|---|---|---|
| `STANDARD` | `links.github` has `/blob/` or `/tree/` | dir name **and** full content diff |
| `REPO_ROOT` | bare `github.com/owner/repo` | no content diff — gaia symlinks the whole clone as one skill while the npm CLI discovers N inside it. Health + name only; the fan-out is a KPI |
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

## Reading the output

Failures print one line per finding, leading with the skill:

```
FAIL  gsd-build/ship    NO_SKILL_MD    no SKILL.md in installed tree .../commands/gsd
FAIL  stanfordnlp/dspy  NOT_A_SKILL_DIR  gaia exited 0 but installed a non-directory: .../dspy/__init__.py
```

### Findings are grouped by where the fix belongs

A flat list of failures is a wall; the same list split by origin is a work plan.
Every finding carries one of four origins, and the report groups by them:

| Origin | Means | Fix in |
|---|---|---|
| `DATA` | the registry entry describes the wrong thing | `registry/named/<contributor>/<slug>.md` — via `gaia dev` verbs, per the Programmatic-First Policy |
| `CLI` | gaia accepted or produced a state it should have rejected | `src/gaia_cli/install.py` |
| `UPSTREAM` | the source repo moved, went private, or vanished | nothing here — re-link or freeze the skill |
| `HARNESS` | measurement noise | re-run, or raise `--timeout` |

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
| `DIRNAME_MISMATCH` | DATA | the two installers named the directory differently |
| `NPX_NO_SKILL_DISCOVERED` | DATA | the npm CLI found no skill at that URL |
| `NPX_FAN_OUT` | DATA | a `blob`/`tree` link resolved to more than one skill |
| `SUITE_COMPONENT_FAILED` | DATA | named components did not install |
| `CONTENT_MISSING_FILE` / `CONTENT_EXTRA_FILE` / `CONTENT_BYTES_DIFFER` | DATA | tree diff — usually the link points at a near-miss directory |
| `DANGLING_SYMLINK` | CLI | gaia reported success but the target does not exist — `_install_single` never validates the subpath |
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
