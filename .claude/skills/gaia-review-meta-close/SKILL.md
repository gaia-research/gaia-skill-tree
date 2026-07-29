---
name: gaia-review-meta-close
description: >
  Close out a review/meta branch that lands an evidence-ingest / curation batch:
  create the named nodes, ingest verified evidence, appraise Trust Magnitude,
  calibrate stars, wire suites, correct upstream naming, stage ONLY the intended
  artifacts (dropping CRLF churn and blocking leaks), validate, and open the PR.
  Use when a curation/ingest batch is verified and ready to land, or when the user
  says "close the review/meta branch", "land the ingest batch", "wrap up the
  intake PR", "/gaia-review-meta-close". Wraps the deterministic hygiene in
  scripts/review_meta_close.py and gates the judgment calls (calibration, Origin,
  suite promotion, naming, merge) behind explicit human checkpoints.
version: "1.0.0"
---

# /gaia-review-meta-close

Turns the messy, rules-everywhere review/meta close-out into a bounded pipeline:
**the script owns the mechanical parts, the human owns the judgment parts.** It
exists because the ingest → appraise → calibrate → suite → name → stage → PR
sequence has ~10 precise rules (Origin gate, suite-manifest survival, CRLF churn,
badge/Class-S discipline, UTF-8 validate) that are easy to get wrong one at a time.

Backed by `scripts/review_meta_close.py` (status / stage / validate / check).

## When to run

After `/ev-pipeline` (or `/gaia-curate-chain`) has verified the evidence and an
L4 reviewer approved the batch. This skill lands it; it does not discover or
re-verify evidence.

## Operating principle

- **Programmatic by default.** Every registry mutation goes through a `gaia dev`
  verb (Programmatic-First Policy). Never hand-edit frontmatter or timelines.
- **Human gates catch what the pipes missed.** Stop at each GATE below for an
  explicit decision. These are the four places prior phases most often ship a
  wrong star, a stripped suite, a capability-vs-upstream name mismatch, or an
  accidental merge. A gate is a genuine stop — present the finding, wait.
- **Prefix every `gaia dev` call** with `GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src`
  and pass `--no-build` on every mutation; run exactly one build at the end.

## Pipeline

### 0. Branch

Work on `review/meta/<slug>` cut from `origin/main`. Confirm you are on it
(`git rev-parse --abbrev-ref HEAD`) before any edit — a commit landing on the
wrong branch is a real failure mode. Commit + push after each logical unit.

### 1. Create nodes (dependency order)

Named-skill evidence cannot be written until the node exists, and a named node
needs its generic ref to exist first. Order:

1. Generic bucket: `gaia dev add "<Name>" --id <slug> --type basic --description "..." --no-build`
   (skip if the generic already exists — `gaia dev list --generic | grep <slug>`).
2. Named skill: `gaia dev add "<Name>" --named --contributor <handle> --generic-ref <slug>
   --description "..." --title "<Title>" --extra-fields '{"links":{"github":"<blob-url>"}}' --no-build`.

Contributor handles must be lowercase (`Panniantong` → `panniantong`); the display
name/title can keep original casing. Blob URL must be `blob/<branch>/<path>`, never `tree/`.

### 2. Ingest evidence (one row at a time)

For each verified row in the data lake, `gaia dev evidence <contributor/skill> "<url>"
--type <type> <typed-flags> --notes "..." --source-started-at YYYY-MM-DD --no-build`.
Use the numeric flags the type supports (`--stars`, `--views`, `--citations`,
`--reviewers`, `--commits`, `--contributors`, `--skill-count-in-repo`, `--percentile`).
A `benchmark-result` needs its full reproducibility payload (attestor, dataset/input
hashes) — a mirrored third-party benchmark that can't supply them is EXCLUDED from
TM; record it in the lake, not as a registry row with faked hashes.

### 3. Appraise (use the RIGHT tool)

TM is a **derived** value read *after* build — never write it. Read it with the
canonical inspector, which loads the named `.md` evidence:

```bash
GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 scripts/inspectTrustMagnitude.py --skill <contributor/skill>
```

Do NOT rely on `scripts/trust_appraise.py --skill` for named skills — it reads the
generic node (empty evidence) and reports TM 0. `trust_appraise.py` is the
pre-curation dry-run (`--repo` suite mode); the inspector is the post-ingest reader.

### 4. GATE — calibration (TM band **and** Origin)

Per `META.md`: TM bands map S≥250→5★, A≥100→4★, B≥50→3★, C≥20→2★, ungraded(<20)→1★.
But **4★ additionally requires Origin status** — being the sole/most-renowned named
implementation in the generic bucket (exactly one Origin per bucket). Before
proposing 4★, check the bucket: `grep -rl "genericSkillRef: <slug>$" registry/named/`.
If a stronger incumbent holds the bucket, the A-grade skill caps at 3★ unless you
move competitors to a different generic (`gaia dev update-named <other> --generic-ref <new-bucket>`)
and set `--origin true`.

