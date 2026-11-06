# Automatic Origin — independent adversarial review

## Initial review: HOLD

- Target: preserved `dev/yggiv-origin-automation` WIP `80150fff8`.
- Governing issue: [#2267](https://github.com/gaia-research/gaia-skill-tree/issues/2267), EPIC #2189.
- Reviewer: separate Terra High agent session, run `69d9517b-f1c4-475a-bfde-7e6763a1bb4b`; did not implement the WIP. Independence is declared, not authenticated.
- Method/limitations: read-only source inspection; tools available to this reviewer did not permit Git or runtime probes. Findings below are inspection findings, not claimed executed reproductions. Exact-SHA runtime and Git-diff verification is still required.
- Authority: latest founder rulings in `CAMPAIGN.md` supersede old one-Origin/manual-transfer and unsupported star/prerequisite gates. Highest merit; genuine ties share Origin; frozen contenders compete with locked TM/grade; sibling cap unchanged.

## Findings requiring repair or explicit verification

| Severity | Finding | Source | Required proof |
|---|---|---|---|
| P0 | Named mutation verbs can still reach frozen writers without a shared guard. | `commands/dev/calibrate.py`, `evidence.py`, `named.py`, `sync_upstream.py`, timeline/rename paths | Relevant CLI writes reject/skip frozen target sets before any byte or timeline change; direct and suite-derived freeze covered. Scope repairs to launch behavior, not a new maintenance lane. |
| P1 | Origin comparison rounds TM to two decimals, falsely tying 50.001 and 50.004. | `src/gaia_cli/origin.py:52-54`, `tests/test_origin_rule.py:37-39` | Compare canonical precision; unequal close scores have one holder, genuine equality has every tied holder. |
| P1 | Missing frozen TM/grade cache falls back to live computation; suite freeze only warns about missing locks. | `frozen.py:84-97`, `origin.py:122-134`, `commands/dev/freeze.py:184-191` | Missing suite lock must fail closed before writes; nested suite and frozen contenders remain stable. |
| P1 | Normal docs generation rewrites approximately 200 canonical Origin fields unnecessarily. | `generateNamedIndex.py:794-819,966-975` | Remove production source-rewrite path; derived automatic projections; restore WIP-only source churn by ordinary commit, preserving history and frozen bytes. |
| P1 | Awakened holders can win Origin but disappear from ledger/leaderboard/API. | `generateNamedIndex.py:731-774`, `inspectTrustMagnitude.py:112-119`, `generateLeaderboardData.py:104-123` | Explicit coherent, appropriately redacted projection for awakened/1-star holders; no invented star floor or status/rank movement. |
| P1 | Meta sweep retains <=1-star Origin suppression and frozen mutation recommendations. | `run_meta_sweep.py:180-188,307-321,436-448`, `test_meta_sweep_champion.py:70-78` | Low-star holder retains derived Origin with display redaction; frozen records excluded from mutation recommendations. |
| P1 | Agent context still states invented Unique prerequisite-Origin and Suite4 gates. | `docs/agent.md:99-114` | Correct against founder ruling and META, without changing TM law or Apex predicates. |
| P1 scope | WIP changes Steward sensor behavior despite EPIC exclusion. | `src/gaia_cli/steward/sensors.py:1726-1800,1899-1902` | Remove WIP sensor delta; no new Steward engineering. |
| P2 | `dev add --extra-fields` can inject manual Origin. | `commands/dev/build.py:71-78` | Reject manual named Origin injection while retaining schema-required legacy initializer. |
| P2 | Generator/UI copy retains first-publication, singular-holder, approved-transfer meaning. | `generateProfilePages.py`, `docs/js/page-ia.js`, `docs/js/trust-lifecycle.js`, `docs/en/faq.html` | Correct current-status copy in source; never mass-edit frozen historical bodies. |
| P2 | Validator comments and public parity tests still encode one holder. | `validate.py:540-543`, `test_public_projection_parity.py:310-324`, `generateNamedIndex.py` module documentation | Shared-tie regressions and consistent terminology. |

## Confirmed direction (inspection only)

- Unique 5-star fusion-prerequisite Origin predicate removed in the WIP promotion helper.
- `update-named --origin` is refused.
- Ratification §IV has an explicit superseding note; WIP META/GOVERNANCE describe automatic selection and shared ties.
- Reviewer found no Origin-related change to the existing 50-TM sibling cap.

## Repaired-SHA Re-Review: SHIP (`016ae6005a6e6bddc7d6a78cb823efa99eddbe97`, PR #2271)

- **Target:** `dev/yggiv-origin-automation` @ `016ae6005a6e6bddc7d6a78cb823efa99eddbe97` (review verified at `087a7f42d1abf806a78a160f2a6925c758686336` + 1-line `tests/test_lifecycle.py` test fix `016ae6005`) ([PR #2271](https://github.com/gaia-research/gaia-skill-tree/pull/2271) → `dev/yggdrasil-iv`, base `5bccf831624ad7fc4c2fbd60557a4240d7ac8a45`).
- **Independent reviewer:** separate Flash High review subagent (`c43da4f5-ddd7-4c1b-af5a-fee34420edba`, session `01a19dee`), read-only profile.
- **Runtime & source proofs:**
  - `PYTHONPATH=src python3 -m pytest -q tests/test_origin_rule.py tests/test_origin_projection_contract.py tests/test_meta_sweep_champion.py tests/test_suiteref_guard.py tests/test_promotion.py tests/test_named_skills.py tests/test_api_projection.py tests/test_public_projection_parity.py tests/test_origin_wreath.py tests/test_trust_lifecycle_node.py tests/test_build_docs_api_projection_write.py` → **135 passed, 2 xfailed** (existing #2251 and #2259 xfails).
  - `python3 scripts/build_docs.py --check` → **Documentation is up to date.**
  - `python3 -m gaia_cli.main dev validate`, `--intake`, `--meta-sync` → **All validation checks passed; all 352 Trust Magnitude surfaces agree.**
  - `git diff --name-only origin/dev/yggdrasil-iv...087a7f42d -- registry/named registry/nodes` → **0 files changed** (all 400 canonical named-skill source files and all 9 frozen records byte-identical).
  - `git diff origin/dev/yggdrasil-iv...087a7f42d -- src/gaia_cli/steward/sensors.py` → **0 lines changed**.

| Severity | Finding | Repaired Status | Verification Evidence |
|---|---|---|---|
| P0 | Named mutation verbs can reach frozen writers without shared guard | **PASS** | `preflightNamedSkillMutable` (`helpers.py:758-781`) wired across `calibrate.py`, `evidence.py`, `named.py`, `rename.py`, `sync_upstream.py`, `timeline.py`; `freeze.py:120-155` preflights nested suite closure locks before any write. |
| P1 | Origin comparison rounds TM to two decimals | **PASS** | `origin.py:42-58` uses exact `(int(levelNumber), float(tm or 0.0))` without `round()`; `deriveBucketOrigins` returns all tied top contenders (`test_origin_rule.py:44-48`). |
| P1 | Missing frozen TM/grade cache falls back to live computation | **PASS** | `frozen.py:88-125`, `origin.py:151-183`, `freeze.py:134-155` fail closed when any frozen contender or suite member lacks a valid lock (`test_origin_projection_contract.py:129-164`). |
| P1 | Normal docs generation rewrites ~200 canonical Origin fields | **PASS** | Source-rewrite path removed (`043befcdb`); `generateNamedIndex.py:226-227` forbids `"origin"` frontmatter rewrites; 0 canonical named files changed in PR #2271. |
| P1 | Awakened holders can win Origin but disappear from ledger/leaderboard/API | **PASS** | `publicOriginStandings` (`origin.py:66-92`) projects redacted `originStandings` across `docs/graph/named/index.json`, `docs/graph/ledger/data.json`, `docs/api/v1/skills/index.json`, and `docs/api/v1/leaderboard.json` (`test_origin_projection_contract.py:24-78`). |
| P1 | Meta sweep retains <=1-star Origin suppression and frozen mutation recommendations | **PASS** | `run_meta_sweep.py:155-245, 320-336, 565` derives Origin at any star and filters frozen records out of mutation recommendations (`test_meta_sweep_champion.py:69-83`). |
| P1 | Agent context states invented Unique prerequisite-Origin and Suite4 gates | **PASS** | `docs/agent.md:99-125` updated to match ratified `META.md` and founder rulings (`test_origin_rule.py:208-216`). |
| P1 scope | WIP changes Steward sensor behavior despite EPIC exclusion | **PASS** | `src/gaia_cli/steward/sensors.py` restored to zero diff against `origin/dev/yggdrasil-iv`. |
| P2 | `dev add --extra-fields` can inject manual Origin | **PASS** | `helpers.py:1297-1302` and `build.py:76-78` reject manual `"origin"` injection (`test_origin_projection_contract.py:79-103`). |
| P2 | Generator/UI copy retains chronological/manual-transfer meaning | **PASS** | Updated across `generateProfilePages.py`, `docs/js/page-ia.js`, `docs/js/trust-lifecycle.js`, `docs/en/faq.html`, `docs/index.html`, `docs/trust/leaderboard/index.html`. |
| P2 | Validator comments and public parity tests encode one holder | **PASS** | `validate.py:653-656` and `test_public_projection_parity.py:317-334` updated for automatic Origin and shared ties. |
