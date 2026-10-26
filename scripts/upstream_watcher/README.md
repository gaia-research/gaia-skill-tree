# Upstream Watcher

The upstream watcher polls the source repositories of curated Gaia suite skills for new releases and opens GitHub issues proposing version bumps, component diffs, and link-liveness reports.

See the [full design spec](../../docs/agents/upstream-watcher.md) for architecture, rationale, and phased rollout plan.

---

## What it does

For each named skill with `suiteComponents` at 2★+:

1. **Fetches the latest GitHub release** from the suite's `links.github` owner/repo.
2. **Compares** the release tag against the stored `upstream.version` in frontmatter.
3. **Produces a finding:**
   - **Bootstrap** — no `upstream:` block yet (first run).
   - **Update** — stored version differs from latest release.
   - _(no finding)_ — already up-to-date.
4. **In `components` mode** (all components point to subpaths in the same repo), for **update** findings only:
   - Diffs the upstream release tree to detect component adds/removes.
   - HEAD-checks each component's `links.github` URL for liveness.
   - **Name drift** (issue #1457): fetches each component's upstream `SKILL.md`, sanitizes its frontmatter `name` the same way `npx skills add` does, and compares it to the registry slug. A mismatch is reported with the exact `gaia dev rename <old-id> <new-id>` fix — this is the same divergence `scripts/install_parity.py` would eventually catch as `DIRNAME_MISMATCH`, surfaced earlier, at release time.
5. **Outputs** findings as a markdown report (`--dry-run`) or creates GitHub issues (`--apply`).

---

## Running locally

### Dry-run (default — no issues created)

```bash
# All suites
python scripts/upstream_watcher/watcher.py --dry-run

# One suite
python scripts/upstream_watcher/watcher.py --dry-run --skill mattpocock/skills

# With verbose logging
python scripts/upstream_watcher/watcher.py --dry-run --verbose
```

GitHub API calls use `GH_TOKEN` env var if set; unauthenticated otherwise (60 req/hr limit — sufficient for dry-runs on small suites).

### Apply mode (creates real GitHub issues)

```bash
export GH_TOKEN="ghp_..."  # requires issues:write scope
python scripts/upstream_watcher/watcher.py --apply
```

**Warning:** `--apply` creates real GitHub issues. Use `--dry-run` first to confirm the output looks correct.

---

## Triggering the workflow manually

1. Go to **Actions → Upstream Watcher** in the GitHub repo.
2. Click **Run workflow**.
3. Optionally fill in `skill_id` to scope to one suite.
4. Set `apply` to `true` to create issues (default is dry-run).

> **Note:** PR 6 ships this code but PR 7 will perform the first real dry-run against the live registry. Do not enable the cron schedule until outputs are verified for 2+ weeks.

---

## Where issues land and how to review them

Issues are created with labels `upstream:release` (umbrella), `upstream:bootstrap` (first-run), or `upstream:child` (new component intake). All start with `needs-triage`.

For the full review protocol — label vocab, approval mechanics, child gate — see [upstream-watcher.md §7 Approval mechanics](../../docs/agents/upstream-watcher.md#approval-mechanics).

**Short version:**
- Apply `upstream:approved` to open a draft sync PR (gated on child intakes being closed first).
- Apply `upstream:rejected` to close without syncing (auto-closes child intakes).
- Apply `upstream:needs-info` to hold without automating anything.

---

## Two-Sided Challenge Watch (Yggdrasil IV P2)

The challenge-watch code is an observation prototype, not yet production-authorized. Its prior local manifest/ledger path is not a durable trust boundary across ephemeral runners, and its original receipt adapter accepted untrusted inline claims. Do not treat its `isVerified` or resolution output as public status or proof of closure. A repair is in progress to consume governed Steward receipts and shared CAS state. Until that lands and is independently verified, run only isolated fixtures; do not enable the scheduled challenge watch.

The intended bounded behavior is two-sided observation, availability probes (`t0 -> +24h -> +72h`), and no score/rank/Origin authority. These are design goals, not verified production guarantees yet.

### Challenge watch rollout gate

The workflow's scheduled path reads the repository variable `GAIA_CHALLENGE_WATCH_ENABLED`. It is intentionally unset/off by default; setting it to `true` or `1` is the reviewed configuration step that opts scheduled runs into challenge watch. This repair does not set the variable or authorize production activation. Manual CLI flags are for isolated development fixtures only until the independent-receipt and cross-run persistence work is complete.

---

## Module layout

```
scripts/upstream_watcher/
├── watcher.py            # Main entry point (CLI flags, poll loop, dry-run report, challenge seam)
├── challenge_watch.py    # Two-sided challenge watch engine, ledger, receipt adapter, probes
├── transport.py          # Transport abstraction, HttpTransport, SimulatedTransport, VirtualClock
├── finder.py             # Suite enumeration, mode detection, finding computation
├── liveness.py           # Link liveness checks, blob→raw URL conversion, component diff
├── name_drift.py         # SKILL.md frontmatter name-drift detection (issue #1457)
├── issuer.py             # Issue body renderers, idempotency checks, gh issue create
├── tests/
│   ├── test_upstream_watcher.py  # Unit tests for suite watcher (all API calls mocked)
│   └── test_challenge_watch.py   # Unit tests for challenge watch (offline injected fixtures)
└── README.md             # This file
```


---

## Status

- **PR 6/7**: Code shipped. Workflows are deployed but the watcher has NOT been run yet.
- **PR 7/7**: First real dry-run against the live registry. Bootstrap issues will be opened for all suites without an `upstream:` block.
