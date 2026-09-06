# Arbor runtime projection, edge contract, and installability publisher — implementation contract

**Status:** design proposal implementing an already-approved direction. **Not** new founder-ratified
fact. Authored 2026-09-06 for `gaia-skill-heaven#116` lanes A/G plus this repo's #1711 and #1712.
Approved envelope: `/tmp/issue-116-orchestration/APPROVED.md`. Decisions were published as comments on
`gaia-skill-heaven#116`, `gaia-research#207`, and this repo's #1712.

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
envelope**; the ENDGAME §9 result profile is its payload; `hh-stamp/v1` is a **projection of that
payload** (`result.stamps[]` + `result.primaryStamp`), never a second source of truth.

**`status` is a required enum, never a silent `null`:** `present` · `absent-no-accepted-record` ·
`absent-subject-version-mismatch` · `absent-superseded`. Reader rules, normative:

| Reader sees | Means | Must NOT be read as |
|---|---|---|
| `absent-*` | **missing** — nothing governed exists | a negative, or a neutral verdict |
| `inconclusive` support / edge status | **inconclusive** — governed, no direction | missing |
| `benchmark-revised`, `relation: conflicts` | **negative** — an asserted finding | missing |
| `indexVersion` / `edgeSetVersion` the reader does not know | **future-version → abstain** | degrade to neutral |

`subject.contentSha256` mismatch against the consumer's resolved skill bytes ⇒ treat the lens as
missing. Historical pins are never rebound to moving canonical bytes (existing README rule, unchanged).

### Why `human-led` / `model-led` need no change

They are **authored declaration facets** — who leads execution, under stated conditions, independent
and non-exclusive (RATIFICATION A1). HH is a **computed index result** over observations; an edge is a
**governed pairwise relation**. ENDGAME §13 assigns those to three different ownership classes
(Authored / Computed / Governed). Flattening HH or edges into the facet enum would (a) put a computed
value on an authored field, violating A1, and (b) repeat exactly the superseded-SPEC error retired by
`gaia-skill-heaven#118` (`polarity` + `confidence` attached to an Arbor-shaped field). They are
**additional structured constituents of one envelope**, not additional enum members.

### Schema-definable now vs genuinely unknown

**Definable now:** the envelope; identity/version/digest fields; `status` enums and reasons;
`authority{actor,basis}`; supersession; finite-number and recursive prestige-key rejection; empty-snapshot validity.

**Must stay unknown / research-owned — do not freeze:** the HH behavior dimension names and their
metric definitions (carry as `result.behavior: {<name>: number}` validated only as finite, plus a
`dimensionSetVersion`); the polarity formula; the stamp vocabulary and tiers (validate against a
research-published `stampVocabularyDigest`, **not** a Tree-hardcoded enum — R1a already revised tier
derivation once, and G1 keeps canon read-only); whether the 0–100 score survives; compaction survival.
`polarity.value` is permitted but MUST carry `provisional: true` per G2, and consumers must not do
arithmetic on it (`gaia-skill-heaven` INV-12).

**Tree records; Tree does not compute.** The builder copies the research-published `result` verbatim and
pins its digest. It validates structure, subject identity/version, the acceptance chain, and
supersession uniqueness. It never recomputes polarity and never derives a stamp.

---

## 2. Governance and provenance chain

Four record classes for HH, on the same axis the sidecar already uses:

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

**Implementer trap, verified in code.** `src/gaia_cli/arbor.py` `SOURCE_INTERPRETATION_KEYS` rejects
`result`, `results`, `outcome(s)`, `finding(s)`, `support`, `verdict` **recursively**, and currently
applies to declarations and receipts. ENDGAME §7/§9 use `result:` as the index payload key. Decide
explicitly per new record class and write the decision into the code as a comment:
`hh-observation-ref` → apply both `PRESTIGE_KEYS` and `SOURCE_INTERPRETATION_KEYS` (it is an
observation); `hh-acceptance` → apply `PRESTIGE_KEYS` only (it is governed, and `resultDigest`/`result`
are legitimate there). Do not widen the rejection sets silently, and do not rename ENDGAME's key to
dodge the checker.

Old unsupported hashes and fields can never be promoted: an altered source has a new digest and
re-enters current-canonical admission; a digest/file mismatch fails `check`; a superseded acceptance is
excluded from the projection rather than downgraded in place.

---

## 3. G1–G4 — minimal edge contract and deterministic projection

**One new source contract and one new projection contract. Nothing else.** The existing
`gaia.arbor-benchmark-receipt/v1` and `gaia.arbor-interpretation/v1` are reused **unchanged** by giving
the edge declaration the same `declarationId` + `claims[]` shape they already target.

- **G1 —** `registry/arbor/contracts/edge-declaration.schema.json`, `$id: gaia.arbor-edge-declaration/v1`:
  `declarationId`, `declaredAt`, `pair: { from: {id, contentSha256}, to: {id, contentSha256} }`
  (ordered — direction is semantic), `claims[]: { id, relation, conditions, rationale, authority }`.
  `relation` enum is **exactly ENDGAME §8**: `stabilizes` `amplifies` `conflicts` `recovers`
  `compresses-after` `unlocks` `duplicates`. No additions. `additionalProperties: false`.
