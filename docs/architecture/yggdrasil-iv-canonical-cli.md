# Guarded canonical CLI integration — P3 engineering increment

This increment continues RFC #2148 / draft #2151 from transaction foundation
`b18bafb19cfba5af89845edf5e20ca3983d8dc8b`. The lifecycle schemas are adopted
on this integration branch under the founder's recorded r2-core-signoff ruling;
that ruling is not a fabricated GitHub review approval. This increment still does
not authorize a live pilot or publish a canonical consequence.

## Source reuse

`evidenceLifecycle.py` is reused byte-for-byte from
`e75623416da27cd9695bcc39f2f024d4d41025ac`, stacked over the independently reviewed
`4aad305b34e00b30d2ff8ba42bc9a09e75641127` repair. Its focused tests
(`tests/test_evidence_lifecycle.py`) are reused with ONE intentional change:
`test_proposed_schema_validates_both_legacy_and_migrated_evidence` is inverted to
`test_unadopted_schema_refuses_migrated_evidence`. The adopted production schema
now validates lifecycle rows; the corresponding refusal coverage installs the
committed synthetic missing-field schemas only into a marked disposable test
repository. The lifecycle core remains a proposal/rehearsal engine; production TM
does not consume its assertion states. The actual validator and its input-context
schema digests are exercised, with no schemaPolicy monkeypatch or permissive `{}`
lifecycle overlay. Separate negatives show that valid adopted-schema output still
cannot authenticate an approval, while genuinely invalid output produces a distinct
refusal. Fixture provenance/digests are documented under
`tests/fixtures/canonical-unadopted-schema/`.

## Authority and limits

The ratification, META.md and GOVERNANCE.md remain authoritative. The current
Frontier ruling was read from `origin/dev/yggdrasil-iv` (founder records #2167):
Frontier discovers, Meta evaluates, Steward maintains, Governance decides.
Implementation and disposable fixtures do not authenticate governance approval.
Yggdrasil III formulas, weights, thresholds, Fusion Score, live stars, Origin and
historical records are unchanged. No global configuration or security activation.

The cooperative lock protects participating writers, not unlocked readers or
external side effects. Multi-file replacement is journaled/recoverable, not an
OS-atomic multi-file publication or external exactly-once guarantee. Publication,
issuer activation, independent integration review, pilot selection, visual review and
main/release remain held.

## Native command surface

`gaia --registry <repository> dev canonical` exposes `plan --request`,
`validate --plan`, `apply --plan`, `status`, and `rollback --plan --journal`.
Preparation is read-only; validation is not approval. The production approval
resolver remains unavailable, and no CLI/environment fixture-provider switch
exists. Fixture grants in `tests/fixtures/` are explicitly not issuers.

## Platform boundary

The ordinary CLI, including help and legacy writers, must not gain an unconditional
POSIX-only import. Cooperating legacy writers use `fcntl.flock` on POSIX or the
standard-library `msvcrt` byte lock on Windows; absence/failure of a lock backend
fails closed. A failed acquisition is never treated as a held lock or unlocked.

Durable canonical **apply/rollback remain POSIX-only**: the Windows legacy lock
adapter does not establish recoverable directory-fsync semantics. These canonical
operations refuse before recovery metadata or target writes when POSIX capability
is absent. Read-only preparation/status does not authenticate an approval.

Platform-capability regression tests include an actual native CLI help invocation
with `fcntl` unavailable and explicit Windows-adapter doubles. The latter are
unit evidence, **not native Windows runtime certification**. Existing real POSIX
two-process contention/crash tests remain in the expanded suite.
