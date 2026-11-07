# Founder decision records

One JSON file per open founder decision that is **not** produced by a sensor:
a product, ontology, or policy question someone has to answer. The Steward
founder desk (`src/gaia_cli/steward/desk.py`) reads every `*.json` file in this
directory; each record whose `status` is `open` appears under
`NEEDS YOUR DECISION`. The scoped issue-family lock consumer also reads the four
`issue-question-q-*.json` records described below; the existing #2283 marker document
is an explicit prerequisite, not a decision record.

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
| `status` | string | `open` appears on the desk as a pending decision; `decided` is history, except a `decided` record with `resolution: approved` and no `landedIn`, which `gaia steward founder` lists as approved-awaiting-landing (see below) |
| `resolution` | string | optional, non-empty; `approved` marks a founder approval (see below), any other value is interpreted only by an explicitly scoped consumer |
| `landedIn` | string | optional, non-empty; the PR, commit or release where an `approved` record's change landed |
| `decision` | string | the question, stated once, non-empty |
| `whyItMatters` | string | non-empty |
| `evidence` | list of strings | facts, not opinions; may be empty |
| `recommended` | string | the answer you would give, non-empty |
| `alternative` | string | the next-best answer, non-empty |
| `unblocks` | string | what moves once this is decided, non-empty |
| `links` | list of strings | issue, PR, or repo-relative path; may be empty |

Exactly the required keys above plus optional `resolution` and `landedIn`: an unknown or missing
required key makes the record malformed.

## Lifecycle

1. Add `<id>.json` with `"status": "open"`.
2. When the question is answered, set `"status": "decided"` (keep the file as
   the audit trail) and put the ruling where it belongs (RATIFICATION, issue,
   policy).

## Locked issue families (#2283)

C1–C4 are final founder rulings, not requests to re-adjudicate them. Their records
use `id: issue-question-q-<hash>` and preserve the exact `issue-question/q-<hash>`
target in both `links` and `evidence`, the source debt ID in `evidence`, affected
issue links and the founder authority comment. No extra schema fields are used.

`issuehygiene/questions.py` validates these mappings and recognizes only the four
explicit resolutions. The sensor, dry-run CLI and closure executor's independent
re-derivation all load them. Reconciliation removes only the answered question;
unrelated new questions remain Class C. C1 permits a technical-only B proposal
without closure or release acceptance. C2/C3/C4 and their held descendants are
`held`/`none`, not actionable batches or closure proposals. A generic
`upstream:needs-info` label also prevents a non-C item from becoming actionable.
The existing `founder/steward/FOUNDER_LOCK_2283.md` implementation boundary or
any canonical lock record enables the complete lock contract: that marker document
must be a file and all four mapped records must be finalized and valid. Missing or
renamed marker documents and missing, renamed, open, malformed or mismapped records
refuse reconciliation; they cannot silently remove final authority.
Unrelated fresh checkouts without
that document or any canonical lock record retain ordinary reconciliation and
do not acquire these rulings. The manifest retains each source body digest and
cites the decision record; it does not rewrite issue or registry payloads.

These records do **not** decide `steward-issue-closure-authority.json`, change
`writesEnabled`, activate workflows or update a live ledger. Old persisted debt
requires a separate authorized re-observation before its queue state can change.

## Frozen post-freeze history acknowledgements (#2283 S7)

A frozen skill's timeline is append-only, so rank events recorded after its
freeze can never be repaired. `frozen_skill_drift` reports them until a founder
acknowledges them with an ordinary decision record (no extra schema fields):

- file and `id`: `steward-frozen-history-<skill id lowercased, "/" -> ".">`,
  e.g. `steward-frozen-history-mattpocock.diagnose.json`;
- `status: decided` and `resolution: acknowledged`;
- one `evidence` line per acknowledged event, exactly
  `postFreezeEvent <skill id> <timestamp> <action> sha256:<digest>`, copied from
  the event's `acknowledgementLine` in the sensor's `postFreezeHistory`. The
  digest covers the event's whole content, so a different event that happens to
  share the timestamp and action is not acknowledged; two byte-identical events
  need two copies of the line.

Each event is matched exactly, so a later post-freeze event is reported again. A
malformed, open or differently resolved record acknowledges nothing. A stored
level that differs from the frozen level is never acknowledged this way; it stays
a founder decision. Steward never writes these records.

## `gaia steward founder`

`gaia steward founder` lists the same records `gaia steward full` does, in three groups:

- **Pending** (`status: open`): decisions waiting for a ruling. They count toward "Decisions for you".
- **Approved, awaiting implementation or landing** (`status: decided`, `resolution: approved`, no `landedIn`):
  the founder has ruled, no new decision is needed, but the change is not yet recorded as landed. Set
  `landedIn` once it has.
- **Cannot be read**: malformed records, never dropped silently.

The command prints "Nothing requires a decision." only when all three groups and the Class C queue are empty.
`--json` carries the same grouping under `decisionRecords`.

## Malformed records

A record that cannot be read, fails the format above, has an `id` that does not
match its file name, or duplicates another `id` never crashes the desk and is
never dropped silently. It is shown under `OPERATIONS` as
`invalid_decision_record` so it gets fixed or removed.

Never put credentials or secret text in a record; the desk prints these fields
verbatim.
