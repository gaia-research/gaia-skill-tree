# Preparing a fresh environment

## Fetch source, don't reconstruct patches

Clone `gaia-research/gaia-skill-tree` and fetch `handoff/steward-campaign-restart-2283`, `dev/steward-campaign-2026-11-05`, `main`, and the exact branches in BRANCHES.json. Fetch explicit refs if the clone is shallow. Verify the listed commit IDs and clean tracked trees before work. Create separate worktrees for builders and independent verifiers. Never use a fresh local default `main` as though it were the current remote main.

The campaign branch contains the third resolved repair and the final one-field metadata correction. The handoff branch adds documentation/evidence/templates only. Do NOT merge the entire evidence package into main merely to deliver CI-churn; select the appropriate campaign/promotion source and preserve normal merge history.

## Tools / authentication

Original host was Termux, Python3.14.6, Git2.56, gh2.93, Pi1.4.0. A new host need not reproduce Termux. Use the repo's declared Python/dependency environment, `git`, authenticated `gh`, and the checkout CLI:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m gaia_cli.main steward full status --ledger git --json
```

Do not install or mutate global configuration silently. No credentials, OAuth stores, provider endpoints/issuers, sessions or authenticated global files are bundled. Arrange authentication independently through the owner's approved mechanism. Git origin is the ordinary repository remote; the real canonical ledger is its dedicated remote Git ref, not a bundled local snapshot. `--ledger git` fails closed; do not replace it with `local` to appear healthy.

Preserve pytest's existing60-second/thread/plugin/barrier/join safeguards. Agent500turn/24h limits are separate from these tests and from bounded Git/network safeguards. Do not raise or disable test limits to get green.

If the demonstrated HTTP2 framing error recurs, command/subprocess-scoped `git -c http.version=HTTP/1.1 ...` or equivalent inherited `GIT_CONFIG_COUNT` entries are the accepted recovery. No global HTTP setting, ledger rewrite or attempt reset.

## Model routing — templates, not an installation

Latest new Steward lanes: shared `openai-codex`. Non-Steward engineering: DSFlash. Luna first, deliberate Terra/Sol/Astra escalation only when needed. Existing launched jobs are not rerouted. Operator directives can change this again.

`environment/historical-local-agent-templates/` preserves this session's local edits for audit; several intentionally pin the OLD non-shared OpenAI route. Do not activate all of them as current defaults. A current shared example is `current-shared-luna-template.md`. Verify actual provider/model/effort from real child assistant envelopes, not UI placeholders or only PI_PROVIDER. No extra paid routing-probe campaign is needed.

Installed pi-subagent0.8.0 had a concrete pin bug: task-level `fallback_models: []` was treated as absent, and fallback-list length could create attempts despite retries0. The documented agent-level literalempty `fallback_models: []` plus max_retries0 resolved to one managed attempt under that version. Do not assume newer/different harness semantics: read installed docs and use a tiny offline resolver check if needed. Never silently substitute providers, especially after an access refusal. A provider access refusal stops that task; use official access/qualified review, not rephrasing/rerouting.

## Restore only necessary data

The packaged canonical packet/diff/proof/reviews are historical evidence for a FINISHED run, not instructions to record them again. Do not blindly restore `.gaia/steward` into a new environment. Refresh actual issue/PR/CI inputs via existing collectors when needed. Raw ledger snapshots were deliberately excluded. Handoff-local/background task IDs do not control anything on another host.

Evidence originals remain on the old host under `.gaia/steward/campaigns/2026-11-05`. Public copies have hashes and redaction disclosure. Their scope is not full provider billing or whole-source approval. `.pi/delegate`, `.pi/tasks` and raw JSONL were deliberately not uploaded because they can contain private prompts/transcripts/auth material. No product/source WIP is hidden there in the scoped worktree inventory; committed branch-only work is preserved via BRANCHES.json.
