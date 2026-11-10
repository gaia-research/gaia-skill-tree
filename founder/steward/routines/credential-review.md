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
EVERY undecided finding's ENTIRE matched value is, by syntax, a variable or
environment reference (`${NAME}`, `$NAME`, `process.env.NAME`, `secrets.NAME`,
`{{ template }}`, `<slot>`), such a reference followed by a hostname tail
(`${NAME}@host.tld/...`), an identifier path the source then calls or indexes,
a documented placeholder made only of placeholder words (`YOUR_API_KEY`,
`FAKE-TOKEN`, `xxxx`), or a short common placeholder word. A marker, `env` or
`getenv` merely appearing inside a longer value proves nothing and stays Class C,
as do opaque values, passphrases, truncated tokens, issuer-format tokens, valid
JWTs and private keys, whatever their entropy. The sensor decides from the
matched value, never from the path, and there is no `tests/` or mirror skip: an
issuer-shaped match under `tests/` is Class C until a per-finding record decides it.

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
   occurrence and the stable-source-context hash.
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

A record binds to the finding's token, its occurrence and its stable source
context: the token's line, the two non-blank lines either side, and the chain of
enclosing less-indented block headers (the function or class around it). Only
edge ASCII whitespace and CR/LF are ignored, so a space or non-breaking space
inside the line counts. It does not bind to the whole file: an edit outside that
window and scope does not reopen it; a changed token, line, window or enclosing
scope, or moving the line to another function, does. If two live findings share
pattern, fingerprint and context (identical occurrences) neither is decided, so
make them distinguishable in the source. A record that omits `occurrence` is
malformed and blocks every occurrence of that token.
