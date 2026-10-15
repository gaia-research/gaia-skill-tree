> Historical lane evidence. Status statements describe the inspected commit, not the final integrated tree. The parent recovery report records subsequent merges and holds.

# PR #2089 independent adversarial review

Verdict: REQUEST CHANGES. Do not merge into `dev/emilkowalski-intake-2026-10-13` pending repair and explicit founder approval.

Reviewed immutable head `32ecd0df7c0683167e2d9dfacf6ecbb4481cb453` against base `f00b3606b355a5c86de6d08190995dbd9ac8aab5`. Inspected all 11 files in the complete triple-dot diff, including original `f1dccf786b591ace040f3863e5ab5132c76ba992`, not merely follow-up `32ecd0df7`. Detached worktree `<review checkout at 32ecd0df7>` stayed clean. No branch changes, live curation, evidence ingestion, or registry changes were made.

## Confirmed blocker: agent-forged L4 authorization admits outside-top-K mappings

Original commit `f1dccf786` added `intakeAdapter.py:178-197` and the equivalent mirrored packet-validator exception at `.agents/skills/gaia-curate/scripts/validate_discovery_packet.py:276-304`. `git blame -L 175,198 HEAD -- src/gaia_cli/intakeAdapter.py` attributes the entire authorization exception to that original commit. At the base, absent-from-shortlist mappings unconditionally errored. Follow-up `32ecd0df7` does not change this exception.

An agent with packet-file control can select another current generic absent from `mappingOptions`, set `l4Resolution.status=approved`, `humanReview.humanOverride=true`, `decision.reasonCode=L4_RATIFIED_MAP`, and invent all human-review strings. `reviewedBy`, `approvalRef`, `reviewedAt`, rationale and attestation are checked for non-empty shape at `intakeAdapter.py:235-259`, with no authenticated actor or approval-event lookup. A nonexistent `assessmentPath` bypasses receipt verification at `intakeAdapter.py:279-315`; its digest can be any 64 hex characters. Even an existing, agent-fabricated two-field receipt passes if its digest matches.

The independently constructed synthetic packet uses a trusted two-generic catalog, a shortlist containing only `retrieved-skill`, an outside target `outside-skill`, `reviewedBy=forged-human`, `approvalRef=attacker-invented-reference`, `reviewedAt=invented-time`, nonexistent assessment file, and a fabricated digest. It returns no errors from both `validateL4Resolution(..., requireHumanReview=True, trustedGenerics=...)` and the standalone packet validator. `_load_yaml_file` accepts it, then `build_from_file_batch` emits the outside target with zero errors. No invocation of `ratifyCommand` or operator authorization is needed. The CLI operator guard still exists in `commands/dev/__init__.py:1123-1133`; direct packet submission bypasses that seam.

Impact is falsely presenting a machine-selected outside-shortlist mapping as post-L4 intake. This does not prove automatic registry promotion or bypass final maintainer merge. The older local-attestation weakness is documented in CURATION-CORE.md, but this PR newly expands it to outside-top-K targets and fails the explicitly required anti-forgery boundary.

Repair must bind outside-shortlist approval to an independently trusted human actor/event and the exact packet revision/target, or fail closed when such approval cannot be verified. Requiring only a locally present receipt or another editable boolean cannot establish human approval.

## #2055 compatibility risk (pre-existing acceptance, not an original regression)

`intakeAdapter.py:151-154`, `commands/dev/ratify.py:75-77`, and `commands/pushFromFile.py:171-175` accept mixed-case contributors. An independently crafted `Hikari9` contributor passes adapter, loader, and batch builder and remains `Hikari9` in output. The case-insensitive duplicate comparison at `intakeAdapter.py:443-450` protects collisions but does not enforce lowercase input. Merge the corrected lowercase-only #2093 contract before reconciling #2089, and resolve shared ratify/adapter/push code deliberately. The approved identity remains `hikari9/auto-office`. Do not silently normalize input.

## Verified protections

Independent probes confirm rejection of duplicate named identity across different generics, case-variant duplicate named identity, conflicting shared-generic definition, duplicate candidate ID, unaccepted generic duplicated across batches, explicit stale retrieval, manual-vector retrieval, stale catalog, and missing human review. Distinct named implementations sharing an identical generic are accepted. The existing required-operator dispatch is still present; it authenticates operator capability, not an L4 human approval event.

## Execution evidence

New synthetic test implementation: `./review2089_adversarial.py` (standard-library unittest, not imported implementer test factories). All synthetic data lives in temporary directories and is deleted. Exact command:

```bash
cd <review checkout at 32ecd0df7>
PYTHONPATH=src:. python ./review2089_adversarial.py
```

Result: 13 tests executed, OK. Three tests intentionally assert actual defect acceptance (forged outside-top-K, fabricated local receipt, and mixed-case contributor), so this passing probe run is evidence of blockers, not a clean approval. Full stdout: `./2089-adversarial.stdout.txt`.

Additional checks: `git diff --check origin/dev/emilkowalski-intake-2026-10-13...HEAD` passed; `python scripts/sync_agent_skill_mirror.py --check` passed; `git status --short` empty. Existing PR receipt reports green completed CI at this head, with one intentionally skipped quick-check job; these historical CI results do not invalidate the independent exploit. The full pytest suite was not rerun by this reviewer because default Python lacks pytest; the independent stdlib suite ran successfully with yaml/jsonschema installed.

Recommended merge order after repairs: complete #2093 lowercase fix in the fleet integration, independently verify #2089 authorization repair, deliberately reconcile lowercase changes into the separate Emil stack, rerun relevant ratify/adapter/push tests, then obtain explicit founder approval before merging #2089. Leave #2087/#2090 untouched. No #2089 merge was attempted.

## Published review evidence

Rechecked live PR head is still `32ecd0df7c0683167e2d9dfacf6ecbb4481cb453`, OPEN. Attempted `gh pr review 2089 --repo gaia-research/gaia-skill-tree --request-changes --body-file ./2089-request-changes.md`; GitHub rejected it because the connected account owns the PR: `Review Can not request changes on your own pull request`. Published the same changes-required findings as a PR comment, without claiming a formal review status: https://github.com/gaia-research/gaia-skill-tree/pull/2089#issuecomment-6195823210 . Final detached worktree `git status --short` remained empty.
