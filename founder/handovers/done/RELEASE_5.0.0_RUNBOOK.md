# Gaia 5.0.0 Release Runbook

This document is the **execution checklist** for the v5.0.0 major release after Marco merges PR #742 to main. Do not bump anything until the merge lands.

## Why 5.0.0 (major bump rationale)

Phase 1.5 ships a fundamental rewrite of the trust model that is **breaking** in two ways:

1. **Schema additions** — `evidence[].sourceStartedAt`, `apexGateStatus.*`, timeline action `apex_pr_signed`. Old tooling that strictly validates against v4.x schemas will reject v5 data.
2. **Trust score semantics** — `trustNumber` is no longer the canonical aggregate. Trust Magnitude (unbounded, set-bonus driven) replaces it. Code that reads `trustNumber` for ranking decisions is now reading legacy data.

Per the version-lockstep rule (`founder/CLAUDE.md` + pre-commit hook), these manifests must all match:

- `pyproject.toml`
- `packages/cli-npm/package.json`
- `packages/mcp/package.json`
- `registry/gaia.json` top-level

All currently at **`4.11.0`** → bump to **`5.0.0`**.

## Pre-merge gate (MUST be green before bump)

- [x] PR #742 reviewed by Marco
- [ ] PR #742 merged to main (merge-commit, **never squash**)
- [ ] CI green on main after merge (validate.yml, branch-scope.yml, meta-guard.yml)
- [ ] feature branches pruned (`design/trust-leaderboard`, `cli/apex-gate-fixes`, `review/meta/i11-floor-curation`, `docs/meta-post-salvage`, `docs/phase-1.5-readme-update`, `docs/dev-md-cli-update`)

## Release execution (post-merge)

### Step 1 — branch from main

```bash
git checkout main
git pull
git checkout -b cli/v5.0.0-release
```

### Step 2 — bump versions in lockstep

```bash
gaia release major --sync
```

This walks all four manifests, sets them to `5.0.0`, and validates the lockstep. If `gaia release` fails (e.g. lockstep already broken), use `gaia release major --sync` first to align, then `gaia release major` again.

### Step 3 — verify the bump

```bash
grep -E '"version"' pyproject.toml packages/cli-npm/package.json packages/mcp/package.json
grep -E '"version"' registry/gaia.json | head -1
# All four MUST print 5.0.0
```

### Step 4 — write CHANGELOG entry

Append to `CHANGELOG.md` (or create if missing) under a `## 5.0.0 — 2026-06-XX` heading:

```markdown
## 5.0.0 — 2026-06-XX

**Breaking — Phase 1.5: G7 Trust Infrastructure**

This is the first release where Trust Magnitude is the canonical scoring axis. Old tooling reading `trustNumber` will see legacy values that no longer drive promotion decisions.

### New
- Trust Magnitude formula live in code (`src/gaia_cli/trustMagnitude.py`).
- 6-predicate Apex gate enforcement (was 9; cross-org and system-wide cap moved behind feature flags per 2026-06-17 delta).
- Public Trust Magnitude leaderboard at `/trust/leaderboard/`.
- `gaia dev evidence` numeric payload flags: `--magnitude`, `--reviewers`, `--views`, `--skill-count-in-repo`, `--percentile`, `--source-started-at`.
- Timeline action `apex_pr_signed` ratified in v3 RFC.
- Hover-reveal trust grade notch in skill plaques (I8).

### Changed
- 10-type evidence taxonomy (G7 RFC v2 ratified 2026-06-18, v3 ratified 2026-06-20).
- Apex gate depth-2 walker now permits suiteComponent overlap with depth-1 (cycle-self guard kept). Implemented in I12.
- Top-4 S-grade skills (`garrytan/gstack`, `ruvnet/ruflo`, `mattpocock/skills`, `obra/superpowers`) hold apex_pr_signed; awaiting full A-graded-origins-≥-5 + tenure-≥-180-days closure.

### Distribution snapshot
- 249 named skills total
- S=4, A=42, B=56, C=76, ungraded=71
- (was S=4, A=20, B=31, C=93, ungraded=101 pre-Phase-1.5)

### Migration
- Schema additions (`sourceStartedAt`, `apexGateStatus`, `apex_pr_signed`) are additive — old data validates as-is.
- Tooling reading `trustNumber` for ranking should switch to `trustMagnitude` + `overallTrustGrade`.
- See `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` (v2) and `founder/handovers/G7_RFC_V3_RATIFICATION_2026-06-20.md` (v3 delta).

### Closes
Phase 1.5 milestone (#8): I1, I2, I3, I4, I5, I6, I7, I8, I9, I10, I11, I12, RFC v3 ratification.
```

