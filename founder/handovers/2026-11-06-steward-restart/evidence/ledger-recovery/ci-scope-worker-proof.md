# CI scope repair worker proof

- Branch: `infra/steward-classb-scope-2283`
- Commit: `a0b6a30c1` — `fix CI scope for canonical Class B unused-import branches`
- Scope: `.github/workflows/branch-scope.yml` recognizes only `steward/b/unused-import-<12 lowercase hex>` and grants `src/gaia_cli/**`, `scripts/**`, `tests/**`; malformed/unknown names fail closed. Fork-origin B classification is downgraded. Existing steward/a rules, unrestricted fork downgrade, reverse schema rule and workflow permissions/triggers are retained.
- Regression proof: `tests/steward/test_landing.py` extracts and executes the actual workflow Bash against disposable bare remotes/worktrees. Coverage includes B positives across each allowed area, mixed allowed/forbidden paths, protected paths, malformed/unknown branches, B fork denial, existing A mirror/source behavior, infra/docs/schema behavior, and unrestricted fork downgrade.
- Checks: `python -m pytest tests/steward/test_landing.py -k branch_scope -q` (15 passed); `python -m pytest tests/test_workflows.py -q` (3 passed); `git diff --check` (passed).
- Counterfactual limitation: Did not execute `reconcile.py` against an original-workflow swap or a real canonical reconcile fixture. The extracted original workflow's existing `steward/a/*`/default classification categorizes this B branch as `other`; the added disposable actual-shell regression demonstrates the corrected workflow passes B paths and rejects its boundaries. Therefore the requested real reconcile.py + canonical fixture before/after proof remains outstanding and is not claimed here.
- Not self-accepted. Fresh Terra review and actual CI/integration remain lead gates.
