# Founder decision records

One JSON file per open founder decision that is **not** produced by a sensor:
a product, ontology, or policy question someone has to answer. The Steward
founder desk (`src/gaia_cli/steward/desk.py`) reads every `*.json` file in this
directory; each record whose `status` is `open` appears under
`NEEDS YOUR DECISION`. Nothing else in this directory is read.

Records are for questions a person raises on purpose. Questions Steward
discovers itself (Class C debt, escalated lane entries) reach the desk
automatically and need no file here.

## Format

File name `<id>.json`; the `id` inside must equal the file stem.

```json
{
  "schemaVersion": "steward-decision-v1",
  "id": "ship-gate-advisory",
  "status": "open",
  "decision": "Should the ship gate block on a red dependency advisory?",
  "whyItMatters": "A red advisory today ships silently.",
  "evidence": ["advisory run 41", "two incidents last month"],
  "recommended": "Block, with a label override.",
  "alternative": "Warn only.",
  "unblocks": "The release workflow rewrite.",
  "links": ["https://github.com/gaia-research/gaia-skill-tree/issues/0000"]
}
```

| Field | Type | Rule |
|---|---|---|
| `schemaVersion` | string | exactly `steward-decision-v1` |
| `id` | string | lowercase `[a-z0-9][a-z0-9._-]*`, equals the file stem, unique |
| `status` | string | `open` appears on the desk; `decided` is kept as history and never shown |
| `decision` | string | the question, stated once, non-empty |
| `whyItMatters` | string | non-empty |
| `evidence` | list of strings | facts, not opinions; may be empty |
| `recommended` | string | the answer you would give, non-empty |
| `alternative` | string | the next-best answer, non-empty |
| `unblocks` | string | what moves once this is decided, non-empty |
| `links` | list of strings | issue, PR, or repo-relative path; may be empty |

Exactly these keys: an unknown or missing key makes the record malformed.

## Lifecycle

1. Add `<id>.json` with `"status": "open"`.
2. When the question is answered, set `"status": "decided"` (keep the file as
   the audit trail) and put the ruling where it belongs (RATIFICATION, issue,
   policy).

## Malformed records

A record that cannot be read, fails the format above, has an `id` that does not
match its file name, or duplicates another `id` never crashes the desk and is
never dropped silently. It is shown under `OPERATIONS` as
`invalid_decision_record` so it gets fixed or removed.

Never put credentials or secret text in a record; the desk prints these fields
verbatim.
