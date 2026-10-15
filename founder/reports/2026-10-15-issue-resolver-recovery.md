# October 15 Issue Resolver Fleet recovery

Snapshot: integration `dev/issue-resolver-fleet-2026-10-15` at `3c999be9af65d9e18b08d6828645a196adfd3aea`, PR [#2097](https://github.com/gaia-research/gaia-skill-tree/pull/2097) open and draft against `main`. This report preserves reviewed evidence while final #2050 repairs and integrated validation continue. It is not a completion or final-CI claim.

The interrupted fleet was recovered from actual branches and existing PRs. Existing integration work remains intact: #2092/#2042 documentation cache busting, #2035 Trust freshness, #2094/#2052 curation authority/provenance, and #2096/#2074 badge outreach policy. No issue was closed, no direct main push or main merge was performed, and #2087/#2090 remain untouched. #2032/#2045 remain separate.

## Issue / PR matrix

| Issue | PR | Verified status | Tests and evidence | Merge state | Next action |
|---|---|---|---|---|---|
| #2042 | #2092 | Preserved completed cache-busting lane | Included in preserved-lane regression check | Already in integration | Final aggregate checks; main remains founder-gated |
| Trust freshness | #2035 | Preserved completed repair | Included in preserved-lane regression check | Already in integration | Final aggregate checks |
| #2052 authority/provenance | #2094 | Preserved completed authority-map/appraisal lane | Existing live-engine contract retained | Already in integration | Final aggregate checks |
| #2074 badge policy | #2096; repair #2100 | Independent review caught and repaired unsafe hostname substring attribution and Markdown-wrapper compatibility | 283 focused tests; six positive/six malicious direct probes; [review](2026-10-15-issue-resolver-evidence/2100-independent-review.md) | #2100 merged as `3c999be9a` | Verify final aggregate CodeQL alert clearance |
| #2055 lowercase identity | #2093 | Lowercase only across add, rename, ratify, push, intake adapter; explicit expected spelling; no silent normalization; legacy case-insensitive collisions retained | 211 worker regressions; 149 independent rerun; direct malformed/lowercase/collision probes; [review](2026-10-15-issue-resolver-evidence/2093-independent-review.md) | Merged as `cddb09ce9` | Final integrated regression checks; approved identity `hikari9/auto-office` |
| #2052 surgical remainder | #2099 | Retired-divisor schema descriptions only; cache/inheritance wording aligned; resume checkpoint wired; founder META commit preserved | 65 worker tests; 49 independent rerun; 12 schemas behavior-identical after excluding descriptions; [review](2026-10-15-issue-resolver-evidence/2099-independent-review.md) | Merged as `7d405ad6a` | Final integrated build/CI; no calibration requested or performed |
| #2050 approval recovery | #2095 | Prior candidate passed independent review; subsequent stale-approval repair under final review | Historical 25 adversarial probes and 154 focused tests at `12bf0fc0f`; [review](2026-10-15-issue-resolver-evidence/2050-independent-review.md) | Open draft; latest observed head `02a0722995ed11157087e459a3c7f83f42558256`; not merged in this snapshot | Finish current-head independent adversarial review and required CI before integration |
| #2039 modernization | #2098 | Technically acceptable at `b3eabcda8282f6933b3aa074f56f747516eb9019`; founder policy approved on 2026-10-15 | 85 independent helper/state tests; 73 playbook tests; mirrors/shell checks; [review](2026-10-15-issue-resolver-evidence/2039-independent-review.md) | Open draft; full CI pending before integration | Founder approval recorded in comment 6196069160; recovery lead verifies full CI and integrates when green |
| Separate intake compatibility | #2089 | Confirmed authorization blocker in original `f1dccf786`; review includes full diff through `32ecd0df7` | 13 independent synthetic probes, including explicit bad-acceptance assertions; [review](2026-10-15-issue-resolver-evidence/2089-review.md) | Open against Emil intake branch; unmerged | Repair authenticated outside-top-K approval, reconcile lowercase contract, independently retest, obtain explicit founder merge decision |

## Security and authorization findings

#2095 review traced authenticated workflow artifacts, actors and rerun actors, canonical workflow/run/attempt/repository provenance, immutable artifact comparison, exact approved issue revisions, and issue/batch/upstream freshness. The original four defects were repaired at the historical reviewed commit: injected issue/comment text grants no authority; materialization reruns are stable; issue bodies and batches are rechecked; workflow inputs enter shell through environment variables with shape validation. Independent review additionally found a queued-label race in the initial candidate; event-bound exact-revision guards repaired it. A later stale-approval workflow repair is still being finalized and must receive current-head review. No historical approval substitutes for that check.

#2089 remains blocked: an editable `humanOverride`/`humanReview` attestation can admit a mapping target outside retrieval top-K without authenticated human approval. Original commit `f1dccf786` introduced the exception; follow-up `32ecd0df7` does not resolve it. Missing or fabricated local assessment receipts also pass the demonstrated path. Duplicate identity/conflicting generic/cross-batch/stale retrieval protections otherwise held in independent probes. The formal changes-requested review was rejected because the connected account owns the PR; the same findings were published as a [PR comment](https://github.com/gaia-research/gaia-skill-tree/pull/2089#issuecomment-6195823210). This is not a clean or decision-ready merge recommendation.

## Surgical #2052 receipt

Founder `META.md` commit `2e7a1b878` is an unchanged ancestor. New commits `ea1095287` and `50a41fe4a` correct only approved wording and resume wiring. TM/Overall Trust Grade may be a CLI-written hash-signed cache via `gaia dev calibrate-trust-magnitude`; reuse requires a matching input hash. Eligible generic-layer evidence contributes effective named TM. No formula, calibration, evidence, registry data, or schema behavior changed.

Resume reads current blocker state instead of replaying historical failures. Open and unproven resolutions remain active; resolved blockers with evidence stay resolved unless a genuine fresh failed check re-raises them. Repeated resume and legacy ledgers are tested. L4, evidence, and calibration human gates remain paused.

## Modernization boundary

#2098 supplies the model-family guidance layer, instruction migration map, targeted entry-surface corrections, feature-pipeline changes, mirrored canonical skills and autonomy/hard-gate regressions. Independent review found and resolved old-gh compatibility and explicit operator-checkpoint wording. Its helper now truthfully reports all reported current-head checks; that result cannot prove absent required checks completed. Founder explicitly approved the governance/instruction policy delta on 2026-10-15, recorded in [PR comment 6196069160](https://github.com/gaia-research/gaia-skill-tree/pull/2098#issuecomment-6196069160). The policy hold is cleared; full required CI and recovery-lead integration remain pending. No CLI, L4, evidence, security, schema or final-main control is waived.

## Integration validation and founder decisions

A preserved-lane regression run reported 297 passing tests before the later aggregate additions; [historical output](2026-10-15-issue-resolver-evidence/preserved-integration-tests.log). Lane CI and independent results above apply to their recorded immutable heads. They do not establish final integration CI. The recovery lead must append the final integration tip, current required-check results, final aggregate tests, CodeQL status and final #2095 review after remaining repairs land.

Remaining founder decisions: whether to merge #2089 into the separate Emil branch after its authorization blocker is repaired and independently verified; and whether to merge the final verified #2097 into main. Main merge approval remains required. All relevant issues stay open until fixes reach main and are verified there.

See the [evidence index](2026-10-15-issue-resolver-evidence/README.md) and [artifact hashes](2026-10-15-issue-resolver-evidence/manifest.json). Historical probe scripts are evidence, not executable authorization policy.

## Interim continuation handover

The user requested pushed recovery and a Flash handover before final integration. Stop new implementation in this receipt lane. The recovery lead will record the exact latest integration/feature heads and continuation commands after this evidence PR is pushed. Final integrated CI and final-main approval are incomplete.

Continue existing #2095 stale-approval repair review on its current branch; do not recreate its PR or use historical 12bf evidence as current-head approval. #2098 policy is approved, but check full current-head CI before integration. Keep #2089 blocked/unmerged and #2087/#2090 untouched. Preserve completed integration merges, use merge commits only, and push each meaningful recovery commit. No issue closes or main merge without the required final verification and founder authorization.
