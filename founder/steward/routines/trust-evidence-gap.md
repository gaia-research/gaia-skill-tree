# Routine — Trust evidence gap

| **Debt kind** | `trust_evidence_gap` |
| **Authority** | **C** — the founder decides; Steward only discovers and records |
| **Detector** | `trust-calibration-drift` (routine 9) |
| **Ruling** | 2026-10-28 (#2201) and 2026-11-06, option 11A |

## Purpose

A named skill whose effective evidence pool (own rows plus rows inherited from
its generic parent) is empty, or holds only rows that score nothing, is
**unmeasured**, not degraded. The sensor reports it as `trust_evidence_gap`,
preserves the stored level (`observedState.preservedLevel`) and proposes no
demotion, no target level and no calibration command. This replaces the interim
`trust_calibration_drift` + `laneEligible: false` marker.

## The discovery routine (read-only)

```bash
python scripts/steward_evidence_discovery.py plan              # gaps and the bounded search plan; writes nothing
python scripts/steward_evidence_discovery.py record LOG.json   # validate a search log, write one receipt
```

Steward's code never searches. A driver (an agent with web access, or you) runs
the searches and hands over a **search log**; the routine validates it,
annotates it and writes an immutable receipt under the ignored
`.gaia/steward/discovery/`. It never writes `registry/`.

```json
{
  "skillId": "owner/skill",
  "searchedBy": "driver identity",
  "searches": [
    {
      "query": "exact query run",
      "channel": "upstream-repo | benchmarks | papers | releases-usage",
      "searchedAt": "2026-11-07T00:00:00Z",
      "results": [
        {"url": "https://...", "title": "...", "evidenceType": "arxiv",
         "attribution": "who published it", "publishedAt": "2026-05-01", "note": "..."}
      ]
    }
  ]
}
```

- **Negative searches are records.** A search with `"results": []` is stored with
  its query, channel and date. "We looked and found none" is what makes a gap
  confirmable.
- **Bounded.** At most 12 searches per receipt, 10 results per search, 500
  characters per text field. A channel family that was not searched is written
  into `coverage.limitations`.
- **Per candidate**, the receipt records URL, publication date, attribution,
  freshness (`fresh` ≤ 365 days, `aging` ≤ 1095, else `stale`, `unknown` if
  undated), duplicate status (against the skill's existing effective evidence
  and earlier candidates, by canonical URL) and admissibility with reasons.
- **Admissibility is an annotation, never an admission.** `admissible-candidate`
  means a Verifier may propose it. Repository stars, self-attestation, social
  signal and `benchmark-result` rows are `needs-review` with the reason stated
  (stars are not proof of capability by default; benchmark rows are
  catalog-gated).
- **Strict schema.** A log carrying an admission, a level or a trust value is
  rejected, not ignored.

The receipt carries `admittedEvidence: []`, `ratingChange: null` and
`preservedLevel` unconditionally.

## What happens next

- `outcome: candidates-found` — a Verifier reviews the candidates and admits any
  that qualify with `gaia dev evidence` (the event-driven restamp then clears the
  affected stamps in the same PR). Calibration is recomputed from qualifying
  evidence through the canonical engine.
- `outcome: candidates-need-review` — no candidate is admissible yet, but at least
  one needs review (typing, attribution, catalog gating, independence). The gap is
  **not** confirmed; a Verifier resolves the review first.
- `outcome: evidence-gap-confirmed` — no admissible and no reviewable candidate
  (only negative searches or inadmissible results). Keep the current rating and report the gap
  to the founder desk, which shows **one grouped decision** for every open gap.
  A demotion needs actual counter-evidence or supersession under #2148, never an
  empty pool.

## Debt identity migration

`trust_evidence_gap` has a different kind than the debts it replaces, so its id
differs. When the sensor first reports a gap for a subject that has a
`trust_calibration_drift` debt **that carried the interim evidence-gap marker**
(`evidenceGap: true`, no target level), the ledger records the link in both
directions and loses nothing. A drift debt for genuine prior drift (it has a target
level) is a different finding and is never linked or resolved by the migration: the new debt carries `supersedes: [old id]`, the old debt is
resolved with `resolution: superseded` and `supersededBy: new id`. The old debt
and its receipts stay in the ledger. If real drift later returns for the same
subject, the old debt reopens normally and its `supersededBy` link is cleared.
