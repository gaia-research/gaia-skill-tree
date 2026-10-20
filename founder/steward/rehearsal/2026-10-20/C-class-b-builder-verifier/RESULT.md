# Scenario C: real Class B builder plus independent verifier

**Result: PASS on attempt 3.** Attempts 1 and 2 were rejected mechanically. Both rejections were
correct behaviour, and each one exposed a contract defect, which was fixed on dev before the next attempt.

| | |
|---|---|
| Setup | Bare sandbox remote. The default branch is `main`; the integration branch is `dev/rehearsal`. Drift was seeded by adding the phantom `"ghostverb"` to `PUBLIC_COMMANDS` (advertised-but-absent). `dev/rehearsal` was fast-forwarded to the seeded commit so the builder can reproduce the drift from `base`. |
| Debt | `debt:cli_contract_drift:cli-command-surface:323275f4a7505ed3` (Class B, rule `cli-contract-drift`) |
| Targeting | `--debt`. With no target, the lane picked a higher-priority `trust_calibration_drift` debt. That was not dispatched: the founder brief forbids calibration until the effective-evidence context is verified. |
| Builder | Fresh Haiku agent, thinking effort medium, given only the packet path. It worked in its own clone. |
| Verifier | Fresh Sonnet agent, thinking effort high. It was given only the verifier prompt and a pristine base checkout, and never saw the builder's reasoning. |
| Lead | The orchestrator merged the builder branch into `dev/rehearsal` with a merge commit and recorded `lead.integrate`. |

## Attempt 1: rejected, proof shape (steward head 70ca86e96)
- **What happened:** The builder produced the correct one-line diff. Its proof file was free-form JSON, because the packet never stated the transcript schema. Mechanical verification rejected it: `proof transcript must declare schemaVersion steward-proof-transcript-v1`.
- **Effect:** The attempt was counted, the work went to `blocked`, and the lane returned it to `queued` under the 3600 s cooldown.
- **Fix:** 8ec3267d7 adds a hand-off section to every build prompt, giving the branch and base, the diff and transcript paths, and the transcript shape.

## Attempt 2: rejected, proof contract (steward head dca7dba16)
Rejected with two reasons:
- `proof contract items with no evidence: 4, 6`. Item 6 is "obtain independent review before integration", which no builder can evidence; the verify step *is* that review. Item 4 is a statement, not a command.
- `exited non-zero` on the reproduction command. A reproduced failure exits 1.

**Fix:** 842ac7d54 makes the evaluator treat only the independent-review item as process-owned. A machine verdict still never accepts. The hand-off and the `gaia-steward-lane` skill now say how to evidence a reproduction (`! cmd`) and a statement.

## Attempt 3: landed and resolved (steward head 842ac7d54)
1. `run --debt … --integration-branch dev/rehearsal` emitted exactly one `agent.build` (attempt 1, allowedModels haiku/sonnet, effortRequired). Exit 0, awaiting-action.
2. `record build:…:1` (exit 0), then `run --resume`. Mechanical verification returned `pending`, and the run emitted exactly one `agent.verify`, with allowedModels `sonnet` and the builder id in forbiddenAgentIds.
3. Negative probes against `record verify` were both refused with exit 2:
   - the builder's id, case-shifted and with a zero-width space inserted, refused as `verification must be independent`;
   - model `haiku`, refused as `not permitted`.
4. `record verify` with an accept verdict (exit 0), then resume. Exactly one `lead.integrate` was emitted.
5. The lead merged `steward/b/cli-contract-drift-65e3ce0b5b00` into `dev/rehearsal` (0ebb32dba) and recorded `integrate` (exit 0). Work moved to `landed` and the lane entry to `closed`.
6. A fresh run on the integrated tree:
   - the debt is `resolved` (`condition_recovered`);
   - the work went `landed → resolved`;
   - the full history is `queued → building → verified → landed → resolved`.

Remote `main` was never written by Steward. Both assignments are in `ledger-final.json`, each with role, agentId, model and effort.
