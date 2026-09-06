# Arbor runtime projection, edge contract, and installability publisher — implementation contract

**Status:** design proposal implementing an already-approved direction. **Not** new founder-ratified
fact. Authored 2026-09-06 for `gaia-skill-heaven#116` lanes A/G plus this repo's #1711 and #1712.
Approved envelope — durable sources of record:
[`gaia-skill-heaven#116` (comment)](https://github.com/gaia-research/gaia-skill-heaven/issues/116#issuecomment-5559466527) ·
[`gaia-research#207` (comment)](https://github.com/gaia-research/gaia-research/issues/207#issuecomment-5559470985) ·
[`gaia-skill-tree#1712` (comment)](https://github.com/gaia-research/gaia-skill-tree/issues/1712#issuecomment-5559471139).

**Nothing in this packet is published or ratified by the packet's own existence.** Every schema below is
a *proposed concrete shape* awaiting review under RATIFICATION G1 (canon is read-only; schema changes
route through the private lane as reviewable proposals).

Authority read: `founder/ENDGAME.md` §4/§8, `founder/ENDGAME - SCHEMA.md` §5–§16,
`registry/arbor/README.md`, `registry/arbor/contracts/*`, `src/gaia_cli/arbor.py`,
`docs/agents/install-parity.md`, `scripts/install_parity.py`,
`gaia-research/founder/RATIFICATION.md` N6/G1/G2/B3/T9/R1a/A1/A2 + §6 open item 2,
`gaia-research/content/reports/hh-benchmark/methodology.md` §5–§7.

**Load-bearing fact that shapes everything below:** the HH benchmark is *"Not yet executed. Receipts
before results."* (methodology, closing line). No HH result and no Arbor edge has governed evidence
today. Every contract here therefore ships with a **valid empty snapshot** and zero fabricated
content. Fixtures do not count as evidence.

---

## 1. Contract shape — one envelope, three lenses

**Decision.** `gaia.arbor-profile/v1` stays closed, unchanged, and valid. A new, separately
versioned **aggregate runtime projection** is what a consumer reads:

```
schema:  gaia.arbor-runtime/v1
subject: { id, contentSha256 }          # canonical identity, never rewritten
inputDigest                              # sha256 over the canonical bytes of every contributing source
lenses:
  claims:       { status, sourceDigest, profile }    # profile = a gaia.arbor-profile/v1 doc, verbatim
  hellHeaven:   { status, sourceDigest, result }     # N6 key; payload per ENDGAME - SCHEMA §9
  interactions: { status, sourceDigest, edges[] }    # gaia.arbor-edge/v1 entries, this subject only
```

Rationale for aggregate-with-embedding rather than field-on-v1 or four separate fetches: it gives the
consumer one fetch and one digest to verify, it keeps each lens independently versioned (ENDGAME §15),
and it does not touch a ratified closed contract. `hellHeaven` is the N6 schema key **on this
envelope**; the ENDGAME §9 result profile is its payload; `gaia.arbor-profile/v1` remains the claims
lens, unchanged.

**`status` is a required enum, never a silent `null`:** `present` · `absent-no-accepted-record` ·
`absent-subject-version-mismatch` · `absent-superseded`.

### 1.1 Two axes that must never be conflated

**`support` is an evidential relation, not a behavioral direction.** It states how a governed
interpretation stands relative to a claim, given a named observation set. **No value of `support` is
inherently positive or negative:**

| `support` | Means | Does NOT mean |
|---|---|---|
| `expert-declared` | nothing governed has yet been interpreted | untested-and-therefore-weak |
| `benchmark-confirmed` | the claim stands as declared | the behavior is *good* |
| `benchmark-qualified` | the claim stands within narrower stated conditions | the claim was weakened |
| `benchmark-revised` | the governed interpretation **changed** the claim — **direction unspecified**; a revision may strengthen, weaken, redirect, or re-scope it | a negative finding, a demotion, or a refutation |
| `inconclusive` | governed, and the evidence did not settle it | missing, or neutral-effect |

**Behavioral effect lives in exactly two places, and `support` is neither:** the signed
`measurements` on an observation record, and an edge's declared `relation`. A reader that infers
direction or magnitude from `support` has manufactured a finding. Concretely: `relation: conflicts`
at `support: inconclusive` means *a negative-valence interaction was claimed and the evidence did not
settle it* — not *a proven conflict*; and `support: benchmark-revised` on a `relation: amplifies`
claim says the claim moved, not which way. Direction must be read from the revised claim text and the
measurements, never from the support label.

### 1.2 Reader rules for absence, staleness, and version drift

| Reader sees | Means | Must NOT be read as |
|---|---|---|
| `absent-*` | **missing** — nothing governed exists | a negative, or a neutral verdict |
| `inconclusive` | **governed, unsettled** | missing, or zero-effect |
| any `support` value | an **evidential** relation | a behavioral direction (§1.1) |
| `indexVersion` / `edgeSetVersion` the reader does not know | **future-version → abstain** | degrade to neutral |
| a unit or dimension name the reader does not know | **abstain on that dimension** | coerce to a number |

`subject.contentSha256` mismatch against the consumer's resolved skill bytes ⇒ treat the lens as
missing. Historical pins are never rebound to moving canonical bytes (existing README rule, unchanged).

### 1.3 Why `human-led` / `model-led` need no change

They are **authored declaration facets** — who leads execution, under stated conditions, independent
and non-exclusive (RATIFICATION A1). HH is a **computed index result** over observations; an edge is a
**governed pairwise relation**. ENDGAME §13 assigns those to three different ownership classes
(Authored / Computed / Governed). Flattening HH or edges into the facet enum would (a) put a computed
value on an authored field, violating A1, and (b) repeat exactly the superseded-SPEC error retired by
`gaia-skill-heaven#118` (`polarity` + `confidence` attached to an Arbor-shaped field). They are
**additional structured constituents of one envelope**, not additional enum members.

### 1.4 Schema-definable now vs genuinely unknown

**Definable now:** the envelope; identity/version/digest fields; `status` enums and reasons;
`authority{actor,basis}`; supersession; finite-number and recursive prestige-key rejection;
per-claim applicability (§2.1); empty-snapshot validity.

**Must stay unknown / research-owned — do not freeze:** the HH behavior dimension names, their units
and their semantics; the polarity formula; the stamp vocabulary and tiers; whether the 0–100 score
survives; compaction survival. `polarity.value` is permitted but MUST carry `provisional: true` per
G2, and consumers must not do arithmetic on it (`gaia-skill-heaven` INV-12).

**Tree records; Tree does not compute.** The builder copies the research-published `result` verbatim and
pins its digest. It validates structure, subject identity/version, the acceptance chain, and
supersession uniqueness. It never recomputes polarity and never derives a stamp.

---

## 2. Governance and provenance chain for HH

Four record classes, on the same axis the sidecar already uses:

1. **Declaration** — existing `gaia.arbor-expert-declaration/v1`. Unchanged.
2. **Observation reference** — new source `gaia.hh-observation-ref/v1`. A *pointer*, not a copy:
   `ledgerRecordDigest`, `benchmarkVersion`, `harness{name,version}`, `model`, `arm`, `repeatIndex`,
   `taskSetHash`. **No measurements are copied**, so the Tree never becomes a second `hh-ledger`
   (frozen upstream, B3/D6). Conclusion-free by construction.
3. **Acceptance** — new source `gaia.hh-acceptance/v1`. A **curator** record: `authority{actor,basis}`,
   `acceptedAt`, `indexId: hell-heaven`, `indexVersion`, `resultDigest`, `observationRefs[]`,
   `supersedes`. This is the no-automatic-receipt→verdict gate for HH, exactly parallel to
   `gaia.arbor-interpretation/v1` for claims. Parallel active acceptances for one subject are rejected.
4. **Projection** — the `hellHeaven` lens, materialized from the single active acceptance.

### 2.1 The HH payload must carry applicability per behavioral claim

A finite-number map plus a `dimensionSetVersion` is **not sufficient**: the moment a unit or a
semantic convention becomes load-bearing, an envelope-level condition blob cannot say which claim it
governs. Required shape — **every behavioral claim carries its own applicability**:

```
result:
  polarity:   { value, label, provisional: true, applicability }
  behavior:
    <dimensionName>: { value, unit, semantics, direction, applicability }
  regimes:
    <regimeName>:  { <metricName>: { value, unit, semantics, applicability }, status }
  coverage:     { ... }
  dimensionSetVersion
  unitVocabularyDigest        # research-published; the reader's abstain key

applicability: { conditions, regime, harness{name,version}, model, arm, taskFamily }
```

`conditions` is required and non-empty on every applicability block — the same discipline the existing
declaration `claim.conditions` already enforces. `unit` and `semantics` are required per dimension;
`direction` states which sign is which so a reader never guesses valence. A reader that does not
recognise a `unit`, a `semantics` string, or the `unitVocabularyDigest` **abstains on that dimension**
and says so — it does not coerce the number. Envelope-level conditions are forbidden as a substitute.

### 2.2 Stamps — proposed here, not yet research-defined

`result.stamps[]` and `result.primaryStamp` are **proposed by this packet and are NOT an existing
research contract.** RATIFICATION T9 (multiplicative stamps, one primary) and R1a (hell-safe tier
bijection) are *rulings about stamps*; neither publishes a serialized field shape, and methodology §5
places stamps after a trial that has not run. Therefore:

- Both fields are **optional** in `gaia.arbor-runtime/v1`. Nothing requires them before research
  publishes a stamp contract, and the empty snapshot omits them.
- If present, they are validated only against a research-published `stampVocabularyDigest` — never a
  Tree-hardcoded enum. R1a already revised tier derivation once; a hardcoded enum would force a Tree
  schema bump on the next rubric revision, against G1.
- **Do not present these as already-defined upstream fields** in downstream docs. If research
  publishes a different stamp shape, this proposal loses, and the lens carries the published shape.

### 2.3 Rejection-set collision — verified in code

`src/gaia_cli/arbor.py` `SOURCE_INTERPRETATION_KEYS` rejects `result`, `results`, `outcome(s)`,
`finding(s)`, `support`, `verdict` **recursively** (`arbor.py:203-214`), and currently applies to
declarations and receipts (`arbor.py:165-166`). ENDGAME §7/§9 use `result:` as the index payload key.
Decide explicitly per new record class and write the decision into the code as a comment:
`hh-observation-ref` → apply both `PRESTIGE_KEYS` and `SOURCE_INTERPRETATION_KEYS` (it is an
observation); `hh-acceptance` → apply `PRESTIGE_KEYS` only (it is governed, and `resultDigest` /
`result` are legitimate there). Do not widen the rejection sets silently, and do not rename ENDGAME's
key to dodge the checker.

Old unsupported hashes and fields can never be promoted: an altered source has a new digest and
re-enters current-canonical admission; a digest/file mismatch fails `check`; a superseded acceptance is
excluded from the projection rather than downgraded in place.

---

## 3. G1–G4 — dedicated edge contracts (reuse proven impossible)

**The previous revision of this packet claimed the existing receipt and interpretation contracts could
be reused unchanged for edges. That claim is wrong.** Proof against the actual closed schemas and the
actual builder linkage:

| # | Evidence | Consequence for reuse |
|---|---|---|
| 1 | `benchmark-receipt.schema.json` and `interpretation.schema.json` both `require` a **single** `skill: {id, contentSha256}`, with `additionalProperties: false` at the record root **and** inside the `skill` definition | A pair is **inexpressible**. There is no second-subject slot and no escape hatch. |
| 2 | `arbor.py:381` — `if receipt["skill"] != declaration["skill"]` (exact dict equality against one declaration skill) | An edge declaration carrying `pair` and no `skill` raises `KeyError`. Adding a `skill` key forces picking one endpoint, **silently dropping the other endpoint's content pin**. |
| 3 | `arbor.py:405` — same single-`skill` equality, plus `if receipt["target"] != target` where `target` is only `{declarationSha256, claimId}` | The link check carries **no pair and no endpoint digest**, so an endpoint whose bytes moved cannot be detected. |
| 4 | `arbor.py:449-461` — `buildProfiles` groups strictly by `key = (skill["id"], skill["contentSha256"])`; `profilePath(root, skillId, skillHash)` writes one file per single subject | An edge belongs to **two** subjects at two content hashes. No grouping key exists for it. |
| 5 | `profile.schema.json` `claim` requires `facet ∈ {human-led, model-led}`, `additionalProperties: false` | An edge `relation` cannot ride on the existing projection. |

**Conclusion: reuse cannot preserve pair / content / version semantics.** The only ways to reuse would
be to mutate two ratified closed contracts (forbidden under G1) or to drop an endpoint pin (unsafe).
So the edge chain gets its **own smallest necessary contracts** — three sources plus one projection,
because pair identity and per-endpoint content pins must be carried **and verified at every link**:

- **G1a —** `edge-declaration.schema.json`, `$id: gaia.arbor-edge-declaration/v1`:
  `declarationId`, `declaredAt`, `pair: { from: {id, contentSha256}, to: {id, contentSha256} }`
  (ordered — direction is semantic), `claims[]: { id, relation, conditions, rationale, authority }`.
  `relation` enum is **exactly ENDGAME §8**: `stabilizes` `amplifies` `conflicts` `recovers`
  `compresses-after` `unlocks` `duplicates`. No additions.
- **G1b —** `edge-observation.schema.json`, `$id: gaia.arbor-edge-observation/v1`: `pair`,
  `target {declarationSha256, claimId}`, `benchmark {id, version}`, `control`/`treatment` arms,
  `provenance`, `measurements`. Conclusion-free.
- **G1c —** `edge-interpretation.schema.json`, `$id: gaia.arbor-edge-interpretation/v1`:
  `interpretationId`, `interpretedAt`, `pair`, `target`, `authority`, `support`, `rationale`,
  `observationSources[]`, `supersedesSha256`.
- **G2 —** `edge.schema.json`, `$id: gaia.arbor-edge/v1`: the projection entry. `pair`, `relation`,
  `conditions`, `authority`, `support`, `declarationSource`, `observationSources[]`,
  `interpretationSource`, and the constant `structuralOverlap: "not-evaluated"`.

**Parallel, not reused.** The `arm`, `environment`, `artifacts`, `measurement`, `authority`
definitions and the four-value `support` enum are **copied verbatim** from the existing contracts so
the two chains stay semantically identical. Only subject cardinality differs. All four new schemas are
`additionalProperties: false`.

**Pair-integrity validators the builder MUST run — this is precisely what reuse could not give:**

1. `observation.pair == declaration.pair` (exact dict equality, **both** endpoints, id *and* digest).
2. `interpretation.pair == declaration.pair`, and for every referenced observation
   `observation.target == interpretation.target` **and** `observation.pair == interpretation.pair`.
3. `supersedes.pair == pair` **and** `supersedes.target == target`; parallel active edge
   interpretations for one `(pair, claimId)` are rejected.
4. **Both** endpoints undergo the current-canonical existence / exact-bytes admission check
   independently on first admission of a new declaration digest.
5. `from != to` — no self-edge.
6. `(from, to)` and `(to, from)` are **distinct** declarations and must not be deduplicated or
   normalised into an unordered pair.

**Grouping and publication.** An edge has no single `(id, contentSha256)` key, so it cannot be written
under `profiles/<skill>/<hash>.json`. It publishes to a **store-wide index**,
`docs/graph/arbor/edges.json` (`schema: gaia.arbor-edge-index/v1`, no generated timestamp), keyed by
`edgeKey = sha256(canonical([from.id, from.contentSha256, to.id, to.contentSha256, relation, claimId]))`.
The same edge then appears in the `interactions` lens of **both** endpoints' runtime projections — and
only where that endpoint's `contentSha256` matches its pin; otherwise that subject's lens reads
`absent-subject-version-mismatch`.

- **G3 —** deterministic publication, plus `coverage: { pairsEvaluated: 0, absenceMeaning: "not-evaluated" }`.
- **G4 —** structural separation enforced structurally, not by convention: a new `STRUCTURAL_KEYS`
  rejection set (`prerequisite`, `prerequisites`, `prereqs`, `fusion`, `suitecomponents`) applied to
  edge sources; the edge builder must not read relations out of `registry/nodes/**` (identity and bytes
  only); and `structuralOverlap` is a hard constant so a consumer can never read its absence as "no
  structural relation". A pair may legitimately hold a Yggdrasil fusion edge **and** an Arbor
  interaction edge; merging them is the failure this guard prevents.

**Ships today: `edges: []`.** Valid, deterministic, empty. `pairsEvaluated: 0` and
`absenceMeaning: "not-evaluated"` are the safety mechanism — a missing edge is *unseen*, never
*proven absent*, so a consumer cannot default to "no conflict". `gaia-skill-heaven` INV-10 stays
unsatisfied and disclosed. A reader whose `conditions` do not match may abstain, and abstention is a
first-class outcome.

---

## 4. Source-agnostic consumer boundary

Identity is four-part: `(namespace, sourceId, skillId, contentSha256)`. Materialization identity is
separate: `materialization { mechanism, harness{name,version}, route }`.

**Namespace alone neither grants nor prohibits canonical enrichment.** The gate is a **proven mapping
to the same canonical subject at exact content**:

| Condition | Enrichment | Reason code |
|---|---|---|
| `namespace == "gaia.canonical"`, `skillId` resolves, `contentSha256` matches | **applies** | the trivial case |
| non-Gaia source whose resolved content digest **equals** a canonical subject's `contentSha256` | **applies** — same bytes are the same subject | `mapped-by-content` |
| non-Gaia source with an explicit governed mapping record asserting the identity, plus a digest match | **applies** | `mapped-by-governed-record` |
| a plausible but unverified identity (same name, same repo, different or unknown bytes) | **does not apply** | `out-of-scope-mapping-unproven` |
| no mapping attempted or available | **does not apply** | `out-of-scope-no-mapping` |

The last two are recorded as `arbor: { status: "out-of-scope-for-publisher", reason }` — which is
neither "unknown because broken" nor "unreachable". An external candidate need not be registered in
Gaia to be enriched; it must be **proven to be the same subject at the same bytes**. Tree-owned
evidence covers Tree's scope and says so. Tree exports no stars, rank, grade, or Trust Magnitude as
behavior — already enforced recursively by `PRESTIGE_KEYS`, which must be extended to every new
contract above. No new live API and no generic federation standard: snapshot and HTTP GET are the same
Class S bytes.

---

## 5. tree#1712 — installability publisher (separate lane)

Two artifacts. **The standalone parity tool's policy does not change**: it stays out of workflows and
CI (`docs/agents/install-parity.md`), and no automatic mass probing is introduced.

### 5.1 Observation (input, committed by a human operator)

`registry/installability/observations/<sha256>.json`, `schema: gaia.installability-observation/v1`,
produced by a new `--observation <path>` flag on `scripts/install_parity.py` that projects the
script's own JSON. `registryCommit` alone pins **Gaia's** bytes, not the external repo's, so it is not
sufficient. Required **per skill**:

```
id
skillContentSha256          # canonical registry bytes of the skill at check time
sourceRoute                 # { url, owner, repo, ref, subpath } — the route actually tested
resolvedRevision            # the commit SHA git actually checked out (provenance only — see 5.4)
deliveredContentSha256      # sha256 over canonical(sorted {relpath: sha256}) of the installed tree
gaiaHealth                  # materialized | refused | failed | not-observed  (gaia side ONLY)
comparator                  # separate object: dirname + content diff outcome, never mixed in
causeEvidence               # { exitCode, stderrDigest, stderrTail, classifiedCause | null }
```

Run context: `checkedAt`, `registryCommit`, `indexPath`, `toolVersion`, `gaiaVersion`, `npxVersion`,
`timeoutSeconds`, `jobs`.

`gaiaHealth` maps directly from the existing `check_gaia_health(...)` function
(`scripts/install_parity.py`, which already resolves the install, records `gaia_mechanism`, and is the
only gaia-side judge) plus `check_no_source(...)` for the refusal case. **`comparator` is a separate
field and the projection never reads it** — that is the structural guarantee that a comparator error
cannot override a successful gaia health observation, stronger than a documented "does not block".

### 5.2 Projection (output, Class S)

`docs/graph/installability/index.json`, `schema: gaia.installability/v1`, per skill
`{ state, reason, observedAt, observationDigest }`, `state ∈ { materializable, not-materializable, unknown }`.

### 5.3 Mapping rules — a coarse exit label is not a durable negative

`Result.verdict` defaults to `PASS` (`install_parity.py:170`) and `check_no_source` leaves a *correct
refusal* at `PASS` (≈L538-560). So the projection reads `gaiaHealth` and `causeEvidence`, never
`verdict` and never `comparator`.

- **`materializable`** — `gaiaHealth == materialized` (a real directory containing `SKILL.md`), or
  every suite component installed. Comparator findings (`DIRNAME_MISMATCH`, `CONTENT_*`, `NPX_*`) are
  curation/parity debt reported elsewhere and **cannot change this state**.
- **`not-materializable`** — only where the cause is durable and evidenced:
  `NOT_A_SKILL_DIR`, `NO_SKILL_MD`, `DANGLING_SYMLINK`, `SUITE_COMPONENT_FAILED` (all of which are
  positive observations of a *wrong thing on disk*), and `reason: no-source` for a `NO_SOURCE` skill
  that refused correctly — **a correct refusal is a parity PASS and a truthful negative.**
- **`unknown`** — everything ambiguous. Specifically:
  - **`GIT_CLONE_FAILED` is `unknown` by default.** `classify_gaia_failure` assigns it on the strings
    `"git error"` or `"fatal:"`, which cover 404, private-repo, expired-auth, DNS, proxy and
    rate-limit **indistinguishably**. It becomes `not-materializable` only with a
    `classifiedCause` in `{repo-absent, path-absent}` backed by an unauthenticated HTTP status
    recorded in the observation, or by repeated identical failure across ≥2 observations at different
    `checkedAt`. Reason codes: `source-unreachable-at-check` (unknown) vs `repo-absent` (negative).
  - **`GAIA_INSTALL_FAILED` is `unknown` by default.** It is literally the classifier's fallback
    bucket — `f"exit {code}: {tail}"` with no taxonomy — so the label carries no cause. It becomes
    `not-materializable` only with a `classifiedCause`; otherwise `reason: unclassified-install-failure`.
  - `TIMEOUT` and other `HARNESS`-origin codes; the skill absent from the observation;
    `UNEXPECTED_SUCCESS` (contradictory).

Absent, timed-out, transient, ambiguous, and stale evidence is **never** a proven negative.

### 5.4 Stale and mismatch handling — implementable offline, no invented evidence

The build step must run with no network. Three checks, all pure local reads:

1. `skillContentSha256` ≠ the skill's current canonical bytes ⇒ `unknown / subject-changed`.
2. `sourceRoute` ≠ the skill's current `links.github` route ⇒ `unknown / route-changed`.
3. skill absent from the observation ⇒ `unknown / not-observed`.

`resolvedRevision` and `deliveredContentSha256` **cannot be re-verified offline** and are therefore
**provenance only, never a freshness test.** Upstream drift after `checkedAt` is undetectable without
network, so the projection must not claim freshness: it states `observedAt` and what changed on the
Gaia side, and nothing more. That is the honest offline-implementable boundary — a stronger claim
would require either a network call in `--check` (forbidden) or invented evidence.

### 5.5 Build wiring

One `_run_step("installability-projection", build_installability_projection, args.check)` in
`scripts/build_docs.py` (beside `docs-named-index`, ≈L1655) and one term added to the `changed` tuple
(≈L1758). The step is a **pure projection of the committed observation file** — no network, no
install, so `python scripts/build_docs.py --check` stays offline. Add one paragraph to
`docs/agents/install-parity.md` stating the publisher reads committed observations only and that the
sweep remains operator-run. A full 40–60 min sweep is **not** required for this contract work.

---

## 6. Research closure — what this packet does and does not close

- **#207 Q1 — a concrete shape is now PROPOSED, not published.** The proposal: the consumer reads
  `gaia.arbor-runtime/v1`; `hellHeaven` (N6) is the lens key; the ENDGAME §9 result profile is the
  payload; `gaia.arbor-profile/v1` remains the claims lens unchanged; stamps are proposed as an
  optional projection of the payload (§2.2). N6's "becomes INVARIANT once the canon ask lands
  upstream" — this packet **is** that canon ask, routed per G1 as a reviewable proposal. It is not
  answered until it is reviewed and accepted.
- **#207 Q2 — a concrete shape is now PROPOSED, not published.** HH sits **inside Arbor, beside the
  claims profile, within one envelope** — not as a field on the closed v1 contract. Join key
  `(skillId, contentSha256)`. Same caveat: proposed, pending review.
- **#207 Q3 — NOT CLOSED.** G2 keeps the continuous float provisional until research shows signal
  beyond the stamps; methodology §7 is still open.
- **#207 Q4 — NOT CLOSED and out of scope here.** RATIFICATION §6 open item 2 (compaction needs its own
  probe) and `gaia-research#216`. Do not duplicate that work.
- **#208 (Lane E) — acceptance steps for the follow-on evidence worker**, with a curator gate:
  1. **E1** One uncertainty from a **real runtime observation** — a recorded `gaia-skill-heaven` decision
     that a declaration claim does not explain. A fixture, a survey, or a plausible-sounding hypothesis
     does not qualify; if no real observation exists, stop and report that.
  2. **E2** One focused benchmark against one declaration claim: control + treatment, same closed
     environment, pinned task/fixture/evaluator hashes, N repeats (B3 — no `seed` field).
  3. **E3** `gaia dev arbor import <receipt>` — conclusion-free, `gaia.arbor-benchmark-receipt/v1`.
  4. **E4** **Curator gate.** A human imports `gaia.arbor-interpretation/v1`. No threshold, count, or
     aggregate in any repo may set `support`. An agent may prepare the record; it may not be the authority.
  5. **E5** `gaia dev arbor replay`, then the published projection changes one runtime decision downstream.
  6. **Hard stop.** If the loop cannot close on one subject, report it as a finding and **do not widen**.
     No fabricated support, no invented verdict.

**The `hellHeaven` lens reads `absent` until ANY accepted, valid HH evidence exists** — via the §2
acceptance chain, from any source that satisfies it. That is **not** tied to `#208` specifically;
`#208` is the nearest concrete path to producing such evidence, not a precondition for the lens.

---

## 7. Numbered implementation steps, PR boundaries, gates

All feature PRs target **`dev/issue116-runtime-integration`** with `dev/issue116-*` head branches
(unrestricted prefix — avoids branch-scope thrash across `registry/`, `src/`, and `scripts/` in one
lane). The integration branch is a workbench and **need not be green**; CI gates the single
integration → `main` merge, which is founder-gated.

| PR | Branch | Files | Acceptance |
|---|---|---|---|
| **A1** (this) | `dev/issue116-arbor-design` | `founder/handovers/2026-09-06-issue116-arbor-runtime.md` | packet merged to integration |
| **A2** contracts | `dev/issue116-arbor-contracts` | `registry/arbor/contracts/{edge-declaration,edge-observation,edge-interpretation,edge,hh-observation-ref,hh-acceptance,runtime}.schema.json`; `registry/arbor/README.md` | every new schema `additionalProperties: false`; the `arm`/`environment`/`measurement`/`authority`/`support` definitions are byte-identical to their originals; a hand-written invalid doc per contract is rejected |
| **A3** builder | `dev/issue116-arbor-builder` | `src/gaia_cli/arbor.py` (`SCHEMA_FILES`, `SOURCE_DIRECTORIES`, `STRUCTURAL_KEYS`, per-class rejection-set decision, the six §3 pair validators, `edgeKey`, HH acceptance chain, `buildProfiles` → `buildRuntime`), `src/gaia_cli/commands/dev/arborCmd.py`, `tests/` | `gaia dev arbor check` green on an empty store; two consecutive `replay` runs byte-identical; each of the six pair validators has a rejecting test (mismatched endpoint digest, cross-pair observation, self-edge, reversed-pair dedup, forked interpretation, unadmitted endpoint); parallel active HH acceptance rejected; a `prerequisite` key on an edge source rejected; a bare-number `behavior` dimension without `unit`/`semantics` rejected |
| **A4** publish | `dev/issue116-arbor-publish` | `scripts/build_docs.py` (`build_arbor_projection` step + `changed` term), `docs/graph/arbor/{edges.json,runtime/}` | `python scripts/build_docs.py --check` exits 0 and makes no network call; empty snapshot committed and schema-valid; no timestamp in output; an edge appears in both endpoints' lenses, and vanishes from one when that endpoint's hash is bumped |
| **B1** observation | `dev/issue116-installability-observation` | `scripts/install_parity.py` (`--observation`), `registry/installability/contracts/observation.schema.json` (`registry/schema/` **not** touched) | `--observation` on a single-skill run (`--only garrytan/health`, ~30s) emits a schema-valid file carrying `sourceRoute`, `resolvedRevision`, `deliveredContentSha256`, `gaiaHealth`, `comparator` and `causeEvidence` as separate fields; **no CI wiring** |
| **B2** projection | `dev/issue116-installability-publish` | `scripts/build_docs.py` (`build_installability_projection` + `changed` term), `docs/graph/installability/index.json`, `docs/agents/install-parity.md` (+1 paragraph) | offline `--check` exits 0; a `NO_SOURCE` correct refusal projects `not-materializable / no-source` **while its parity verdict is PASS**; a `DIRNAME_MISMATCH` projects `materializable`; an unclassified `GIT_CLONE_FAILED` and an unclassified `GAIA_INSTALL_FAILED` both project `unknown`; a changed `links.github` route projects `unknown / route-changed` with no network access |

**Migration and unknown states.** Nothing migrates: `gaia.arbor-profile/v1` documents stay byte-valid
and are embedded verbatim. There are zero existing sources, so there is no back-fill. Every new lens
ships `absent-no-accepted-record`, and every new index ships empty-but-valid.

**Genuine open gates — do not report these closed.**

1. **#207 Q1/Q2 are proposed shapes awaiting review**, not published or ratified answers. Q3 and Q4
   remain research-open.
2. **No HH evidence exists**, so the `hellHeaven` lens ships `absent` until any accepted valid
   evidence arrives through the §2 chain. `gaia-skill-heaven` INV-10 stays unsatisfied and must be
   disclosed, not dressed up.
3. **E4 is a human curator gate.** An agent cannot be the interpreting authority.
4. **The stamp vocabulary and the HH unit vocabulary are research-owned.** If implementation needs a
   hard enum to validate either, that is a signal to stop and ask upstream — not to invent one
   (`#118` kill criterion, mirrored).
5. **Durable-negative classification for install failures needs a cause taxonomy that does not exist
   yet.** Until `classifiedCause` is defined and populated, `GIT_CLONE_FAILED` and
   `GAIA_INSTALL_FAILED` project `unknown`. That is correct, not a gap to paper over.
6. **integration → `main`** is founder-gated. No public frontend surface changes in any PR above;
   the new artifacts are JSON only, so no `window.GAIA_MOUNTS` entry and no design-review gate applies.
