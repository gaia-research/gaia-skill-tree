# Founder/watcher corrective repair proof

## Status and scope

Corrective builder only; **fresh independent review is required** before integration. Base `6d3768096bd4cedfe577cb484ed5a72f87e97ba4`; final local commit `939d8ef4b4476535c558969b969238ead2762d61` on `dev/steward-founder-lock-2283`, authored/committed with approved Marcus identity. No push, integration or history rewrite. Final worktree clean. Runtime route supplied by CLI: direct `openai/gpt-6.1-terra`, high effort; no nested agent or fallback.

Changed only:
- `scripts/upstream_watcher/issuer.py`
- `scripts/upstream_watcher/tests/test_upstream_watcher.py`
- `tests/upstream_watcher/test_identity_2283.py`
- `src/gaia_cli/steward/issuehygiene/questions.py`
- `tests/steward/issuehygiene/test_founder_locks_2283.py`
- `founder/steward/decisions/README.md`

## Before and after

Before implementation, with new regression tests applied on base:

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/upstream_watcher/test_identity_2283.py -k same_run_shared_source tests/steward/issuehygiene/test_founder_locks_2283.py -k 'same_run_shared_source or final_lock_loss'
```

Result: **5 failed**. Both same-source different-skill fanout tests failed to raise (same version silently skipped; differing version reached fake update). Missing, renamed, and schema-valid open C3 records all failed to make the real sensor reconciliation unavailable. GH issue calls in these tests were mocked; no actual writes.

After repair, at exact final commit:

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/steward/issuehygiene tests/steward/test_founder_workflow_lock_2283.py tests/upstream_watcher scripts/upstream_watcher/tests/test_upstream_watcher.py
```

Result: **1343 passed in 344.28s**. `git diff --check` passed and `git status --short --branch` was clean. Earlier broad run had 1342 passed / 1 failed because a legacy test expected five different skills to silently collapse to one umbrella. That expectation contradicted the new identity boundary; it now tests five repetitions of the same identity, retaining its original duplicate-create protection. The new explicit conflicting-identity tests cover the rejected behavior.

## Safety behavior

Fanout preflights every non-bootstrap finding against the same normalized source key used for umbrella routing. Two distinct skill IDs sharing that key are refused before the initial snapshot and before any write, regardless of version; existing source-release validation still runs. Created/updated umbrella bodies are retained in the run cache and validated before every subsequent same-run skip or update. Initial snapshot payloads are also validated; an unexpectedly unavailable cache/snapshot identity refuses. Existing headless-payload recovery behavior is unchanged. Tests cover same/different version conflicts, zero fake writes, same-identity idempotency and cached conflicting payload validation, alongside existing source-release tests.

For decisions, the existing `founder/steward/FOUNDER_LOCK_2283.md` implementation boundary is the checkout-specific enablement context. Presence of that document **or any canonical expected decision record** requires all four exact finalized, schema-valid mapped decisions. Missing, renamed, open or malformed/mismapped entries refuse, including if all four disappear while the document remains. This is not a new authority or automatic decision: unrelated fresh repositories lacking both the document and those records continue ordinary reconciliation. Deliberate removal of both the boundary document and every canonical record is outside this detection mechanism and would require separate repository review.

Tests exercise missing/renamed/open C3 using a stale-label-free GBrain umbrella through the real sensor reconciliation, the standalone CLI reconciliation, and the executor's independent closure re-derivation; no manifest is emitted on CLI refusal. The closure gate is exercised with temporary synthetic checkout authority and data, not live authority or forge writes. Existing focused tests preserve independent C questions, C1 technical-only behavior, C2/C3/C4 holds, history and children. The saved 67-child/218-object replay described in the prior independent review was not re-run here; no claim of a fresh canonical replay or settlement is made.

## Residual gates / resume

- Independent Terra reviewer must review final SHA, run independent regressions and assess both enablement boundary and watcher cache/preflight design. Builder is not verifier.
- C1 AgentDB registry metadata/baseline reconciliation remains separately reviewed and gated; no registry, trust, evidence or ranking changes were made.
- Historical #2278 mismatch root cause remains unproven; runner-context read-only evidence remains required. No operational resolution is asserted.
- C2 migration and C3 founder curation remain deferred. No child, issue history or live labels changed.
- C4 compiled workflow synchronization, pause preservation, threat-engine and future non-Copilot activation remain separately authorized gates. No compilation, activation or credentials.
- `writesEnabled=false` and open closure authority remain untouched. No canonical scan/run/record/migrate/rollback, shared leases/actions, live GitHub writes, issue closures, release/deploy, installs or global configuration changes occurred.
