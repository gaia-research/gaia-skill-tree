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
`absent-subject-version-mismatch` · `absent-superseded` · `unavailable-unsupported-payload` (a payload
arrived that no accepted contract identifies — the builder rejected it; see §2.1 fail-closed).

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

**A consumer reads behavioral effect only from an explicitly accepted statement under known
semantics and matching conditions** — an accepted claim, an edge's declared `relation`, or an accepted
HH result payload. It never *calculates* one. Specifically forbidden:

- **inferring direction or magnitude from `support`** — that is the axis confusion §1.1 exists to stop;
- **reading a sign off a raw `measurement`** — a measurement is a conclusion-free observation, and its
  sign carries no beneficial/harmful valence on its own. Whether a delta is good, bad, or irrelevant is
  a governed judgement, and the ledger is frozen precisely so nobody re-derives one downstream;
- **parsing free prose** — `rationale`, `conditions`, and revised claim text are for a human reader.
  A consumer that regex-reads them has bypassed governance.

Concretely: `relation: conflicts` at `support: inconclusive` means *a negative-valence interaction was
claimed and the evidence did not settle it* — not *a proven conflict*; and `support: benchmark-revised`
on a `relation: amplifies` claim says the claim moved, not which way, and a consumer that cannot read
which way from an accepted structured field **abstains**. **Unknown semantics, unknown units, or
unmatched conditions ⇒ abstain on that statement** and disclose the abstention.

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

### 2.1 The HH payload — the lens is defined now, the payload contract is not

**The HH result payload contract is research-owned and unpublished. This packet does not freeze it,
and must not, merely to give the envelope something to hold.** What the Tree defines now is the *lens*:
its `status`, its provenance chain (§2), its acceptance gate, and one durable requirement stated below.
The metric set, the units, and the result contract itself remain research's to publish.

**The one durable requirement — applicability must be preserved.** Whatever shape research publishes,
each behavioral statement must arrive with the conditions under which it holds; a finite-number map
plus a `dimensionSetVersion` is not sufficient, because an envelope-level condition blob cannot say
which statement it governs. That is a constraint on *acceptance*, not a schema this packet imposes.

**Fail closed until the contract exists.** Concretely, in `gaia.arbor-runtime/v1`:

- the **empty lens is fully valid and fully implementable now** — `status: absent-no-accepted-record`,
  no payload, nothing pending. A4 ships and validates this today with no research dependency;
- an **unsupported populated lens fails closed**: if a payload is present and no accepted research
  contract identifies its shape, the builder **rejects the record** and the lens publishes
  `status: unavailable-unsupported-payload`. It does **not** pass the bytes through, and it does not
  guess;
- **the initial absent lens must not be presented as though acceptance were operational.** There is no
  accepted HH contract, so there is no working acceptance path to demonstrate. Saying otherwise —
  in a PR body, a downstream doc, or a demo — would be a fabricated happy path;
- the only permitted populated examples are **explicitly labelled schema fixtures**, marked as
  illustrative, never committed as evidence and never counted as a closed loop.

Once research publishes and ratifies a payload contract, the lens evolves to carry it in a separate
upstream ask — not by widening this packet.

**The per-claim shape below is a PROPOSAL for that future ask, offered so the applicability
requirement is concrete. It is not a contract, and nothing implements it in A2–A4:**

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

In this proposal `conditions` would be required and non-empty on every applicability block — the same
discipline the existing declaration `claim.conditions` already enforces — with `unit` and `semantics`
required per dimension and `direction` stating which sign is which, so a reader never guesses valence.
A reader that does not recognise a `unit`, a `semantics` string, or the `unitVocabularyDigest`
**abstains on that dimension** and says so; it does not coerce the number (§1.1). Envelope-level
conditions would be forbidden as a substitute. **Research may publish a different shape that satisfies
the applicability requirement differently; if so, this proposal loses and the published shape wins.**

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

**Parallel, not reused.** The `arm`, `environment`, `artifacts`, `measurement` and `authority`
definitions are **copied verbatim** from the existing contracts so the two chains stay semantically
identical. Only subject cardinality differs. All four new schemas are `additionalProperties: false`.

**`support` has two different cardinalities upstream and both must be copied exactly — do not
normalise them:**

| Contract | Enum | Verified source |
|---|---|---|
| `gaia.arbor-interpretation/v1` (governed source) | **4 values** — `benchmark-confirmed` `benchmark-qualified` `benchmark-revised` `inconclusive` | `interpretation.schema.json` `properties.support.enum` |
| `gaia.arbor-profile/v1` (projection claim) | **5 values** — the four above **plus `expert-declared`** | `profile.schema.json` `definitions.claim.properties.support.enum` |

`expert-declared` is a *projection* state meaning "no governed interpretation exists yet"; it is not
something an interpretation may assert. So `gaia.arbor-edge-interpretation/v1` copies the **4-value**
enum and `gaia.arbor-edge/v1` copies the **5-value** enum. Copying the wrong cardinality either lets a
curator assert `expert-declared` or makes an un-interpreted edge unrepresentable.

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
The same edge then appears in the `interactions` lens of **both** endpoints' runtime projections.

