# Semantic curation implementation checkpoint

Branch: `dev/curation-semantic-system`. Owner: Astra; final merge: Marco only.

## Architecture decisions

- Keep `gaia dev prefill` as recall and `gaia dev ratify` as the post-L4 seam. Add `gaia dev assess` for a non-authoritative, durable principles receipt. No automatic canonical mutations.
- Cosine thresholds are retrieval hints, not identity or permission. Empty recall does not prove novelty; multiple neighbors do not prove fusion. Source validity, exact duplication, packaging and semantic identity are separate questions.
- Consolidate existing META/Yggdrasil/GOVERNANCE doctrine in a versioned, packaged contract, `src/gaia_cli/data/curation/principles.json`. No changes to Trust Magnitude, star gates or canonical topology.
- Assessment receipts live in caller-controlled ignored output, separately from discovery packets. They bind candidate/source, semantic packet inputs, rubric and generic semantic definitions. Machine proposal never writes `l4Resolution`.
- Reuse the existing Jev client, ledger, cache and limits. Explicit opt-in live calls; bounded typed questions; failures/disagreement remain visible. Never equate a fallback handoff with execution of another agent.
- Ratification records an explicit human reviewer, approval reference and rationale; checks the assessment against current semantic inputs before writing. Local receipts are auditable attestations, not cryptographic proof that a human used a terminal. Operator authorization alone is not L4 approval.
- Declare embedding model/revision/backend/config in `src/gaia_cli/data/curation/retrieval.json`. Preserve MiniLM until a Gaia corpus and real Termux measurement justify migration. Candidate model evaluation is opt-in.
- Invalidate embeddings by sorted semantic rows + encoder identity/config, not dates, stars, evidence or unrelated edits. Preserve compatible APIs; fail visibly on stale/mismatched artifacts.
- Add a small provenance-labelled oracle and evaluation runner. Historical human cases and synthetic regression probes must never be conflated. Report unavailable metrics as unavailable rather than zero.
- Repository-owned setup, doctor, maintenance and real Termux smoke paths use the declared model and shared caches, never a laptop-specific path. Maintenance is read-only by default, does not run paid advice, and rebuilds only on explicit request with semantic staleness.

## Current truth inspected

Starting point `301a14268` (v8.17.1), including Jev PR #2029 and dogfood PR #2031. Relevant historical issues: #1482 Termux, #1675 retrieval, #1677 browser boundary, #1483 product coupling, #1801/#1803 attribution, #1809 over-purge, #1906 probabilistic SHOULD vs MAY, #1922 stewardship.

The existing ratify implementation is already human-intended. The existing curation core's threshold-only decision policy conflicts with useful semantic assessment; it will be reconciled while keeping historical packet readers compatible. No canonical registry node changes are planned.

This checkpoint records architecture, not a claim that implementation or validation has completed. Final measured outcomes belong in the branch handoff receipt.
