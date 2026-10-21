# D - Class C stops at the desk: PASS (with one vacuous check)

Real-repo clone, `full run --triage --ledger git --json` then `--triage --afk`, both exit 0, completed, `actions: []`.
- Triage counts A 0 / B 51 / B-report-only 199 / C 22. POLICY.yaml Class C kinds are credential_leak, generic_mapping, trust_stamp_stale; the only Class C debt kind present is `trust_stamp_stale` (22), and it appears only under `triage.classC`. None of the 22 appears in classA, classB, reportOnly, held or any action. 51 Class B are all `trust_calibration_drift`; B-report-only kinds are all B in POLICY. See d-analysis.txt.
- Desk: 6 founder decisions (5 `decision-record` files from founder/steward/decisions/ + 1 grouped Class C item `decision-bd6c25b50dfe8d0d3b4e` carrying the 22 debt ids). Every one has all of decision, whyItMatters, evidence, recommended, alternative, unblocks, links, non-empty (desk-full-fields.json). Credential findings none present on this tree.
- Operational items are a separate list (`desk.operations`, 4): 3 not_evaluated sensors (ci-health, dependency-advisory, test-history) and stale_schedule. No failed dispatches on this run.
- `--afk`: exit 0, completed, no prompt (stdin was /dev/null), decisions identical to the non-afk run, Class A/B work not blocked. Caveat: the runner contains no prompting path at all; `--afk` is only recorded in run options (`afk: true` in the ledger), so the "queues without prompting" check cannot distinguish afk from non-afk behaviour.
- Triage-only mode emits no Class A/B actions by design, so "no action for Class C" is also shown in a full run in scenario F (see there).
Files: run-triage.json, run-triage-afk.json, run-triage-afk-human.txt, desk-full-fields.json, d-analysis.txt.
