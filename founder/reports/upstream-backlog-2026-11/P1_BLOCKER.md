# P1 blocker — founder direction required

**State:** HARD STOP. P1 is blocked and incomplete. No more engineering until a bounded founder-authorized contract reconciliation resolves the conflict between whole-record schema validation and canonical legacy-record/writer behavior.

## Verified checkpoint

- Dedicated worktree: `/data/data/com.termux/files/home/.gaia-worktrees/upstream-backlog-2026-11-p1`
- Branch: `dev/upstream-backlog-watcher-2026-11`
- Exact source reviewed: `60120a1ec7b24a31e7e9e0a5d75c337963993442`; clean before this bookkeeping-only change.
- Integration base for PR #2468: `dev/upstream-backlog-2026-11`.
- Independent Terra FINAL verdict: **FINDINGS, not PASS**. Two routine correction rounds exhausted.
- Actual checks: 1015 pytest passed; parity exit 0 with both equality checks true; diff check passed. Empty-name/root-crossfield/active `.gaia/registry` schema/missing-invalid schema/invalid Git refs/valid encoded `#` and `/` isolated tests confirmed.
- No real-runner dispatch; P1 incomplete; P2–P7 not started.

## Exact schema diagnosis

Baseline `9b4d9b98043140188f00b14d0ac8fa6bc02491b7` and integration contained 10 AgentDB raw-schema errors: permitted `trustMagnitudeInputHash`; `apexGateStatus` `crossOrgVerifier` + `systemWideCap` (one error); five `migrate_trust_magnitude` events; one `recalibrate_trust_magnitude`; and two `github-actions[bot]` contributors. P1 `da255f0` appended an additional `note` timeline event at `registry/named/ruvnet/agentdb.md:148`; `src/gaia_cli/commands/dev/named.py:175` emits that event. Therefore current count is 11, not all pre-existing. `P1_HANDOFF.md` historical lines 94/151 are explicitly superseded. `scripts/validate.py:535` validates named records; `scripts/check_trust_magnitude_consistency.py:83` documents drift and checks selected fields/evidence/timeline shape, not full raw-schema normalization. The actual AgentDB named check passed; raw-schema errors remain.

## Blocking finding

`src/gaia_cli/commands/dev/sync_upstream.py:457` whole raw-schema validation blocks safe sync: actual AgentDB dry-run (record hash unchanged) is blocked, as is the read-only scan of all 23 watcher-in-scope suites with invalid raw schemas. Ordinary future approval-route sync is therefore blocked. No actual runner was dispatched.

`gaia dev validate` is not a clean overall pass: `scripts/validate.py` passed 11/11, but the command exited 1 because generated `registry/named-skills.json` is absent for redaction/timeline/TM consistency checks. Regeneration remains deferred until P7/canonical gates; this is not a new regression.

## Prohibited before founder decision

Do not choose/codify normalization, exemption, or validation policy; alter CLI/schema/writer/validator, trust input hash/cache, evidence, trust schema/history, ranks, Origin, frozen records, or timelines; start another repair round; regenerate; dispatch runner; advance phases; create issues/comments/PRs or mutate labels/variables. Preserve exact source state; do not reset/discard.

Next gate, only after founder direction: bounded contract reconciliation, then independent Terra review and real-runner `apply=false` requiring exit 0 and empty `unknownEvidence`. PR #2468 remains existing draft, blocked and unmerged.

Campaign-complete usage/cost unavailable. `$4.907920` is a prior P0-only partial checkpoint; original interrupted/resumed run inclusion unverified and actual billing unknown. Current bookkeeping excluded.
