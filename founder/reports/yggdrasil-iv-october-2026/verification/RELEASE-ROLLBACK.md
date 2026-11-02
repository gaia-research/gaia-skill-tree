# Yggdrasil IV release and rollback receipt

## Status: preparation, not authorization

EPIC #2189; aggregate [#2151](https://github.com/gaia-research/gaia-skill-tree/pull/2151). No production release, tag, founder approval or final merge is performed by this receipt. Feature integration uses reviewed merge-commit PRs into `dev/yggdrasil-iv`.

## Verified resume anchors

Observed at 2026-10-30T18:22Z–18:40Z (UTC; not the October cutoff):

| Role | Ref |
|---|---|
| Current production source/restore anchor | `origin/main` = `dc07528884a759dbd3668d4a0007469265ab396f` |
| Integration at resume | `origin/dev/yggdrasil-iv` = `f70b55e62b39308a9b1dd78c0b52849d6df19216` |
| Launch proof branch at resume | `329acaf82cd0bc41381023c7f6e9ee825908a932` |
| Preserved Origin WIP (not verified) | `80150fff8` |
| Preserved adjudication tooling WIP (not verified) | `c35b1b69b` |

These are resume anchors. **Immediately before founder merge, re-pin the actual main tip and reviewed dev SHA.** If main advances, use its new pre-merge tip as the rollback anchor, synchronize by merge, regenerate and reverify. Never restore a stale anchor over unrelated intervening work.

## Final release gate (all must be satisfied)

- Independent Origin review repaired and accepted; no frozen canonical-byte mutation or new Steward engineering.
- Schema adoption tests retain synthetic unadopted refusal coverage; applicable real founder/schema authority documented, no agent-authenticated founder approval.
- #2251 then #2259 integrated after Origin; deterministic source and public projection agree.
- Fresh separate calibration Meta re-audit **PASS**, with exact target SHA and evidence in `CALIBRATION-REVERIFICATION.md`; CI alone is insufficient.
- Adjudication approved/proposed dispositions reproduce current founder rulings with `--check`.
- All 76 L4 choices accounted for, exact source/assessment and CLI provenance retained; frozen protections and November deferrals honored.
- Final October upstream/corpus/evidence refresh occurs only after `2026-10-31T23:59:59Z`. Keep the provisional snapshot immutable; preserve final input/output manifests and diff.
- Separate mattpocock witness probe occurs after `2026-11-01T16:40Z`; record actual clock/status and no automatic penalty.
- #2266 fully fact-verified and rendered at 1440/390/320px with keyboard/focus evidence; actual founder visual/content approval precedes merge.
- W8/W9 acceptance covers homepage, leaderboard, Origin/contested indicators, skills, evidence, profiles, API, history and Meta Report with coherent approved data and no synthetic challenge.
- Proof branch integrated through independently reviewed merge-commit PR; current #2151 head is conflict-free, required CI green, independent review current.
- Actual rollback rehearsal and production/publication acceptance plan attached. Founder explicitly authorizes #2151 merge and release.

## Rollback procedure (operator runbook; not executed yet)

1. Freeze publication decisions. Record actual release version/tag, #2151 merge SHA, its parents, deployed artifact/snapshot digest, incident and founder authorization. Do not delete challenge/evidence/history receipts.
2. Fetch current refs. Verify `git show --no-patch --format='%H %P' <2151-merge-sha>` identifies the recorded pre-merge main as parent 1. Refuse if the parent/source does not match the signed-off receipt.
3. Create a **new rollback feature branch/worktree from current main**. Run `git revert -m 1 <2151-merge-sha>` there, preserving history. No direct main push, reset or force push. If later work conflicts, resolve narrowly with review; do not overwrite newer unrelated changes.
4. Regenerate source-derived artifacts with the canonical CLI/build tooling, retain the required deterministic Class S set, and inspect named/frozen source diffs. Restore approved historical data, not a new unapproved recalibration. Preserve the evidence/assertion/challenge event chain.
5. Run applicable Python/JS regression, schema/DAG/integrity, timeline, version-lockstep and deterministic publication parity checks. Compare corpus and public projections against the pinned restore source. Record any intentional difference (e.g. subsequent unrelated commits or rollback audit event).
6. Open a rollback PR to main with the exact before/after manifests, reason, rendered preview and test evidence. Obtain real founder approval and merge/release authorization. Deploy only the approved artifacts/version; do not silently retag a release or overwrite historical October snapshot bytes.
7. Verify public health/version, named/ledger/leaderboard/API equality, homepage and report links, representative and frozen profiles, Origin and challenge histories after deployment. Record deployment identifier and observed outputs. Rollback is not complete merely because Git reverted.

## Rehearsal evidence

**Not yet run at the final launch SHA.** Existing publication rehearsals under `founder/reports/yggdrasil-iv-evidence/publication-b81/` are historical evidence, not a substitute for the final October release receipt. A disposable rehearsal must not approve or deploy production.

## Time and human gates

The October cutoff and +72h probe are not yet due at resume. Report remains provisional until then. Founder touchpoints: #2266 visual/content approval; #2151 final merge/release authorization. Existing recorded L4/policy approvals are not reopened.
