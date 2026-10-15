# Badge Provisioning Campaign #1817: runbook

`manifest.json` is the authoritative **campaign ledger** (lifecycle, approvals, attempts, PR URLs, history).
Upstream reconciliation (Issue #2069) adds an *observation* layer. It never changes the ledger.

## Architecture

| Piece | Where | Role |
|---|---|---|
| Planner / ledger CLI | `scripts/plan_badge_provisioning.py` | `plan`, `record-outcome`, plus `reconcile`, `predispatch`, `release-reservation`, `policy` |
| Policy engine | `scripts/badge_policy.py` | Pure: signal extraction, channel decision, append-only policy ledger, approval provenance, local draft (Issue #2074) |
| Policy ledger | `policy-ledger.jsonl` | Append-only, hash-chained channel / approval / closure events. Never edited, never erased |
| Local drafts | `drafts/` | Draft proposals. **Local only, never sent** |
| Reconciler engine | `scripts/badge_reconcile.py` | GitHub evidence, badge normalization, coverage, decision engine, receipts, reservations |
| Tests | `tests/test_badge_reconcile.py`, `tests/test_badge_policy.py` | Fixture-only (fake GitHub transport), no network |
| Receipts | `campaigns/badge-provisioning/receipts/<id>/receipt.{json,md}` | Evidence output of `reconcile` |

Evidence per repository (all must be complete or the result is `UNKNOWN`):
1. **Identity**: `GET /repos/{name}` follows renames. Records GitHub ID, canonical name, aliases, default branch.
2. **PRs**: ledger-recorded PRs, the live open-PR list, and search (`gaiaskilltree.com`, `"Gaia Skill Tree"`, campaign author). Each candidate's diff is fetched and inspected for Gaia badge URLs. **Unmarked open PRs** (odd title/branch/author) are diff-scanned too, newest first, up to `--open-scan-limit` (default 40) per repo.
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
- **Open-PR scan limit.** Every open PR's diff is inspected up to `--open-scan-limit` (default 40, newest first; ~1 API call each). If a repo has more unmarked open PRs than that (or a README diff is too large to read), the scan is recorded as incomplete (`open_pr_scan_incomplete`), the repo can never be `READY_TO_APPROVE` (it becomes `UNKNOWN`), and `predispatch` refuses. Live example: Graphify has ~840 open PRs, so it reports `UNKNOWN`. For one repo, a human may raise it explicitly (`predispatch --open-scan-limit 200`). A full `--all` run costs roughly 1 API call per inspected PR, so keep the limit low (the hourly core budget is 5000 calls) and avoid repeated full runs inside one hour. After the first `RATE_LIMITED` response the client stops calling GitHub and the remaining repos report `UNKNOWN` (fail closed).
- **No apply path.** Observed states are never written back automatically; a lead records outcomes with `record-outcome`.
- Static badges do not authenticate repository ownership (#494).

## Contribution-channel policy (Issue #2074)

Before any outreach every repo gets exactly one channel: `PR_ALLOWED`, `ISSUE_FIRST`, `NO_OUTREACH` or `UNKNOWN`.
`UNKNOWN` fails closed. `NO_OUTREACH` and `UNKNOWN` are internal holds with **no PR and no issue**.

```bash
# scoped (policy scan on by default for --repo); --all never scans policy unless forced
python3 scripts/plan_badge_provisioning.py reconcile --repo <o/r> [--policy-budget 36]
python3 scripts/plan_badge_provisioning.py reconcile --all                     # policy_channel UNKNOWN (not scanned), no policy calls
python3 scripts/plan_badge_provisioning.py reconcile --all --policy on --policy-max-repos 43   # explicit, expensive, rarely right

python3 scripts/plan_badge_provisioning.py policy {verify,status,apply,classify,record-closure,record-refusal,draft,record-sent,approve,revoke} ...
```

**Evidence read** (all GET): README (already fetched), `CONTRIBUTING` (root and `.github/`), `AGENTS.md`/`CLAUDE.md`,
issue templates/forms and `config.yml`, PR templates, `CODE_OF_CONDUCT`, `SECURITY`, policy-looking workflows,
repo settings (issues enabled/disabled, archived), maintainer and bot comments on prior Gaia PRs/issues, closed-as-not-planned
issues, and the policy ledger (recorded refusals and closures). Searches cover PRs **and** issues, open and closed, under the
canonical name and its aliases (renames, `KNOWN_MIGRATIONS`).

**Decision**: incomplete evidence is `UNKNOWN` (flagged). Otherwise a restriction beats a permission; issue-first beats a general
"PRs welcome"; `PR_ALLOWED` needs an explicit permission from `CONTRIBUTING`, the README, or an `OWNER`/`MEMBER`/`COLLABORATOR`
comment. Silence, templates, bots and strangers never grant permission. `ISSUE_FIRST` with no usable issue channel (issues disabled,
bug-only forms, maintainer-only) is `NO_OUTREACH`: no issue is manufactured into a form that does not accept it.

**One attempt, two stages.** Any prior Gaia issue or PR (any state, any alias) is part of the same attempt. `predispatch` refuses a
second issue or PR. The one exception: PR(s) closed under the repo's own issue-first policy (`record-closure --kind
ISSUE_FIRST_REDIRECT`) do not block the single README PR once a maintainer approval is recorded AND verified upstream.

**Approval provenance.** `policy approve` stores approver, authority, evidence comment URL and verbatim excerpt, recorded by a
named human against the single recorded proposal issue. `predispatch` re-reads the issue comments and verifies author, association,
excerpt, no withdrawal, and that the approver is named by the repo's policy. Anything else is `UNVERIFIED` and holds.

**Cost guard.** Per repo at most `--policy-budget` calls (default 36): about 5 listings, 12 file reads, 2 searches per name
(max 3 names), 6 comment reads. Exhausting a cap, a rate limit, a 403, a truncated or `incomplete_results` search all give
`UNKNOWN` plus an anomaly. The receipt `cost` block reports calls used and `full_campaign_scan_required: false`.

**Lifecycle.** A PR closed upstream under a policy is recorded as `POLICY_HOLD` (non-terminal, history kept). Leaving it needs a fresh
`APPROVED --approved-by`; `POLICY_HOLD -> PR_OPEN` is refused. Impeccable #1010 is `POLICY_HOLD` (CLOSED_UNMERGED, issue-first
redirect); `drafts/pbakaus__impeccable.issue-first-proposal.md` is a local draft that has **not** been sent. No upstream contact
happens without a fresh human decision.
