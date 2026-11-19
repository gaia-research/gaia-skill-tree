# Upstream Watcher

> **Current P1 Candidate Scope (Detection / Plan-Only):** On this P1 candidate branch, ordinary watcher operation is **detection and plan-only** — it polls upstream releases and plans repository envelopes with zero GitHub issue writes. Valid ordinary `--dry-run` runs may exit `0` with planned reports and `writeReadiness: false` (plus the plan-only `executionHold`); invalid CLI invocations or staging rollout checks may exit `1`; unknown/poll/inventory errors may exit `3`; ordinary `--apply` routes reaching the apply hold exit `4` with no issue effect; and `--escalate` is separately held read-only at `exit 3`. All issue-write, create, update, adopt, record-reset, and review flows described below belong to **deployed legacy `main` or historical V1/staging design reference only** — they are never actionable on this candidate.

Historically (on deployed legacy `main`), the upstream watcher polls the source repositories of curated Gaia suite skills for new releases and opens GitHub issues proposing version bumps, component diffs, and link-liveness reports. On this P1 candidate, it runs detection and envelope planning only.

See the [full design spec](../../docs/agents/upstream-watcher.md) for historical architecture, rationale, phased rollout plan, and P1 candidate boundaries.

---

## What it does

For each eligible named skill with `suiteComponents` at 2★+:

1. **Resolves the upstream source and fetches the latest GitHub release** from the suite's `links.github` `owner/repo`. When `links.github` is empty or missing, `resolve_suite_source` falls back to canonical `upstream.repo` (for example `gsd-build/get-shit-done`); non-empty invalid `links.github`, invalid `upstream.repo`, or contradictory `links.github` vs `upstream.repo` identities fail closed as unknown evidence (`exit 3`).
2. **Compares** the release tag against the stored `upstream.version` in frontmatter.
3. **Produces a finding:**
   - **Bootstrap** — no `upstream:` block yet (first run).
   - **Update** — stored version differs from latest release.
   - _(no finding)_ — already up-to-date.
