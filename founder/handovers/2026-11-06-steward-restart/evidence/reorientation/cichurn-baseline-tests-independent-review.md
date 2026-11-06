# Independent review: CI churn baseline tests

## Status
ACCEPT — exact head `11de8c847c2f836a6cf5d36a673fbfdef5d58317`, against `f1839ff22c3ca056fa2125dc0120a2cf635e75ff`. This accepts the test-only prerequisite, not canonical debt closure or a production change.

## Findings
- No actionable defects found in the assigned test-only change.
- The single added file `tests/test_ci_churn.py` imports and exercises the actual script: 14 collected cases include five classification/precedence cases, JSONL parsing, synthetic commit/run API parsing, mocked subprocess success/error, nonempty churn/failure accounting and report output, empty churn/hint deduplication, and four duration cases. Assertions check concrete expected results; there are no accidental unused global replacements or tautological assertions. The parametrization marker expands cases, not skips.
- The exercised `_gh` subprocess seam is mocked, as is `_gh` for API parsing. Tests do not call `main` or `detect_repo`; no live GH, git, installs, downloads or network calls are made by these test paths. Fixture values are synthetic and the session file is under `tmp_path`. The added test file introduces no skip, timeout, thread, conftest or configuration weakening. Existing `tests/conftest.py` blocks process replacement and adds an isolation fixture only to integration-marked cases; it does not skip these tests.
- Exact parent is the stated base; the committed diff contains only the new test file. `git diff --check f1839ff22 HEAD` passes. HEAD, base and worktree `scripts/ci_churn.py` all bind to Git blob `56f075d2073c8ee7c1b6714e51e2e34e4f21ffe1`, preserving `os`, `timezone`, and all other source bytes. No runtime/workflow/guard/config files changed in the diff. Tracked worktree was clean; pre-existing untracked `.pi/tasks/` was observed.

## Verification Limits
- Fresh independent command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_ci_churn.py -q -p no:cacheprovider` → **14 passed**, 0.26s on Python 3.14.6. Two warnings report existing pytest `timeout`/`timeout_method` config options unknown because plugin autoload was disabled. No test skipped. Separate import probe confirmed `ci.__file__` resolves to this worktree's `scripts/ci_churn.py` and independently computed its Git blob hash above.
- Baseline, not exhaustive coverage: no CLI orchestration, real GitHub/git/network integration, malformed non-object JSONL, or every report combination. Tests characterize current accounting and do not establish its normative correctness. Full suite not run.
- Reviewer runtime environment reported `openai/gpt-6.1-terra`, reasoning `high`; no nested delegation or fallback was used. Graft skeleton was consulted and refreshed its ignored graph. No source edits, real authority/ledger/lane operations, push or merge were performed. Future canonical two-import cleanup requires its own genuine packet, capabilities and fresh authority.
