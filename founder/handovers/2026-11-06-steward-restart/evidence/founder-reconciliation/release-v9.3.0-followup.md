# Queued low-priority /gaia-release — existing v9.3.0 / PR #2281

Authority: explicit user request in this session. Priority LOW; execute AFTER current Lane B campaign/lanes. Do not interrupt live workers, overwrite their source, change the active campaign lease or create another release. User explicitly restricts PyPI to a later publication ASSESSMENT, no automatic publication.

Read `.agents/skills/gaia-release/SKILL.md` at execution time (loaded when queued). This is a **verification-only subset** of the skill: its bump/sync, tag creation, release promotion/edit and publishing examples are NOT authorized by this request.

## Required verification

1. Inspect actual PR #2281 merged SHA and Routine 19 spec/introduced commands and intended package assets; don't invent command names from an old checkout.
2. Verify existing remote tag `v9.3.0`, exact peeled commit, existing GitHub release identity/channel/draft/prerelease flags and associated tag/release/build CI at exact SHA. Report queued/failed/missing evidence honestly. Do not move/recreate tags or promote/edit release channels.
3. Mandatory ancestry evidence: verify PR #2281's merge is included in v9.3.0 as appropriate and tag commit is ancestor of actual current `origin/main`. Fetch read-only into isolated ref/object store if necessary to avoid overwriting current lane tags/refs. A failure means report BLOCKED, not create a replacement release.
4. Verify lockstep at TAG, not merely local dirty/current checkout: `pyproject.toml`, `packages/cli-npm/package.json` and generated/internal registry version where available. Use existing verify_lockstep tooling in isolated tagged checkout, record missing generated data without confusing it with a released artifact. No `gaia dev release --sync`, version edits or bump commands.
5. Confirm actual packaged CLI artifact includes Routine 19 implementation, registered commands and required runtime data/resources; compare installed package metadata/version/provenance with tag. Do not claim source checkout import proves installed wheel contains it.
6. Perform a truly CLEAN installation of the existing release artifact/tag into a fresh isolated environment. Do not overwrite globally installed Gaia or alter active campaign dependencies. Clear PYTHONPATH/source path contamination; show installed executable/import locations, distribution version and commands actually resolved from the isolated environment. Prefer existing GitHub release/build artifact for package proof; if only locally built tag wheel is possible, explicitly distinguish artifact-build assurance from public distribution availability. Respect Gaia's existing channels and platform constraints; no unauthorized install scripts/global package changes.
7. Basic Steward/Routine 19 smoke tests: help/command discovery, safe read-only status/observation on disposable checkout/fixtures, ordinary non-write behavior. No actual PR merge/closure, canonical live campaign advance, workflow activation, shared-ledger migration or security/curation decisions as a smoke test. Do not bypass existing issue-write switches or GitHub protections. If write-path behavior is needed, mock/disposable tests only.
8. Record exact commands/outputs, tag/PR/release/CI IDs+SHAs, clean-install paths, package inventory and limitations in current campaign handoff; concise #2283 receipt as authorized. Distinguish verified release from unverified public distribution.

## PyPI / release boundaries

Queue a LATER publication assessment (existing distribution availability, policy/channel/prerequisite review) only. Do NOT run publish-pypi.yml, workflow_dispatch, upload/twine, release-create/edit, git-tag/push, version bump/sync, channel promotion or deployment. No duplicate release just because distribution verification fails. User's Done: existing release verified to evidence available, remaining distribution work documented, zero duplicate releases.

## Scheduling and agents

Current four lanes and their independent reviews/integration take precedence. Shared-write Routine 19 follow-up is separately queued; this release audit targets EXISTING PR #2281 and v9.3.0, not an excuse to cut a release for new follow-up work. Use explicit `*-shared` agents on openai-codex, no imposed task timeout/turn cap or Antigravity fallback, at most four concurrent children. Don't call a launch or shell exit 0 verification success; inspect actual model terminal/error and command outcomes.
