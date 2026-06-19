# Changelog

All notable changes to GAIA are documented in this file. Versions follow semver (MAJOR.MINOR.PATCH); the four manifests (`pyproject.toml`, `packages/cli-npm/package.json`, `packages/mcp/package.json`, `registry/gaia.json`) move in lockstep.

## 5.0.0 — 2026-06-20

**Breaking — Phase 1.5: G7 Trust Infrastructure**

This is the first release where Trust Magnitude is the canonical scoring axis. Old tooling reading `trustNumber` will see legacy values that no longer drive promotion decisions.

### New
- Trust Magnitude formula live in code (`src/gaia_cli/trustMagnitude.py`).
- 6-predicate Apex gate enforcement (was 9; cross-org and system-wide cap moved behind feature flags per 2026-06-17 delta).
- Public Trust Magnitude leaderboard at `/trust/leaderboard/`.
- Interactive `gaia tm-inspect` skill viewer + HTML/JSON output modes for `inspectTrustMagnitude.py`.
- `gaia dev evidence` numeric payload flags: `--magnitude`, `--reviewers`, `--views`, `--skill-count-in-repo`, `--percentile`, `--source-started-at`.
- Timeline action `apex_pr_signed` ratified in v3 RFC.
- Hover-reveal trust grade notch in skill plaques (I8).
- CLI Pre-Flight Rule: `gaia dev update-named` now rejects schema-invalid states before write (status=`named` requires `title` or `catalogRef`); auto-emits `name` timeline event on awakened→named promotion.
- `--title` and `--catalog-ref` flags on `gaia dev update-named` for one-shot canonicalization.
- `/memory-snapshot` skill at `.claude/skills/memory-snapshot/` for additive MEMORY.md updates.

### Changed
- 10-type evidence taxonomy (G7 RFC v2 ratified 2026-06-18, v3 ratified 2026-06-20).
- Trust grade thresholds at G7 floors: **S ≥ 250, A ≥ 100, B ≥ 50, C ≥ 20** (legacy 90/80/60/40 retired). All bundled schemas (`src/gaia_cli/data/registry/schema/`) sync'd to canonical.
- Apex gate depth-2 walker permits `suiteComponent` overlap with depth-1 (cycle-self guard kept). Implemented in I12.
- `generateNamedIndex.py` propagates frontmatter `trustMagnitude` / `overallTrustGrade` canonical (frontmatter wins; recomputation only when missing) — fixes mattpocock badge regression (20 → 34 named, suite TM 480.3) and S=4 leaderboard alignment.
- Top-4 S-grade skills (`garrytan/gstack`, `ruvnet/ruflo`, `mattpocock/skills`, `obra/superpowers`) hold `apex_pr_signed`; awaiting full A-graded-origins-≥-5 + tenure-≥-180-days closure (deferred to Sprint A).

### Distribution snapshot
- 249 named skills total
- **S=4, A=42, B=56, C=76, ungraded=71**
- (was S=4, A=20, B=31, C=93, ungraded=101 pre-Phase-1.5 — +30 across the C floor, +22 to A)

### Migration
- Schema additions (`sourceStartedAt`, `apexGateStatus`, `apex_pr_signed`) are additive — old data validates as-is.
- Tooling reading `trustNumber` for ranking should switch to `trustMagnitude` + `overallTrustGrade`.
- See `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` (v2) and `founder/handovers/G7_RFC_V3_RATIFICATION_2026-06-20.md` (v3 delta).

### Closes
Phase 1.5 milestone (#8) — 29 issues closed. Final consolidation in PR #742 (merged 2026-06-20 at `4dd4e945`, never-squashed merge-commit per founder/GIT.md §3.2).

---

## Earlier versions

For releases prior to 5.0.0, see `git log --oneline --grep "release"` and the GitHub releases page.