### Step 5 — pre-flight tests

```bash
PYTHONPATH=src python3 -m gaia_cli validate
pytest -k "not test_packaging"   # skip platform-specific packaging tests
gaia docs build --check          # verify generated artifacts are in sync
```

### Step 6 — commit + push + tag

```bash
git add -A
git commit -m "release: 5.0.0 — Phase 1.5 G7 Trust Infrastructure

See CHANGELOG.md for full breakdown. Closes Phase 1.5 milestone (#8).
First major release with Trust Magnitude as the canonical scoring axis."

git push origin cli/v5.0.0-release
git tag -a v5.0.0 -m "5.0.0 — Phase 1.5 G7 Trust Infrastructure"
git push origin v5.0.0
```

### Step 7 — open release PR

```bash
gh pr create \
  --base main \
  --head cli/v5.0.0-release \
  --title "release: 5.0.0 — Phase 1.5 G7 Trust Infrastructure" \
  --body "$(cat <<'EOF'
Major release — see CHANGELOG.md.

## Pre-merge checklist
- [ ] CHANGELOG.md entry written and reviewed
- [ ] All 4 version manifests in lockstep at 5.0.0
- [ ] `gaia validate` passes
- [ ] `pytest` green (skip platform-specific packaging tests)
- [ ] `gaia docs build --check` passes
- [ ] Tag `v5.0.0` pushed

## Post-merge
- [ ] PyPI publish (see Step 8)
- [ ] npm publish (cli-npm + mcp-server)
- [ ] GitHub release page (auto from tag)

Resolves Phase 1.5 milestone #8.
EOF
)"
```

### Step 8 — PyPI publish (post-merge)

```bash
# Clean build
rm -rf dist/ build/ *.egg-info/

# Build sdist + wheel
pip install build twine
python3 -m build

# Verify artifacts
ls -la dist/
# Should see: gaia_cli-5.0.0-py3-none-any.whl + gaia_cli-5.0.0.tar.gz

# Test upload to TestPyPI first
python3 -m twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ --no-deps gaia-cli==5.0.0
gaia --version  # MUST print 5.0.0

# Real upload
python3 -m twine upload dist/*

# Verify
pip install --upgrade gaia-cli
gaia --version  # MUST print 5.0.0
```

### Step 9 — npm publish (post-merge)

```bash
cd packages/cli-npm
npm publish --access public

cd ../mcp
npm run build
npm publish --access public
```

### Step 10 — GitHub release

```bash
gh release create v5.0.0 \
  --title "5.0.0 — Phase 1.5 G7 Trust Infrastructure" \
  --notes-file CHANGELOG.md \
  --target main
```

### Step 11 — post-release verification

- [ ] `pip install gaia-cli==5.0.0` works in a fresh venv
- [ ] `gaia --version` prints `5.0.0`
- [ ] `gaia validate` passes against fresh registry pull
- [ ] `npm install -g @gaia-registry/cli@5.0.0` works
- [ ] `npx @gaia-registry/mcp-server` starts cleanly
- [ ] gaia.tiongson.co/trust/leaderboard/ renders post-deploy
- [ ] Update `founder/MEMORY.md` with release timestamp

## Rollback path

If a critical bug surfaces post-publish:

1. **PyPI**: cannot delete a published version, but can yank: `python3 -m twine yank --reason "..." gaia-cli==5.0.0`. Bump to 5.0.1 with the fix.
2. **npm**: `npm unpublish @gaia-registry/cli@5.0.0` (must be within 72 hours of publish, or unrestricted if no dependents). Otherwise, ship 5.0.1.
3. **GitHub release**: `gh release delete v5.0.0` + delete tag `git push origin :refs/tags/v5.0.0`.
4. **Registry**: revert the merge commit on main, force-push (with team coordination).

For non-critical bugs, ship 5.0.1 normally.

## Token cost estimate (release execution)

- Manual execution (Marco): zero LLM cost
- If orchestrator drives it: ~$0.30 (mostly verification + CHANGELOG draft)

## Known caveats

- **Windows console encoding** — `validate_redaction.py` and `validate_timelines.py` print Unicode glyphs (`✓`, `≤`, `★`) that break on Windows `cp1252` consoles. Workaround: `PYTHONIOENCODING=utf-8`. Functionality is unaffected; only the print line. Linux CI is fine.
- **Setuptools ≥ 77 required** for the wheel build (`pip install "setuptools>=77"`). Pre-flight test 5 catches this.

---

*Authored: 2026-06-20, end of Phase 1.5 consolidation. Execute post-merge of PR #742.*
