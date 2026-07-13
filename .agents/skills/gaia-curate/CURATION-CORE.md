# Gaia Discovery Curation Core

This is the canonical read-only contract for `/gaia-curate`, `/gaia-curate-chain`, and `/gaia-curate-dynamic`. It is a discovery compiler, not a registry mutation workflow. Extensions may orchestrate packets but may not change this lifecycle or cross the L4 stop.

## Lifecycle and boundary

Process exactly one candidate at a time:

`discovered → fetched → parsed → normalized → deduped → mapped → review-ready | deferred | rejected`

`fetched` requires an actually fetched upstream `SKILL.md`; `parsed` requires non-empty `name` and `description` frontmatter. Preserve source facts only: canonical URL, host repository, cited origin, available commit SHA/content hash, and source-native trend signals. Do not collect evidence, score evidence, assign grades/classes, calculate Trust Magnitude, calibrate stars, mutate the registry, regenerate docs, commit, push, or create a PR.

## Bounded mapping

Query generics programmatically before mapping:

```bash
gaia dev list --generic --json
```

Perform exact dedupe on canonical URL and content hash before proposing at most three existing-generic options. A worker may emit exactly one decision:

`MAP`, `NEW_GENERIC`, `DUPLICATE`, `NOT_A_SKILL`, or `DEFER`.

It may not invent generic IDs, assign type beyond an L4-reviewable Yggdrasil II `basic|fusion` proposal, or use free-form acceptance language. `MAP` must select one supplied ID. `NEW_GENERIC` carries only a proposed name, falsifiable description, and `basic|fusion` type; deterministic downstream intake assigns or validates the canonical ID. Invalid or ambiguous worker output is recorded as `DEFER` with `DEFER_INVALID_PACKET` or `DEFER_AMBIGUOUS_OUTPUT`; it never becomes an inferred mapping.

## Packet contract

Every candidate uses `discovery-packet-v1`, specified by [schemas/discovery-packet.schema.json](schemas/discovery-packet.schema.json) and executable via [scripts/validate_discovery_packet.py](scripts/validate_discovery_packet.py). The packet includes source provenance, hash, source-native trend signals, normalized candidate, exact-dedupe result, up to three mapping options, one bounded decision, stable reason code, and flags. The valid example is [fixtures/review-ready-packet.json](fixtures/review-ready-packet.json).

The bounded Luna viability input is [fixtures/luna-viability-page.json](fixtures/luna-viability-page.json), with the separate oracle at [fixtures/luna-viability-expected.json](fixtures/luna-viability-expected.json): existing-generic implementation, exact duplicate, malformed artifact, ambiguous capability, and copied/cited-origin skill. Give the worker only the input page, then compare against the oracle after the run. The verified Hermes/Luna result and usage receipt are recorded in [LUNA-VIABILITY.md](LUNA-VIABILITY.md). These fixtures are not registry inputs.

Stable validator codes include `MALFORMED_PACKET`, `MISSING_REQUIRED_FIELD`, `INVALID_CANDIDATE_ID`, `INVALID_LIFECYCLE_TRANSITION`, `MISSING_SOURCE_PROVENANCE`, `MISSING_FETCHED_PROVENANCE`, `INVALID_SOURCE_LANE`, `INVALID_SOURCE_URL`, `MISSING_FETCHED_FRONTMATTER`, `INVALID_CONTENT_HASH`, `INVALID_MAPPING_OPTIONS`, `TOO_MANY_MAPPING_OPTIONS`, `UNKNOWN_DECISION`, `INVALID_DECISION_STATE`, `INVALID_GENERIC_SELECTION`, `INVALID_NEW_GENERIC_PROPOSAL`, and `DOWNSTREAM_FIELD_FORBIDDEN`.

## Human checkpoint

An L4 human reviews every `review-ready` row, all deferrals, and every proposed new generic. Shortlist acceptance is not registry acceptance. Stop after producing the L4 review artifact. Only after L4 may a separate intake/evidence workflow collect evidence or request registry changes.