**STOP.** Present a table (skill | TM | grade | bucket occupancy | proposed star)
and get explicit operator approval. Then apply approved calibrations:
`gaia dev calibrate <contributor/skill> <N★> --no-build` (star glyph, not bare int).
A skill landing at 1★ is not Named — that is a legitimate outcome for ungraded
Stage-1 skills; the redaction validator handles it, `status: named` is fine.

### 5. GATE — suites (use `gaia dev fuse`, not update-named)

If the batch includes a suite capstone: **`gaia dev update-named --suite-components`
alone does NOT survive `gaia dev build`** — `gaia dev docs` strips `suiteComponents`
from frontmatter unless a suite manifest at `registry/suites/<contributor>/<slug>.json`
backs it. Establish suites with:

```bash
gaia dev fuse <generic-id> --name "<Name>" --description "..." \
  --prereqs <comp-generic-ids> --named-capstone <contributor/capstone> \
  --suite-components <contributor/comp-1>,<contributor/comp-2>,... --no-build
```

Verify after build that `grep -c suiteComponents registry/named/<contributor>/<capstone>.md`
is ≥1. **STOP** for the capstone rank decision (recipe-driven TM can overstate a
young repo — a founder ruling may hold it below its TM band).

### 6. GATE — upstream naming

The intake slug is often the *capability* name, not the real upstream skill
(e.g. `ux-audit` for `ui-ux-pro-max`, `format-output` for `i-have-adhd`). Compare
each named id against its `links.github` folder/file. **STOP** and confirm which
should be corrected — intentional command-name divergences (documented in the
intake issue) are left alone. To correct: `gaia dev rename <contributor/old>
<contributor/new>` (named-skill rename is supported), then `gaia dev update-named
<contributor/new> --name "<Upstream Name>" --title "<Upstream Name>"`. The
`genericSkillRef` (capability bucket) does not change — only the named id + display.

### 7. Build once, then hygiene + stage

```bash
GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev build   # single build
python scripts/review_meta_close.py status -v          # classify real / EOL-noise / leaks
python scripts/review_meta_close.py stage --contributor <h1,h2,...> --apply   # stage intended only
python scripts/review_meta_close.py check               # must be CLEAN
```

The script stages ONLY: `registry/{named,nodes,suites}`, tracked `registry/*.md`,
`docs/graph/*` (Class S — Guard E), `docs/badges/registry.json`, and
`docs/badges/_assets/<h>/` + `docs/og/<h>/` for the handles you pass. It
renormalizes to LF (killing CRLF churn) and never stages a leak. Badges are only
2★+ (1★ carry none). Everything else the build touched (version-bump churn on
unrelated profiles, other contributors' badges) is intentionally left out —
never `git add -A`. If `stage` lists real changes OUTSIDE the allowlist, review
them: they are either version-churn (discard) or need another `--contributor`.

### 8. Validate + commit + push

```bash
python scripts/review_meta_close.py validate    # gaia dev validate, UTF-8-safe, must PASS
git commit -m "..."   # conventional; note calibrations, renames, suite in body
git push
```

Merge conflicts land only in generated `docs/graph/*` — take `--ours`, complete
the merge, re-run the single build, re-stage `docs/graph/*`. Never hand-merge them.

### 9. PR

Open (or edit) the PR with `--body-file` (real newlines):
- `Resolves #<n>` for each fully-closed intake issue. A suite issue with sub-skills
  held for separate promotion is listed but NOT auto-resolved — say so explicitly.
- Summary table: skill | TM | grade | calibrated stars.
- Note the pre-ingest fixes (e.g. a `tree/`→`blob/` correction) and any renames.
- Include an **Entrypoints** section (usually "registry-data + CLI PR; no new
  user-facing pages" for a pure ingest).
- Verify: `gh pr view <n> --json body,mergeable`.

### 10. GATE — merge

Do **not** merge. Report the PR URL, CI status, and the calibration table. The
final merge to `main` is a human decision (this skill never merges).

## What the script owns vs what you own

| Mechanical (script) | Judgment (you, at a GATE) |
|---|---|
| classify real vs EOL-noise vs leaks | which star each skill lands at (§4) |
| LF-renormalized allowlist staging | Origin bucket resolution (§4) |
| refuse/flag leaks, never `git add -A` | suite capstone rank (§5) |
| UTF-8-safe `gaia dev validate` | which names to correct vs leave (§6) |
| staged-EOL-noise + conflict preflight | which issues to `Resolves` (§9); merge (§10) |

## Known tooling frictions (worked around here; report persistent ones)

- `gaia dev build` strips `suiteComponents` without a suite manifest → use `gaia dev fuse` (§5).
- `gaia dev validate` crashes on Windows (cp1252 on ✓) → the script runs it UTF-8-safe.
- `trust_appraise.py --skill` reads the empty generic node for named skills → use `inspectTrustMagnitude.py` (§3).
- Windows checkouts introduce CRLF churn on every touched file → the script's LF-renormalized allowlist drops it.
