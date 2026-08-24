# registry/arbor/ — Arbor I

Arbor I is the **behavioral Tree** of the Gaia capability graph
(`founder/ENDGAME.md` §4–§8). It answers:

> *What does this capability do to an agent, and what happens when it interacts
> with other capabilities?*

Arbor is a rankless projection of empirically measured behavior. It has no
stars, ranks, Trust Magnitude, trust grades, or prestige fields. Those values
are rejected at the ingestion boundary rather than ignored.

## Ownership boundary

Gaia Research owns trial execution and decision production. Gaia Skill Tree
owns validation, immutable acceptance, and projection. Tree does not import
Research source code. The cross-repository boundary is the narrow
`hh-stamp/v1` JSON contract in `registry/schema/hh-stamp.schema.json`.

The receiving contract is intentionally defined here while Research Workstream
A pre-registers execution and has not yet published `hh-stamp/v1`. It follows
Issue #190 and PR #191's frozen principles: exact content identity, exact rung
metadata outside `hh-ledger/v1`, retained receipts, and no stamp before the
pre-registered decision rule passes. This contract does not claim that a trial
has run.

## Source of truth and projection

- `sources/<sha256>.json` is the immutable, digest-addressed source of truth.
  Each file is canonical JSON for one accepted Research bundle. The filename is
  the SHA-256 of those canonical bytes.
- `stamps.jsonl` is a generated projection. Its rows sort by stable `skillId`,
  use canonical JSON bytes, and end with exactly one LF. Never edit rows by
  hand.
- `registry/schema/arborStamp.schema.json` validates projected rows. Canonical
  and wheel-bundled schema copies are synchronized by
  `python scripts/sync_bundled_schemas.py`.

Every decision binds a stable canonical skill identity to the SHA-256 of the
**exact raw `SKILL.md` bytes** at trial time: 64 lowercase hexadecimal
characters, with no newline, Unicode, or other normalization. Every decision
also carries a nonempty set of immutable `hh-ledger/v1` record digests and the
immutable Research `sourceDigest`.

## Decision semantics

Stamps are multiplicative. `heaven-native`, `hell-safe`, and `ultra-ready` may
coexist, but an accepted decision names exactly one accepted stamp as PRIMARY.
`hell-safe` includes an exact rung (`low`, `med`, `high`, `xhigh`, or `max`) and
closed environment qualifiers for network, filesystem, sandbox, approval, and
cost conditions.

Deny status is explicit and rung-independent. A denied skill cannot be
`hell-safe`, although a measured decision may retain another accepted stamp.

`no-stamp` is not missing research. It is an explicit empirical decision with
nonempty ledger receipts and deny status. It carries neither stamps nor a
PRIMARY stamp. Inconclusive, mixed, or underpowered cells may produce this
outcome only when valid measured records exist. Missing, unavailable, or
invalid-only research cannot cross this acceptance boundary.

## Operator commands

```bash
# Mutating; requires normal Verifier/operator authorization
gaia dev arbor import path/to/hh-stamp-v1.json
gaia dev arbor replay

# Read-only; no operator authorization required
gaia dev arbor check
```

`import` validates all retained state, the complete incoming bundle, and the
complete future projection before writing. A malformed, duplicate, or
conflicting bundle leaves canonical files byte-unchanged. Re-importing the same
bundle is idempotent.

`replay` regenerates only `stamps.jsonl` from retained bundles. `check` validates
retained bundles and detects projection drift without rewriting it. The normal
`gaia dev validate` path also runs the read-only Arbor check.

## Current state

There are **no real Arbor decisions yet**. `stamps.jsonl` contains only its
generated-file header and `sources/` contains no bundle. `SEED-MAPPING.md`
remains predictions only. Valid synthetic records exist solely in tests; no R1
prediction is treated as an R2 result.
