# Steward issue hygiene — session state (paused for compact, 2026-10-21)

Governing issues: #2130 (reconciliation), #2131 (watcher fanout), #2132 (backlog burn-down).
Architecture contract: `2026-10-21-steward-issue-hygiene-architecture.md` (read first).
Lead: Sonnet 5.5 High. Builders/verifiers: Haiku 5.5, **effort xhigh from here on** (founder instruction mid-session; early lanes A/C/F ran medium, D1 high). Opus advisor: **not used** (1 pass still reserved; only for a genuine architecture blocker).

## Integration branch
`dev/steward-issue-hygiene` (remote, tip after this file). All lane branches below are merged into it by merge commit unless marked WIP.
Draft PR to `main`: opened in this session (see PR comment trail). Founder authorized the `skip-scope-check` label for it (founder/GIT.md).

| Lane | Branch | Status |
|---|---|---|
| A census/identity/collector | `-a` | merged |
| C watcher batching (+C2 list-based gate, C3 carry-forward/gate fix, C4 301/full-history/fail-closed fanout) | `-c`,`-c2`,`-c3`,`-c4` | merged |
| D1/D1b policy, sensor, runner `forge.close_issue`, routine 18, coverage, desk | `-d1`,`-d1b` | merged (1719 steward tests, coverage checker ok at D1b) |
| B reconcile/closure (+B2 ref-free A1, B3 simple-ref trust) | `-b`,`-b2`,`-b3` | merged (230 issuehygiene tests) |
| D2 skills/driver/docs wiring | `dev/steward-issue-hygiene-d2` | **WIP, paused, unverified** (commit 7aa6e2ea5: edits fullrun.py, closure.py, sensor.py, tests, new test_closure_proof.py; skills/scripts NOT yet written) |
| E adversarial tests | `dev/steward-issue-hygiene-e` | **WIP, paused** (692ff751c: only `tests/steward/issuehygiene/e_fakes.py`) |
| F cost skill | `gaia-research/skill-cost` PR #10, branch `feat/run-report` tip 830a548 | built, 85 tests; round-2 re-verification was stopped mid-run → **must be re-run** |

Latest verified combined run on integration tip: `tests/upstream_watcher + tests/test_upstream_approve_workflow.py + tests/steward/issuehygiene` = 374 passed.

## Lead rulings in force (do not re-litigate)
- Policy keys are flat: `issueHygiene.{enabledRules,maxClosuresPerRun(10, hard cap 25),maxCensusAgeSeconds,closedWindowDays,a5Disabled,writesEnabled}`; no `issue-closure` entry in `repairs.executors`; closure goes through pending action `forge.close_issue` (triage special-case).
- Routine 18 "GitHub Issue Hygiene" owns the sensor `issue-hygiene` (debt kinds `issue_closure_ready` A, `issue_suite_review` B, `issue_founder_decision` C).
- A1 matches owner/repo + path, ignoring git ref, only when both refs are simple (HEAD/main/master/semver tag/7-40 hex) or URLs identical; accepted residual: slash-branch with simple first segment (documented in the contract).
- Census age/fixture: pass `--now` for reproducible runs (fixture fetchedAt 2026-10-21T19:00Z).
- `skip-child-gate` and `upstream:approved` never imply acceptance/rejection/closure.
- #2126 (gh-aw Detection Runs tracker) and #2127 (Copilot billing failure) are **Class C**, one question: all `steward-build-*`/`steward-verify-*` gh-aw workflows are still `active` on GitHub (dispatchable), so the automation is not verifiably disabled.
- F3 amended: default = umbrella + lossless batch record (payloadVersion 2); per-candidate children only by `--escalate`; existing children are adopted. Approve gate and close-children use list pagination, 301/404/410 child = absent (row returns to unresolved), umbrella uses `Refs` not `Fixes` while unresolved rows exist; carry-forward from the full closed history.
- `closed` outcome in `record` must accept ONE of `commentUrl | commentId | markerVerified:true` (D2 to implement).
- `/cost` rulings: floats malformed, 10**15 bound, ambiguous id-only merge ⇒ incomplete, `usdComplete` key, run-report-only flags exit 2 without `--run-report`.