**Publication and runtime applicability are different questions, and both endpoints govern the second.**
An edge stays published under an endpoint whose `contentSha256` still matches its pin — that record is
**historical pinned data** and is correct to retain. But **a runtime reader MUST abstain from the edge
if *either* participant no longer matches its pin**, including the endpoint the reader did not ask
about. A pairwise claim is only applicable when the pair it was made about is the pair in front of you;
one drifted endpoint invalidates the claim in both directions. The projection therefore carries an
explicit per-edge `pairApplicable: true | false` (false as soon as either pin mismatches), so a reader
never has to re-derive it, and a `false` edge is presented as **abstain**, never as absence of an
interaction.

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

**Content alone is NOT subject identity.** Two candidates can ship a byte-identical `SKILL.md` while
bundling different scripts, fixtures or assets, resolving through different source routes, or running
under different execution conditions. A digest match is **necessary and not sufficient**; there is no
`mapped-by-content` shortcut, and an earlier revision of this packet was wrong to propose one.

Enrichment requires **all three** to hold together:

1. **Proven canonical subject mapping** — the candidate is demonstrated to *be* a named canonical
   subject, not merely to resemble one. **Verified canonical route identity is expected to suffice**
   (the candidate resolves through the same `links.github` `blob/branch/subpath` the registry records).
   **Do not invent a new mapping ontology to satisfy this** — if existing canonical route verification
   covers the case, that is the mechanism; a new shipped record type would need its own upstream ask.
2. **Matching content and version** — `contentSha256` equal, and the projection's `subject` version
   pins match.
3. **Applicable conditions** — the accepted statement's execution / source / materialization
   conditions match the candidate's actual `materialization { mechanism, harness{name,version}, route }`
   and harness context. A statement whose conditions do not apply is not enrichment; the reader abstains.

| Condition | Enrichment | Reason code |
|---|---|---|
| all three above hold (the `namespace == "gaia.canonical"` case is the trivial instance) | **applies** | `mapped-and-applicable` |
| mapping proven, content matches, but conditions do not apply | **does not apply** | `conditions-unmatched` |
| content matches but the subject mapping is not proven | **does not apply** | `mapping-unproven` |
| no mapping attempted or available | **does not apply** | `no-mapping` |

**Absent enrichment never disqualifies a candidate.** The bottom three rows record
`arbor: { status: "absent", reason }` — neither "unknown because broken" nor "unreachable" — and the
candidate **remains fully eligible** for retrieval and composition on its own terms. An external
candidate need not be registered in Gaia; it must be proven to be the same subject, at the same
content, under conditions that actually apply. Tree-owned evidence covers Tree's scope and says so. Tree exports no stars, rank, grade, or Trust Magnitude as
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
- **`not-materializable`** — only where an **actually observed intrinsic or pinned-content cause**
  is recorded. Two cases qualify today:
  - `NOT_A_SKILL_DIR`, `NO_SKILL_MD`, `DANGLING_SYMLINK` — the clone succeeded and the **pinned content
    itself** is wrong: a file where a directory was expected, a tree with no `SKILL.md`, a subpath that
    does not exist upstream. These are positive observations of the delivered bytes, not of the network.
  - `reason: no-source` for a `NO_SOURCE` skill that refused correctly — **a correct refusal is a parity
    PASS and a truthful negative.**

  **`SUITE_COMPONENT_FAILED` is NOT in this set.** A component can fail for exactly the same
  auth / DNS / private-repo / transient reasons as any other fetch. It projects `unknown` unless every
  failing component independently carries an intrinsic pinned-content cause from the list above.
