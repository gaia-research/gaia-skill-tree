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

## Semantic retrieval and bounded prefill

Prefill (`gaia dev prefill`) performs deterministic retrieval over the skill corpus to supply **recall hints** to aid human evaluation. It embeds the candidate's `{name}: {description}`, retrieves the top nearest generics by cosine similarity, performs exact dedupe, checks artifact validity, and attaches mapping candidates with similarity scores and tiers (`strong|weak`).

### Normative semantic principles (replaces threshold-only rules)

Cosine similarity scores and threshold tiers are **retrieval recall hints, not normative ontology or identity**. They guide discovery rather than dictating ontology:

1. **Cosine similarity is a recall hint, not semantic identity or permission.** High similarity suggests an existing generic node to consider; it does not replace human domain judgment of whether the candidate's core capability is truly identical, subordinate, or distinct.
2. **No-match is not semantic novelty.** When `nTotal == 0` (no existing generic exceeds `weakMap`), this indicates an empty retrieval result in the current embedding space, NOT proof that the candidate is a genuinely novel universal primitive. Many candidates with zero matches are hyper-specific tools, vendor wrappers, or rephrased capabilities that belong under an existing generic or require rejection.
3. **Proximity flags are not fusion or suite proof.** Multiple high-similarity generic options (`IMPLIED_FUSION`) indicate multi-domain semantic overlap or phrasing ambiguity; they do not prove an implied fusion node is missing or required. Similarly, nearby named neighbor skills are advisory context, not an automatic suite declaration.
4. **Exact deduplication requires proof.** An exact duplicate decision requires matching canonical URL, cited origin, or exact SHA-256 content hash. A non-null dedupe object with `matched: false` is not a duplicate.
5. **Mandatory advisory principles receipt before L4.** Every prefilled candidate automatically receives a durable principles assessment receipt (`generated-output/curation/<candidate>.assessment.json`) evaluated against the versioned curation principles rubric (`src/gaia_cli/data/curation/principles.json`). This receipt evaluates source validity, packaging, neutrality, and ontological fit. An assessment receipt is mandatory input for L4 review.
6. **The machine never ratifies or makes an L4 decision.** Machine proposals, embedding ranks, and advisory outputs (including Jev sidecars) are strictly non-authoritative advisory context. Only an authorized human reviewer inspecting the candidate, the discovery packet, and the principles assessment receipt holds the authority to ratify topology.
7. **Historical viability fixtures are harness threshold tests, not gold ontology.** Older test fixtures (such as `luna-viability-page.json` and `luna-viability-expected.json`) capture historical test-harness threshold behaviors; they do not define canonical Gaia ontological ground truth.

The persisted generic snapshot still governs validation: persist the complete `gaia dev list --generic --json` array before worker dispatch, copy it into `genericSnapshot.generics`, record that exact command, and SHA-256 canonical JSON (`sort_keys=True`, compact separators) into `contentSha256`. Validate every mapped packet against that separate persisted JSON array: the validator rejects absent or mismatched trusted snapshots and mapping IDs absent from the receipt.

## Packet contract

Every new candidate uses `discovery-packet-v2`, specified by [schemas/discovery-packet-v2.schema.json](schemas/discovery-packet-v2.schema.json) and executable via [scripts/validate_discovery_packet.py](scripts/validate_discovery_packet.py). The validator retains `discovery-packet-v1` read compatibility, but v1 is not normative for new output. Validate a mapped packet with `python scripts/validate_discovery_packet.py --generic-snapshot generic-snapshot.json packet.json`; the generic snapshot is a required independent input, never inferred from the packet. The packet includes source provenance, hash, source-native trend signals, normalized candidate, exact-dedupe result, up to three mapping options (each with `similarity` + `matchTier`), one bounded decision, stable reason code, and flags. The valid example is [fixtures/review-ready-packet.json](fixtures/review-ready-packet.json), with its [trusted snapshot fixture](fixtures/generic-snapshot.json).

The bounded Luna viability input is [fixtures/luna-viability-page.json](fixtures/luna-viability-page.json), with the separate oracle at [fixtures/luna-viability-expected.json](fixtures/luna-viability-expected.json). Its candidates exercise every precedence rule top to bottom: existing-generic strong match (`MAP`), weak-match adjudication (`DEFER`), no-match empty options (`NEW_GENERIC`), exact duplicate (`DUPLICATE`), malformed artifact (`NOT_A_SKILL`), ambiguous multi-capability bundle (`DEFER`), and copied/cited-origin skill (`DUPLICATE`). Each option on the page carries the pre-stamped `matchTier` the worker branches on — the worker never re-derives tier from the description. Give the worker only the input page, then compare against the oracle after the run. The verified Hermes/Luna result and usage receipt are recorded in [LUNA-VIABILITY.md](LUNA-VIABILITY.md). These fixtures are not registry inputs.

