# Next safe unused-import nominations — read-only

Source HEAD verified: `78bf592d439e0666afe0c4cef1e89d20cb7fe0a7`. Current IDs were taken only from `summary.reobserve.freshOpenDebt` in `roster-fresh-postmerge-reconcile.json`. No scan, CLI, test, lane, record, dispatch, global-ledger operation, or source edit was performed.

## Nominations: none

The old executable-queue document is treated as leads, not authority. Its superficially attractive `scripts/ci_churn.py` lead (`debt:unused_import:scripts-ci-churn-py:51b6876e863ec208`) is in the fresh ID list, but current AST inspection shows the flagged `timezone` name is used as `datetime.timezone`; it is not an unused import. The old `generate_weekly_report.py` `Any` lead is also stale: current AST inspection finds `Any` used. Neither qualifies.

The remaining old import leads rely on application imports or are upstream-watcher/security-sensitive code with side-effect/public-consumer uncertainty; they do not meet the requested retained-stdlib/no-side-effect and genuinely focused-test bar from read-only confirmation. No fresh replacement candidate was sufficiently confirmed against all criteria, so I prefer no nomination over an unsupported packet lead.

This is not a claim about per-row authority, attempt counts, or dispatchability. A lead must revalidate canonical debt and prepare the required packet before any work. No existing tests were run; no broad `-k` collection is proposed.