- **G2 —** `registry/arbor/contracts/edge.schema.json`, `$id: gaia.arbor-edge/v1`: the projection.
  Carries `pair`, `relation`, `conditions`, `authority`, `support` (the existing five-value enum,
  unchanged), `declarationSource`, `benchmarkSources[]`, `interpretationSource`, and the constant
  `structuralOverlap: "not-evaluated"`.
- **G3 —** deterministic published index at `docs/graph/arbor/edges.json`,
  `schema: gaia.arbor-edge-index/v1`, no generated timestamp, plus
  `coverage: { pairsEvaluated: 0, absenceMeaning: "not-evaluated" }`.
- **G4 —** structural separation enforced structurally, not by convention: a new `STRUCTURAL_KEYS`
  rejection set (`prerequisite`, `prerequisites`, `prereqs`, `fusion`, `suitecomponents`) applied to
  edge sources; the edge builder must not read relations out of `registry/nodes/**` (identity and bytes
  only); and `structuralOverlap` is a hard constant so a consumer can never read its absence as "no
  structural relation". A pair may legitimately hold a Yggdrasil fusion edge **and** an Arbor
  interaction edge; merging them is the failure this guard prevents.

**Ships today: `edges: []`.** Valid, deterministic, empty. `pairsEvaluated: 0` and
`absenceMeaning: "not-evaluated"` are the safety mechanism — a missing edge is *unseen*, never
*proven absent*, so a consumer cannot default to "no conflict". `gaia-skill-heaven` INV-10 stays
unsatisfied and disclosed; **one real edge lands only when a governed interpretation exists**, which
requires `gaia-research#208` to close (§6 below). A reader whose `conditions` do not match may abstain,
and abstention is a first-class outcome.

---

## 4. Source-agnostic consumer boundary

Join key: `(namespace, sourceId, skillId, contentSha256)`. Materialization identity is separate:
`materialization { mechanism, harness{name,version}, route }`.

Canonical Arbor enrichment applies **only** when `namespace == "gaia.canonical"`, the `skillId`
resolves in the published projection, **and** `contentSha256` matches exactly. Otherwise the consumer
records `arbor: { status: "out-of-scope-for-publisher" }` — which is neither "unknown because broken"
nor "unreachable". An external candidate need not be registered in Gaia; Tree-owned evidence covers
Tree's scope and says so. Tree exports no stars, rank, grade, or Trust Magnitude as behavior — already
enforced recursively by `PRESTIGE_KEYS`, which must be extended to every new contract above. No new
live API and no generic federation standard: snapshot and HTTP GET are the same Class S bytes.

---

## 5. tree#1712 — installability publisher (separate lane)

Two artifacts. **The standalone parity tool's policy does not change**: it stays out of workflows and
CI (`docs/agents/install-parity.md`), and no automatic mass probing is introduced.

1. **Operator observation (input, committed by a human).**
   `registry/installability/observations/<sha256>.json`, `schema: gaia.installability-observation/v1`,
   produced by a new `--observation <path>` flag on `scripts/install_parity.py` that projects the
   script's own JSON. Per skill: `id`, `category`, `gaiaOutcome`, `failureCodes[]`, `gaiaMechanism`.
   Run context: `checkedAt`, `registryCommit`, `indexPath`, `toolVersion`, `gaiaVersion`, `npxVersion`,
   `timeoutSeconds`, `jobs`.
2. **Deterministic projection (output, Class S).** `docs/graph/installability/index.json`,
   `schema: gaia.installability/v1`, per skill `{ state, reason, observedAt, observationDigest }`,
   `state ∈ { materializable, not-materializable, unknown }`.

**Mapping rules — the whole point is that `verdict` is not the answer.** `Result.verdict` defaults to
`PASS` (`scripts/install_parity.py:170`) and `check_no_source` leaves a *correct refusal* at `PASS`
(≈L538–560). Derive from **gaia-side signals only**:

- `materializable` — `gaia install` produced a real directory containing `SKILL.md`, or every suite
  component installed. **Comparator failures do not block this**: `DIRNAME_MISMATCH`, `CONTENT_*`,
  `NPX_*` are parity/curation findings, and the skill still materialized.
- `not-materializable` — `GAIA_INSTALL_FAILED`, `NOT_A_SKILL_DIR`, `NO_SKILL_MD`, `DANGLING_SYMLINK`,
  `GIT_CLONE_FAILED`, `SUITE_COMPONENT_FAILED`; and `reason: no-source` for a `NO_SOURCE` skill that
  refused correctly — **a correct refusal is a parity PASS and a truthful negative.**
- `unknown` — `TIMEOUT` and other `HARNESS`-origin codes, the skill absent from the observation,
  `UNEXPECTED_SUCCESS` (contradictory), or `reason: stale-observation` when the skill's canonical bytes
  changed after `registryCommit`. Absent, timed-out, and stale evidence is **never** a proven negative.

