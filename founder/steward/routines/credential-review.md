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

Routing defaults to the founder desk (Class C). A file lands here only when
EVERY undecided finding's matched value is positively benign: a variable or
environment reference, a template placeholder, a code expression or call, a
documented placeholder marker standing alone (`EXAMPLE`, `FAKE`, `xxxx`,
`<...>`, `${...}`), or a short common placeholder word. Opaque values,
passphrases, truncated tokens, anything issuer-format, a valid JWT, a private
key, or a value that merely contains a redaction-like substring stays Class C,
whatever its entropy. The sensor decides from the matched value, never from the
path: a mirrored or `tests/` file with a live-shaped value stays Class C.

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
   `author` (your agent id). Leave `verifiedBy`, `verifiedAt` and
   `verificationReceipt` empty.
4. Stop and escalate rather than guess if the value could be live.

## Stop conditions

1. The value looks live, or its provenance is ambiguous.
2. The diff would touch anything outside `founder/steward/security-dispositions/`.
3. A record would need `verifiedBy` or a receipt, or any receipt would be written.
4. The line or token changed since the debt was observed.

## Independent verification

`verifiedBy` is never self-asserted. A different verifier agent reproduces the
evidence through the dispatch's `agent.verify` step. The lead's integrate step
then records that outcome as a receipt in
`founder/steward/security-dispositions/receipts/<id>.json` (schema:
`founder/steward/credential-verification-receipt.schema.json`) listing each
covered record's reviewed-content hash (`scripts/steward_credential_disposition.py
hash <record>`), and stamps `verifiedBy`, `verifiedAt` and `verificationReceipt`
into the records. The builder's envelope forbids the receipts directory, so it
cannot write one. The consumer accepts a record only when its receipt exists and
is committed, is for this file's `credential_review` debt, names the same
verifier, a different builder equal to `author`, and covers the record's content.

A record binds to the finding's token, its occurrence and its exact line (only
leading/trailing whitespace and CR/LF are ignored; a space or non-breaking
space inside the line counts), not to the whole file: an unrelated edit does not
reopen it, a changed token or line does. A record that omits `occurrence` is
malformed and blocks every occurrence of that token.
