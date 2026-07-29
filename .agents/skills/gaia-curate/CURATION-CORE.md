# Gaia Discovery Curation Core

This is the canonical read-only contract for `/gaia-curate`, `/gaia-curate-chain`, and `/gaia-curate-dynamic`. It is a discovery compiler, not a registry mutation workflow. Extensions may orchestrate packets but may not change this lifecycle or cross the L4 stop.

## Lifecycle and boundary

Process exactly one candidate at a time:

`discovered → fetched → parsed → normalized → deduped → mapped → review-ready | deferred | rejected`

`fetched` requires an actually fetched upstream `SKILL.md`; `parsed` requires non-empty `name` and `description` frontmatter. Preserve source facts only: canonical URL, host repository, cited origin, available commit SHA/content hash, and source-native trend signals.

**Stage-1 minimum-effort evidence (RFC2 §3.2 carve-out — the only relaxation).** The worker MAY write exactly the Stage-1 minimum-effort evidence set the crawler already holds: `github-stars-own` (stargazer count), `repo-own` (commits + contributors), and `self-attestation` (the flat baseline). These are REAL canonical evidence rows in the same shape `gaia dev evidence` writes — not a throwaway estimate — recorded from signals already fetched during discovery. Everything else about evidence remains forbidden: **no web search** at this stage (that is Stage 2 / Phase 0, a separate workstream), do not score evidence, do not assign grades or classes, do not set a star level, and do not hand-compute a final Trust Magnitude — TM is derived canonically at appraisal time from the evidence rows. Beyond writing these three Stage-1 rows, do not mutate the registry, regenerate docs, commit, push, or create a PR; everything else still stops at L4.

## Named-first ordering

