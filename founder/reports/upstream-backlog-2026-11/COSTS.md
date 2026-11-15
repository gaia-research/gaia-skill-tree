# Campaign usage checkpoints

No budget ceiling; active execution window confirmed by the founder. Values below are estimates, not confirmed invoices or subscription expenditure.

## 2026-11-15 — preflight / P0 start

Source: installed canonical `/pi-cost` v1.10.0, `python3 ~/.pi/agent/skills/pi-cost/scripts/pi_cost.py --offline --json`. Catalog provenance: Gaia skill-cost / LiteLLM; catalog fetched 2026-11-14T14:12:12Z. Snapshot includes 46 completed lead turns and six direct worker receipts (including the failed original Opus lane). Later activity is not yet included.

| Date | Task/role | Model/pricing key | Input | Output | Cache read | Estimate USD | Method |
|---|---|---|---:|---:|---:|---:|---|
| 2026-11-15 | Sol lead | openai/gpt-6.1-sol | 153394 | 26389 | 6156288 | $1.186307 | Pi-recorded lead cost |
| 2026-11-15 | Readiness probes | gemini/gemini-4-hydrogen | 46614 | 1831 | 37566 | $0.086471 | Canonical public-rate worker estimate |
| 2026-11-15 | Readiness probes | gpt-6-luna | 18784 | 79 | 18432 | $0.002102 | Canonical public-rate worker estimate |
| 2026-11-15 | Readiness probes | gpt-6.1-terra | 19302 | 75 | 18816 | $0.020618 | Canonical public-rate worker estimate |
| 2026-11-15 | Readiness probes | claude-opus-5-5 | 30958 | 502 | 30007 | $0.139873 | Canonical public-rate worker estimate |

- Worker public-rate subtotal: $0.249064. Mixed-method observed subtotal including the lead: $1.435371.
- Counters are reproduced as reported by the canonical tool; cache counters are shown separately, not silently summed into an invented token total. No cache writes were reported.
- The initial failed Opus and unintended fallback attempts reported zero usage, which does not establish zero billing. Failed-attempt provider billing remains unverified.
- Known canonical tool limitations: native `subagent_wait` receipts can be omitted and repeated native result records can double-count. No wait receipts or repeated result deliveries were intentionally used here. These numbers are not complete provider billing.
- Actual billed cost: unavailable. No private prompts, transcripts, credentials, or raw logs are published.
- In-flight worker usage is unavailable until its receipt is delivered; each push/PR update must state its accounting cutoff and replace this checkpoint with the next measured snapshot when available.

## 2026-11-15 — P0 builder delivered; administration not yet delivered

**Cutoff:** latest completed turns recorded in the parent session, through the delivered Hydrogen builder receipt for commit `6674c8268703f6137f8e4c8067e0be7ca73bd378`. Canonical command: `/pi-cost` v1.10.0 with `--offline --json` and the explicitly selected parent-session file. This is a session snapshot, not a complete billing ledger. Catalog provenance remains Gaia skill-cost / LiteLLM, source `BerriAI/litellm` model price catalog fetched `2026-11-14T14:12:12Z` (not stale at calculation).

Sanitized totals below are grouped by date/provider/model/task. No tasks, prompts, transcripts, logs or private paths are included. Token counters are shown separately; cache reads are not added to input. Estimates use the catalog public rates for workers and the session-recorded harness cost for Sol.

| Date | Provider / model | Task | Input | Output | Cache read | Estimate USD |
|---|---|---|---:|---:|---:|---:|
| 2026-11-15 | openai / gpt-6.1-sol | campaign administration (lead session) | 158796 | 34998 | 7577344 | 1.425306 |
| 2026-11-15 | antigravity / gemini-4-hydrogen | readiness probes + P0 builder | 311839 | 45531 | 2663038 | 1.008968 |
| 2026-11-15 | openai / gpt-6-luna | readiness probe | 18784 | 79 | 18432 | 0.002102 |
| 2026-11-15 | openai-codex / gpt-6.1-terra | readiness probe (not P0 review) | 19302 | 75 | 18816 | 0.020618 |
| 2026-11-15 | antigravity / claude-opus-5-5 | readiness probe | 30958 | 502 | 30007 | 0.139873 |

- Delivered mixed-method subtotal: **$2.596868** (Sol session-recorded cost plus priced worker estimates). Hydrogen rows aggregate three completed receipts; only the successful P0 builder receipt includes implementation work. This does not include current in-flight administration, whose usage is unavailable until delivery.
- Failed initial probe reports zero measured usage; this does not establish zero provider billing. No speculative estimate is assigned to it.
- Tool scope limitations still apply: `subagent_wait` receipts may be omitted and repeated native result records may double-count. This snapshot cannot certify provider charges. Actual billed cost remains unavailable.

