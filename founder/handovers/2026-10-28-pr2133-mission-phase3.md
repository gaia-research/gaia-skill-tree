# PR #2133 — mission phase 3 engineering receipt

This is an engineering receipt, **not** founder ratification, rollout approval, a live closure receipt, or permission to merge. Work is on `work/steward-legacy-2133`; the parent retains publication and independent-verification responsibility for the existing draft PR #2133. No replacement feature PR is needed.

## Integration and coherent units

- Started from PR #2133 `7facad74`; merged main `fc0e6f8d9` non-destructively as `6b0d2f9a0`. Main's full-abandon and browser-render implementation remains, together with routine 18. Conflicts were resolved in coverage, liveness, sensors and their CLI/coverage tests; coverage validates with 18 routines and 32 registered sensors.
- `636d6dab8`: public closure executors require a checkout, current policy/proof, fresh complete census, confined receipt path and reserved budget; authority remains OPEN. Complete comment transport, multipart readback/resume and final issue/history rechecks prevent the original bypass/preservation/race defects.
- `947076316`: independent review follow-up. A decided rejection is not approval: the authority record must have both `status: "decided"` and exact `resolution: "approved"`. The desk accepts an optional non-empty resolution without changing old records. Final foreign history is compared with the initial complete history, so an intervening objection **before** the newly posted marker also blocks closure.
- `64b2dcfd4`: CLI/manual defaults and the daily schedule remain fanout. Staged batch writes and hardened approve/reject/close-children jobs require explicit rollout opt-in. Main's legacy event-job step bodies are retained verbatim and regression-hashed. Staged child listing verifies pagination, terminal probes and an independent open count. Skip-label and rejection guards prove upstream ownership before writes. Rejection explicitly dispatches a cascade because `GITHUB_TOKEN` closure events do not trigger another workflow; the target rechecks current closed/rejected ownership.
- Luna commits `d47ee9ffdef38a74ca459e27ec69cd2648d4c79b` and `6e0e89a8130022c87ef53e71e7c859e76a1ef56a` cherry-picked cleanly as `7ca234c07` and `b2be77915`: legacy child source identity and full-finding coverage (adds/removes/liveness/name drift), including escalation and fixture corrections.
- `90f06ff57`: the batch registry-failure test explicitly selects batch rather than asserting an unauthorized default switch.
- `f1dead01a`: only the staged jobs receive explicit checkout read permission; legitimate staged bootstrap rejection remains supported. Legacy job bodies and permissions remain unchanged.
- `bd2eb2ebc` / `87e19fb54`: successful receipts truthfully record the final readback verification (`markerVerified: true`), not just the earlier POST URL. The old URL-only expectation was updated.
- `9d3c28303`: the merged fleet test asserts 32 unique sensors, including exactly one browser-render and one issue-hygiene sensor. Record resets require explicit batch selection rather than being silently ignored by the restored fanout default.

- Luna follow-up `ddc762a000ec9af47cc8171db41e0545a3ee51b8` cherry-picked cleanly as `1743f2d7c`: arbitrary slash-ref prefixes are no longer stripped, and `www.github.com` canonicalizes to `github.com`. The ref-ignoring comparison uses the same simple-ref trust policy as Steward's `registryindex.refSplitTrusted` (HEAD/main/master, semver-like tags and commit-like hashes), not a live GitHub ref lookup.

Final broad gate evidence is recorded below. The focused and broad scopes overlap; their counts must not be summed as distinct tests.

## Verification already completed

All local forge interactions below are mocked. Test commands clear `GH_TOKEN` and `GITHUB_TOKEN` and set `PYTHONPATH=src`.

- Original closure checkpoint: **97 passed**.
- Independent-review failing-first probes: **4 failed, 1 passed** before repair (missing/rejected decisions and an objection before the new marker reproduced the defects).
- Follow-up closure safety, adversarial, executor, identity, script, policy-doc and desk tests: **159 passed** (`mission-terra-after.log`).
- Complete mocked workflow/rollout/dispatch fault suite: **183 passed** (`mission-workflow-final2.log`).
- Explicit batch registry-failure plus rollout contracts: **8 passed**.
- Receipt verification plus mission/adversarial safety: **39 passed**, after a failing-first fresh-receipt assertion.
- Sensor fleet, reset behavior and rollout contracts: **20 passed**.
- Upstream CLI verbs, Steward CLI and browser-render sensor tests: **73 passed** (`mission-cli-render.log`).
- Fresh full issue-hygiene plus CLI, browser-render, driver closure, founder desk, routine coverage, full sensor fleet and upstream verb integration: **1,023 passed** (`mission-closure-final.log`). This includes the repaired receipt assertion.
- Final complete mocked watcher, approval/workflow, rollout and dispatch suites after all three Luna commits: **733 passed** (`mission-watcher-final.log`).
- Fresh remaining Steward suite (everything under `tests/steward` outside issue-hygiene): **1,621 passed** (`mission-steward-rest.log`), including full-abandon, controller, desk, driver, coverage and sensor compatibility. The component gates are green; local Python is 3.14/Termux, not the publication PR's Ubuntu CI environment.
- Coverage, skill mirror, both Steward skill quick validators and playbook contract: pass.
- Skill inventory validation: **81 skills, 0 errors**, with **64 existing orphan-asset warnings**; not represented as a warning-free run.
- Python compile checks, browser collector JavaScript syntax, workflow YAML and embedded Bash syntax: pass. Legacy workflow step objects independently compare equal to merged main.