4. **In `components` mode** (all components point to subpaths in the same repo), for **update** findings only:
   - Diffs the upstream release tree to detect component adds/removes.
   - HEAD-checks each component's `links.github` URL for liveness.
   - **Name drift** (issue #1457): fetches each component's upstream `SKILL.md`, sanitizes its frontmatter `name` the same way `npx skills add` does, and compares it to the registry slug. A mismatch is reported with the exact `gaia dev rename <old-id> <new-id>` fix — this is the same divergence `scripts/install_parity.py` would eventually catch as `DIRNAME_MISMATCH`, surfaced earlier, at release time.
5. **Outputs (plan-only on this P1 candidate):** emits findings as a markdown report (`--dry-run`) and plans repository envelopes (`writeReadiness: false`). Valid ordinary `--dry-run` may exit `0` with planned reports; invalid invocation/rollout checks may exit `1`; unknown/poll errors may exit `3`; ordinary watcher envelope `--apply` routes reaching the hold fail closed at `exit 4` with zero GitHub issue writes; and `--escalate` is separately held read-only at `exit 3`. Legacy issue write/create/adopt behavior belongs to deployed legacy `main` only.

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

### Apply mode (currently plan-only guarded)

```bash
export GH_TOKEN="ghp_..."  # requires issues:write scope
python scripts/upstream_watcher/watcher.py --apply
```

**Note:** Ordinary watcher envelope `--apply` routes (including unstaged `--child-mode batch --apply`, `--child-mode fanout --apply`, `--staging weekly --apply`, and `--reset-records`) are currently fenced plan-only at the `watcher.py` entry point: reaching the apply hold exits `4` with zero GitHub issue writes (and `--reset-records` does **not** rebuild records on this candidate), while ordinary `--dry-run` may exit `0` with `outcome: "planned"` for valid unheld repositories (and `outcome: "held"` for known legacy holds) while reporting `writeReadiness: false` and the plan-only `executionHold`. Invalid invocation or staging rollout checks may exit `1`, unknown/poll/inventory errors may exit `3`, and `--escalate` is separately held read-only at `exit 3` with zero writes. Direct offline tests of `repository_batch.run_repository_batch(..., apply=True)` remain active.

### Recovery and skipped suites (#2131 round 4 — historical / deployed-legacy reference)

> **Scope (not actionable for writes/resets on this P1 candidate):** The issue-write, create, update, adopt, and `--reset-records` rebuild descriptions below belong to **deployed legacy `main` / historical V1 reference only**. On this plan-only P1 candidate, ordinary runs never write, create, adopt, or rebuild GitHub issues or record comments.

- A suite whose upstream is permanently refused (HTTP 451, 410, or a 403 whose body is the repository's own refusal, such as a DMCA takedown or a blocked or disabled repository) is **skipped**, not fatal. The run prints a `::notice::`, lists the suite under `unavailable` in the report with `reason: "permanent"`, and proceeds with the remaining suites (on deployed legacy `main`, writing the other suites; on this P1 candidate, planning only). To bring it back, repair or remove its `links.github` entry in the registry. A 403 that names a token or App permission problem, and a bare 403, are not skips: they stop the run with exit 3 and a message that names the permission.
- A truncated component tree is read one directory at a time, within 200 requests for the suite. If that budget runs out, the suite is skipped with `reason: "tree-truncated"` and the other suites proceed.
- A transient GitHub read (no response, 5xx, 429, a rate-limited 403) gets three attempts, with waits of 1s and then 2s, before it counts as unknown evidence.
- **Deployed legacy `main` umbrella/child behavior (reference only):** One OPEN canonical umbrella per suite. Findings update it in place. When no OPEN umbrella exists, a new one is created only for a genuinely new finding. A finding a closed issue's payload already records is not re-created (listed under `suppressedProcessed`). A closed issue that cannot prove its finding blocks the suite with exit 3. The watcher never edits, comments on or reopens a closed issue. Several open umbrellas for one suite: the lowest number is canonical, the others are listed under `duplicateOpenUmbrellas` for Steward reconciliation and left untouched. A title that names the suite but does not parse blocks that suite with exit 3 and no write.
- **Record reset (`--reset-records`, historical / non-actionable on this P1 candidate):** A suite whose record comments are damaged or deleted fails closed with exit 3, and historical help or error messages may still name `--reset-records <suite>`. **This P1 candidate does NOT rebuild records**, even if the old help or error text suggests the flag: invalid CLI/rollout combinations exit `1`, earlier unknown/poll errors exit `3`, and `--apply --reset-records <suite>` reaching the plan-only apply hold exits `4` with zero GitHub writes. The apply-only rebuild semantics documented in `docs/agents/upstream-watcher.md` (Records, M4) are historical / deployed-legacy reference only and are not actionable on this candidate.

---

## Triggering the workflow manually

1. Go to **Actions → Upstream Watcher** in the GitHub repo.
2. Click **Run workflow**.
3. Optionally fill in `skill_id` to scope to one suite.
4. Leave `apply` at `false` (default) for an ordinary dry-run (`exit 0` on a valid run with findings/planned counters and `writeReadiness: false`). Setting `apply` to `true` passes `--apply`, which on this candidate branch is deliberately plan-only: it exits `4` with zero issue effects if planning reaches the apply hold (invalid/rollout checks exit `1`; genuine earlier unknown/poll errors exit `3`). Pinned-`main` deployed behavior is separate and not newly modified or qualified here.

> **Note:** The daily schedule in `.github/workflows/upstream-watcher.yml` remains unchanged and uncommented (`06:00 UTC`, `--apply`), though ordinary watcher runs on this candidate are plan-only as noted above (separately deployed pinned `main` is not newly modified or qualified here). That schedule still contradicts the manual-only decision in `docs/agents/upstream-watcher.md` (F5). Keeping or disabling the schedule is a founder call (M4); see that document's Open questions.

---

## Where issues land and how to review them

> **Scope (deployed `main` only):** The issue-creation and review flow below describes separately deployed `main` behavior (not newly modified or qualified here), not this candidate branch's plan-only ordinary watcher behavior.

On deployed `main`, issues are created with labels `upstream:release` (umbrella), `upstream:bootstrap` (first-run), or `upstream:child` (new component intake). All start with `needs-triage`.

For the full review protocol — label vocab, approval mechanics, child gate — see [upstream-watcher.md §7 Approval mechanics](../../docs/agents/upstream-watcher.md#approval-mechanics).

**Short version:**
- Apply `upstream:approved` to open a draft sync PR (gated on child intakes being closed first). A human applies it, including to a bootstrap baseline: the watcher never does.
- Apply `upstream:rejected` to close without syncing. The umbrella's open child intakes are closed too, and each one is labelled `upstream:rejected` so the rejection stays on record.
- Apply `upstream:needs-info` to hold without automating anything.
- If an approved umbrella's payload changes (a new version, a removed component, a new broken link, a changed candidate row), the watcher removes `upstream:approved`, applies `upstream:needs-info` and posts one note. Re-apply `upstream:approved` after review. A body whose stored `payloadSha256` no longer matches its own payload counts as a change, so an edited body loses its approval too (D1a).
- A sync runs only for the payload a reviewer approved. The approve workflow records that digest as a watcher-authored approval marker and re-checks it before any sync. A bot re-fire of an approval is accepted only when the labeler of that approval is a Verifier (D1b, D3).

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

The workflow's scheduled path reads the repository variable `GAIA_CHALLENGE_WATCH_ENABLED`. It is intentionally unset/off by default; setting it to `true` or `1` is the reviewed configuration step that opts scheduled runs into challenge watch. Challenge watch runs in its own `challenge-watch` job (`watcher.py --challenge-only`), the only job with `contents: write` (it pushes the `steward/ledger` ref); the poll/issue job stays at `contents: read`. The job `needs` the watcher job (exit 3 unknown evidence skips it), is skipped for single-row escalations and for any ref other than the default branch, and hands its packets on as the `challenge-watch-packets` artifact. This repair does not set the variable or authorize production activation. Manual CLI flags are for isolated development fixtures only until the independent-receipt and cross-run persistence work is complete.

---

## Module layout

```
scripts/upstream_watcher/
├── watcher.py            # Main entry point (CLI flags, poll loop, dry-run report, batch dispatch, challenge seam, --challenge-only)
├── challenge_watch.py    # Two-sided watch, fresh-state CAS journal/outbox, probes
├── admission.py          # Explicit domain receipt-port bridge (CLI default unavailable)
├── transport.py          # Transport abstraction, HttpTransport, SimulatedTransport, VirtualClock
├── finder.py             # Suite enumeration, mode detection, finding computation
├── liveness.py           # Link liveness checks, blob→raw URL conversion, component diff
├── name_drift.py         # SKILL.md frontmatter name-drift detection (issue #1457)
├── issuer.py             # Issue body renderers, idempotency checks, gh issue create, bootstrap memory
├── approval.py           # Digest, approval-marker, reset-note, Verifier and allowlist checks shared with the workflows
├── markers.py            # The one payload-block regex, imported by every reader (L3)
├── batch.py              # Umbrella batch planner (payloadVersion 2): prechecks, approval reset, writes
├── records.py            # Records mode: full batch rows in watcher-authored record comments, written per generation
├── prechecks.py          # Registry, tracked and prior-disposition checks for candidate rows
├── live.py               # GitHub access for the planner: paginated LISTs, comments, fail-closed errors
├── tests/
│   ├── test_upstream_watcher.py  # Unit tests for suite watcher (all API calls mocked)
│   ├── test_challenge_watch.py   # Watch policy (explicit TEST-only admission)
│   ├── test_challenge_watch_admission.py # Domain receipt-port integration
│   └── test_challenge_watch_transactional.py # Processes, crash/recovery, tamper
└── README.md             # This file
```


---

## Historical V1 rollout status (reference only)

> **Not current P1 candidate status:** Current P1 on this candidate branch is detection and plan-only (no bootstrap or release issues are opened). The bullets below record the original V1 PR plan only.

- **PR 6/7**: Code shipped. Workflows are deployed but the watcher has NOT been run yet.
- **PR 7/7**: First real dry-run against the live registry. Bootstrap issues will be opened for all suites without an `upstream:` block.
