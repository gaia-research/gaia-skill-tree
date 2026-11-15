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