Logs named here are session-local under `$TMPDIR`, not public evidence or committed artifacts. The interrupted older broad run is not a passing result. A later combined run was deliberately interrupted after **3,027 passes and four failures**; it had collected two expectations before concurrent repairs and exposed the remaining fleet/reset contracts fixed above. A closure integration run completed **891 passes and one failure**, the old URL-only receipt expectation corrected in `87e19fb54`. Neither run is represented as green; fresh final gate results follow below.

### Exact final component commands

```bash
env -u GH_TOKEN -u GITHUB_TOKEN PYTHONPATH=src python -m pytest \
  tests/steward/issuehygiene tests/steward/test_cli.py \
  tests/steward/test_sensors_render.py tests/steward/test_steward_drive_close.py \
  tests/steward/test_desk.py tests/steward/test_routine_coverage.py \
  tests/steward/test_sensors.py tests/test_dev_upstream_verbs.py -n 4 -q

env -u GH_TOKEN -u GITHUB_TOKEN PYTHONPATH=src python -m pytest \
  tests/steward --ignore=tests/steward/issuehygiene -n 4 -q

env -u GH_TOKEN -u GITHUB_TOKEN PYTHONPATH=src python -m pytest \
  tests/upstream_watcher tests/test_upstream_approve_workflow.py \
  scripts/upstream_watcher/tests -n 4 -q
```

Engineering is complete with the feature disabled, ready for the parent's independent verification and publication on existing PR #2133. PR Ubuntu CI, the source founder merge, the separate founder decisions below, and any later authorized release sequence remain gates—not claims of work performed here.

## Explicit remaining founder decisions

All five records are OPEN and visible to the founder desk:

1. `steward-issue-closure-authority`: whether to ratify proposed Class A A1–A5 issue-write authority. The real record has resolution `pending`; raw `writesEnabled` remains false, effective writes are false and effective enabled rules are empty. A switch edit alone cannot activate execution.
2. `steward-issue-1981-incident`: disposition of the historical accidental closure. This mission neither repairs nor ratifies that live event.
3. `steward-upstream-batch-rollout`: whether to amend F3 and enable the new batch/event behavior. No repository variable was changed here. With the new `STEWARD_ISSUE_HYGIENE_V2` variable unset, legacy jobs remain active; scheduled runs stay `0 6 * * *`, fanout, with existing concurrency.
4. `steward-closed-umbrella-disposition`: whether a matching closed finding is processed without an explicit accepted/rejected/receipt disposition. The founder's canonical open-suite amendment evidence is retained; it is not treated as a ruling on this separate question.
5. `steward-census-empty-page-crosschecks`: independent proof of empty closed histories and related completeness limitations. Persistent-empty acceptance and conservative full-page terminal refusal are not claimed solved.

These decisions are not pending coding tasks. Engineering completion does not authorize their resolution, source merge, rollout, or a live closure dry run/pilot.

## Boundaries and honest limitations

- No push, PR creation, remote issue/branch mutation, closure pilot/dry run, source merge or release was performed. No #2230 integration or #2139 lifecycle edit is included. Release remains held until the required source founder merge and later authorized release sequence.
- Existing legacy jobs deliberately retain main's bootstrap/actor/interpolation and token-event limitations. Staged-path tests do not claim to repair the active fallback, or to prove live GitHub Actions permissions, event delivery or concurrency behavior.
- REST rechecks are conservative, not an atomic server-side transaction with comment creation and issue close. No live operational result is inferred from mocked safety tests.
- Reference normalization follows the existing Steward simple-ref trust envelope. It refuses arbitrary prefixes such as `release/feature`, but does not query GitHub to disambiguate a slash ref beginning with an otherwise trusted prefix (for example `main/feature`). That broader shared-policy limitation is explicitly disclosed, not claimed fixed by the watcher follow-up.
- No registry nodes, generated site assets, founder ledger lifecycle rows or unrelated worktrees were edited by the mission repair commits. Tool task output under `.pi/tasks/` is excluded.
- Scope audit: 170 feature-PR files versus merged main; 515 files versus the old feature head (including main's authorized registry/site/release updates); 66 files in the repair range after `6b0d2f9a0`. Both starting heads remain ancestors. The repair range is whitespace-clean. Whole-PR `diff --check` versus main retains two original feature-file EOF-blank warnings (`batch.py`, `test_e_watcher_adversarial.py`); neither was introduced by the mission repairs. Browser collector and browser-render sensor source remain identical to merged main.
- Graft was used before source exploration; the observed context calls reported at least **71,107 tokens saved** (not a claim of complete session-wide instrumentation).