## 2026-11-15 — first Terra findings and correction-round-1 cutoff

**Cutoff:** canonical `/pi-cost` v1.10.0 run offline with `--json` against the explicitly designated campaign parent session. This snapshot includes first Terra review of `6674c826`, builder correction round 1 at `11405f2`, and the completed administration represented in that session. It does not include future or currently in-flight administration/review. The designated session path and prompts are intentionally omitted from this public record.

| Date | Provider / model | Task grouping | Input | Output | Cache read | Estimated USD |
|---|---|---|---:|---:|---:|---:|
| 2026-11-15 | openai / gpt-6.1-sol | lead campaign session | 162980 | 42467 | 8713216 | 1.621952 |
| 2026-11-15 | antigravity / gemini-4-hydrogen | preflight + P0 builder + correction round 1 | 525172 | 75479 | 4533382 | 1.693854 |
| 2026-11-15 | openai / gpt-6-luna | preflight + campaign administration/configuration | 98548 | 6441 | 532608 | 0.018401 |
| 2026-11-15 | openai-codex / gpt-6.1-terra | roster probe + independent first review | 127136 | 4002 | 688640 | 0.181578 |
| 2026-11-15 | antigravity / claude-opus-5-5 | readiness probe | 30958 | 502 | 30007 | 0.139873 |

- **Measured mixed-method subtotal: $3.655659** (Sol's harness-recorded cost plus direct worker estimates). Canonical catalog provenance: LiteLLM public model-price catalog (`BerriAI/litellm`), fetched 2026-11-14T14:12:12Z, marked not stale by the offline tool; worker values are estimates from public rates, not invoice amounts.
- The table groups the reported direct-worker work by model/task; cache-read tokens are separate from input and not summed into it. Cache-write count was zero in the report.
- The previous mixed-method checkpoint was $2.596868; the current measured session snapshot is the authoritative cutoff here, not an additive invoice. Actual provider/subscription billing remains unknown. Any administration or independent second review still in flight is unavailable and is excluded; do not infer zero cost.

## 2026-11-15 — P0 census collection & doc-only correction 2 cutoff

**Cutoff:** canonical `/pi-cost` v1.10.0 (`--offline --json`) run against the explicitly designated campaign parent session after delivery of the Luna P0 census collection receipts. Includes 59 completed lead turns and 13 direct worker receipts (no nested or explicit AGY receipts). Does **not** include the in-flight doc-only correction 2 / baseline-package administration or pending final Terra doc-only review. Private session path, prompts, and raw logs are omitted.

| Date | Provider / model | Task grouping | Input | Output | Cache read | Estimated USD | Method |
|---|---|---|---:|---:|---:|---:|---|
| 2026-11-15 | openai / gpt-6.1-sol | lead campaign session (59 turns) | 170285 | 50051 | 9306496 | $1.771730 | Pi-recorded lead cost |
| 2026-11-15 | antigravity / gemini-4-hydrogen | preflight + P0 builder + correction round 1 | 525172 | 75479 | 4533382 | $1.693854 | Canonical public-rate worker estimate |
| 2026-11-15 | openai / gpt-6-luna | preflight + campaign admin + P0 census collection | 173739 | 10183 | 1183104 | $0.034296 | Canonical public-rate worker estimate |
| 2026-11-15 | openai-codex / gpt-6.1-terra | roster probe + independent first review | 127136 | 4002 | 688640 | $0.181578 | Canonical public-rate worker estimate |
| 2026-11-15 | antigravity / claude-opus-5-5 | readiness probe | 30958 | 502 | 30007 | $0.139873 | Canonical public-rate worker estimate |

- **Measured mixed-method subtotal: $3.821332** (`$1.771730` Sol harness-recorded cost + `$2.049602` canonical public-rate worker estimates).
- **Rate provenance:** Gaia `skill-cost` / `BerriAI/litellm` public model-price catalog, fetched `2026-11-14T14:12:12Z` (`stale: false` in offline check). Values are estimates only; actual provider/subscription billing remains unknown.
- **Counters & caveats:** `cacheRead` is shown separately from `input`; `cacheWrite` was `0` across all rows. The initial failed `gemini-4-hydrogen:medium` probe reported `0` measured usage (provider billing remains unverified). In-flight administration (this doc-only correction 2 & baseline package) and subsequent Terra reviews are excluded until delivered; do not infer zero cost.
