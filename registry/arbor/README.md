# registry/arbor/ — Arbor I

Arbor I is the **behavioral Tree** of the Gaia capability graph
(`founder/ENDGAME.md` §4–§8). It answers:

> *What does this capability do to an agent, and what happens when it interacts
> with other capabilities?*

Its conceptual domain is Heaven behavior, Hell behavior, Ultra behavior —
convergence, exploration, trajectory spread, outcome stability, recoverability,
churn, endurance, behavioral compatibility and interaction edges.

## Governing structure and index

- **Dominant structure:** the Hell-Heaven behavioral graph.
- **Dominant index:** the Hell-Heaven (HH) Index (WIP; lives in `gaia-research`).
- **Observations:** benchmark receipts and runtime measurements.

## No stars, no ranks

Arbor does not have stars. Arbor does not have ranks. It does not award prestige
because a numerical score is high. Capability and behavior govern its topology —
raw capability only. Where other Trees carry rank or trust grades, those are not
read here; only benchmark receipts move an Arbor entry.

## Projections differ, identity stable

The Yggdrasil projection is governed by taxonomy/fusion/rank/prestige; the Arbor
projection by behavioral polarity, capability effect, interaction edges,
recoverability and benchmark coverage. A skill may visibly "move" when switching
Trees. This is intentional: the projection has changed; the identity has not.

## Blank canvas

This directory is a **blank canvas**: zero entries today.

`stamps.jsonl` carries only its leading comment line. Entries land only after
R2 benchmark receipts exist — no hand label becomes an entry, because hand labels
are predictions, never results.

## Planned entry shape (`arbor/v0`) — for future entries only

Each future JSONL entry will carry:

- `schema`: `"arbor/v0"`
- `skillId`: canonical skill identity (shared across all Trees)
- `contentSha256`: sha256 of the skill's `SKILL.md` at receipt time
- `stamps`: object, multiplicative per the T9 ruling:
  - `heavenNative`: bool
  - `hellSafe`: tier object (tier + environment qualifiers)
  - `ultraReady`: bool
  - multiple stamps may hold simultaneously
- `primaryStamp`: exactly one declared PRIMARY stamp per entry (T9)
- `denyListed`: optional bool / status field (T8 publish-class deny-list,
  rung-independent)
- `evidence.ledgerRefs`: array of references into the hell-heaven-bench ledger;
  **must be non-empty for every real entry** once entries land. No receipt,
  no entry.

Predictions about which stamps skills will receive live in `SEED-MAPPING.md`
and are marked as predictions there. They are inputs to labeling, never entries.
