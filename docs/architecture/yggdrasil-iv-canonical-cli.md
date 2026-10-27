# Guarded canonical CLI integration — P3 engineering increment

This increment continues RFC #2148 / draft #2151 from transaction foundation
`b18bafb19cfba5af89845edf5e20ca3983d8dc8b`. It does not restart the campaign,
adopt schemas, authorize a live pilot or publish a canonical consequence.

## Source reuse

`evidenceLifecycle.py` is reused byte-for-byte, with its focused tests, from
`e75623416da27cd9695bcc39f2f024d4d41025ac`, stacked over the independently reviewed
`4aad305b34e00b30d2ff8ba42bc9a09e75641127` repair. This is selective source reuse,
not a cherry-pick of the held evidence/schema lane. Schema commit
`fa0ba3a9257682e76a57568358e2806391099f9c` is NOT adopted. The lifecycle core is a
proposal/rehearsal engine; production TM does not consume its assertion states.
The copied schema-acceptance test was adapted to assert the actual unadopted
schema refusal; no held schema was copied just to make a test green.

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
issuer activation, schema quorum, independent integration review, pilot selection,
visual review and main/release remain held.

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
