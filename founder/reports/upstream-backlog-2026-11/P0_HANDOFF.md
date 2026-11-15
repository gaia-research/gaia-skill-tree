# P0 Handoff — Bounded C2/C3 Decision & Consumer Amendment

**PR:** #2467 (<https://github.com/gaia-research/gaia-skill-tree/pull/2467>)
**Base branch:** `dev/upstream-backlog-2026-11`
**Feature branch:** `dev/upstream-backlog-authority-2026-11`
**Status:** READY FOR REVIEW

## Implementation

1. **Decision records (`steward-decision-v1` schema preserved, no extra fields):**
   - `founder/steward/decisions/issue-question-q-bfd37238.json` (GBrain C3): updated `resolution` to `records-and-version-sync-only`, preserved the original decision text, evidence, and `previous resolution (2026-11-04): curation-deferred` verbatim in `evidence`, and appended the verbatim 2026-11-15 card text (`Ruling 2, C. Lift for records and version-only sync`) and authority link `founder/reports/upstream-backlog-2026-11/CAMPAIGN.md`.
   - `founder/steward/decisions/issue-question-q-2568173e.json` (Addy C2): updated `resolution` to `records-and-version-sync-migration-deferred`, preserved the original decision text, evidence, and `previous resolution (2026-11-04): migration-deferred` verbatim in `evidence`, and appended the verbatim 2026-11-15 card text (`Ruling 3, B. Records and version sync, migration still deferred`) and authority link `founder/reports/upstream-backlog-2026-11/CAMPAIGN.md`.
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

- `python3 -m pytest tests/steward/issuehygiene -q` → **930 passed in 218.16s** (includes all 923 existing `issuehygiene` tests + 7 new regression tests in `tests/steward/issuehygiene/test_founder_locks_2026_11.py`).
- `python3 -m pytest tests/steward/test_founder_records.py tests/steward/test_desk.py -q` → **64 passed in 4.37s** (validates all repository decision records against `steward-decision-v1` schema and desk classification).
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

## Next Action

Independent Terra review of PR #2467 (`dev/upstream-backlog-authority-2026-11` -> `dev/upstream-backlog-2026-11`), followed by P1 watcher/CLI repairs once P0 is merged.
