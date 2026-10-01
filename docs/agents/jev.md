# Budgeted Jev Advisory Lane

A bounded, read-only semantic advisory sidecar for Gaia workflows, backed by TypeSafe AI's System One (`jev-1.13.0`) and grounded by an actionable fallback to `worker-luna`.

## Overview & Architecture

Prior to repository integration, Jev advisory existed solely as a user-installed personal agent skill. This integration provides a repository-native, bounded, read-only sidecar harness for Gaia workflows.

Jev operates strictly as a non-authoritative read-only sidecar. It assists with generic capability mapping, issue triage, upstream release analysis, and evidence review without altering deterministic checks, registry data, or human authority.

- **Sidecar Mapping Remains Backwards Compatible:** The existing `scripts/jev_advisory.py` sidecar runner (`--mode mapping`, report to `generated-output/jev/report.json`) remains fully supported and backwards compatible for auxiliary shortlist advisory and external triage workflows.
- **Optional `gaia dev assess` Semantic Assessment Path:** The new CLI assessment command (`gaia dev assess <packet.json> [--jev live]`) provides an optional, structured semantic evaluation against the versioned curation principles rubric (`principles.json`), writing a durable principles assessment receipt (`generated-output/curation/<candidate>.assessment.json`). This assessment is an optional semantic analysis path and NOT a deterministic decision authority. Machine assessments default to unknown semantics when signals are absent or ambiguous, never auto-ratify topology, and require explicit human review authorization at L4.
- **Zero Registry Mutation:** Jev never modifies files under `registry/`, never re-ranks or overrides deterministic prefill outputs, and never sets stars.
- **Zero Authority Expansion:** All human ratification gates (L4 curation review, PR review, issue assignment) remain mandatory.
- **No Replacement of Deterministic Systems:** Jev advisory does NOT replace Gaia Steward sensors or runtime reconciliation, does NOT replace HTTP liveness checks or `validate_sources.py`, does NOT replace Phase 2B benchmark verification, and does NOT replace deterministic prefill or Trust Magnitude math.
- **Strict Budget Bounding:** Enforces local and CI spend limits against a \$5.00/month account envelope.
- **Real Luna Handoff:** If confidence is below 0.75, an outcome is uncertain, the budget is exhausted, or credentials are unset, the runner outputs a structured fallback packet for `worker-luna`. Luna is an actual reasoning agent; a fallback is a bounded handoff packet for Luna, never a fake assertion that Luna ran.

## One-Minute Quickstart (Offline / $0 Spend)

By default, all commands execute in offline / dry-run mode ($0 spend) without requiring an API key. You can safely exercise the advisory runner immediately using the repository's native discovery packet fixture:

```bash
python scripts/jev_advisory.py --mode mapping --input tests/fixtures/discovery-packet-v2-valid.json
```

This writes an evaluation report to `generated-output/jev/report.json`.

### Consuming the Luna Handoff

The advisory runner does NOT launch an agent, invoke external processes, or spawn sub-agents. When running offline (default), or when live confidence falls below 0.75, or budget/Flash quota is exhausted, each evaluated item includes an actionable handoff under `.fallback`:

```json
{
  "candidateId": "testcontrib/test-skill",
  "name": "Test Skill",
  "advisoryShortlist": [
    "research"
  ],
  "advisoryShortlistIncomplete": false,
  "status": "fallback",
  "reason": "dry_run",
  "advisoryResult": null,
  "fallback": {
    "agent": "worker-luna",
    "instruction": "Evaluate state with questions using worker-luna reasoning (dry run mode active)."
  },
  "usage": {},
  "estimatedCostUsd": 0.0,
  "reservedUsd": 0.0
}
```

Human operators or higher-level orchestrators can inspect this report and provide the structured `fallback` context directly to Luna reasoning agents when automated sidecar advisory is unavailable, low confidence, or depleted. Route based on task complexity:
- **`worker-luna`** (medium): Standard candidate mapping, duplicate triage, and routine PR/issue review.
- **`worker-luna-high`**: High-complexity candidate evaluations, ambiguous capability taxonomies, or conflicting evidence triage.
- **`worker-luna-xhigh`**: Deep architectural review, structural ontology changes, or contested policy decisions.

