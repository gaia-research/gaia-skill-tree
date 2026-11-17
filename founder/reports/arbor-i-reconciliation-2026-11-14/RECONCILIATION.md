# Arbor I reconciliation: founder integration gates (2026-11-14)

**Status:** review and engineering handoff; NOT a claim of completed code repair, test execution, cross-vendor review, or merge authorization.  
**Integration branch:** `dev/arbor-i-reconciliation-2026-11-14` (initially at `086d385bdd499a59cd0ab4047fcd57d01ba8f050`).  
**Affected PR:** [#2439](https://github.com/gaia-research/gaia-skill-tree/pull/2439), head `8aeed7ef64c3b07f4c656ebbeb89d6d4dc84435e`.  
**Canonical work:** [#2441](https://github.com/gaia-research/gaia-skill-tree/issues/2441) and [#2440](https://github.com/gaia-research/gaia-skill-tree/issues/2440); consumer documentation [gaia-skill-heaven#253](https://github.com/gaia-research/gaia-skill-heaven/issues/253).

## Inventory and independence of gates

On 2026-11-14, GitHub listed four open PRs in gaia-skill-tree: #2439 Arbor, #2450 release v9.5.0, #2445 Steward calibration, and #2436 documentation routines. The Arbor PR had diverged from main (five commits ahead, 34 behind at inspection), with its previous graph and package CI green at its older HEAD. Those historical CI results do **not** establish current integration readiness.

- #2450 release is mergeable at the Git ref level but its workflow runs report `action_required`. A retry of Validate Gaia Graph run 43431753485 was rejected with 403, "This workflow run cannot be retried". Do not merge until GitHub Actions can run and the required checks pass.
- #2445 carries a **scoped 2026-11-13 founder ruling** for manual disposition of the unchanged one-record 2★→3★ calibration. The missing original Steward scan/dispatch/proof receipt is **not** verified and may not be recreated. This is not approval to merge to main: use a fresh integration wave, Class S regeneration and checks, plus founder review.
- #2436 is a documentation draft; its diff against current main has seven net docs files, eight branch-only commits and 11 commits behind. Consolidate after structural reconciliation.

## Arbor I invariants to preserve

1. Every canonical Gaia Skill Tree skill is an Arbor subject. A skill with no Arbor record is **not excluded**, just not yet declared.
2. `expert-declared` is a source-backed hypothesis, never proof of a benchmark, a Hell-Heaven stamp, or invocation authorization. A missing accepted HH record remains `absent-no-accepted-record`; `pairsEvaluated` stays 0 for an all-declaration seed.
3. Canonical skill records, identities, and history are not merged, deleted, replaced, or silently re-curated by Arbor. `duplicates` describes behavioral overlap only.
4. Attribution: source skill owner(s) are primary, the drafting agent is supporting author, founder is governance. Neither the source owner nor founder is claimed to have endorsed agent-authored claim wording unless independently documented.
5. Yggdrasil's structural/fusion graph and Arbor's behavioral interactions remain **different evidence types**. Structural composition may inform a *candidate hypothesis* to be examined, but must not silently become an observed Arbor edge, governed interpretation, or HH result. Schema changes, structural source ingestion, and whether/where to compute `structuralOverlap` require an explicit reviewed contract decision.
6. No benchmarks, acceptance stamps, materialized Ultra behavior, or automatic permission changes in the seed PR.

## Blocking engineering work: #2441

### Pin identity and durability
Current `arbor.py` pins `contentSha256` to the entire `registry/named/<owner>/<slug>.md` canonical record, which includes trust evidence and timeline. Thus a prestige-only change invalidates the consumer's behavioral join. Conversely, upstream instructions behind mutable `main` URLs can change without changing the canonical file hash.

**Required behavior:** a prestige-only edit retains valid behavioral knowledge; a behavior-changing upstream instruction edit cannot silently keep its old applicable claim. Keep historical declarations immutable. Do not rebind old declarations as if they were authored against new bytes. Evaluate versioned behavioral source identity or a governed carry-forward protocol with explicit immutable provenance and fail-closed handling of unavailable upstream bytes. This is a contract/consumer decision requiring tests and independent review, not a prose-only fix.

**Required regression controls:** append only a timeline event; add only trust evidence; change a source `SKILL.md`; change a canonical instruction link; remove or make upstream unavailable. Test effect on claims, endpoint matching, edge applicability, historical profiles, and runtime consumers. Include generic nodes and cross-owner edge pairs, not just current same-owner seeds.

### Projection atomicity and CI
Current `gaia dev docs` rebuilds `docs/graph/arbor` but not the registry runtime/edge projections, while `gaia dev arbor replay` updates registry files. The normal workflow does not directly assert `gaia dev arbor check`. This can produce drift or unexpected failures in unrelated curation changes.

**Required behavior:** one documented, deterministic projection operation maintains all tracked Arbor output, or an explicitly ordered and enforced pipeline does. Add a CI check for registry Arbor projection freshness and the published docs projection. No automatic timestamp churn; no silent mutation in read-only CI. Test that a curation change to an edge endpoint fails closed or is regenerated deterministically.

## Declaration seed #2439 review gate

- Retain the 20 skills, 27 claims, and 3 source-declared relations only if all authoritative source bytes, exact citations, author attribution, and canonical pins still match after integration.
- Examine the low-confidence `garrytan/qa` model-led and `caioribeiroclw-pixel/evidence-attestation` claims particularly closely, per the author's own handoff.
- Preserve the unresolved stop-rule precedence for `systematic-debugging` recovering `executing-plans` as an explicit caveat, not a chosen policy. Leave `guard` / `careful` / `freeze` comparisons as test candidates.
- Require the declared source/observation/governed interpretation/Hell-Heaven separation in both the raw store and consumer projections.
- Recheck every surviving claim against immutable cited source bytes; handle missing upstream sources honestly.
- Run `gaia dev arbor check`, relevant Arbor pytest suites, `python scripts/build_docs.py --check`, schema/integrity checks, and required PR CI on the final integrated HEAD.
- Fresh independent review is required. The prior handoff reports that Pi `@parke.dev/pi-subagent` and Terra reviewer were unavailable and native Sonnet subagents were substituted; this was disclosed but is not proof of an approved cross-vendor review. Preflight model/provider/effort, permissions, and bounded worker roster; no silent fallback or automatic escalation.
- Respect branch topology: feature PRs into a `dev/*` integration branch; integration PR into `main` requires founder review and green final checks. Do not mark a historical green CI run as current proof.

## Execution order

1. Clear release PR #2450's GitHub Actions approval/execution requirement if authorized. Validate version/generator lockstep and green final checks, then consider merge. This is **separate** from Arbor approval.
2. Land a reviewed #2441 repair of identity, applicability, projection, and CI in feature PR(s) targeting the integration branch.
3. Reconcile #2440's documentation and explicitly mark unsettled contract questions; cross-repo document cleanup in Skill Heaven #253 follows the actual ratified contract.
4. Refresh and independently inspect #2439 against fresh main and the integration changes. Integrate only after its seed is valid under the repaired contract.
5. Publish the integration→main PR and request founder review. No automatic merge or stamp.
6. Deliver #2445 on its own Steward integration wave with the existing founder disposition, and consolidate #2436 separately after its seven net docs changes are verified.

## Required worker handoff

Each implementer must push an isolated feature PR plus a self-contained handoff covering implementation, authoritative governance, branch base and HEAD SHA, exact tests and CI links, independent reviewer findings, and open blockers. Final report format: PR (#/URL), Commit (HEAD SHA), Handoff (repo path), Status (READY FOR REVIEW / BLOCKED). Do not merge on behalf of the founder unless separately authorized for the final reviewed HEAD.
