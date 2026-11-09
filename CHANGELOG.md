# Changelog

All notable changes to GAIA are documented in this file. Versions follow semver (MAJOR.MINOR.PATCH); the three manifests (`pyproject.toml`, `packages/cli-npm/package.json`, `registry/gaia.json`) move in lockstep.

## [9.4.0] - 2026-11-09

### Performance — Steward Batched Dispatch Scan Reuse (#2316)

Eliminates redundant repository-wide scans during batched Class B Steward maintenance repairs (`gaia steward full run`).

- **Targeted Scan Reuse**: During batched Class B dispatch, `render_dispatch` and `render_dispatch_prompt` now safely reuse the run's existing fresh `ScanResult` across compatible repair packets when git HEAD is unchanged, the working tree is clean, local inputs are identical, and the scan is within the 300-second freshness window. Drops 8 of 9 scans (~89% execution time reduction from ~27 min to ~3 min per 8-build batch).
- **Fail-Closed Freshness Guarantees**: Fresh repository scans are strictly preserved whenever git HEAD moves, the working tree is modified (tracked or untracked), local state or driver inputs change, or time-sensitive inputs cross freshness boundaries. Outside a git repository, scan reuse is refused.
- **Batched Packet Recovery**: Multi-packet lost prompt recovery reuses the active scan across unroutable and routable packets alike, eliminating repeated scans on interrupted runs.
- **Independent Verification & Receipts**: Each packet retains its individual immutable routing receipt referencing the run's scan receipt, preserving complete auditability.

### Other Improvements (since v9.0.0)

- **Security & Integrity**: Strengthened defensive checks and governance links (#2422), fail-closed scope gates with exact immutable SHAs (#2334), and verified runner baselines (#2428).
- **Topology & Intakes**: Ratified topology batches for #2274 and #2275 (#2435), canonical node listing without generated graph (#2302), and strict frozen Trust Magnitude index validation (#2430).
- **Steward Full Delivery**: Merged full-campaign closeout delivery for #2283 with independent verification, closed-issue baselines, and bound Class B route authorities (#2427).

## [9.0.0] - 2026-11-03

### Yggdrasil IV — EPIC #2189 — challenge-driven, reversible trust governance

**This is a breaking meta shift.** Ratified 2026-10-25 (`founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md`). Who may question a skill's standing, and how a skill recovers, are rebuilt. **No Trust Magnitude weight, cap, threshold, grade boundary or Fusion Score rule changes.** Releases 7.0.1 to 8.29.1 are recorded on GitHub Releases, not in this file. The fact-checked announcement is the Meta Report "Yggdrasil IV: A Challenge Must Be Earned, and Standing Can Recover" (`docs/meta/reports/2026-10-31-yggdrasil-iv-a-challenge-must-be-earned-and-standing-can-recover.html`).

#### What breaks

- **Origin is derived, never assigned.** The highest-merit named implementation in each generic bucket holds Origin, computed at build time (`src/gaia_cli/origin.py`). `gaia dev update-named --origin` refuses manual assignment, and the frontmatter `origin` field is historical attribution only. Ties share Origin; a 1★ skill can hold it.
- **One displayed level on every surface.** The Trust Grade ceiling (S 6★, A 4★, B 3★, C 2★, ungraded 1★) now applies on the trust ledger and the leaderboard, as it already did on the named index and the skills API. Stored levels are never edited; the ledger keeps `storedStars` beside `currentStars`. Consumers that read the old unclamped ledger stars will see lower numbers for skills above their grade.

#### What is new

- **Evidence-lifecycle schema.** Five evidence-lifecycle schema families are adopted, kept byte-identical across `registry/schema/`, `docs/schema/` and `src/gaia_cli/data/registry/schema/` (#2176). Evidence now counts once per type per source; this corrects how an existing rule was applied and is not a new rule.
- **Challenge lifecycle.** A challenge must be tested, independently re-checked and admitted before it can affect a rating; elapsed time, a broken link or a newer competitor is a reason to look, never a penalty. Four real challenges ran in October and none was admitted. Public record: the Trust Challenges page, `docs/trust/challenges/`.
- **Frozen skills keep their stars.** `gaia_cli.frozen.frozenIds` is the one definition of a frozen skill. A frozen skill keeps its locked Trust Magnitude and grade, competes for Origin, and is exempt from the grade ceiling: `clampLevelToGrade` and `publishedLevelNumber` take `frozen=True` (founder ruling 2026-11-03). `tests/test_frozen_skills.py` guards every frozen skill against un-freezing, recalibration or evidence changes after its freeze.
- **Registry.** 75 named skills added since ratification and 12 new generic skills plus one rename (`grill-me` to `interview-me`). 784 records: 311 generic and 473 named (426 named, 47 awakened). 237 Origin families.
- **Report tooling.** `scripts/add_post.py` supports `{{include: file}}` (confined to the source directory) and `{{fig: name}}` directives for interactive report figures.

#### Corrections

- `leonxlnx/output-skill`: the evidence row removed at its freeze is restored and its score is back at 50 (B). Hand-edited under an explicit founder waiver because no `gaia dev` verb can write a frozen record (#2277).
- `mattpocock/personal`: its owner tree is reconciled to the stored 3★ with `scripts/trace_timeline.py`.

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
