# October 15 fleet recovery evidence

These are compact historical review receipts, synthetic probe sources and test summaries. They establish what was inspected at each immutable commit; they do not authorize policy, prove live privileged workflow execution, or establish final integrated CI. The [recovery report](../2026-10-15-issue-resolver-recovery.md) distinguishes subsequent merges and unresolved gates.

`manifest.json` records SHA256 of each original scratch artifact and its sanitized published copy. Markdown machine paths became relative evidence references or checkout placeholders. The only functional script adaptation replaces fixed local checkout paths with `GAIA_REVIEW_REPO` (default current directory); the synthetic test bodies are unchanged. These scripts are historical evidence, not a new runtime policy or replacement for maintained regression tests.

To reproduce a historical probe, create an isolated checkout at its reviewed commit, install the repository's required dependencies, and run with that checkout as the working directory:

```bash
GAIA_REVIEW_REPO="$PWD" PYTHONPATH=src:. python <evidence-directory>/review2089_adversarial.py
GAIA_REVIEW_REPO="$PWD" PYTHONPATH=src:. python <evidence-directory>/review2050_adversarial.py
```

- #2089 probe target: `32ecd0df7c0683167e2d9dfacf6ecbb4481cb453`. Its 13 passing assertions include three confirmed bad acceptances; **passing is evidence of blockers**, not approval.
- #2050 probe target: `12bf0fc0fceaaed4a4b21c5245e09b23ea965d46`. Its 25 passing assertions document that reviewed candidate. Subsequent workflow stale-approval changes require a fresh review and receipts before integration.
- #2055: implementation and independent reviews plus 149-test rerun and direct lowercase/collision probes.
- #2052: implementation and independent reviews plus 49-test rerun and schema/cache/checkpoint probes.
- Badge repair: review receipt and direct normalization probes; broader 283-test result recorded in the receipt.
- #2039: independent review records initial findings and their correction; technical acceptability does not grant founder policy approval.

Full API responses, transient CI snapshots, raw session logs, and machine credentials are excluded. No historical result here claims that missing required checks passed.
