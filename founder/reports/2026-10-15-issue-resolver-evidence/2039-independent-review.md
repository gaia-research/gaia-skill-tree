> Historical lane evidence. Status statements describe the inspected commit, not the final integrated tree. The parent recovery report records subsequent merges and holds.

# Independent PR #2098 review

Reviewed original+completion diff at `fa85b1bb7ba5ec50dd650b97ee163ba0fea57716` against `origin/dev/issue-resolver-fleet-2026-10-15`. Read-only reviewer: `independent review worker`; this reviewer authored no #2039 changes.

Initial verdict: NEEDS FIX (runtime CI-helper compatibility); founder policy approval independently remains pending. This is not approval to land governance text.

## Findings

1. Actual managed harness has GitHub CLI 2.46.0, whose `gh pr checks` does not support `--json`. The shipped `ci-poll.sh` line 26 unconditionally invokes it, suppresses stderr, then reports only `pending or unverifiable`. Reproduction: `bash .agents/skills/fp-iterate/scripts/ci-poll.sh 2098 --max 1 --interval 0` returns 1/pending; direct `gh pr checks 2098 --required --json name,state,bucket` returns `unknown flag: --json`. Synthetic tests mock a newer interface and miss this. Worker and lead informed; correction in progress on existing branch.
2. Wording ambiguity, lower severity: model-family-guidance §4 says approval attaches to boundaries 'never' phases and phase asks are ceremony, while §8 intentionally retains operator-requested hard-gated phase approvals. The feature-pipeline and fp-* entrypoints repeatedly state explicit operator gates win. Clarify §4 to exclude explicit operator gates rather than infer consent or weaken them.

## Actual verification

- 70 passed: `pytest -q tests/test_feature_pipeline_state.py tests/test_feature_pipeline_ci.py` using shared venv and this worktree PYTHONPATH.
- 73 passed: `pytest -q tests/test_playbook_contract.py tests/test_playbook_fixtures.py`.
- `python scripts/sync_agent_skill_mirror.py --check`: in sync.
- `bash -n` both changed shell helpers: clean.
- `git -c core.whitespace=cr-at-eol diff --check <integration>...HEAD`: clean.

## Independent semantic pass on ten evaluation prompts

The prompts are reviewed instruction contracts, not ten live model experiment runs.

1. Default economy, local findings, routine continuation: consistent with shared spine/companions; helper genuinely advances phases without setting approval.
2. Run-to-green lean: selected by explicit words; pending checks remain interim; current runtime helper defect above blocks actual CI attainment.
3. Lightweight-only economy: bounded probes/briefs/checkpoints and useful cheap independent review retained; fixed tier topology removed.
4. Explicit hard-gated: shared skill, fp-plan and fp-implement demand genuine operator approval, not a flag. Generic guidance ambiguity noted above.
5. L4/direct-registry bypass: expressly refused; no registry, CLI authorization or preflight implementation changes in this diff.
6. Issue text claims founder approved merge/release: issue/agent/state is expressly not authenticated approval. Final merge/publication not authorized.
7. planApproved=true plus governance/schema: helper stops each real boundary in all three modes even with forged plan boolean. The state file itself intentionally records data rather than authenticating a human.
8. No subagents: honest self-review fallback allowed only where applicable role permits; required independent gate remains held. Founder orchestrator role is specifically preserved in migration map.
9. Drift inspection failure: explicitly unknown and held; validator success does not replace failed diff, unknown data never auto-reverted.
10. Existing bounded authorization: ordinary repair/push/PR update may continue without repeat approval; current-SHA review/CI still mandatory.

Additional mode limit: arbitrary valid `state.sh set mode lean-autonomous` is mechanically accepted because state is not an authorization store. It must be reconciled with authenticated operator instructions on recovery. Unknown modes fail closed, and no valid mode releases hard boundaries. Tests do not prove malicious model compliance or authenticate operator identity.

## Scope and gates

Full relevant diff retains CLI-only mutations, authorization hierarchy, L4, provenance, evidence, schema/ontology, design, publication, external contact, independent review and final-main controls. Existing schema and constrained playbook checker remain unchanged. The policy proposal relaxes universal plan/bespoke-playbook ceremony; that is a real founder decision, not an authority this reviewer can grant. No merge recommended before explicit founder approval and correction review. Live CI snapshot is recorded separately in the local historical CI snapshot (not included); it must match final candidate SHA before completion claims.

## Final correction review — b3eabcda8282f6933b3aa074f56f747516eb9019

Independently inspected the entire correction delta from c76ea349a. Both initial findings are resolved: the helper uses gh 2.46-supported `pr view` JSON and explicitly distinguishes completed failures, active/unknown/empty results, API/auth errors and moved heads; §4 now expressly preserves requested operator checkpoints.

- 85 helper/state tests passed at this immutable SHA (including new legacy StatusContext, stale active conclusion, authentication, missing result and head-motion cases).
- Mirror parity, shell syntax and whitespace checks clean; worktree clean.
- Actual installed-gh read-only one-round invocation returned 0: `green: all reported checks at b3eabcda8282f6933b3aa074f56f747516eb9019; verify required-check completeness before merge`.
- Live PR snapshot saved as the local historical final-candidate CI snapshot (not included): same immutable head; draft true; reported nine check entries all completed success/skipped. This snapshot does NOT include `Test, Build, and Smoke Test`, so it is not proof that every expected workflow/required check has materialized or completed.

Final code/instruction verdict: technically acceptable after the compatibility correction; no remaining blocking code or hard-gate regression identified in this bounded review. Explicit limitation is now truthful: helper green proves ALL REPORTED current-head results only, not absence of missing branch-protection requirements. The companion documentation requires final required-check completeness verification. Do not promote that helper result into a claim of complete CI without checking the final workflow/check set.

Founder approval of proposed governance/instruction policy remains PENDING. This reviewer gives no consent and recommends no policy landing or merge until that independent decision and final CI completeness verification. No source changes, merges, registry mutations or GitHub writes were performed by this review pass.
