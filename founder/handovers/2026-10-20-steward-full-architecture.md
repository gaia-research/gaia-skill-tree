# Gaia Steward Full — architecture and worker contract

Date: 2026-10-20 · Integration branch: `dev/gaia-steward-full` (from `main` @ `f77e4daf8`)
Lead: Opus orchestrator. Workers: Sonnet and Haiku only. Founder merges to `main`.

This document is the interface every worker builds against. If a worker needs
to change an interface named here, it stops and reports instead of improvising.

## 0. Baseline (verified on `main` @ `f77e4daf8`, 2026-10-20)

| Fact | Value |
|---|---|
| Engineering routines (`founder/ROUTINES.md`) | 17 |
| Registered sensors (`default_sensors()`) | 14 |
| Coverage matrix | 11 partial / 6 absent (routines 1, 2, 4, 5, 13, 16 absent) |
| Class B dispatch rules / Class A executors | 5 / 2 |
| Steward test suite | 372 passed |
| Live scan | 76 observations, 51 open B debt (42 `trust_calibration_drift`, 8 `frozen_skill_drift`, 1 `benchmark_source_drift`), 0 unknown |
| #2114 | Reproduces: `hikari9/auto-office` scored with empty context map → false 2★ demotion proposal |

Structural defects found in the audit (all in scope):

1. **Drift-only sensors can never retire debt.** `reconcile_debt` resolves a
   debt only when the same subject is observed `healthy`. Sensors that emit
   only drift (trust calibration, frozen skills, …) leave every past finding
   open forever — including the #2114 false positives after the fix.
2. **No honest "not evaluated" state.** A sensor either succeeds or raises
   (→ `sensor_coverage_unknown`, blocks Class A). Optional external inputs
   (CI history, advisories) have no way to say "not supplied".
3. **Checkout-local state only.** `.gaia/steward/` is ignored, per-checkout
   state. Manual and scheduled runs cannot see each other's work.
4. **Class A repairs never land.** `steward.yml` repairs in a throwaway
   checkout and uploads a patch.

## 1. Shape

```
/gaia-steward-full  (thin skill: argument mapping + driver loop)
        │
        ▼
gaia steward full …   (deterministic, zero-model runner; emits actions)
  ├─ ledger   (durable shared state: runs, leases, work items, lane)  ← git ref steward/ledger
  ├─ controller.scan (sensors → observations → debt)                 ← existing + new sensors
  ├─ triage   (dedupe, prioritize, A/B/C, routine mapping)
  ├─ landing  (Class A: worktree repair → verify → branch → PR action)
  ├─ lane     (Class B: bounded dispatch, existing caps, shared via ledger)
  ├─ verify   (mechanical verify → independent verifier action)
  └─ desk     (founder decisions + operational failures)
        │
        ▼ actions (JSON) executed by a driver: the Claude skill session, or the
          scheduled workflow's driver step. The runner never calls a model.
```

**Skills own HOW; the runner owns ORDER, SCHEDULING, RECONCILIATION, COMPLETION.**

## 2. Sensor conventions (all new sensors)

- Module per family under `src/gaia_cli/steward/`: `sensors_code.py`,
  `sensors_tests.py`, `sensors_security.py`, `sensors_ci.py`,
  `sensors_contracts.py`. Never edit `sensors.py` except the owner of #2114.
- Inventory via `gaia_cli.steward.primitives` only: `tracked_files`,
  `read_text_bounded`, `parse_python`, `finding_payload`. Do not walk the
  filesystem for repository inventory.
- Class shape:

  ```python
  class DeadCodeSensor:
      """One-line purpose."""
      id = "dead-code"
      routine_ids = (1,)
      resolution_scope = "exhaustive"   # its scan covers its whole domain
      def scan(self, repo_root: Path, observed_at: str) -> list[Observation]: ...
  ```

- `Observation(kind="<literal string>", …)` — the kind **must** be a string
  literal at the call site (the coverage checker reads ownership from the AST).
- **Aggregate per subject** (one observation per file/workflow/skill), never
  per line. `observed_state` carries `finding_payload(findings)` plus any
  metrics. Findings are sorted and deterministic.
- **Emit only `drift` observations.** Recovery is handled by sweep resolution
  (§4). Do not emit healthy observations per clean file.
- Failure semantics:
  - required input missing/unreadable/truncated/oversized → `raise SensorUnavailable(reason)`
  - optional external input absent → `raise SensorNotEvaluated(reason)`
  - a malformed *subject* (e.g. one file with a syntax error) is a finding or
    a skip with a counted reason, never a whole-sensor crash.
- Confidence: `1.0` only for exact facts; heuristics `0.5–0.8`.
- Read-only: never write anything. Never fetch the network.
- Never print secrets: credential findings carry `sha256(match)[:12]` and a line number only.

### New sensors and debt kinds

