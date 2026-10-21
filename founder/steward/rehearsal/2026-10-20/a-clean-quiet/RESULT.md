# A - clean run is quiet: PASS after fix (first run PARTIAL; see re-run below)

Repo: `_clean_cli_repo` fixture (tests/steward/test_cli.py), bare remote with HEAD=main, `--ledger git`.

- PASS: `full run --ledger git --json` exit 0, status `completed`, phase `done`, `actions: []`, 38 observations, 0 open debt, 0 coverage unknown, `desk.decisions: []`. `full status` exit 0 (lease free, work none, 3 completed runs in the ledger incl. the scheduled one).
- FAIL (expectation): the desk is NOT quiet (`desk.quiet: false`). It lists 4 operations: 3x `not_evaluated` (ci-health, dependency-advisory, test-history: optional driver inputs absent) and `stale_schedule` ("no scheduled run has ever been recorded"). With `--trigger scheduled` the stale_schedule item clears, but the 3 not_evaluated remain, so a fresh repo with no driver inputs can never reach quiet.
- FAIL (expectation): the human form never prints `Gaia Steward: nothing needs you.`. `render_desk()` / `QUIET_LINE` (desk.py) are referenced only by tests/steward/test_desk.py; `commands/steward.py` prints its own summary (`Desk   0 decision(s), 4 operation(s)`, or `Desk   nothing needs you` when quiet, a different string). The gaia-steward-desk skill's input (`full status --json`) carries no desk at all; the desk is only in the `run` view.
- Side note: 3 runs wrote 60 commits to refs/heads/steward/ledger (one fast-forward per step), ledger.json 69 KB.
Files: run.json, run-human.txt, run-scheduled.json, status.json, status-human.txt, ledger-tree.txt, ledger.json.

## Re-run after the fix: PASS (`rerun-after-fix/`, steward head f40fb3ba6)

The two failures above were fixed in 482a3ba90. Same fixture, fresh bare remote, `--ledger git`:

- **Scheduled run** (`run --trigger scheduled`): exit 0, `completed`, `desk.quiet: true`. The human form prints exactly `Gaia Steward: nothing needs you.`
- **Absent driver inputs**: the three not-evaluated sensors are still reported, as `notEvaluated` entries with `inputAbsent: true`. They are never counted healthy, but they are no longer desk operations. A stale, foreign or future-dated input remains an operation.
- **Manual run on the same ledger**: exit 0, `quiet: true`, no operations. A scheduled run is now on record, so `stale_schedule` does not fire.
- **`status --json`**: carries `desk` (quiet) and `deskRunId`. Human `status` ends with the quiet line.

The human summary still shows `Class B blocked landing target not configured` as a phase line when no integration branch is configured. There was no Class B work, so the line is cosmetic: it does not reach the desk, and the run status is `completed`.