Stable validator codes include `MALFORMED_PACKET`, `MISSING_REQUIRED_FIELD`, `INVALID_CANDIDATE_ID`, `INVALID_LIFECYCLE_TRANSITION`, `MISSING_SOURCE_PROVENANCE`, `MISSING_FETCHED_PROVENANCE`, `INVALID_SOURCE_LANE`, `INVALID_SOURCE_URL`, `MISSING_FETCHED_FRONTMATTER`, `INVALID_CONTENT_HASH`, `INVALID_MAPPING_OPTIONS`, `TOO_MANY_MAPPING_OPTIONS`, `UNTRUSTED_GENERIC_SNAPSHOT`, `INVALID_GENERIC_SNAPSHOT`, `INVALID_DUPLICATE_PROOF`, `UNKNOWN_DECISION`, `INVALID_DECISION_STATE`, `INVALID_GENERIC_SELECTION`, `INVALID_NEW_GENERIC_PROPOSAL`, and `DOWNSTREAM_FIELD_FORBIDDEN`.

## L4 presentation requirement

At L4 the packet MUST show WHY the worker chose `MAP` vs `NEW_GENERIC` — both the **signal** (cosine `similarity` + `matchTier`) AND the **source** (which generic/named id it matched). This is the human ratification surface for all new topology (new generics, fusions, suites). The `mappingOptions[].similarity` / `mappingOptions[].matchTier` fields plus the matched id carry this WHY through from prefill → worker → L4 report.

## Human checkpoint and ratification flow

`/gaia-curate` writes each review-ready `discovery-packet-v2` JSON to `registry-for-review/discovery-packets/` (alongside the existing `registry-for-review/skill-batches/` intake), and automatically emits an advisory assessment receipt to `generated-output/curation/<candidate>.assessment.json`.

An L4 human reviews every candidate row, all deferrals, proposed new generics, and the advisory assessment receipt. Shortlist acceptance is not registry acceptance.

### Canonical five-step curation flow

1. **Prefill (recall hints & automatic assessment receipt):**
   ```bash
   gaia dev prefill <candidate_id> --name ... --description ... --url ...
   ```
   Writes `registry-for-review/discovery-packets/<candidate>.json` and `generated-output/curation/<candidate>.assessment.json`.
2. **Optional live advisory evaluation:**
   ```bash
   gaia dev assess registry-for-review/discovery-packets/<candidate>.json --jev live
   ```
   Reruns principles evaluation with live Jev advisory advice if requested.
3. **L4 human review:**
   Human examines candidate SKILL.md, packet mapping options, and assessment receipt.
4. **L4 ratification (operator + human review attestation):**
   ```bash
   # For MAP the generic metadata flags are OPTIONAL and are resolved from the
   # live canonical node; supply them only to assert a value (mismatches are
   # rejected, so MAP can never rewrite canonical metadata).
   gaia dev ratify registry-for-review/discovery-packets/<candidate>.json \
     --decision {MAP,NEW_GENERIC} \
     --generic-id <generic-id> \
     [--generic-name <name> --generic-description <desc> --generic-type {basic,fusion}] \
     [--prereqs <a,b,c>] \
     --contributor <handle> \
     --skill-name <kebab-name> \
     [--skill-file-url https://github.com/owner/repo/blob/branch/SKILL.md] \
     --assessment generated-output/curation/<candidate>.assessment.json \
     --reviewed-by <user> \
     --approval-ref <ref> \
     --reason "<rationale>" \
     --acknowledge-human-review
   ```
   `NEW_GENERIC` requires `--generic-name`, `--generic-description` and `--generic-type`. Atomically attaches `l4Resolution` containing the ratified generic/named identities, blob URL, and `humanReview` attestation metadata. Requires operator override and explicit human acknowledgement; operator authorization alone is not L4 approval.

   **Enforcement boundary, stated honestly:** the CLI refuses to ratify without the acknowledgement flags and a fresh assessment, and `push --from-file` refuses any packet lacking `humanReview`. But `humanReview` is a *local file attestation* — it is not cryptographic proof that a human approved it. Anyone with write access to the packet can hand-write that block and intake will accept it on a machine where the gitignored receipt is absent. This seam is trusted to repository write access and maintainer review, not to mathematics.
5. **Intake submission:**
   ```bash
   gaia push --from-file registry-for-review/discovery-packets/<candidate>.json
   ```
   Validates the frozen snapshot and resolution, rejects exact canonical duplicates, and creates the intake issue.

## Optional semantic advisory sidecar (L4)

Before human L4 review, an operator may optionally run `python scripts/jev_advisory.py --mode mapping --input <packet.json>` or `gaia dev assess <packet.json> --jev live` to attach a non-binding semantic second opinion ([docs/agents/jev.md](../../../docs/agents/jev.md)). This advisory executes strictly outside the deterministic worker loop, cannot alter `matchTier` or decision precedence, and falls back gracefully. The L4 human gate remains the sole ratification authority.
