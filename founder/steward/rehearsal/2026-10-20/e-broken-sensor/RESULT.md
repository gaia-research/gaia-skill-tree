# E - broken sensor reports UNKNOWN: PASS

E1: real-repo clone, `git rm -r registry/named` committed (plus a seeded agent-skill mirror drift, so a Class A landing would otherwise have happened), pushed to main and dev/rehearsal.
- `full run --integration-branch dev/rehearsal --push --json`, `full run --observe --json`, `full run --retro --json` and the human retro form: all exit 3, status `blocked`, `actions: []`.
- `coverageUnknown` names exactly the 5 sensors that read registry/named: evidence-link-health, frozen-skill-integrity, timeline-causality, trust-calibration-drift, upstream-watcher. In the retro table each is `unknown` with drift 0 / healthy 0 (never healthy, never counted as executed); the routine rows that depend on them read `unknown` (routine 10) or `partial`. The other 22 executed sensors keep their results.
- Class A: summary.class_a = blocked, "sensor coverage is unknown; refusing Class A landing" although 1 Class A mirror-drift debt is open; summary.class_b = blocked likewise. Remote refs afterwards: only main, dev/rehearsal, steward/ledger (no steward/a/ branch), main sha unchanged.
- Reason text is in the local debt (unknown-sensor-debts.json): "required named-skill records are missing: registry/named (required inventory is empty: registry/named)", errorType SensorUnavailable. The run JSON and desk carry only the sensor names and a generic sentence, not the reason.
E2: `registry/schema/meta.json` replaced by invalid JSON, `full run --observe --json`: exit 3, blocked, coverageUnknown = registry-integrity, taxonomy-script-drift.
Files: run-full.json, run-observe.json, run-retro.json, run-retro-human.txt, run-e2-meta-invalid-observe.json, local-receipt-last-run.json, unknown-sensor-debts.json.

## Follow-up (lead)

Before the fix, the cause of unknown coverage appeared only in the local `debt.json`. Since 482a3ba90 the run summary carries `coverageUnknownReasons`, scrubbed and bounded, and the desk's `coverage_unknown` operation names the cause. Regression test: `tests/steward/test_fullrun_cli.py::test_unknown_coverage_names_its_cause_in_the_run_and_on_the_desk`.
