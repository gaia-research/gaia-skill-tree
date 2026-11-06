# CI churn offline baseline test proof

- Scope: infrastructure/test prerequisite only; **not canonical debt closure** or source acceptance.
- Worktree: `$HOME/.gaia-worktrees/steward-cichurn-tests-2283`; branch `dev/steward-cichurn-tests-2283`.
- Starting HEAD: `f1839ff22c3ca056fa2125dc0120a2cf635e75ff`.
- Test-only commit: `11de8c847c2f836a6cf5d36a673fbfdef5d58317`; sole committed path `tests/test_ci_churn.py` (138 lines). Tracked worktree clean after commit.
- Source blob at HEAD and in worktree: `56f075d2073c8ee7c1b6714e51e2e34e4f21ffe1`; script unchanged, including existing imports.
- Runtime: Python 3.14.6; provider/model `openai/gpt-6.1-terra`, reasoning `medium`.
- Actual imported module path: `$HOME/.gaia-worktrees/steward-cichurn-tests-2283/scripts/ci_churn.py`.
- Actual command: `python -m pytest tests/test_ci_churn.py -q` → **14 passed in 0.90s**, exit 0. `git diff --cached --check` passed before commit.
- Scope exercised: commit classification including precedence, JSONL session parsing, synthetic PR/run response parsing, mocked gh subprocess success/error, churn and failure accounting, duration formatting, text rendering and hint deduplication. Subprocess/GH seams used in tests are mocked; no live API or git mutation is invoked by tests.
- Limits: focused baseline, not exhaustive branch or line coverage; main CLI orchestration, real gh/git/network integration, malformed non-object JSONL, and every report combination are not tested. Assertions reflect current behavior, not an endorsement of every accounting assumption. No production fix, package install, push, PR, merge, or real ledger/lane/census/record operation performed.
