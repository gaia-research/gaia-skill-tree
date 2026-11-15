# P0 Handoff — Bounded C2/C3 Decision & Consumer Amendment

**PR:** #2467 (<https://github.com/gaia-research/gaia-skill-tree/pull/2467>)
**Base branch:** `dev/upstream-backlog-2026-11`
**Feature branch:** `dev/upstream-backlog-authority-2026-11`
**Status:** NARROW REPORTING-ARTIFACT CORRECTION — READY FOR NARROW TERRA CHECK (P0 NOT COMPLETE)

## Implementation

1. **Decision records (`steward-decision-v1` schema preserved, no extra fields):**
   - `founder/steward/decisions/issue-question-q-bfd37238.json` (GBrain C3): updated `resolution` to `records-and-version-sync-only`, preserved the original baseline `9b4d9b98` decision text and evidence verbatim alongside `Previous resolution (#2283 baseline): curation-deferred` (see correction round 1 below; an earlier draft's ungrounded `2026-11-04` label was removed), and appended the verbatim 2026-11-15 card text (`Ruling 2, C. Lift for records and version-only sync`) and authority link `founder/reports/upstream-backlog-2026-11/CAMPAIGN.md`.
   - `founder/steward/decisions/issue-question-q-2568173e.json` (Addy C2): updated `resolution` to `records-and-version-sync-migration-deferred`, preserved the original baseline `9b4d9b98` decision text and evidence verbatim alongside `Previous resolution (#2283 baseline): migration-deferred` (see correction round 1 below; an earlier draft's ungrounded `2026-11-04` label was removed), and appended the verbatim 2026-11-15 card text (`Ruling 3, B. Records and version sync, migration still deferred`) and authority link `founder/reports/upstream-backlog-2026-11/CAMPAIGN.md`.
   - `founder/steward/decisions/README.md` and `founder/steward/FOUNDER_LOCK_2283.md`: appended the scoped consumer contract and November 15, 2026 amendment while preserving all historical #2283 content.

2. **Canonical Steward `issuehygiene` consumer (`questions.py` and `reconcile.py`):**
   - `src/gaia_cli/steward/issuehygiene/questions.py`:
     - Added `ALLOWED_RESOLUTIONS` and `AMENDED_RESOLUTIONS` so both the original #2283 full-hold resolutions (`migration-deferred`, `curation-deferred`) and the 2026-11-15 amended resolutions (`records-and-version-sync-migration-deferred`, `records-and-version-sync-only`) validate fail-closed. Amended resolutions additionally require `founder/reports/upstream-backlog-2026-11/CAMPAIGN.md` in `links`. Unknown, open, malformed, or unlinked records continue to raise `ValueError`.
     - Added `BASELINE_CHILDREN` enumerating the exact 67 `garrytan/*` children and 4 `addy-osmani/*` children (`#2008`, `#2013`, `#2014`, `#2015`) from `founder/reports/upstream-backlog-2026-11/PLAN.md`.
   - `src/gaia_cli/steward/issuehygiene/reconcile.py`:
     - Updated `applyFounderLocks` so a child under an amended C2/C3 resolution proceeds to `finalize()` **only** when it is a `child`, its `(issue_number, candidate_id)` matches `BASELINE_CHILDREN`, `draft.proofRule == RULE_A1` (exact registry/source match), `draft.unknowns` and `draft.questions` are empty, `draft.authority != AUTH_C`, and `upstream:needs-info` is absent.
     - All other family items—umbrellas (`#1835`, `#2002`), new/absent/unknown/unproven/source-mismatched children, alias-suspect candidates, breadth audit `#2276`, `skip-child-gate` on GBrain, Addy handle migration (`addyosmani/*`), unrelated descendants, and items under the old full-hold resolutions—remain held (`held`/`none` or Class C for unrelated/alias questions).
     - C1 (`q-08ecd62d`) and C4 (`q-6720aecf`) are unchanged. `issueHygiene.writesEnabled` remains `false`.

## Exact Files Changed

- `founder/steward/decisions/issue-question-q-2568173e.json`
- `founder/steward/decisions/issue-question-q-bfd37238.json`
- `founder/steward/decisions/README.md`
- `founder/steward/FOUNDER_LOCK_2283.md`
- `src/gaia_cli/steward/issuehygiene/questions.py`
- `src/gaia_cli/steward/issuehygiene/reconcile.py`
- `tests/steward/issuehygiene/test_founder_locks_2026_11.py`
- `founder/reports/upstream-backlog-2026-11/P0_HANDOFF.md`

## Validation Commands & Results

- `python3 -m pytest tests/steward/issuehygiene -q` → **932 passed in 235.08s** (includes all 923 existing `issuehygiene` tests + 9 regression tests in `tests/steward/issuehygiene/test_founder_locks_2026_11.py`).
- `python3 -m pytest tests/steward/test_founder_records.py tests/steward/test_desk.py -q` → **64 passed in 4.41s** (validates all repository decision records against `steward-decision-v1` schema and desk classification).
- `python3 scripts/check_steward_coverage.py --check` → **Steward coverage check: ok**.
- `git diff --check` → **clean (exit 0)**.

## Proof References

`tests/steward/issuehygiene/test_founder_locks_2026_11.py` verifies:
- `BASELINE_CHILDREN` matches the exact 67 GBrain and 4 Addy rows in `PLAN.md`, and both decision records preserve prior resolutions/history verbatim alongside the 2026-11-15 card text.
- Scoped baseline children (`#1925`, `#1984`, `#2008`, `#2015`) release to `A1-child-curated` (`authority: A`, `action: close`) only with exact matching registry/source proof; umbrellas (`#1835`, `#2002`) stay `held`/`none`.
- Source-mismatched baseline children (`#1925`, `#2014`) and `upstream:needs-info` baseline children (`#1926`) stay `held`/`none` (no approval by registry presence alone).
- New GBrain candidates (`#2500` even if present in registry), absent candidates (`#2501`), breadth audit (`#2276`), unknown-URL children (`#2502`), and `skip-child-gate` on `#1835` remain `held`/`none`.
- Addy handle migration (`addy-osmani/*` vs `addyosmani/*` alias on `#2008` -> Class C; non-baseline `addyosmani/new-skill` `#2510` -> `held`/`none`) and unrelated questions (`#9999` -> Class C) remain held/unanswered.
- Old full-hold resolutions (`curation-deferred`, `migration-deferred`) retain full holds on baseline children; C1 (`#1833` -> `B`) and C4 (`#2126`, `#2127` -> `held`/`none`) are unchanged.
- Amended resolutions fail closed without `CAMPAIGN.md` in `links`, and `founder/steward/POLICY.yaml` retains `issueHygiene.writesEnabled: false`.

## Limitations & Outstanding Decisions

- This P0 amendment closes/comments on nothing and performs no registry or workflow mutation.
- `issueHygiene.writesEnabled` remains `false`; enabling Steward closure writes still requires the independent verification gate from `steward-issue-closure-authority.json`.
- Version-only synchronization of already-tracked records still requires fresh human `upstream:approved` on refreshed umbrellas (P2/P4).

## P0 Correction Round 1 (Addressing Terra Review Findings on `6674c826`)

1. **CRITICAL `reconcile.py:964` — Independent normalized provenance & fail-closed membership:**
   - **Before:** `applyFounderLocks` matched family membership using only `suiteRepo(draft.suite)` (parent-derived for children), so a new GBrain candidate (`#2500 garrytan/brand-new` with `garrytan/gbrain` evidence URL and matching registry record) reparented under `#2600 garrytan/gstack` resolved to `resolved A A1-child-curated close`.
   - **Correction:** Added `_normRepo` and expanded `applyFounderLocks` to check normalized provenance across `suiteRepo(draft.suite)`, `draft.identity.evidenceRepo`, `draft.exact.upstreamRepo`, `draft.exact.github.repo`, and `BASELINE_CHILDREN[qid]` membership, without broadly holding unrelated proven `garrytan/gstack` work.
   - **After (reproducer):** `#2500` -> `held none None keep`; `#2601` (proven `garrytan/gstack`) -> `resolved A A1-child-curated close`; reparented baseline `#1925` with exact `garrytan/gbrain` A1 proof -> `resolved A A1-child-curated close`; missing-URL `#1926` -> `held none`.
2. **WARNING `reconcile.py:1015` — C1 `#1833` generic `upstream:needs-info` hold:**
   - **Before:** C1 `technical-reconciliation-only` set `forcedC = True` and `authority = AUTH_B`, causing `finalize()` to return before checking `upstream:needs-info`; `#1833` carrying `upstream:needs-info` remained `actionable B`.
   - **Correction:** `applyFounderLocks` now honors `upstream:needs-info` on `technical-reconciliation-only` (`state = held`, `authority = none`, `notProven += "upstream-needs-info-hold"`) while retaining `actionable B` when `upstream:needs-info` is absent. C1 (`q-08ecd62d`) and C4 (`q-6720aecf`) decision records remain byte-identical to baseline `9b4d9b98`.
   - **After (reproducer):** `#1833` with `upstream:needs-info` -> `held none ['founder-lock:q-08ecd62d:technical-reconciliation-only', 'upstream-needs-info-hold']`; without `upstream:needs-info` -> `actionable B`.
3. **WARNING C2/C3 decision JSON historical text restoration:**
   - **Before:** `issue-question-q-2568173e.json` line 12 rewrote `'user-tree unlockedSkills and timeline history'` as `'user-tree unlocked IDs and immutable timeline history'`, both C2/C3 rewrote `whyItMatters`/`recommended`/`alternative`/`unblocks`, and both included an ungrounded `2026-11-04` date.
   - **Correction:** Restored all original baseline `9b4d9b98` text verbatim in `issue-question-q-2568173e.json` and `issue-question-q-bfd37238.json`, removed the invented `2026-11-04` date (`Previous resolution (#2283 baseline): ...`), and appended the dated `2026-11-15` amendment inside the existing `steward-decision-v1` schema.

## P4 Prerequisite (Recorded Observation — NOT Implemented in P0)

- **Terra observation (`upstream-approve.yml:469`):** `upstream-approve.yml:469` honors authorized `skip-child-gate` with no GBrain-specific prohibition; otherwise open children gate sync. Fresh human `upstream:approved` alone does not guarantee GBrain version-only sync when held children remain open.
- **Required before P4:** Independently establish a canonical allowed version-only route that retains held children and prohibits GBrain `skip-child-gate` bypass. This P0 patch does **not** modify workflows or implement that route.

## Next Action

Final narrow independent Terra check of PR #2467 reporting-artifact correction (`dev/upstream-backlog-authority-2026-11` -> `dev/upstream-backlog-2026-11`), verifying the `BASELINE_UPSTREAM_METADATA.json` (`counts.frozen: 24`, per-record `frozen` flags, `entriesDigestSha256`), `CAMPAIGN.md`, `P0_HANDOFF.md`, and `COSTS.md` changes. Do not start P1 before P0 has passed its independent gate and been merged under campaign authority.

## Baseline Snapshots (Initial P0 Evidence)

- `founder/reports/upstream-backlog-2026-11/BASELINE_UPSTREAM_RECORDS.json`: extracted from the saved canonical `scripts/steward_issue_census.py` output (`steward-github-census-v1`, `fetchedAt: 2026-11-15T17:23:35Z`, 249 open + 325 recentlyClosed, first closed baseline seeded at 728 because no prior baseline was retrievable). Selects the exact **81** `PLAN.md` issues (6 umbrellas, 3 bootstraps, 72 appendix children): **81 found** (all `open` in `issues`), **0 missing**. Initial P0 evidence only — **NOT** a P2 watcher census, and grants **no** closure proof.
- `founder/reports/upstream-backlog-2026-11/BASELINE_UPSTREAM_METADATA.json`: extracted from `registry/named/**/*.md` at approved `main` `9b4d9b98043140188f00b14d0ac8fa6bc02491b7`: **472** named files, **17** with `upstream` block, **0** frozen *(superseded: raw frontmatter flag check; canonical `gaia_cli.frozen.frozenIds` count is **24**, `entriesDigestSha256: 997c80e0b5d8df626817e43f26fbbb94ac3d1b854c3f93f5e1ac07185e75e324`)*, **15** `installable: true`, **30** `installable: false`, **427** `installable` unset, **445** with `links.github`.

## Independent Terra receipt on builder commit `6674c8268703f6137f8e4c8067e0be7ca73bd378` (First Review — Superseded by `11405f2dacaa2f6501039dbce3936106e0fb9bee`)

**Verdict: FINDINGS.** This was an independent review/verification in the separate detached checkout. Terra independently ran and passed 930 `issuehygiene` tests and 64 founder-record/desk tests, plus the Steward coverage checker and `git diff --check`. The findings were:

- **Critical — reparented/new GBrain hold escape:** family membership derived from parent suite alone could allow a new candidate reparented beneath a different GBrain family to escape the intended hold. *(Fixed in `11405f2dacaa2f6501039dbce3936106e0fb9bee`.)*
- **Warning — C1 needs-info bypass:** the C1 technical-reconciliation path could become actionable before honoring the generic `upstream:needs-info` hold. *(Fixed in `11405f2dacaa2f6501039dbce3936106e0fb9bee`.)*
- **Warning — Addy historical text rewrite:** decision-record wording changed existing historical text rather than preserving the prior ruling verbatim. *(Fixed in `11405f2dacaa2f6501039dbce3936106e0fb9bee`.)*
- **Conditional P4 dependency:** a permitted version-only route needs resolution in the approval workflow; this observation was not a P0 source-change request. *(Recorded prerequisite; not implemented in P0.)*

These are summarized findings, not a transcript or raw review prompt.

## Independent Terra receipt on builder commit `11405f2dacaa2f6501039dbce3936106e0fb9bee` (Second Review)

**Verdict: FINDINGS (solely stale doc date in `P0_HANDOFF.md` lines 11–12).** Terra independently reverified the code and decision records at `11405f2dacaa2f6501039dbce3936106e0fb9bee` in a separate detached checkout:

- **Prior findings resolved:** all 3 prior code/record findings (reparented/new GBrain hold escape, C1 `upstream:needs-info` bypass, Addy historical text restoration) are fixed.
- **Tests and checks:** 932 `issuehygiene` tests PASS, 64 founder-record/desk tests PASS, `scripts/check_steward_coverage.py --check` PASS, `git diff --check` PASS.
- **Independent synthetic probe:** 71 synthetic baseline children using actual registry URLs yielded `A1` proposals (explicitly **not** live closure proof).
- **Unchanged boundaries:** C1 (`q-08ecd62d`), C4 (`q-6720aecf`), and `founder/steward/POLICY.yaml` (`issueHygiene.writesEnabled: false`) remain unchanged.
- **P4 prerequisite:** `upstream-approve.yml:469` version-only workflow gap remains a recorded prerequisite, not permission to apply GBrain `skip-child-gate`. No code, workflow, or decision records were modified in doc-only correction 2.
- **Sole remaining finding:** `P0_HANDOFF.md` initial summary lines 11–12 still carried the contradictory `previous resolution (2026-11-04)` wording; corrected in doc-only correction 2. **Final Terra doc-only review is PENDING; P0 is not PASS/complete and P1 is not started.**

## Independent Terra receipt on `4778b2a04de62f60df48f7a0a7df5c9aa943da22` and Narrow Reporting-Artifact Correction

**Verdict on `4778b2a`: FINDINGS (solely `frozen` count/flags in `BASELINE_UPSTREAM_METADATA.json` and `0 frozen` prose).** Terra independently verified in the detached review worktree:
- **Verified clean:** doc-only delta (no code/test/decision/POLICY/workflow/registry changes), 81 `BASELINE_UPSTREAM_RECORDS.json` IDs match `PLAN.md` and canonical census with valid digests, all 472 `BASELINE_UPSTREAM_METADATA.json` Git paths/blobs/source fields match baseline `9b4d9b98`, historical date fix is correct, and cost privacy is clean.
- **Sole finding:** `BASELINE_UPSTREAM_METADATA.json` line 9 reported `0` frozen and all 472 entries `frozen: false` (inferred from absence of a frontmatter `frozen` flag, contradicting canonical `gaia_cli.frozen.frozenIds`), plus unqualified `0 frozen` in `CAMPAIGN.md` line 119 and `P0_HANDOFF.md` line 85.

**Diagnostic & narrow correction status:**
- **Routine limit:** the two routine correction rounds are exhausted; no code, policy, authority, workflow, or registry repair or scope expansion was performed. Reviewed code at `11405f2` remains untouched.
- **Canonical recalculation:** applied `gaia_cli.frozen.frozenIds` (`src/gaia_cli/frozen.py`, including suite inheritance) to the 472 `registry/named/**/*.md` records parsed directly from baseline `9b4d9b98043140188f00b14d0ac8fa6bc02491b7` Git objects.
- **Result:** **24** canonical frozen skills (all 24 self-frozen via `timeline:upstream_deprecated` with `installable: false`, including `garrytan/investigate` and `mattpocock/personal` whose 2 `suiteComponents` — `mattpocock/edit-article`, `mattpocock/obsidian-vault` — are also self-frozen; active capstones `mattpocock/productivity` and `mattpocock/skills` remain unfrozen).
- **Updated artifacts:** `BASELINE_UPSTREAM_METADATA.json` (`counts.frozen: 24`, per-record `frozen` flags, `frozenDefinition: "gaia_cli.frozen.frozenIds (src/gaia_cli/frozen.py)"`, `entriesDigestSha256: 997c80e0b5d8df626817e43f26fbbb94ac3d1b854c3f93f5e1ac07185e75e324`), `CAMPAIGN.md`, `P0_HANDOFF.md`, and `COSTS.md`. `BASELINE_UPSTREAM_RECORDS.json` (81 issues) is untouched.
- **Gate:** **Final PASS still pending; P0 not complete; P1 not started.**