## Live backlog ground truth (2026-10-21 census, REST)
224 open issues + 8 PRs; 105 bot-authored (96 `upstream:child` = #1835:72 #2002:17 #2020:4 #1823:3; 6 umbrellas #1823 #1833 #1835 #2002 #2020 #2040; bootstrap #2091; gh-aw #2126 #2127).
Fixture reconcile (115 issues, `--now 2026-10-21T20:00:00Z`): children A=17 (A1: #1981 #1994 #1995 #2003-2007 #2009-2012 #2016-2018 #2022 #2024), B=78 (22 path-only plugin/ vs skills/ differences + 1 repo/path difference among them), C=1 (#1982 alias-suspect); umbrellas 4 C (#1823,#1835 skip-child-gate gate; #1833,#2002 title/payload suite mismatch) + 2 B (#2020,#2040); bots 2 C; #2091 none; 10 untracked. Six founder questions (Q-08ecd62d, Q-2568173e, Q-6720aecf, Q-67f85dde, Q-bfd37238, Q-d736d093). Sim of watcher on the four families: 0 creates, 96 suppressed, 96 retained.

## Routine facts
Scheduled routine = trigger `trig_01NLfT4PzgwkWh8utSzRRopE` "Gaia Steward Daily" (CRON_TZ=Asia/Manila 10:45 daily = 02:45Z), fresh checkout, invokes `/gaia-steward-full`, collects driver inputs in Phase 1, uses the authenticated Claude session (no API keys/Copilot). It reads the repo's default branch ⇒ **work must be merged to `main`** to count. Trigger prompt still says "30 sensors / 17 routines" (founder-owned text; leave, mention in report). `steward-full.yml` (gh-aw) is paused by founder; do not touch.

## Remaining plan (in order)
1. Resume/redo **D2** (fresh xhigh Haiku, start from `-d2` WIP): new atomic skill `gaia-steward-issue-hygiene` (+ `.claude/skills` mirror), update full/observe/triage/retro/land/lane/verify/desk skills and mirrors (1-18 routines, Step 0 census refresh, `forge.close_issue` row), `scripts/steward_issue_close.py`, `scripts/steward_drive.py` handler + census refresh, ordinary driver-input collection wiring, `record` closed-outcome proof relaxation, docs (`founder/steward/README.md`), checker mapping to the new skill. Validators: `quick_validate_skill.py`, `validate_skills.py`, `sync_agent_skill_mirror.py --check`, `check_steward_coverage.py --check`, `pytest tests/steward -k "not hardlink"`.
2. Resume **E** (from `-e` WIP): scenarios 1-15 in the E brief + the end-to-end test that drives the ordinary `/gaia-steward-full` entrypoint (`gaia steward full run`) on a fixture checkout: discovers issue hygiene, emits `forge.close_issue`, records via fake forge, resume, second run zero actions.
3. Independent verification (fresh Haiku xhigh, not authors): watcher lane, reconcile/closure lane, runner/skills lane; fix findings.
4. Re-run **skill-cost** re-verification (verifier a6c2292 was stopped), merge PR #10 into skill-cost `main` (merge commit), then final `/cost --run-report` with role map for the campaign.
5. Dry-run on the LIVE census (`python scripts/steward_issue_census.py` then `python scripts/steward_issue_reconcile.py --summary`), watcher dry-run against live GitHub (no recreation), then a limited live pilot (≤5 A1 closures, re-read live state each time, verify the C4 301-behavior assumption on a real transferred issue if one exists), replay for idempotency; expand in batches ≤10.
6. Merge integration PR to `main` (merge commit, never squash; label `skip-scope-check`; CI green; no rebase/force-push), then run `gaia steward full run` for real on main checkout twice (second = idempotent) and ideally observe the 02:45Z scheduled run.
7. Post completion status + proof links on #2130, #2131, #2132; founder packets for the 6 questions (+ B suite batches); final `/cost` receipt on the governing PR and linked from #2130.

## Spend log (user preference: log per push; canonical /cost, public-rate equivalents, NOT billed)
2026-10-21 interim (skill-cost 1.2.1 run report, window 18:59→19:56Z, session 3f42d4e9, 17 subagent logs): Sonnet 5.5 lead 152 in / 88,214 out / 15.47M cache-read / 308k cache-write ≈ $3.66; Haiku 5.5 subagents 2,132 in / 51,973 out / 217.7M cache-read / 4.18M cache-write ≈ $2.73; total ≈ $6.39 public-rate equivalent (subscription use, not an API charge). Opus advisor: not used. Interim = provisional (cost branch re-verification pending; role split builder/verifier not yet mapped).
