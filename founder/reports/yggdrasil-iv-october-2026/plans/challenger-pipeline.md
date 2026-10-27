# Challenger pipeline plan (EPIC #2189 outcome 3 + challenge part of 5)

Opus planner, read-only at `43797a441`, 2026-10-28.

## Gaps by stage
- **Lead** — exists: `src/gaia_cli/frontier.py` (validation, forged-authority refusal, dedupe key), schema `src/gaia_cli/data/frontier/challenger-lead-v1.1.schema.json` incl. native non-SKILL.md kinds. Missing: persistent dedupe ledger; tooling hard-coded to the git-log-L case (`examples/frontier/build_verification_request.py`, `record_experiment.py`).
- **Match** — missing: target is hand-entered; no registry candidate matcher; no "already registered elsewhere" flag (Graphify is `registry/named/safishamsi/graphify.md` under `knowledge-graph-build`).
- **Verify** — missing a machine-readable Meta verification record; receipts accept artifacts only under gitignored `generated-output/frontier` (`frontier.py:221`), so committed archives can't revalidate.
- **Admit** — correct fail-closed: `challengeDomain.open_challenge` needs bound resolver; production `GitHubActionsSource.fetch` raises `ReceiptUnavailable`. Missing: admission request + recorded `held` outcome; `_challenge_id_from_draft` private.
- **Project** — `produce_lifecycle` wired with `lifecycle_ports=None`; no truthful channel for non-admitted reviews.
- **Respond / recover** — post-admission functions exist; pre-admission: nothing (no response route, no append-only history).

## Honest boundary
Demonstrable on dev: lead → registry match → bound request → paired receipt → Meta verification record (separate session, independence *declared, unauthenticated*) → admission request → real admission attempt via production resolver → outcome `held: trusted-issuer-unavailable` → committed bundle re-validated at build → separate `gaia-challenge-review/v1` projection + API → neutral "admission held" disclosure. TM/stars/grade/Origin/leaderboard byte-identical (parity test).

Not demonstrable without issuer + governance admission: `trustLifecycle` challenge items, verified-pending, Origin-contested marker, closure, consequences. **Held items must never be labelled "contested"** (ratification §II).

Data: `evidence/frontier-challenges/<caseId>/` (lead, sources, protocol, request, receipts, artifacts, meta-verification, admission-request, events.jsonl, RUN.md, MANIFEST.sha256; README: non-canonical review records, not TM evidence) → `generateNamedIndex.py` `challengeReviews` (sibling of `trustLifecycle`) → `docs/api/v1/challenges/reviews.json` → `docs/js/challenge-review.js` in `#se-tm`.

## Founder decision packets
FD-1 held-review disclosure on dev (label, placement Explorer+API only, favorable reviews shown?, visual gate; recommend neutral, never the assay mark). FD-2 contributor notice/response route (drafts only, nothing sent). FD-3 independence standard. FD-4 issuer + Class C admission (existing gate). FD-5 cross-bucket comparison only if C1 substantiates.

## Real cases (pre-register rule, bind digest, then run; out-of-tree builds)
- C1 Graphify 0.8.13 vs `trailhq/graft` — callers of 5 pinned functions on `src/gaia_cli` at pinned SHA vs reviewed `ast` ground truth; substantiated iff recall ≥ incumbent+0.2 on ≥3 targets and precision ≥ incumbent−0.05; contradicted iff incumbent ≥ on all; else inconclusive.
- C2 Claude Code native `permissions.deny` (native-platform, no SKILL.md) vs `mattpocock/git-guardrails-claude-code` — 12 dangerous + 6 safe git commands incl. evasions; incumbent hook fed PreToolUse JSON; native via `claude -p --model haiku --settings` in disposable repo; ground truth = observed state change.
- C3 `git log -L` vs graft — expected negative; host Git 2.50.1 version mismatch ⇒ at most inconclusive; Meta: rejected, complementary scope.
- C4 ripgrep vs graft callers — rejected at triage (weak similarity), no experiment.
All-contradicted is a valid truthful result; no positive is manufactured.

## Slices (into `dev/yggdrasil-iv`)
1. `dev/yggiv-frontier-match-dedupe` — `src/gaia_cli/frontierMatch.py`, `gaia dev frontier match|dedupe`, tests.
2. `dev/yggiv-frontier-protocol-generic` — generic protocol-driven receipt builder, `artifact_root` param; git-log-L receipt byte-identical.
3. `dev/yggiv-meta-verification-record` — `meta-verification-v1.schema.json`, validator; skill mirrors emit it.
4. `dev/yggiv-challenge-admission-hold` — `src/gaia_cli/challengeAdmission.py`, append-only events, public `draft_challenge_id()`; no edits under `steward/`.
5. `review/meta/yggiv-challenger-cases` — Sonnet runs C1–C4; separate Opus session verifies; bundles + manifests.
6. `dev/yggiv-challenge-review-projection` — `challengeReviewProjection.py`, wiring, parity test, regen.
7. `design/yggiv-challenge-review-disclosure` — frontend, FD-1 + founder visual gate.
8. `dev/yggiv-frontier-docs-closeout` — docs, skill mirrors, FD packets.
