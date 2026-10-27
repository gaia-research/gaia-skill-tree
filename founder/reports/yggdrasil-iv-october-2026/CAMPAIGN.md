# Yggdrasil IV launch campaign — control file (EPIC #2189)

Recovery entry point. Updated on every material state change and pushed to
`dev/yggdrasil-iv-launch` (proof-of-work branch; lands into `dev/yggdrasil-iv`).

- Baseline: `dev/yggdrasil-iv` @ `43797a441` (all of `main` + IV lanes; #2151 CLEAN, CI green).
- Snapshot label: **provisional-2026-10-28**. Cutoff **2026-10-31T23:59:59Z**; the final
  record is regenerated from the same pipeline after the cutoff. Nothing before then is final.
- Lead: Opus 5.5 (Claude Code, macOS). Roster: Opus / Sonnet / Haiku, explicit effort always.
- Excluded: Steward implementation (EPIC #2189 exclusion).

## Lanes

| Lane | Outcome | Plan | State |
|---|---|---|---|
| Meta sweep (13 dims + per-record appraisal of 701 records) | 1 | `sweep/` | running — Workflow run `wf_fb1ee3fb-d06` |
| Upstream / PR / intake reconciliation | 2 | `reconciliation/` | ledger done (313); #2190 landed (fa90e9d85); #2197 upstream sync (15 skills; supersedes #2170/#2171); #2199 intake triage (90: 59 ready-for-L4, 17 needs-info, 1 reject, 7 dup, 6 by-sync); 38 stale intakes closed |
| Challenger pipeline (frontier match → verify → admission → projection) | 3 | `plans/challenger-pipeline.md`, `plans/issuer.md` | #2191 landed (85fd1bf89); #2193/#2196 repairing after review; #2198 issuer in security review; cases C1–C4 running |
| Adjudication / consequence ledger | 4 | derives from sweep ledger | after sweep |
| Website (W0..W9) | 5 | `plans/website.md` | W0, W2, W7 dispatched |
| October record + `/meta-post` (registered as `gaia-post`) | 6 | — | after 1–4 |
| Integration / release readiness | 7 | — | continuous |

## Recovery

- Sweep Workflow resume: `Workflow({scriptPath: "~/.claude/projects/-Users-marcotiongson-gaia-skill-tree/873dce0c-9f78-4e5a-b06d-610d69445003/workflows/scripts/october-2026-meta-sweep-wf_fb1ee3fb-d06.js", resumeFromRunId: "wf_fb1ee3fb-d06"})` (same session only). Durable fallback across sessions: per-batch shards `sweep/batches/*.ledger.json` are written to disk as each auditor finishes — rerun only batches whose shard is missing or short.
- Deterministic pre-pass: `sweep/prepass.json` (generator: `sweep/tools/prepass.py`), registry revision 43797a441: 400 named files (352 indexed, 48 awakened), 301 generic nodes (152 basic, 149 fusion), 874 evidence rows, 0 deterministic star-gate violations.

## Defects found so far (engineering, in scope)

- D1 `gaia dev docs` content-engine step fails on dev: `ModuleNotFoundError: publication_context` (regression from #2172) → W0.
- D2 `docs/api/v1/health.json` version 8.26.10 vs 8.28.1; 65 profile pages `?v=8.26.10` (not in cache-bust list) → W0.
- D3 `trust-lifecycle.js` loaded only on 2 of the pages that load `skill-explorer.js` → W2.
- D4 `leaderboard.json` has no `generatedAt` though `leaderboard.js` reads it → W0.
- D5 `docs/badges/registry.json` stale (missing `nvidia`) — warn-only, human-curated badge lane.
- Anomaly: one `awakened` named file at 4★ — `google-deepmind/workflow-skill-creator` (grade A, `origin: true`), sits only in `awaitingClassification`, absent from every public list (W0 #2195 finding).
- D6 cross-surface level disagreement: 39 ungraded skills show 2–3★ on ledger/leaderboard but 1★ in named index + skills API (the 268→229 gap). Pinned by strict xfails in #2195. Cause: `scripts/generateNamedIndex.py:617` clamps the projected level to the TM-grade ceiling (S6/A4/B3/C2/ungraded1, #1729, 2026-09-05) while ledger/leaderboard publish the stored level. Prepass: exactly 39 named skills stored above ceiling (38× 2★ ungraded, 1× 3★ ungraded). Core adjudication candidate set (outcome 4) — deterministic Ygg III gate, not IV decay; canonical calibration or display reconciliation is a founder decision (FD-7).
- D1/D2/D4 fixed in #2195 (W0), pending review.

## Founder decision packets (accumulating)

FD-1 held-review disclosure on dev; FD-2 contributor notice route; FD-3 independence standard;
FD-4 issuer + Class C admission (existing gate); FD-5 cross-bucket comparison if C1 substantiates;
plus existing: #2176/#2177 two Core approvals, visual acceptance, main merge, release, launch.

## Founder rulings this campaign

- **2026-10-28 — "approved issuer for dev"** (founder, in session, replying to the FD-4 packet:
  contested marks require the trusted challenge issuer). Scope as interpreted: build and activate
  an authenticated challenge-receipt issuer for the `dev/yggdrasil-iv` integration environment,
  confined to the receipt-source adapter (`src/gaia_cli/steward/challenge_receipts.py`
  `AuthenticatedApprovalSource` + its producer workflow). This is the one authorized exception to
  the Steward exclusion; no Steward sensors, watcher, scheduler, transport or policy changes.
  Production publication of anything it admits still rides the founder-gated `main` merge.
  Each admitted challenge still needs its own authenticated approval; the issuer approval is not
  a blanket admission of any case.
- **2026-10-28 — founder clarification:** "Right now only me--I'm the only operator. Don't
  overcomplicate the issuer approval. I'm leaning towards steward automating this--see issue
  trails. For any issues you genuinely closed on dev, close it once it lands on dev. I'll still be
  the one merging to main after my checks." Applied: single-operator issuer (founder as the one
  authenticated approver), simplest GitHub-authenticated mechanism, pluggable so Steward can
  automate later (RFC #2148 D8 trail) without Steward work now. Issues genuinely fixed by a PR are
  closed when that PR lands on `dev/yggdrasil-iv`, not at the main merge.

## Pending founder decisions (accumulating packets)

- FD-6 sealed attested approval snapshot as durable offline approval proof (recommend yes).
- FD-7 39 named skills stored above the TM-grade ceiling (38×2★, 1×3★ ungraded): canonical calibration vs display reconciliation.
- FD-8 hyperframes: 12 components dropped upstream (all 3★, SHA-pinned links still resolve) — freeze or keep.
- L4: 59 intake candidates ready (`reconciliation/INTAKE-L4-PACKET.md` via #2199).
- Environment `challenge-receipt-issuer` settings (founder action, see `plans/issuer.md`).
- Machine: disk ≈2.7 GB free after removing finished worktrees; caches outside the campaign are the founder's call.