Build wiring: one `_run_step("installability-projection", build_installability_projection, args.check)`
in `scripts/build_docs.py` (beside `docs-named-index`, ≈L1655) and one term added to the `changed`
tuple (≈L1758). The step is a **pure projection of the committed observation file** — no network, no
install, so `python scripts/build_docs.py --check` stays offline. Add one paragraph to
`docs/agents/install-parity.md` stating the publisher reads committed observations only and that the
sweep remains operator-run. A full 40–60 min sweep is **not** required for this contract work.

---

## 6. Research closure — what this packet does and does not close

- **#207 Q1 — ANSWERED.** The consumer reads `gaia.arbor-runtime/v1`. `hellHeaven` (N6) is the lens key
  on that envelope; the ENDGAME §9 result profile is the payload; `hh-stamp/v1` is a projection of it;
  `gaia.arbor-profile/v1` remains the claims lens, unchanged. N6's "becomes INVARIANT once the canon
  ask lands upstream" — this packet **is** that canon ask, routed per G1 as a reviewable proposal.
- **#207 Q2 — ANSWERED.** HH sits **inside Arbor, beside the claims profile, within one envelope** — not
  as a field on the closed v1 contract. Join key `(skillId, contentSha256)`.
- **#207 Q3 — NOT CLOSED.** G2 keeps the continuous float provisional until research shows signal
  beyond the stamps; methodology §7 is still open. Report as open; do not close.
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

---

## 7. Numbered implementation steps, PR boundaries, gates

All feature PRs target **`dev/issue116-runtime-integration`** with `dev/issue116-*` head branches
(unrestricted prefix — avoids branch-scope thrash across `registry/`, `src/`, and `scripts/` in one
lane). The integration branch is a workbench and **need not be green**; CI gates the single
integration → `main` merge, which is founder-gated.

| PR | Branch | Files | Acceptance |
|---|---|---|---|
| **A1** (this) | `dev/issue116-arbor-design` | `founder/handovers/2026-09-06-issue116-arbor-runtime.md` | packet merged to integration |
| **A2** contracts | `dev/issue116-arbor-contracts` | `registry/arbor/contracts/{edge-declaration,edge,hh-observation-ref,hh-acceptance,runtime}.schema.json`; `registry/arbor/README.md` | every new schema `additionalProperties: false`; a hand-written invalid doc per contract is rejected |
| **A3** builder | `dev/issue116-arbor-builder` | `src/gaia_cli/arbor.py` (`SCHEMA_FILES`, `SOURCE_DIRECTORIES`, `STRUCTURAL_KEYS`, per-class rejection-set decision, edge/HH validators, `buildProfiles` → `buildRuntime`), `src/gaia_cli/commands/dev/arborCmd.py`, `tests/` | `gaia dev arbor check` green on an empty store; two consecutive `replay` runs byte-identical; parallel active acceptance rejected; a `prerequisite` key on an edge source rejected |
| **A4** publish | `dev/issue116-arbor-publish` | `scripts/build_docs.py` (`build_arbor_projection` step + `changed` term), `docs/graph/arbor/{edges.json,runtime/}` | `python scripts/build_docs.py --check` exits 0; empty snapshot committed and schema-valid; no timestamp in output |
| **B1** observation | `dev/issue116-installability-observation` | `scripts/install_parity.py` (`--observation`), `registry/schema/` **not** touched; `registry/installability/contracts/observation.schema.json` | `--observation` on a single-skill run (`--only garrytan/health`, ~30s) emits a schema-valid file; **no CI wiring** |
| **B2** projection | `dev/issue116-installability-publish` | `scripts/build_docs.py` (`build_installability_projection` + `changed` term), `docs/graph/installability/index.json`, `docs/agents/install-parity.md` (+1 paragraph) | offline `--check` exits 0; a `NO_SOURCE` correct refusal projects `not-materializable / no-source` **while its parity verdict is PASS**; a `DIRNAME_MISMATCH` projects `materializable`; a `TIMEOUT` projects `unknown` |

**Migration and unknown states.** Nothing migrates: `gaia.arbor-profile/v1` documents stay byte-valid
and are embedded verbatim. There are zero existing sources, so there is no back-fill. Every new lens
ships `absent-no-accepted-record`, and every new index ships empty-but-valid.

**Genuine open gates — do not report these closed.**

1. **#207 Q3 and Q4** remain research-open (continuous-score survival; compaction survival).
2. **No HH evidence exists**, so the `hellHeaven` lens ships permanently `absent` until `#208` closes.
   `gaia-skill-heaven` INV-10 stays unsatisfied and must be disclosed, not dressed up.
3. **E4 is a human curator gate.** An agent cannot be the interpreting authority.
4. **The stamp vocabulary is research-owned.** If A2 finds it needs a hard enum to validate, that is a
   signal to stop and ask upstream — not to invent one (`#118` kill criterion, mirrored).
5. **integration → `main`** is founder-gated. No public frontend surface changes in any PR above;
   the new artifacts are JSON only, so no `window.GAIA_MOUNTS` entry and no design-review gate applies.
