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

This is bounded, reactive observation of **already independently admitted** challenges, not production authorization. Frontier discovers external leads; Meta evaluates; the challenge domain and governance admit challenges; Steward maintains targeted two-sided watch. Native leads, experiments, similarity and caller approval/status/receipt JSON never become admitted challenges here. There is no general ecosystem crawler or canonical score/rank/Origin writer.

### Admission boundary (default unavailable)

The unsafe `StewardReceiptChallengeAdapter` has been removed. The CLI supplies **no admission resolver**, so even apparently verified/resolved manifests fail closed as `class-c-required` / verification unavailable, without upstream requests or lifecycle changes. `--challenge-shadow` does not bypass admission. `receipts_root` is an inert compatibility argument, not a filesystem authority.

The explicit in-process `admission.DomainChallengeAdmissionResolver` accepts **reference-only** inputs (`{"challengeId": "..."}`). The caller supplies the existing `gaia_cli.challengeDomain.VerificationReceiptResolver`, trusted challenge lookup and exact repository/pin bindings. Every run revalidates all history events and their independent immutable receipts via `validate_challenge_history`. The bridge is not an issuer, human authenticator or cryptographic sandbox; this repair configures no production issuer. Synthetic inline admission exists only as an explicitly injected TEST-only fixture. Separate integration tests exercise actual domain opening, receipt validation and authorized technical closure.

### Shared transaction and recoverable packet outbox

- The sole durable shared store is existing Steward `GitRefLedgerStore`, under `operations.upstreamWatcherChallengeWatch`; no second database. Other operations and unrelated Git refs/configuration survive. The local-ledger option is single-process/offline only; local cache never seeds shared state.
- Inputs union by immutable identity; conflicting contexts fail closed. Filtered/empty manifests and budgets cannot replace accepted inputs. Each immutable observation binds input digest, validated admission snapshot/context, observation time, request budget and captured responses.
- **Every CAS retry** validates fresh shared bytes, unions input/observation deltas and folds in `(observedAtUTC, observation digest)` order. Stale clones cannot replace newer challenge entries. Known fields survive newer partial-budget observations. Technical closure is terminal for an immutable challenge identity; reopening requires a distinct linked domain challenge.
- Polling HTTP occurs once **outside** CAS. Retries replay captured responses with zero network calls. Relative rate-limit delays are frozen at observation time. Partial/unknown checks remain explicit and do not prove restoration.
- The same atomic shared save reserves **complete immutable packet payloads**, payload hash, identity/context, source-observation and derivation references, and stable policy/episode intents. **Save precedes local materialization.** A killed clone can leave no files; any fresh clone repairs the entire outbox without original manifest/cache/output files. Local conflicts/tampering fail closed.
- Restore checks state digest, observation/input identity, context, packet identity/hash/reference, and exact packet reproduction from its immutable observation prefix. Rehashed packet-body or projected-state edits are rejected. These hashes detect corruption/context mismatch, **not malicious writers able to rewrite the entire trusted history**. Legacy v1 state fails closed pending explicit audited migration; it is not silently discarded.
- Packet IDs bind policy, challenge context and semantic intent, not daily polling time. `t0/+24h/+72h` steps share a stable outage episode. Continued outage and continuous `72h-review` unknown episodes do not generate daily actions; recovery followed by a new outage starts a new episode.

**No exactly-once external delivery claim.** There is no live HTTP packet publisher here. Downstream publication must follow shared save, remain outside CAS, and use `packetId` for remote idempotency. Without remote idempotency, ambiguous crash/ack entails at-least-once delivery or duplicates. Restored files are not new reservations: `result.packets` lists only newly committed intents.

Offline proofs include actual concurrent two-clone Python processes against a local bare Git remote, first-CAS barriers and forced stale-writer conflict, with HTTP counts, input union, partial-field preservation and duplicate-intent assertions. A process exits between shared save/materialization, followed by fresh-clone recovery. Virtual `t0/+24h/+72h` fixtures prove policy, **not four elapsed operational weeks**, live issuer readiness or independent acceptance. Journal/outbox growth is not automatically compacted; the Steward transport's payload bound fails closed rather than dropping history.

### Challenge watch rollout gate

The workflow's scheduled path reads the repository variable `GAIA_CHALLENGE_WATCH_ENABLED`. It is intentionally unset/off by default; setting it to `true` or `1` is the reviewed configuration step that opts scheduled runs into challenge watch. This repair does not set the variable or authorize production activation. Manual CLI flags are for isolated development fixtures only until the independent-receipt and cross-run persistence work is complete.

---

## Module layout

```
scripts/upstream_watcher/
├── watcher.py            # Main entry point (CLI flags, poll loop, dry-run report, challenge seam)
├── challenge_watch.py    # Two-sided watch, fresh-state CAS journal/outbox, probes
├── admission.py          # Explicit domain receipt-port bridge (CLI default unavailable)
├── transport.py          # Transport abstraction, HttpTransport, SimulatedTransport, VirtualClock
├── finder.py             # Suite enumeration, mode detection, finding computation
├── liveness.py           # Link liveness checks, blob→raw URL conversion, component diff
├── name_drift.py         # SKILL.md frontmatter name-drift detection (issue #1457)
├── issuer.py             # Issue body renderers, idempotency checks, gh issue create
├── tests/
│   ├── test_upstream_watcher.py  # Unit tests for suite watcher (all API calls mocked)
│   ├── test_challenge_watch.py   # Watch policy (explicit TEST-only admission)
│   ├── test_challenge_watch_admission.py # Domain receipt-port integration
│   └── test_challenge_watch_transactional.py # Processes, crash/recovery, tamper
└── README.md             # This file
```


---

## Status

- **PR 6/7**: Code shipped. Workflows are deployed but the watcher has NOT been run yet.
- **PR 7/7**: First real dry-run against the live registry. Bootstrap issues will be opened for all suites without an `upstream:` block.
