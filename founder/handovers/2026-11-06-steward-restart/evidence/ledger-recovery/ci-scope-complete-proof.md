# CI branch-scope follow-up proof

## Counterfactual

Executed `.proof-tmp/proof.py` using disposable git remotes and the exact branch `steward/b/unused-import-31cdbdb60a39` with the changed path `src/gaia_cli/steward/issuehygiene/reconcile.py`. Original workflow was extracted from `d694986b865e158e21c613683021a9b7822f945c:.github/workflows/branch-scope.yml`; current candidate was extracted from the working tree. Workflow shell was executed, not inferred from source. Fixture represented correction `e39fb42c6a7b54dde55a5c12c3eb19f2f2fccba9` (removing unused `Path` import).

Command: `PYTHONPATH=src python .proof-tmp/proof.py`

Original: exit 1; `Detected prefix: other`; error: `src/gaia_cli/steward/issuehygiene/reconcile.py (unrecognized branch prefix ...)`.

Candidate: exit 0; `Detected prefix: steward-b-unused-import`; final output: `✓ All human commits are within scope for branch prefix 'steward-b-unused-import'.`

## Regression tests and verification

Corrected successful-prefix assertions to independently verify Class A and Class B classifications. Matrix includes successful `src/gaia_cli/`, `scripts/`, and `tests/` paths; out-of-scope paths including registry schema/named/nodes, skill-trees, founder, docs, `.github/workflows`, `.agents/.claude` skills, packages and source outside `src/gaia_cli`; mixed allowed/forbidden changes; unknown, short, long, uppercase, and non-hex Class B names. Existing Class A, fork Class B denial, and unrestricted fork downgrade cases retained.

- `pytest -q tests/steward/test_landing.py` — 93 passed.
- `python -m unittest tests.test_workflows` — 3 passed.
- No CI, integration, or debt-closure claim; fresh independent Terra review remains pending.
