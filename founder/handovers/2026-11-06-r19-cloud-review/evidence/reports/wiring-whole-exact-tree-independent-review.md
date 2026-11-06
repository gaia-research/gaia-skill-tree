# Independent whole-feature review of exact-tree candidate — BLOCKED

## Status and actual route

**BLOCKED.** The required actual route is `openai/gpt-6.1-terra` HIGH, with no Codex substitution. The current harness exports **`PI_PROVIDER=openai-codex`**, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`. The provider is therefore not the required provider; no fallback or provider-side attestation is claimed. This is an actual route mismatch, not a conclusion that the source is defective. A reviewer on the required route must resume and perform the requested audit; this report grants no source acceptance.

## Candidate and limited observations

- HEAD `314fdf655edb7a6cb9bd131461bc11952366979d`, tree `e53b5920571b1458a6b6d0bde1fe454f57c7b411`; `git status --porcelain` returned no entries.
- Read the new `exact-tree-export-repair-proof.md`, full `tests/steward/prmaintenance/test_exact_tree.py`, and the `e7f1933...` to HEAD `proofs.py` diff and stat. That stat identifies only `proofs.py` and `test_exact_tree.py` changed. This is preliminary inspection, not a review finding or certification.
- No fresh tests or probes were executed in this turn, and no parent long-test evidence, hashes, exits, failure logs or packaging evidence was audited. Prior reports and their described tests remain historical evidence at their cited SHAs, not fresh passes at 314f. The requested old/new expected-invariant check and full source/consumer/safeguard audit remain unperformed.
- No candidate source, prior report or real state was modified. No live GitHub, namespace, clock, legacy or coordination-ledger operation, activation, migration, writer drain, installation, push or merge was performed.

## Findings and verification limits

No source finding is asserted from this blocked partial inspection. The route mismatch prevents fulfilling the mandated independent review; it must not be treated as a clean or accepted whole-feature audit. The parent-reported four zero-exit groups have not been independently verified or relabeled as this reviewer's results. No claim is made for real time, server protections, exactly-once delivery or liveness.

The separate owner gates remain: explicit activation; independently provisioned namespace/genesis and verified protection; trusted clock; retirement/drain of bypassing writers; historical shared-Git campaign transition; and the separate before/after founder gate for changed visible CLI output. None is waived by this report.
