# Arbor declaration-first sidecar

Arbor is Gaia Skill Tree's behavioral Tree. This sidecar implements the smallest
useful evidence loop ratified in
[gaia-research/gaia-research#196](https://github.com/gaia-research/gaia-research/issues/196)
(the external `gaia-research` founder/RATIFICATION A1/A2 ruling) and follows this
repo's local [`founder/ENDGAME.md`](../../founder/ENDGAME.md) observation
doctrine: an expert declaration, an optional focused observation, and an
explicit governed interpretation. It does not pre-label skills or create a bulk
coverage campaign.

## Doctrine (founder review of 2026-11-11; reconciled 2026-11-14, #2440)

- **Membership.** Every canonical Gaia Skill Tree skill, generic or named, is an
  Arbor subject. A skill with no Arbor record has nothing declared yet; it is
  never excluded, and absence is never evidence about its behaviour.
- **Evidence tiers stay distinct.** A *declaration* is an authored, source-backed
  hypothesis (projected support `expert-declared`). An *observation* is a
  conclusion-free receipt. An *interpretation* is an explicit governed curator
  decision. An *earned outcome* (a Hell-Heaven acceptance, a benchmark result)
  is research-owned. None of these is inferred from another, and no Arbor
  record, at any tier, grants permission to invoke a skill or confers a
  Hell-Heaven stamp.
- **Yggdrasil structure is not Arbor behaviour.** A Yggdrasil composition (for
  example a fusion of grilling and ubiquitous language) may be cited in a
  declaration's rationale as the *reason* to hypothesise an interaction. The
  result is still an authored `expert-declared` hypothesis that must stand on
  its own conditions; it never becomes an observed edge, a governed
  interpretation, or an HH result. Edge sources keep rejecting structural
  fields (`prerequisites`, `fusion`, `suiteComponents`, ...), and every edge
  keeps `structuralOverlap: "not-evaluated"`. A structured provenance field for
  graph-suggested hypotheses, and any computation of `structuralOverlap`, are
  contract changes that need their own ratification; they are not implied by
  this doctrine.
- **`duplicates`** records behavioural equivalence or overlap between two
  canonical skills that both keep their identity, history and ownership. It
  never instructs or implies canonical deduplication, merging, removal or
  re-curation, and it is not evidence of observed performance.
- **Attribution.** For a claim drafted from a skill's own instructions, the
  skill owner(s) receive primary attribution, the drafting agent is the
  supporting author, and project governance (the founder) is named separately
  from authorship. Naming the owner or the founder never asserts that either
  wrote, reviewed or endorsed the claim's wording unless that is independently
  documented. The evidence tier is stated in `authority.basis` ("source-declared;
  not benchmark-observed; not governed-interpreted"). That wording is for
  people; consumers read the tier from the projected `support` value. A
  structured owner/author/governance/tier field would be a contract change.
  Records issued before this pattern (for example the 2026-08 declaration for
  `obra/receiving-code-review`) are immutable and stay as issued.

Canonical skill identity remains outside Arbor and is never rewritten. Every
Arbor source points to the exact canonical `skill.id` and the SHA-256 of its
source file's unmodified bytes (see *Behavioural identity and applicability*
below for how that pin is joined to later canonical bytes). Resolution is deterministic: generic IDs resolve
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
closed. Publication-time `pairApplicable` and `applicability` are not runtime
assurance: a consumer must still check the stated conditions, and for a
mutable instruction link it must treat `mutable-ref-unobserved` as unverified. The empty
edge index and absent HH lens therefore do not close Arbor G, A, E, or the
human curator evidence gate.

## Behavioural identity and applicability (#2441)

A source's `contentSha256` pins the whole canonical file, which also carries
evidence, timeline, level and trust. Joining on exact current bytes therefore
made Arbor knowledge disappear on every curation edit, while a change to the
upstream instructions behind a mutable `main` link left it in place. The pin
stays the immutable identity of every source; applicability is decided
separately:

- **Pins** (`gaia.arbor-pin/v1`, `pins/<skill-id path>/<contentSha256>.json`)
  are published once per pinned subject, at admission, from bytes verified to
  hash to the pin. Each records the *behavioural identity digest*
  (`gaia.arbor-behavioral-identity/v1`): the canonical record with standing and
  history removed (`level`, `status`, `origin`, `evidence`, `timeline`,
  `trustMagnitude`, `overallTrustGrade`, `verification`, `apexGateStatus`,
  timestamps, display name/title/tags, `upstream.syncedAt`, and for generic
  nodes `derivatives` and `knownAgents`). Every other field, including any
  field not yet known to this list, and the markdown body stay in the digest,
  so new fields fail closed. `gaia dev arbor pin <id>` backfills a pin from
  current bytes or, with `--from-git REV`, from a historical blob that must
  hash to the pin. `check` requires a pin for every subject and re-derives
  every pin whose bytes are still current.
- **Instruction observations** (`gaia.arbor-instruction-observation/v1`) record
  upstream bytes behind the canonical `links.github` blob link. A *baseline*
  names the exact commit a declaration was read from and must hash to the
  sha256 the claim cites (`gaia dev arbor observe-instruction`). A
  *drift-check* (`gaia dev arbor upstream-check --record`, network) records
  what a mutable link serves later, or that it is unavailable. Observations are
  immutable and monotonic: once a drift is recorded the old claims stay
  inapplicable even if upstream later reverts; restoring applicability takes a
  new declaration against the new bytes.
- **`applicability`** on every runtime record (and `applicable` /
  `behavioralSha256` on each `runtime/index.json` subject) is `true` only when
  the current canonical record is behaviour-equivalent to the pin and no
  drift-check found changed or unavailable instruction bytes.
  `instruction.status` is one of `no-instruction-link`, `immutable-ref`,
  `mutable-ref-unobserved`, `baseline-observed`, `instruction-changed` or
  `instruction-unavailable`. `pairApplicable` requires both endpoints to be
  applicable, and the interaction and HH lenses abstain for an inapplicable
  subject. Historical profiles are never rebound.

Because the projection reads only behavioural digests, a prestige-only edit
(new evidence, a timeline event, a calibration) changes no generated Arbor
file, and a behavioural edit changes it deterministically. `gaia dev docs`
replays `registry/arbor/{profiles,runtime,edges.json}` and the published
`docs/graph/arbor/` copy in one step; `gaia dev docs --check` and
`gaia dev arbor check` (run by `validate.yml`) fail on either drift.

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
gaia dev arbor pin obra/receiving-code-review --from-git <rev>   # legacy backfill
gaia dev arbor observe-instruction <id> --content-sha256 <pin> --commit <sha> --expect-sha256 <cited>
gaia dev arbor upstream-check            # report-only; --record writes drift
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
