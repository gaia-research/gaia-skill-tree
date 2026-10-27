# Yggdrasil IV lifecycle projection contract (engineering only)

`gaia_cli.lifecycleProjection.produce_lifecycle(entry, ports)` produces the
`gaia-trust-lifecycle/v1` DTO. `scripts/generateNamedIndex.py::write_index`
accepts an optional in-process `LifecyclePorts`; the ordinary CLI passes none.
It removes any input `trustLifecycle` before optionally attaching the producer
output. The index is mirrored to `docs/graph/named/index.json` and consumed by
`docs/named/index.html` → `openExplorer()` → `#se-tm`. No production provider,
issuer, canonical migration or deployment is supplied by this increment.

## Trust boundary

`ChallengeSource.challenges_for(subject)` must return a complete immutable
challenge tuple, or `None` when unavailable. Empty is a verified empty set
only when the trusted source explicitly returns it. The source and
`VerificationReceiptResolver` are injected by trusted application code, not
loaded from a registry field or a fixture switch. Every challenge must match
the subject, be unique and have a domain-valid immutable history and receipts.
The producer rejects the complete projection on malformed or mismatched data;
it never hides one bad item and claims the remainder is complete.

`CanonicalConsequenceSource.consequence_for(subject)` separately supplies a
`CanonicalConsequence` or `None`. Its trusted adapter must establish the
subject, generic scope, coherent publication state and consequence authority.
`current-baseline` and `approved-decision` are distinct adapter outcomes;
`None` serializes as `unavailable`, never as an empty verified collection or
approval. Neither dataclass construction nor a caller-supplied dict, ID, hash,
URL, name, date or boolean authenticates the adapter. The adapter is a port,
not a proposed issuer implementation. Parent must align it with Sol's canonical
transactions and dual histories before activation. The DTO is a read projection,
not a schema adoption or canonical mutation.

The DTO carries exact subject and generic scope, linked challenge ID, claim,
comparison conditions, immutable domain event history, verifier receipt
references and materiality. Its contested bit aggregates all unresolved material
challenges. Technical closure never writes or restores rank, TM or Origin;
recalibration pending comes only from the consequence source. Existing rank,
Origin and history fields outside this DTO are not changed by the producer.
The consequence source must describe the same current hero metrics or the
producer fails closed. Missing consequence authority does not suppress valid
challenge history, but Origin ownership and numerical consequence stay unknown.

Browser validation rejects unsupported, malformed and contradictory DTOs; it
is **not authentication**. Only a correctly configured publication boundary
can attest the source. Direct calls with attacker-created JSON do not establish
trust. Synthetic test ports in `tests/fixtures/lifecycle_dto_test_ports.py` are
solely disposable tests and are never installed by production code.

## Held gates

No native rendered evidence has been captured. Capture the actual changed
`#se-tm` panel at desktop, 390px and 320px, including keyboard focus, with
fixture provenance clearly labeled. DOM tests are not screenshots. Independent
source review, coherent cross-surface publication alignment, genuine adapter
security, founder visual approval and rollout gates remain outstanding.
