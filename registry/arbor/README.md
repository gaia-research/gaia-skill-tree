# Arbor declaration-first sidecar

Arbor is Gaia Skill Tree's behavioral Tree. This sidecar implements the smallest
useful evidence loop ratified in
[gaia-research/gaia-research#196](https://github.com/gaia-research/gaia-research/issues/196)
(the external `gaia-research` founder/RATIFICATION A1/A2 ruling) and follows this
repo's local [`founder/ENDGAME.md`](../../founder/ENDGAME.md) observation
doctrine: an expert declaration, an optional focused observation, and an
explicit governed interpretation. It does not pre-label skills or create a bulk
coverage campaign.

Canonical skill identity remains outside Arbor and is never rewritten. Every
Arbor source points to the exact canonical `skill.id` and the SHA-256 of its
source file's unmodified bytes. Resolution is deterministic: generic IDs resolve
to exactly one of `registry/nodes/{basic,fusion}/<id>.json`; named
`<contributor>/<slug>` IDs resolve to
`registry/named/<contributor>/<slug>.md`. Current canonical existence and exact
bytes are checked only when admitting a new declaration digest. Once admitted,
the declaration digest plus `contentSha256` pins immutable history: full check,
replay, idempotent re-import, later receipts, governed interpretations, and
generated profiles do not rebind it to moving canonical bytes. Import never
edits canonical nodes, named skills, or a Skill Tree.

## Contracts

Contracts are JSON Schema files under `contracts/` and reject unknown fields.
The original four single-skill contracts are closed and unchanged. Edge
contracts are parallel, not extensions: every edge carries an ordered `from`
and `to` endpoint with its own exact content pin.

1. **`gaia.arbor-expert-declaration/v1`** — one immutable governed declaration,
   identified by `declarationId` and `declaredAt`, with one or more operational
   claims. Each claim has its own `facet`, `conditions`, `rationale`, and
   `authority`. `human-led` and `model-led` are independent, nonexclusive
   facets; both may describe the same skill under different stated conditions.
2. **`gaia.arbor-benchmark-receipt/v1`** — one focused, conclusion-free
   observation targeting one declaration claim. It defines control and
   treatment arms, structured measurements, and provenance. Both arms pin the
   exact task, fixture, and evaluator artifact hashes and must use the same
   closed environment. Measurements may include counts and a stated difference,
   but no interval or threshold is required and no support classification is
   calculated from them.
3. **`gaia.arbor-interpretation/v1`** — a small, explicit curator record that
   records one declaration claim as confirmed, qualified, revised, or
   inconclusive using named receipt digests. It has its own identity, time,
   authority, rationale, and immutable digest. A later
   interpretation must explicitly supersede the active interpretation for that
   claim; parallel active interpretations are rejected.
4. **`gaia.arbor-profile/v1`** — a deterministic generated projection referencing
   exact declaration, receipt, and interpretation digests. Every claim remains
   `expert-declared` unless an explicit governed interpretation source sets it
   to `benchmark-confirmed`, `benchmark-qualified`, `benchmark-revised`, or
   `inconclusive`. The profile exposes the exact active `interpretationSource`;
   receipts alone never classify a claim.
5. **`gaia.arbor-edge-declaration/v1`**, **`gaia.arbor-edge-observation/v1`**,
   **`gaia.arbor-edge-interpretation/v1`**, and **`gaia.arbor-edge/v1`** — the
   separate pairwise chain. It preserves both endpoint IDs and hashes at every
   link, keeps the governed interpretation support enum at four values, and
   keeps the projected edge support enum at five values (including
   `expert-declared`). The seven relation values are exactly:
   `stabilizes`, `amplifies`, `conflicts`, `recovers`, `compresses-after`,
   `unlocks`, and `duplicates`.
6. **`gaia.hh-observation-ref/v1`** and **`gaia.hh-acceptance/v1`** — provenance
   and curator envelopes for the research-owned Hell-Heaven result. No HH
   result payload contract is published here.
7. **`gaia.arbor-runtime/v1`** — one aggregate with verbatim claims, an
   independently absent HH lens, and subject-scoped interactions. An accepted
   HH envelope currently projects `unavailable-unsupported-payload`; the empty
   `absent-no-accepted-record` lens is the only operationally populated HH
   state in this repository.

The edge index uses `gaia.arbor-edge-index/v1`. Its `absenceMeaning` is always
`not-evaluated`: an empty edge set is not evidence that no interaction exists.
The deterministic `edgeKey` includes the complete ordered pair, relation,
`declarationSha256`, and `claimId`; the declaration digest is intentionally
included to prevent colliding claim IDs from different declarations.

Stars, rank labels, Trust Magnitude, grades, trust/prestige fields, and authored
receipt conclusions are rejected recursively. They belong to Yggdrasil or to an
explicit governed Arbor interpretation, not to declaration or observation
sources. Runtime never parses free prose into verdicts, reads Yggdrasil
prerequisite/fusion relations, or calculates HH polarity, units, dimensions,
stamps, or behavioral direction. Unknown payloads and future versions fail
closed. Publication-time `pairApplicable` is not runtime assurance: a consumer
must verify both current endpoint bytes and applicable conditions. The empty
edge index and absent HH lens therefore do not close Arbor G, A, E, or the
human curator evidence gate.

## Programmatic workflow

Use the dynamic developer command. Mutating operations use the existing Verifier
authorization guard; `check` is read-only.

```bash
gaia dev arbor check declaration.json
gaia dev arbor import declaration.json
gaia dev arbor import focused-receipt.json
gaia dev arbor import governed-interpretation.json
gaia dev arbor replay
gaia dev arbor check
```

`import` validates and canonicalizes JSON, computes its SHA-256, then atomically
publishes it under:

```text
registry/arbor/sources/declarations/<sha256>.json
registry/arbor/sources/receipts/<sha256>.json
registry/arbor/sources/interpretations/<sha256>.json
```

Source files are immutable. Re-importing identical bytes is idempotent, including
after the canonical skill evolves. Altered declaration bytes have a new digest
and therefore undergo current canonical admission again; a stale or mismatched
hash is rejected. A digest/file mismatch fails `check`. Before publishing a
declaration, import builds and validates the complete affected profile, including
declaration-ID and claim-ID uniqueness. Before publishing a receipt, it validates
the immutable declaration and claim target. Before publishing an interpretation,
it validates its declaration, claim, receipt sources, and explicit supersession.
Failed preflight publishes no source, so an immutable poison record cannot be
introduced.

`replay` reads only immutable sources and atomically materializes:

```text
registry/arbor/profiles/<skill-id path>/<skill-content-sha256>.json
registry/arbor/edges.json
registry/arbor/runtime/<skill-id path>/<skill-content-sha256>.json
```

The site publisher projects the same deterministic state into
`docs/graph/arbor/edges.json` and `docs/graph/arbor/runtime/`. Its `--check`
path is offline and deletes stale files only inside the Arbor artifact
directory. No generated timestamp is written.

No timestamp is generated, so replay is deterministic. Declaration and
interpretation times are copied from immutable sources. Full `check` recomputes
every profile in memory and fails if an immutable source is altered, a reference
is broken, an interpretation forks, or a generated profile is stale; it does not
compare historical pins to current canonical bytes. Standalone `check <path>`
validates contract/schema integrity and stored references. A declaration digest
already stored identically is checked as history. Only a not-yet-stored
declaration receives the additional current canonical existence/exact-bytes
admission check.

Import, replay, and check share one store-wide lock, so an import cannot race a
replay into a stale overwrite. Replay stages and validates the complete
generation in memory before publication, then uses atomic per-file replacement
and removes stale profiles. This is not a transactional multi-file manifest
switch: a process crash during publication can leave a mix of individually
complete old/new profile files, and a hard crash can leave `.store-lock` behind
for an operator to inspect and remove. A subsequent replay reconciles the set;
validation failures occur before any profile write.

## Interpretation rule

A receipt is an observation linked to a claim, never a verdict. Importing any
number of receipts leaves the generated claim at `expert-declared`. Confirming,
qualifying, revising, or leaving the declaration inconclusive is an intentional
curator action: import a `gaia.arbor-interpretation/v1` record naming the exact
declaration, claim, and receipt digests. Replay then projects that explicit
support and source digest. Changing that support requires another immutable
interpretation that explicitly supersedes the current one. No measurement
threshold, interval, prestige signal, or hidden numerical algorithm can classify
an expert declaration.