Curation is presented **named-first**: a concrete NAMED skill (a contributor's implementation, e.g. `mattpocock/grill-me`) is shown to the worker, whose job is to confirm or correct its mapping onto the correct **generic** node — creating the generic if none exists. This is a presentation REORDER, not a decouple: the generic mapping edge is never removed. Generic mapping (`genericSkillRef` → generic id) remains **required** for every review-ready packet — `MAP` selects one supplied id, `NEW_GENERIC` proposes one (deterministic downstream intake assigns or validates the canonical id). One named skill = exactly one `genericSkillRef`; named-first never makes the generic mapping optional.

## Bounded mapping

The bounded mapping consumes a deterministic **prefill** (produced by `gaia dev prefill`) so the worker performs **no semantic re-judgment**. The prefill has already embedded the candidate's `{name}: {description}`, ranked the top-K generics by cosine similarity, performed exact dedupe, and stamped every `mappingOptions[]` entry with `genericId`, `rationale`, `similarity` (cosine 0..1), and `matchTier` (`strong|weak`, derived from `meta.json` thresholds). Options below `weakMap` are already dropped — anything below threshold never reaches the worker. **The worker does not re-rank, re-score, or re-derive tier from the text.** It counts the pre-stamped options by tier and follows the precedence checklist below.

### Decision precedence — first matching rule wins, top to bottom

First compute two integers from the pre-stamped `mappingOptions[]` (no text reading): `nTotal` = number of options, `nStrong` = number of options whose `matchTier == "strong"`. Then evaluate these rules in order against the literal fields. Stop at the first rule that fires; do not skip ahead, do not weigh alternatives, do not inspect *why* a field holds a value — the prefill already decided that.

1. **`NOT_A_SKILL`** — if `artifactGate != "valid-skill"`. Reason code `NOT_A_SKILL`.
2. **`DUPLICATE`** — if `exactDedupe != null` (the prefill already matched the candidate's canonical URL or content hash, including a `cited-origin` digest, to an existing candidate). The `exactDedupe` object IS the proof; do not re-verify it. Reason code `DUPLICATE_EXACT`.
3. **`DEFER`** — if `ambiguity != null`. Reason code `DEFER_AMBIGUOUS_BUNDLE`. (The prefill sets `ambiguity` when the candidate straddles multiple capabilities; do not re-evaluate that — only check the field for null.)
4. **`NEW_GENERIC`** — if `nTotal == 0` (no generic cleared `weakMap`). Reason code `NEW_GENERIC_NO_MATCH`.
5. **`MAP`** — if `nStrong == 1`. Select that one strong option's `genericId`. Reason code `MAP_EXISTING_GENERIC`. (If `nStrong == 1` but other weak options also exist, still MAP the single strong one — the weak options are non-competing.)
6. **`DEFER`** — every remaining case (`nStrong == 0` with `nTotal >= 1` — i.e. only weak options; or `nStrong >= 2` — multiple strong options competing). Reason code `DEFER_WEAK_ADJUDICATION`. Never MAP a weak option and never guess between strong options to break a tie.

These six rules are exhaustive and mutually exclusive once `nTotal`/`nStrong` are computed: rule 4 owns `nTotal == 0`, rule 5 owns `nStrong == 1`, rule 6 owns `nStrong == 0 && nTotal >= 1` and `nStrong >= 2`. A lone weak option (`nTotal == 1, nStrong == 0`) is rule 6 (`DEFER`), never rule 5.

The worker emits exactly one decision from `MAP`, `NEW_GENERIC`, `DUPLICATE`, `NOT_A_SKILL`, `DEFER` — nothing else. It may not invent generic IDs, re-derive `matchTier`, assign type beyond an L4-reviewable Yggdrasil II `basic|fusion` proposal, or use free-form acceptance language. `MAP` selects the single strong option's ID (rule 5). `NEW_GENERIC` (rule 4) proposes a `basic|fusion` type and copies the candidate's own `normalized.name` + `normalized.description` verbatim as the proposed name and description — the worker does NOT author or quality-judge new prose; deterministic downstream intake assigns or validates the canonical ID and vets the description. Malformed worker output (a decision not in the vocabulary, or a `MAP` to an id absent from `mappingOptions`) is recorded as `DEFER` with `DEFER_INVALID_PACKET`; it never becomes an inferred mapping.

The persisted generic snapshot still governs validation: persist the complete `gaia dev list --generic --json` array before worker dispatch, copy it into `genericSnapshot.generics`, record that exact command, and SHA-256 canonical JSON (`sort_keys=True`, compact separators) into `contentSha256`. Validate every mapped packet against that separate persisted JSON array: the validator rejects absent or mismatched trusted snapshots and mapping IDs absent from the receipt.

## Packet contract

Every candidate uses `discovery-packet-v2`, specified by [schemas/discovery-packet-v2.schema.json](schemas/discovery-packet-v2.schema.json) and executable via [scripts/validate_discovery_packet.py](scripts/validate_discovery_packet.py) (which selects the v1 or v2 code path on `contractVersion`; existing `discovery-packet-v1` packets remain valid for back-compat). Validate a mapped packet with `python scripts/validate_discovery_packet.py --generic-snapshot generic-snapshot.json packet.json`; the generic snapshot is a required independent input, never inferred from the packet. The packet includes source provenance, hash, source-native trend signals, normalized candidate, exact-dedupe result, up to three mapping options (each with `similarity` + `matchTier`), one bounded decision, stable reason code, and flags. The valid example is [fixtures/review-ready-packet.json](fixtures/review-ready-packet.json), with its [trusted snapshot fixture](fixtures/generic-snapshot.json).

The bounded Luna viability input is [fixtures/luna-viability-page.json](fixtures/luna-viability-page.json), with the separate oracle at [fixtures/luna-viability-expected.json](fixtures/luna-viability-expected.json). Its candidates exercise every precedence rule top to bottom: existing-generic strong match (`MAP`), weak-match adjudication (`DEFER`), no-match empty options (`NEW_GENERIC`), exact duplicate (`DUPLICATE`), malformed artifact (`NOT_A_SKILL`), ambiguous multi-capability bundle (`DEFER`), and copied/cited-origin skill (`DUPLICATE`). Each option on the page carries the pre-stamped `matchTier` the worker branches on — the worker never re-derives tier from the description. Give the worker only the input page, then compare against the oracle after the run. The verified Hermes/Luna result and usage receipt are recorded in [LUNA-VIABILITY.md](LUNA-VIABILITY.md). These fixtures are not registry inputs.

Stable validator codes include `MALFORMED_PACKET`, `MISSING_REQUIRED_FIELD`, `INVALID_CANDIDATE_ID`, `INVALID_LIFECYCLE_TRANSITION`, `MISSING_SOURCE_PROVENANCE`, `MISSING_FETCHED_PROVENANCE`, `INVALID_SOURCE_LANE`, `INVALID_SOURCE_URL`, `MISSING_FETCHED_FRONTMATTER`, `INVALID_CONTENT_HASH`, `INVALID_MAPPING_OPTIONS`, `TOO_MANY_MAPPING_OPTIONS`, `UNTRUSTED_GENERIC_SNAPSHOT`, `INVALID_GENERIC_SNAPSHOT`, `INVALID_DUPLICATE_PROOF`, `UNKNOWN_DECISION`, `INVALID_DECISION_STATE`, `INVALID_GENERIC_SELECTION`, `INVALID_NEW_GENERIC_PROPOSAL`, and `DOWNSTREAM_FIELD_FORBIDDEN`.

## L4 presentation requirement

At L4 the packet MUST show WHY the worker chose `MAP` vs `NEW_GENERIC` — both the **signal** (cosine `similarity` + `matchTier`) AND the **source** (which generic/named id it matched). This is the human ratification surface for all new topology (new generics, fusions, suites). The `mappingOptions[].similarity` / `mappingOptions[].matchTier` fields plus the matched id carry this WHY through from prefill → worker → L4 report.

## Human checkpoint

`/gaia-curate` writes each review-ready `discovery-packet-v2` JSON to `registry-for-review/discovery-packets/` (alongside the existing `registry-for-review/skill-batches/` intake). An L4 human reviews every `review-ready` row, all deferrals, and every proposed new generic. Shortlist acceptance is not registry acceptance. Stop after producing the L4 review artifact. Only after L4 may a separate intake/evidence workflow collect evidence or request registry changes.