| Sensor id | Routine(s) | Kinds | Owner |
|---|---|---|---|
| `dead-code` | 1 | `unused_import`, `orphan_module` | S1 |
| `code-structure` | 2 | `import_cycle`, `code_duplication` | S1 |
| `error-handling` | 3 | `swallowed_exception` | S1 |
| `test-portfolio` | 4 | `shadowed_test`, `unregistered_marker`, `empty_test_module` | S2 |
| `test-isolation` | 5 | `test_isolation_risk` | S2 |
| `test-history` (optional input) | 5 | `flaky_test` | S2 |
| `mutation-boundary` | 7 | `ungated_mutation`, `unsafe_execution` | S3 |
| `browser-sink` | 16 | `browser_sink_risk` | S3 |
| `secret-scan` | 16, 14 | `credential_leak` (Class C) | S3 |
| `ci-workflow` | 13 | `workflow_hygiene` | H1 |
| `ci-health` (optional input) | 13 | `ci_failure` | H1 |
| `supply-chain` | 14 | `version_lockstep_drift`, `dependency_pin_drift`, `license_metadata_drift` | H1 |
| `dependency-advisory` (optional input) | 14 | `dependency_advisory` | H1 |
| `schema-validity` | 8 | `schema_contract_drift` | H2 |
| `timeline-causality` | 10 | `timeline_causality_drift` | H2 |
| `frontend-contract` | 15 | `frontend_contract_drift` | H2 |
| `trust-calibration-drift` (extended) | 9 | + `trust_stamp_stale` (Class C, #1642 detection only) | S4 |

All kinds are classified in `POLICY.yaml` (Opus-owned). Every new kind is
report-only Class B unless stated; **no new mutation authority is granted by
classifying a kind.** Optional-input files live under ignored
`.gaia/steward/inputs/` and are produced by a driver (never by a sensor).

## 3. Mandatory sensor test categories

Every sensor family's test file covers, with real fixture repositories
(`tests/steward/sensor_fixtures.make_repo`):

1. known-clean state → zero drift
2. reproducible real defect → exact finding
3. repeat invocation → identical observations (dedupe/determinism)
4. missing or stale required input → `SensorUnavailable`
5. partial/truncated observation → `SensorUnavailable` (never partial healthy)
6. unavailable dependency/API → `SensorUnavailable` or `SensorNotEvaluated`
7. unsupported/ambiguous condition → lower confidence or explicit skip reason
8. false-positive regression (historical or constructed near-miss) → no finding
9. authority/protected-path: the sensor writes nothing (tree digest unchanged)
10. recovery: fix the defect → finding disappears (and through the controller, the debt resolves)

No fabricated findings; UNKNOWN never becomes PASS.

## 4. Controller changes (S4)

- **Sweep resolution.** A sensor with `resolution_scope = "exhaustive"` that
  completed with known coverage in this run resolves every open debt whose
  `source == sensor.id` that it did not re-observe as drift, with
  `resolution="condition_not_reobserved"`. Sensors without the attribute keep
  today's semantics. A sensor that raised resolves nothing.
- **Not evaluated.** `SensorNotEvaluated` → no coverage-unknown debt, no
  sweep, no Class A block; the receipt gains `notEvaluated: [{sensor, reason}]`.
  `SensorUnavailable` and every other exception keep today's unknown path.
- **#2114.** `TrustCalibrationDriftSensor` evaluates against
  `buildMergedSkillMap(repo_root)` — the same effective-evidence context as the
  canonical inspector. If the context cannot be built, raise
  `SensorUnavailable` (no confident demotion from an own-only number).
- **#1642 detection.** Where a named skill stores `trustMagnitude` and it
  differs from the computed effective TM beyond rounding, emit
  `trust_stamp_stale` (Class C: how to refresh stamps is an open founder
  decision in #1642; the sensor only measures).

## 5. Durable ledger (S6) — `src/gaia_cli/steward/ledger.py`

Transport: a dedicated Git ref `refs/heads/steward/ledger` on `origin` holding
one file `ledger.json`. Writes are compare-and-swap by **fast-forward push
only** (new commit's parent = the version read). A rejected push is a conflict:
re-read, re-apply the mutation, retry. **Never force-push.** Plumbing only
(`hash-object`, `mktree`, `commit-tree`, `push`, `fetch`) — never the working
tree or index.

```python
class LedgerConflict(RuntimeError): ...
class LedgerUnavailable(RuntimeError): ...

class LedgerStore(Protocol):
    transport: str   # "git-ref" | "local-file"
    shared: bool     # True only for git-ref with a remote
    def load(self) -> tuple[dict, str | None]: ...           # (document, version)
    def compare_and_swap(self, expected: str | None, document: dict, message: str) -> str: ...

class GitRefLedgerStore:   # (repo_root, remote="origin", ref="steward/ledger")
class FileLedgerStore:     # (path) — tests/offline; shared=False, says so everywhere

def update(store, mutate: Callable[[dict], T], *, retries: int = 5) -> tuple[T, str]
def acquire_lease(doc, key, holder, now, ttl_seconds) -> bool      # pure, inside update()
def release_lease(doc, key, holder) -> bool
def empty_ledger() -> dict   # {"schemaVersion": "steward-ledger-v1", "generation": 0, "runs": {}, "leases": {}, "work": {}, "lane": None}
```

Document (`steward-ledger-v1`): `generation` (+1 per write), `updatedAt`,
`runs{runId: RunRecord}`, `leases{key: {holder, acquiredAt, expiresAt}}`,
`work{debtId: WorkItem}`, `lane` (the existing `lane_document()` payload — the
shared Class B lane). RunRecord carries: `runId, mode, trigger, startedAt,
sourceHead, integrationBranch, integrationHead, phase, status, steps[],
agentAssignments[], leases[], branches[], pullRequests[], proofArtifacts[],
ciResults[], receipts[], decisions[], unresolvedWork[], nextAction`.
WorkItem carries `debtId, routine, authority, state, assignments[{role,
agentId, model, effort, tokensIn, tokensOut, costUsd}], branch, pullRequest,
proof, history[]` with `state ∈ {queued, building, proposed, verified,
no_change, blocked, escalated, landed, resolved}`.

## 6. Full runner (S7) — `src/gaia_cli/steward/fullrun.py`, `landing.py`

Phases: `recover → reconcile → observe → triage → class_a → class_b → verify
→ reobserve → retro → report → done`. Modes select phases:

| Flag | Phases |
|---|---|
| (none) | all |
| `--observe` | recover, reconcile, observe, report |
| `--triage` | + triage |
| `--routine N` / `--debt ID` | all, triage restricted |
| `--verify` | recover, verify, reobserve, report |
| `--retro` | recover, retro, report |
| `--status` | read-only view of ledger + local state |
| `--resume RUN` | continue RUN from its recorded phase |
| `--afk` | founder decisions queue silently; never prompts |

Rules:

- One active run per ledger: lease `run` (TTL, renewable). A second invocation
  observes the holder and reports it; it does not duplicate work.
- Every step has a deterministic `stepId` and `idempotencyKey`; a step marked
  `done` is never re-executed on resume. External writes (branch push, PR) are
  recorded *intent first*, then confirmed; resume checks for existence before
  repeating.
- The runner emits **actions** for anything requiring a model or a forge it
  cannot reach: `agent.build`, `agent.verify`, `forge.open_pr`,
  `forge.await_ci`, `lead.integrate`, `founder.decide`. The driver performs
  them and calls `gaia steward full record RUN STEP --json-input FILE`.
- Class B honours the existing lane caps (`maxInFlight`, `maxAttempts`,
  `cooldownSeconds`, `maxDispatchesPerRun`) computed over the **shared** lane in
  the ledger. Verifier identity must differ from builder identity; the record
  call refuses a same-agent verdict.
- Class A landing: repair in a fresh `git worktree` at the integration branch
  head using the existing executor, verify parity, commit on
  `steward/a/<kind>-<fingerprint12>`, push, emit `forge.open_pr` targeting the
  configured integration branch. Code floor: refuses `main`/the default branch
  as target and any path outside the executor's writable path.
- Terminal work states are distinct: `no_change, proposed, verified, blocked,
  escalated, landed, resolved`. `resolved` only after re-observation shows the
  debt resolved.

## 7. File ownership (disjoint)

| Worker | Writable files |
|---|---|
| S1 | `steward/primitives/pyast.py`, `steward/sensors_code.py`, `tests/steward/test_sensors_code.py` |
| S2 | `steward/sensors_tests.py`, `tests/steward/test_sensors_tests.py` |
| S3 | `steward/sensors_security.py`, `tests/steward/test_sensors_security.py` |
| H1 | `steward/sensors_ci.py`, `tests/steward/test_sensors_ci.py` |
| H2 | `steward/sensors_contracts.py`, `tests/steward/test_sensors_contracts.py` |
| S4 | `steward/controller.py`, `steward/models.py` (Receipt only), `steward/sensors.py` (trust sensor only), `tests/steward/test_controller_resolution.py`, `tests/steward/test_trust_calibration_regression.py` |
| S6 | `steward/ledger.py`, `tests/steward/test_ledger.py` |
| S7 | `steward/fullrun.py`, `steward/landing.py`, `steward/desk.py`, `commands/steward.py` (`full` subcommand only), `tests/steward/test_fullrun*.py` |
| Opus | `POLICY.yaml`, `default_sensors()` registration, `routine-coverage.json`, checker, founder docs, skills, workflows, integration |

## 8. Worker rules

- Work in your isolated worktree on branch `feat/steward-full-<lane>` created
  from `origin/dev/gaia-steward-full`. Commit and push after each logical unit.
- Run your focused tests before every push and report exact results.
- Never merge, never push to `dev/*` or `main`, never edit files outside your
  row, never edit `POLICY.yaml` or `.gaia/steward/`, never weaken a test.
- Never spawn further agents.
- Report: branch, final SHA, files, test command + result, live-repo scan
  result of your sensors (count of findings per kind on the real tree), known
  limitations.
