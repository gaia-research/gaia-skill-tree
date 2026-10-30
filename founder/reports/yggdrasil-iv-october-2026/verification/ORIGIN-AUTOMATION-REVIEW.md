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

## Status

**Not approved, not integrated, no PR opened.** A separate implementation session is repairing/reproducing the findings. Require an independent repaired-SHA re-review, real tests, source/frozen-byte checks and clean applicable CI before integration. This record does not claim the initial WIP or any subsequent repair passed.