*Note: The advisory tool emits this structured handoff packet for consumption by the user or harness orchestrator; it never automatically spawns or executes fallback agents.*

## Pricing and API Specifications

Data from official TypeSafe System One documentation (`https://api.typesafe.ai/v1/systemone`):

- **Model:** Pinned to `jev-1.13.0`.
- **Pricing:** \$0.042 per million input tokens; output tokens are free.
- **Context Maximum:** 64,000 input tokens per request.
- **Reservation Floor:** \$0.003 reserved atomically per attempt (conservative upper bound covering the 64k token ceiling).
- **Request Bounds:** Size <= 12,000 UTF-8 bytes; at most 3 Choice questions per request; response <= 128 KB; ~10-second timeout.
- **Deterministic Explanations:** Only routing rationale and probabilities are emitted; no invented generic names or synthetic evidence rows.
- *Note:* Official docs and pricing numbers represent snapshot estimates, not measured cost savings.

## Budget Allocation & Spend Controls

The \$5.00/month provider envelope is allocated across two distinct lanes:

| Lane | Monthly Budget | Cap Mechanic | Max Calls |
|---|---|---|---|
| **CI (GitHub Actions)** | \$3.60 / month | Run-history gate (max 60 runs/month) | 20 calls / run (\$0.06 limit) |
| **Local Developer** | \$0.50 / month | Local state ledger (`.gaia/jev`) | 20 calls / run |
| **Unallocated Buffer** | \$0.90 / month | Margin against provider-side drift | — |

### CI Budget Gate (`scripts/jev_ci_budget.py`)
- CI spend is bounded by GitHub Actions workflow run history, **not** cache keys.
- Fails closed on any API error, malformed JSON, missing current run, or month mismatch.
- Re-runs (`run_attempt > 1`) are strictly forbidden from paid execution.
- Workflows serialize globally (`concurrency: group: jev-advisory-lane, cancel-in-progress: false`).
- Default-branch only (`main`); no pull request triggers.

### Known Spend Limitations
- **External usage:** Spend on the same API key from third-party tools or separate repositories cannot be observed by this repository's run history. We have not inspected provider hard-limit documentation; configure account spend caps in your provider account settings if supported by the provider, rather than assuming provider dashboard hard enforcement.
- **Run-history deletion:** Deleting workflow run history in GitHub Actions resets the run counter. Enforce strict repository administrative permissions.
- **Multiple Local Ledgers / Worktrees:** Separate git checkouts or worktrees maintain independent local state directories (`.gaia/jev`) by default and do not automatically aggregate spend counters. Operators working across multiple worktrees should specify a single shared directory using `--state-dir` (for example, `--state-dir ~/.gaia/jev`) to maintain a unified local budget ledger.

## Setup and Credentials

### GitHub Actions Configuration
1. **Repository Secret (Required for Live Calls):**
   - Navigate to **Settings** > **Secrets and variables** > **Actions**.
   - Click **New repository secret**.
   - Name: `TYPESAFE_API_KEY`.
   - Value: Paste the API key.
   - *Via GitHub CLI:* `gh secret set TYPESAFE_API_KEY` (reads key securely from stdin; never pass secrets in shell arguments or commit them).
2. **Repository Variable (Optional for Scheduled Runs):**
   - In **Settings** > **Secrets and variables** > **Actions** > **Variables**, add `GAIA_JEV_ENABLED=true` to enable weekly scheduled live runs. By default, scheduled runs execute in dry-run mode.
3. **Manual Trigger:**
   - Under GitHub Actions, select the **Jev Advisory Lane** workflow.
   - Click **Run workflow**, set `live: true`, and launch on `main`.

