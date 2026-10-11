# Badge Provisioning Campaign #1817: runbook

`manifest.json` is the authoritative **campaign ledger** (lifecycle, approvals, attempts, PR URLs, history).
Upstream reconciliation (Issue #2069) adds an *observation* layer. It never changes the ledger.

## Architecture

| Piece | Where | Role |
|---|---|---|
| Planner / ledger CLI | `scripts/plan_badge_provisioning.py` | `plan`, `record-outcome`, plus `reconcile`, `predispatch`, `release-reservation` |
| Reconciler engine | `scripts/badge_reconcile.py` | GitHub evidence, badge normalization, coverage, decision engine, receipts, reservations |
| Tests | `tests/test_badge_reconcile.py` | Fixture-only (fake GitHub transport), no network |
| Receipts | `campaigns/badge-provisioning/receipts/<id>/receipt.{json,md}` | Evidence output of `reconcile` |

Evidence per repository (all must be complete or the result is `UNKNOWN`):
1. **Identity**: `GET /repos/{name}` follows renames. Records GitHub ID, canonical name, aliases, default branch.
2. **PRs**: ledger-recorded PRs, the live open-PR list, and search (`gaiaskilltree.com`, `"Gaia Skill Tree"`, campaign author). Each candidate's diff is fetched and inspected for Gaia badge URLs. **Unmarked open PRs** (odd title/branch/author) are diff-scanned too, newest first, up to `--open-scan-limit` (default 100) per repo.
3. **README**: default-branch HEAD SHA, then the README at that SHA. Markdown, HTML, URL-encoded, `?repo=`, `&amp;`, `_assets`/worker paths, and `-seal` variants are normalized.
4. **Other files**: code search for Gaia badge URLs outside the README.
5. **Coverage**: badge `(handle, stem)` mapped to every Named Skill mapped to the repo in `docs/badges/registry.json`: `full` / `partial` / `none` / `unknown`.

## CLI

```bash
# read-only; writes receipt.json + receipt.md only
python3 scripts/plan_badge_provisioning.py reconcile --repo pbakaus/impeccable --repo trailhq/Graft --out-dir <dir>
python3 scripts/plan_badge_provisioning.py reconcile --all

# mandatory gate immediately before an upstream PR (exit 0 allowed / 2 refused)
python3 scripts/plan_badge_provisioning.py predispatch --repo <o/r> --worker <id>
python3 scripts/plan_badge_provisioning.py record-outcome --repo <o/r> --status PR_OPEN --pr-url <url> --reservation-token <token>
python3 scripts/plan_badge_provisioning.py release-reservation --repo <o/r> --token <token>   # or --force for a stale one
```

Auth: `GITHUB_TOKEN` / `GH_TOKEN`, else `gh auth token`. Only HTTP GET is ever issued.
Transient failures (5xx, network) are retried; 403/404/429 are never retried and fail closed.

## Decision precedence (observed state; ledger untouched)

1. Evidence incomplete: `UNKNOWN`
2. Full skill coverage on default-branch README: `ADOPTED` (campaign provenance) or `ALREADY_ADOPTED`
3. Open relevant PR: `PR_OPEN`
4. Partial coverage: `PARTIAL_COVERAGE`
5. Merged PR but badge missing, contributor-level or other-file badge only, ambiguous PR, no README, archived: `NEEDS_REVIEW`
6. Closed unmerged: `CLOSED_UNMERGED`
7. Prior outreach in ledger but nothing upstream, or ledger eligibility not dispatchable: `NEEDS_REVIEW`
8. Otherwise `READY_TO_APPROVE`

`DECLINED`, `OPTED_OUT` and `NO_RESPONSE` ledger statuses are carried as `terminal_restriction` and force the action
`NO_OUTREACH_TERMINAL_RESTRICTION`. Founder holds (`CAMPAIGN_HOLDS`, currently Graphify under #2067) force
`HELD_UNDER_<issue>_DO_NOT_REQUEST_APPROVAL` and fail the gate.

## Dispatch safety and remaining risk

`predispatch` order: reserve, refresh upstream evidence, check ledger + approval, refuse or hand back a token.
`record-outcome --status PR_OPEN` verifies and consumes the token. The token is bound to a snapshot of the ledger (status, approval, attempts, PR URL, outcome, history length): if the ledger changes after `predispatch` (for example `DECLINED` or `OPTED_OUT`), the token is void. Any other `record-outcome` also deletes the repo's reservation. Expiry is enforced as well.

`--force` on `record-outcome` and `release-reservation` is an **administrative override** (founder-authorized recovery only). It bypasses transition validation and the reservation gate. Agents and routines must not use it. Manifest read-modify-write is serialized with an
`flock` lock file and written atomically (temp file + `os.replace`).

Not guaranteed (do not claim otherwise):
- **Local-only reservation.** `.reservations/*.lock` (`O_CREAT|O_EXCL`) protects one filesystem. Workers on different machines are not serialized.
  Expired reservations are never stolen automatically; release them explicitly.
- **TOCTOU.** GitHub has no atomic "create PR if none exists". Between the final evidence refresh and PR creation, a maintainer or
  another worker can still open a PR. Mitigation: one dispatcher at a time, create the PR immediately, re-run `reconcile` afterwards.
- **Search index lag.** Merged/closed PRs not in the ledger are found via GitHub search, which can lag minutes behind and is capped at 1000 results (flagged incomplete).
  The *open* PR list is read directly and is not subject to index lag.
- **Open-PR scan limit.** Every open PR's diff is inspected up to `--open-scan-limit` (default 100, newest first; ~1 API call each). If a repo has more unmarked open PRs than that (or a README diff is too large to read), the scan is recorded as incomplete (`open_pr_scan_incomplete`), the repo can never be `READY_TO_APPROVE` (it becomes `UNKNOWN`), and `predispatch` refuses. Live example: Graphify has ~840 open PRs, so it reports `UNKNOWN`.
- **No apply path.** Observed states are never written back automatically; a lead records outcomes with `record-outcome`.
- Static badges do not authenticate repository ownership (#494).
