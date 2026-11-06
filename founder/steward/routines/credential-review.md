# Routine — Credential review

| | |
|---|---|
| **Policy rule** | `credential-review-disposition` |
| **Sensor** | `secret-scan` — credential-shaped strings, stored only as a fingerprint |
| **Debt kind** | `credential_review` |
| **Authority** | Class B — draft a record, an independent verifier signs |
| **Cadence** | Every scan |
| **Decision** | `steward-credential-reconciliation-2283` (founder rulings 2026-11-06 and its follow-up) |

---

## What it is for

A file lands here, not on the founder desk, only when no undecided finding in it
is evidence of a live credential: no issuer-format token (`ghp_`, `AKIA`,
`sk-ant-`, `xox[bp]-` and the like), no structurally valid JWT, no private-key
body, no opaque high-entropy value. The sensor decides this from the matched
value, never from the path. A mirrored or `tests/` file with a live-shaped value
stays Class C; a `src/` file with a variable reference lands here.

The work is a disposition record per finding, nothing else.

## Envelope to grant

The `POLICY.yaml` rule is authoritative; this guide cannot widen it.

- **May write:** `founder/steward/security-dispositions/**` only.
- **Never writes:** any source file, test, workflow, policy, decision or receipt.
  Nothing is rotated, revoked or edited.
- **May run:** `python scripts/steward_credential_disposition.py draft <debt id> --write`,
  `python scripts/check_security_dispositions.py`, the disposition tests.

## Procedure

1. Run the draft helper for the debt. It prefills path, pattern, fingerprint,
   occurrence and the sha256 of the normalized line.
2. Read the flagged line and its callers. Pick the locked policy: D1 mirrored
   Firecrawl/Impeccable source, D2 test/fixture value, D3 code/workflow/docs.
3. Fill in `policy`, `disposition`, `evidence` (specific, reproducible) and
   `author`. Leave `verifiedBy` and `verifiedAt` empty.
4. Stop and escalate rather than guess if the value could be live.

## Stop conditions

1. The value looks live, or its provenance is ambiguous.
2. The diff would touch anything outside `founder/steward/security-dispositions/`.
3. A record would need `verifiedBy`, or the author equals the verifier.
4. The line or token changed since the debt was observed.

## Independent verification

A different verifier reproduces the evidence for each record, then sets
`verifiedBy` (not the author) and `verifiedAt`. Until then the consumer ignores
the record and the debt stays open. A record binds to the finding's token, its
occurrence and its normalized line, not to the whole file: an unrelated edit does
not reopen it, a changed token or line does.