### Local Developer Setup
To use Jev advisory locally:
```bash
# Sourcing local credentials explicitly (repo-local, gitignored, mode 0600):
# (Do NOT commit .gaia/jev/local.env or pass credentials in command-line arguments)
set +x; source .gaia/jev/local.env  # In bash
# or in POSIX sh: set +x; . .gaia/jev/local.env

# Alternatively, prompt securely without saving secrets into your shell history:
read -rs TYPESAFE_API_KEY; export TYPESAFE_API_KEY

# 1. Initialize the monthly budget ledger (required before first live call)
python scripts/jev_advisory.py --mode mapping --init-budget

# 2. Run advisory in offline/dry-run mode (default, $0 spend)
python scripts/jev_advisory.py --mode mapping --input tests/fixtures/discovery-packet-v2-valid.json

# 3. Run advisory in live mode (requires initialized budget and key; add --live)
python scripts/jev_advisory.py --mode mapping --input tests/fixtures/discovery-packet-v2-valid.json --live
```
By default, all commands execute in offline / dry-run mode ($0 spend). No network calls occur unless `--live` is explicitly passed, `TYPESAFE_API_KEY` is present in the environment, and a valid budget ledger exists. The runner does not automatically load credential files; operators must explicitly export or source their credentials into the process environment.

## Integration Matrix: 6 Modes & 8 Skills

The advisory runner provides 6 operational modes integrated across 8 Gaia skills:

| Mode | CLI Invocation | Primary Integrating Skills | Description |
|---|---|---|---|
| `mapping` | `python scripts/jev_advisory.py --mode mapping --input <packet.json>` | `gaia-curate`, `gaia-draft-curate`, `jev-advisory` | Evaluate candidate discovery packet against vendor-neutral generic shortlist |
| `issues` | `python scripts/jev_advisory.py --mode issues --input <issues.json>` | `gaia-triage`, `jev-advisory` | Triage duplicate issues and recommend P0-P4 priorities |
| `upstream` | `python scripts/jev_advisory.py --mode upstream --input <findings.json>` | `jev-advisory` | Review upstream release diffs and identify changed capabilities |
| `evidence` | `python scripts/jev_advisory.py --mode evidence --input <evidence.json>` | `ev-adversarial-audit`, `jev-advisory` | Flag semantic anomalies in evidence documentation |
| `meta` | `python scripts/jev_advisory.py --mode meta --collect-repo` | `gaia-meta-audit`, `gaia-meta-sweep`, `jev-advisory` | Inspect generic descriptions for vendor neutrality and abstraction scope |
| `steward` | `python scripts/jev_advisory.py --mode steward --input <debt.json>` | `gaia-steward-lane`, `jev-advisory` | External operator review of maintenance debt (strictly outside automated dispatch loop) |

## Runner Modes & Commands

All commands run offline by default ($0 spend). To enable live TypeSafe API calls, add `--live` (requires `TYPESAFE_API_KEY` and initialized budget).

```bash
# 1. Mapping — Evaluate candidate against generic shortlist (offline default)
python scripts/jev_advisory.py --mode mapping --input registry-for-review/discovery-packets/<packet>.json

# 2. Issues — Triage duplicate issues and recommend P0-P4 priorities (offline default)
python scripts/jev_advisory.py --mode issues --input <issues.json>

# 3. Upstream — Review release notes and identify changed capabilities (offline default)
python scripts/jev_advisory.py --mode upstream --input <findings.json>

# 4. Evidence — Flag semantic anomalies in evidence documentation (offline default)
python scripts/jev_advisory.py --mode evidence --input <evidence.json>

# 5. Meta — Identify generic description ambiguity or product coupling
# Uses --collect-repo to inspect canonical generic nodes directly from registry/nodes/
# Supports bounded paging via --offset (default: 0) and --max-calls
python scripts/jev_advisory.py --mode meta --collect-repo --offset 0

# 6. Steward — External operator review of maintenance debt (outside runtime only)
gaia steward scan --json > /tmp/debt.json
python scripts/jev_advisory.py --mode steward --input /tmp/debt.json
```

## Policy Invariants

1. **Gaia Steward Zero-Model Invariant:** Gaia Steward maintenance dispatches run with a hard zero-model budget. Jev advisory is strictly forbidden inside the Class A/B dispatch loop (`gaia steward run`/`dispatch`). An operator may only run `steward` mode as an external preflight before queuing work.
2. **Curation Decision Precedence:** Jev advisory never re-ranks `mappingOptions[]`, never derives `matchTier`, and never alters the 6-rule precedence in `CURATION-CORE.md`. It provides an auxiliary review sidecar presented at L4 human check.
3. **Evidence & Trust Methodology:** Jev does not mark evidence verified, does not validate URLs, and never touches Trust Magnitude scoring or Star Bar requirements.
