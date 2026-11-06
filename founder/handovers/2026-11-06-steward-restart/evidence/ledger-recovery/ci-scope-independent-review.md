# Independent CI scope review

## Decision: ACCEPT

Candidate `c5de985cb18515ceb245fb91ebc3053b94c18ece` against base `d694986b865e158e21c613683021a9b7822f945c`. The base is an ancestor; checkout HEAD is the exact candidate. Reviewed the complete diff: only `.github/workflows/branch-scope.yml` and `tests/steward/test_landing.py` (46 insertions, 4 deletions). No blocking findings. Acceptance is of this bounded CI patch, not permission to dispatch, integrate, merge, push, or close debt.

## Findings and protection checks

- No actionable correctness or security findings in the reviewed change.
- `.github/workflows/branch-scope.yml:71`: the case and anchored regex recognize only `steward/b/unused-import-` followed by exactly 12 lowercase hex characters. Fork-origin B branches are downgraded to `other` (`:107`); the existing unrestricted-fork downgrade remains intact.
- `.github/workflows/branch-scope.yml:228`: B human-commit paths are restricted to `src/gaia_cli/`, `scripts/`, and `tests/`, with no generic markdown exemption. Mixed allowed/disallowed paths are rejected. This intentionally includes the bundled schema mirror under `src/gaia_cli/data/registry/schema/`; the separate reverse rule protects canonical `registry/schema/` and remains unchanged.
- Class A mirror classification and restrictions, reverse canonical-schema check, pull request events, permissions, job label guard, human/non-merge commit selection and GitHub Actions bot filtering are unchanged in the diff. Existing early exit for a branch with no human commits remains an inherited limitation, not a new B-specific protection. Required-check repository configuration and GitHub's actual enforcement were not inspected or changed.
- `tests/steward/test_landing.py:846-930`: tests extract and execute the workflow shell against disposable Git remotes; the B success assertion is reachable independently of the Class A assertion. Matrix includes allowed roots, mixed paths, forbidden source/package/registry/tree/founder/docs/workflow/skills surfaces, malformed and wrong B identifiers, fork downgrade, Class A and existing scope examples. Canonical reverse rule is exercised by the registry schema case. Tests do not establish every possible Git path or GitHub event scenario.

## Verification performed

- `git diff --check d694986b865e158e21c613683021a9b7822f945c c5de985cb18515ceb245fb91ebc3053b94c18ece`: exit 0. `git merge-base --is-ancestor` on those revisions: exit 0. Final `git status --short`: empty.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/steward/test_landing.py`: **93 passed** (131.01s).
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/steward/test_steward_workflow.py`: **3 passed** (2.43s).
- An initial incorrect runner invocation, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest -v tests.steward.test_steward_workflow`, returned exit 5: `Ran 0 tests in 0.000s` / `NO TESTS RAN`. It did not execute the pytest-style tests; the pytest invocation above is the actual workflow test result.
- Independently executed a Python temporary-fixture counterfactual: `git show <revision>:.github/workflows/branch-scope.yml` supplied each exact workflow; PyYAML extracted `jobs.scope-check.steps` / `Check branch scope` shell, substituting same-repository GitHub expressions. A temporary bare remote and separate work repo contained the actual `e39fb42c6^:src/gaia_cli/steward/issuehygiene/reconcile.py` as base and the actual `e39fb42c6` version as the branch commit; verified their only change was removal of `from pathlib import Path`. Ran the shell with `BRANCH=steward/b/unused-import-31cdbdb60a39`, `BASE_REF=main`, and fixture origin. Original `d694986b865e158e21c613683021a9b7822f945c`: **exit 1**, `Detected prefix: other`, `unrecognized branch prefix` for the real path. Candidate `c5de985cb18515ceb245fb91ebc3053b94c18ece`: **exit 0**, `Detected prefix: steward-b-unused-import`, all human commits in scope. Assertions checked both results. The only push was into the temporary local bare fixture, not the actual origin.

## Boundaries and limits

No tracked source edits, actual workflow dispatch, GitHub writes, shared-ledger writes, canonical steward run/scan/record/abandon, trust/rank/intake changes, integration, merge, push to a real remote, package installation, or global configuration changes. No subdelegation. Review and tests are local; no claim is made about live GitHub branch protection, required-check settings, or future integration state. The in-house Skill Heaven surface was not available in this harness; the required graft skill was used without installation.