- **`unknown`** — everything ambiguous. Specifically:
  - **`GIT_CLONE_FAILED` is `unknown`, and stays `unknown`.** `classify_gaia_failure` assigns it on
    the strings `"git error"` or `"fatal:"`, which cover 404, private-repo, expired-auth, DNS, proxy
    and rate-limit **indistinguishably**. Two rules follow, and an earlier revision of this packet got
    both wrong:
    - **An unauthenticated 404 is not evidence of absence.** GitHub returns 404 for a private
      repository to an unauthorised caller — that is deliberate, and indistinguishable from deletion.
      It **must not** produce a `repo-absent` verdict.
    - **Repetition does not convert ambiguity into fact.** There is no two-repeat (or N-repeat)
      threshold. A failure that is auth-, DNS- or visibility-ambiguous stays ambiguous no matter how
      many times it is observed; a post-hoc repeat threshold would be exactly the kind of manufactured
      verdict this packet forbids elsewhere.

    What the observation *may* record is the scoped, honest fact:
    `reason: inaccessible-at-check` with `checkedAt` and `causeEvidence`. **`inaccessible-at-check`
    is not `not-materializable`** — it says the operator could not reach the source at that moment
    under that credential set, and nothing about whether the skill is intrinsically materializable.
  - **`GAIA_INSTALL_FAILED` is `unknown`, and stays `unknown`.** It is literally the classifier's
    fallback bucket — `f"exit {code}: {tail}"` with no taxonomy — so the label carries no cause at all.
    `reason: unclassified-install-failure`.

  **No cause taxonomy is assumed to exist.** `classifiedCause` is named here only as the *shape* a
  future upstream taxonomy would occupy. Until such a taxonomy is defined and ratified upstream,
  **no `classifiedCause` value promotes anything to `not-materializable`**, and the implementer must
  not invent one. The intrinsic-content cases above stand on their own observed evidence, not on a
  taxonomy.
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
| **A2** contracts | `dev/issue116-arbor-contracts` | `registry/arbor/contracts/{edge-declaration,edge-observation,edge-interpretation,edge,hh-observation-ref,hh-acceptance,runtime}.schema.json`; `registry/arbor/README.md` | every new schema `additionalProperties: false`; the `arm`/`environment`/`artifacts`/`measurement`/`authority` definitions are byte-identical to their originals; **`support` copies the 4-value interpretation enum into `edge-interpretation` and the 5-value projection enum into `edge` — a test asserts an interpretation asserting `expert-declared` is rejected and an un-interpreted edge projects `expert-declared`**; a hand-written invalid doc per contract is rejected |
| **A3** builder | `dev/issue116-arbor-builder` | `src/gaia_cli/arbor.py` (`SCHEMA_FILES`, `SOURCE_DIRECTORIES`, `STRUCTURAL_KEYS`, per-class rejection-set decision, the six §3 pair validators, `edgeKey`, HH acceptance chain, `buildProfiles` → `buildRuntime`), `src/gaia_cli/commands/dev/arborCmd.py`, `tests/` | `gaia dev arbor check` green on an empty store; two consecutive `replay` runs byte-identical; each of the six pair validators has a rejecting test (mismatched endpoint digest, cross-pair observation, self-edge, reversed-pair dedup, forked interpretation, unadmitted endpoint); parallel active HH acceptance rejected; a `prerequisite` key on an edge source rejected; a bare-number `behavior` dimension without `unit`/`semantics` rejected |
| **A4** publish | `dev/issue116-arbor-publish` | `scripts/build_docs.py` (`build_arbor_projection` step + `changed` term), `docs/graph/arbor/{edges.json,runtime/}` | `python scripts/build_docs.py --check` exits 0 and makes no network call; empty snapshot committed and schema-valid; no timestamp in output; an edge appears in both endpoints' lenses; **and a two-part endpoint test: bumping endpoint A's hash must (i) drop the edge from A's lens AND (ii) set `pairApplicable: false` in B's lens, where B's own hash is unchanged** — asserting only (i) is inadequate and must not be the whole test |
| **B1** observation | `dev/issue116-installability-observation` | `scripts/install_parity.py` (`--observation`), `registry/installability/contracts/observation.schema.json` (`registry/schema/` **not** touched) | `--observation` on a single-skill run (`--only garrytan/health`, ~30s) emits a schema-valid file carrying `sourceRoute`, `resolvedRevision`, `deliveredContentSha256`, `gaiaHealth`, `comparator` and `causeEvidence` as separate fields; **no CI wiring** |
| **B2** projection | `dev/issue116-installability-publish` | `scripts/build_docs.py` (`build_installability_projection` + `changed` term), `docs/graph/installability/index.json`, `docs/agents/install-parity.md` (+1 paragraph) | offline `--check` exits 0; a `NO_SOURCE` correct refusal projects `not-materializable / no-source` **while its parity verdict is PASS**; a `DIRNAME_MISMATCH` projects `materializable`; an unclassified `GIT_CLONE_FAILED` and an unclassified `GAIA_INSTALL_FAILED` both project `unknown`; a changed `links.github` route projects `unknown / route-changed` with no network access |

**Everything above is proposed, not ratified.** Every `$id`, field name, reason code, `edgeKey`
formula, digest and pin in this packet is a **proposed shape awaiting review under G1** — naming one
here does not publish it, and downstream docs must not cite them as canonical. The existing four
source schemas remain **unchanged** by this packet.

**Schema-only implementation is not lane closure.** Landing A2–A4 and B1–B2 delivers *contracts,
validators, and empty valid snapshots* — nothing more. It does **not** close lane **G** (#1711 needs a
real governed edge), lane **A** (`gaia-skill-heaven#118` needs a profile to consume), or lane **E**
(#208 needs one closed evidence loop with a human curator gate). An empty snapshot is a correct and
honest deliverable; reporting it as a closed lane is not.

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
5. **No install-failure cause taxonomy exists, and none is assumed.** `GIT_CLONE_FAILED` and
   `GAIA_INSTALL_FAILED` project `unknown` and stay there: an unauthenticated 404 can mask a private
   repo, and repetition never converts ambiguity into fact. `inaccessible-at-check` is a scoped,
   honest observation, **not** a negative. Defining such a taxonomy is a separate upstream ask.
6. **integration → `main`** is founder-gated. No public frontend surface changes in any PR above;
   the new artifacts are JSON only, so no `window.GAIA_MOUNTS` entry and no design-review gate applies.
