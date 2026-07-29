# Changelog

All notable changes to GAIA are documented in this file. Versions follow semver (MAJOR.MINOR.PATCH); the three manifests (`pyproject.toml`, `packages/cli-npm/package.json`, `registry/gaia.json`) move in lockstep.

## [7.0.0] - 2026-07-26

### Yggdrasil II — EPIC #1002 — the second meta generation of the registry

**This is a breaking meta shift.** The registry's classification model is rebuilt from the ground up. Ratified 2026-07-07 (v2 amendment 2026-07-14), folded into the live source of truth (`META.md` + `CONTEXT.md`), and released here. Four structural cuts land together, plus the Ascension Overdrive frontend redesign that moved in lockstep on the staging branch.

#### 1 — Type collapse: four values → two

The starless node `type` axis goes from `{basic, extra, ultimate, unique}` to just **`{basic, fusion}`** — `basic` for 0-prerequisite nodes, `fusion` for ≥1. The retired literals `extra` / `ultimate` / `unique` are gone from the schema, the CLI, and every read-time consumer.

- `feat(schema)`: collapse the type enum to `{basic, fusion}`, prune the now-dead `allOf` invariants, drop `evidenceFloors` (#995).
- `feat(cli)`: `gaia dev add --type` and `gaia dev reclassify` choices narrowed to `{basic, fusion}`; `gaia dev fuse` always writes a `fusion` node.
- `feat(#997)`: `scripts/migrate_taxonomy_v6.py` — hard-cutover reclassification (starless type rewrite + directory reorganization, Phase A) and named-skill recalibration (`type_change` + 4★ demotions, Phase B). **Live result: 113 basic + 130 fusion = 243 starless nodes, 0 residue in legacy values.**

#### 2 — Branch derived, never declared

The named-skill **branch** axis stops being a stored field and becomes a read-time derivation `branch = f(suiteComponents present?, rank)`. Three branches — `suite` / `standard` / `unique` — with two 6★ pinnacles: **Apex** (suite) and **Unique Impossible** (unique).

- `feat(tm)`: `computeBranch()` derives branch from `suiteComponents` + rank; provisional `checkUniqueImpossibleGate` (6★ Unique) and `checkUniqueBranchGate`.
- `feat(cli)`: `taxonomy.py` authority module (single source of truth for branch/rank/medallion/contractVersion) + unit tests.
- `feat(index)`: emit `branch` / `rank` / `rankWord` / `medallion` / `contractVersion` from `taxonomy.py` into the Class-S projection.

#### 3 — "Ultimate" rank rename

The rank formerly labeled "Ultimate" is renamed throughout the schema (`meta.json` label), CLI formatters, and every rendering surface. `feat(formatting)`: branch-aware rank labels with a Unique-branch accent.

#### 4 — Evidence Floor removal → Trust Magnitude sole gate

The per-star Evidence Floor and the ≥10k-stars hard requirement are **retired**. Trust Magnitude is now the sole promotion gate (S ≥ 250 / A ≥ 100 / B ≥ 50 / C ≥ 20). Live grades across 249 named skills: S=4 / A=42 / B=56 / C=76 / ungraded=71.

#### Ascension Overdrive (AOV) — the frontend register

The website was rebuilt to render the new taxonomy: rank 4–6 hot-tier node treatments (4★ dwarf / 5★ sun / 6★ pulsar), branch-forked medallions and badges (Suite gold / Unique amethyst→ember ladder), the Hall of Heroes ceremonial manifesto + windowed locator rail, Unique cluster repositioned to the front of the world tree, and a full `--tier-*` → `--rank-*` design-token migration across every JS/CSS/HTML surface. Frontend JS was collapsed onto the emitted taxonomy so the site no longer re-derives branch client-side.

#### Also in this release

- **Docs & agent-prompt ratification** (#994, #1000): `META.md` §4.4 Unique Impossible gate, `CONTEXT.md` quartet scrub, `DESIGN.md` truth-up; retired-floor logic and fabricated taxonomy scrubbed from the curation/audit/fusion agent skills.
- **CI guards** (#999): Yggdrasil II banned-synonym check, meta-sync check, timeline-pairing guard, Taxonomy Authority Guard, Apex/Unique gate checks.
- **Security hardening** (`fix(sec)`): resolved CodeQL high-severity DOM-XSS/taint sinks across `docs/badges/`, `docs/codex.html`, `docs/en/cli-reference.html`, `docs/js/hoh-modal.js`; hardened the `</script>` close-tag regex in the pre-CodeQL guard scripts.
- **Meta-post**: [Yggdrasil II: Two Types, One Trust Gate, and a Branch Axis That Is Never Declared](https://gaiaskilltree.com/meta/reports/2026-07-26-yggdrasil-ii-two-types-one-trust-gate-and-a-branch-axis-that-is-never-declared.html) — every stat verified against the live registry.

### Breaking changes

- Starless `type` values `extra` / `ultimate` / `unique` are removed. Consumers reading these will find `basic` / `fusion`.
- Named-skill `branch` is no longer a stored field — derive it via `computeBranch()` / read the emitted `branch` in the Class-S projection.
- `evidenceFloors` removed from `meta.json`; promotion is gated on Trust Magnitude alone.
- `gaia dev reclassify` is deprecated (type auto-derives from prereq structure).

## [6.0.0] - 2026-07-06

### Sprint D EPIC #902 — Evidence, Benchmarks, and the Content Engine

This release closes Sprint D, the "flywheel orbit" epic. Four key capabilities land together:

- **KC1 — Weekly Content Engine.** `.github/workflows/weekly-content-engine.yml` runs every Monday at 08:00 UTC, generating a canonical JSON report + public HTML page for the ISO week. Draft-only by default; toggle `GAIA_CONTENT_ENGINE_PUBLISH=1` in the `content-engine-live` environment to publish. First live report: [2026-28](https://gaiaskilltree.com/reports/2026-28/).
- **KC2 — `gaia push --benchmark`.** New verb for submitting a claimed benchmark score as a pending evidence row. See [`docs/benchmarks/humaneval-v1/`](https://gaiaskilltree.com/benchmarks/humaneval-v1/).
- **KC3 — Public /benchmarks/ page + reports archive.** New site sections at `gaiaskilltree.com/benchmarks/` and `gaiaskilltree.com/reports/` with nav + footer + homepage entrypoints per CLAUDE.md §Design Entrypoints.
- **KC4 — HumanEval CI reproduction.** `.github/workflows/benchmark-humaneval-ci.yml` reproduces a claimed HumanEval score deterministically and promotes the pending row to `provenance: ci-reproduced` with the workflow-run URL as attestor.

### Also in this release

- `fix(ci)`: branch-scope guard survives all-bot commit windows (#967) — `git log | grep -v github-actions[bot]` under `set -euo pipefail` no longer silently kills the check on cron-generated branches.
- `fix(content-engine)`: weekly report publish step is now idempotent (`git push --force-with-lease` upsert + open-PR detection), so stale same-week branches don't crash the runner.
- `fix(tests)`: `tests/test_seo.py:65` regex updated from `gaia\.tiongson\.co` to `gaiaskilltree\.com` (missed in the June domain migration).
- Domain migration to `gaiaskilltree.com` fully consolidated; all CNAME, sitemap, robots, and test references aligned.

### Breaking changes

None at the CLI or API surface. The major bump marks the Sprint D closure milestone, not a contract break; existing tree JSONs, evidence rows, and benchmark row shapes are all backwards-compatible.

## 5.1.1 — 2026-06-23

### Fixed
- **CI packaging**: Updated `publish-pypi.yml` workflow to copy the `registry/named` directory directly from the workspace instead of `/tmp/gaia-snap/registry/named` (#810). This fixes wheel packaging issues where fresh snapshots weren't bundled correctly.

## 5.1.0 — 2026-06-23

**Epic #780 Close-out & Badge Redaction Safety**

### Added
- **Pre-flight calibration constraints**: Calibrating a named skill to 3★+ now validates that `links.github` is present and uses a `blob/` URL. Missing or `tree/`-only links are rejected before write (#789).
- **Percentile guard**: `gaia dev evidence --type benchmark-result` now requires `--percentile <0-100>` to avoid generating ungraded entries with a 0 trust magnitude score (#789).
- **Redaction backstop**: Shipped `_apply_redaction_backstop` in `scripts/build_docs.py` to automatically evict stale pre-named (≤1★) handle directories from `docs/badges/_assets/` during docs compilation. This fail-safe also validates the committed tree and fails CI on drift (#808).
- **Deprecation warnings**: Wired deprecation warnings to top-level shims (`gaia release`, `gaia validate`, `gaia test`, `gaia docs build`, `gaia mcp`) directing users to their `gaia dev` counterparts. (Removal slated for v7.0.0).

### Changed
- **Housekeeping**: Relocated `MISSION.md`, `NOTES.md`, and `RESOURCES.md` from the repository root to `docs/en/` (#809).
- **Badges regeneration**: Rebuilt `registry.json` and restored deleted handle/skill SVGs for active contributors (#806).

### Removed
- **`gaia dev evidence --class` flag**: Fully removed the deprecated `--class` flag in favor of `--trust <0-100>` (#790). Callers using `--class A|B|C` must migrate to `--trust` before upgrading.

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
