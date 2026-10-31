# Yggdrasil IV launch campaign — control file (EPIC #2189)

Recovery entry point. Updated on every material state change and pushed to
`dev/yggdrasil-iv-launch` (proof-of-work branch; lands into `dev/yggdrasil-iv`).

- Baseline: `dev/yggdrasil-iv` @ `43797a441` (all of `main` + IV lanes; #2151 CLEAN, CI green).
- Snapshot label: **provisional-2026-10-28**. Cutoff **2026-10-31T23:59:59Z**; the final
  record is regenerated from the same pipeline after the cutoff. Nothing before then is final.
- Lead: Opus 5.5 (Claude Code, macOS). Roster: Opus / Sonnet / Haiku, explicit effort always.
- Excluded: Steward implementation (EPIC #2189 exclusion).

## Live resumption — Sol High, 2026-10-30 UTC

This block supplements (does not erase) the recorded founder decisions below. Current lead is Sol High; optional workers/reviewers are Luna/Terra only, explicit effort, no worker turn limits. Lean autonomous execution; no new planning ceremony or Steward work.

- Preserved launch worktree verified at `329acaf82`; remote integration `f70b55e62`; production `dc0752888`. Default `~/gaia-skill-tree` checkout is old main with unrelated local edits and is untouched.
- Schema worktree was clean at `8aea82dd4`, three commits behind its remote `1c9613aee`; fast-forward reconciled. Repair `7baa3a148` exercises adopted schemas and explicit synthetic unadopted refusal fixtures; 155 focused tests reported passing, parent verification/current-SHA CI pending. No merge yet.
- Origin automation WIP `80150fff8` received independent Terra High **HOLD** before PR creation. Findings/evidence limitations: `verification/ORIGIN-AUTOMATION-REVIEW.md`. Repairs in progress on its existing feature branch; no PR yet. Promised ruling issue [#2267](https://github.com/gaia-research/gaia-skill-tree/issues/2267) filed as `nova-gaia`.
- Report presentation repairs continue on existing #2266; separate era metadata PR in preparation. No report/era approval or merge claimed.
- Agent GitHub operations switched to `nova-gaia`. No agent performed founder approvals, issuer approvals, main merge or release.
- Clock at resume `2026-10-30T18:22:54Z` is before October cutoff and the +72h witness deadline. Snapshot remains provisional; do not manufacture finalization.
- Release/rollback acceptance checklist and operator runbook: `verification/RELEASE-ROLLBACK.md` (preparation only; final-SHA rehearsal still required).

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

## Founder rulings 2026-10-30, late (verbatim, in session)

> "my last request of change management that includes /meta-post after everything requires Yggdrasil IV drop with the new challenger mechanic to be the highlight for October. This is the last piece of the puzzle. Find the dependencies for this as this is the user facing one and one that genuinely needs my eye before the big merge. Draft one in anticipation of all our decisions so far--so that final passes are more of sanity checks and verification of facts only. Commits on dev branch"
>
> "For my rulings, 1 is deferred. Lets change nothing, keep the cap but add a filed issue for audit.
> 2. origin ties mean two are origin. Very rare edge case since tm is a real number.
> 3. No more manual. Automatic from now on"

Applied as:
1. Suite sibling cap (META §2.1a, 50 TM per component): unchanged; audit issue filed. FD-7 suite linking stays automatic under the existing cap (founder earlier: "FD-7 should be automated").
2. Automatic Origin ties: every tied top contender holds Origin.
3. Origin is automatic; the IV ratification §IV manual "Origin transfer = Class C" path is superseded.

## Founder rulings 2026-10-30, rounds 2-4 and L4 (verbatim from the review page store)

| Decision | Choice | Note |
|---|---|---|
| r2-core-signoff | Yes, land both into dev |  |
| r2-general-video | Freeze |  |
| r2-graphify | Keep 5★ and change the rule | Uniques dont need a fusion prerequisite origin at all. Where did that come from? thats from suites. A lot of hallucinations lately, for uniques only it being the origin is required, tm is the usual gate. audit this and I dont want to see this issue again. |
| r2-hermes | Keep Origin, gather evidence | origin = "the original" with the highest merit. It is still the origin, it is just not "named". 2 star up is "named" and I have no rule about origins having a star requirement. |
| r2-main-merge | Hand it to me ready |  |
| r2-visual-2250 | Approve #2250 |  |
| r3-adj-evidence | Defer all three to November |  |
| r3-adj-judgement | Recommended | agent-reach is a really highly regarded skill. There is evjdence. Rederive |
| r3-fd17-leftovers | Remove the dead evidence rows now | dead evidence means either skill moved elsewhere or skill was superseded. If it was removed, freeze is the right option. If superseded or removed, renaming or editing the links is the better option. |
| r3-fd7-basis | Accept this basis |  |
| r3-origin-meaning | Highest merit (transfer) | why is this asked again?? document properly so agent never asks again. Origin is highest merit. Better if there is an automated system for this. File issue and fix before ship. |
| r3-structural | Discuss | Use recommended defaults first for L4, gather evidence, then meta audit deferred on november. These authors are verified with named skills. I expect the same treatment for new upstreams. File issue, ill fix the system to treat it like this on november. |
| r4-2257 | Approve #2257 |  |
| r4-audit | Acknowledged |  |
| r4-frozen-def | Also suites whose upstream is frozen | gaia dev freeze any node. |
| r4-peer-review-rows | Discuss | Check any articles related for actual peer reviews, or better since its google deepmind, actual papers (arxiv, etc) related. |
| r4-suite-membership | Discuss | Discuss the sibling cap. I dont recal having this. I think some skills have high TMs, and only the fusion is separated |

Founder message 2026-10-30 (verbatim): "Done. FD-7 should be automated, doesnt need my call anymore. Remove manual work on origins, make them automatic--only exceptions would be frozen contenders. Frozen skills lock the TM and grade, and they can beat live ones. Highest merit only."

### L4 topology choices (76; reviewer: founder, via the review page)

| Skill | Choice | Generic | Note |
|---|---|---|---|
| (7 parked drafts) | approve |  |  |
| addy-osmani/debugging-and-error-recovery | approve |  |  |
| addy-osmani/git-workflow-and-versioning | approve |  |  |
| addy-osmani/idea-refine | approve |  |  |
| addy-osmani/interview-me | approve |  | I do think we need to rrename the generic node to NOT be grill me, but have both as named skills |
| addy-osmani/using-agent-skills | decline |  | support |
| arcmira/find-quotes | approve |  |  |
| cathrynlavery/diagram-design | approve |  |  |
| cis2042/product-design-harness | new |  | product design plus design review fusion |
| emilkowalski/animate-expo | approve |  |  |
| emilkowalski/animate | approve |  |  |
| emilkowalski/animation-performance | new |  | fuse performance-tuning and an animation skill |
| emilkowalski/apple-design | approve |  |  |
| emilkowalski/break-ui | new |  | make a new generic, breaking ui should be different from auditing ui. Its like a fusion of red teaming and ui audit perhaps |
| emilkowalski/emil-design-eng | approve |  |  |
| emilkowalski/find-animation-opportunities | approve |  |  |
| emilkowalski/improve-animations | approve |  |  |
| emilkowalski/mobile-native | approve |  |  |
| emilkowalski/prototype | other | design-review | the same with design shotgun  |
| emilkowalski/review-animations | approve |  |  |
| emilkowalski/write-swift | approve |  |  |
| firecrawl/firecrawl-build | other | browser-automation |  |
| garrytan/article-enrichment | approve |  |  |
| garrytan/ask-user | approve |  |  |
| garrytan/brain-ingest-gate | approve |  | make sure this is prereq to the one that needs this skill. |
| garrytan/brain-link-discipline | approve |  | link as prereq. |
| garrytan/brain-pdf | approve |  |  |
| garrytan/brain-taxonomist | approve |  | prereq |
| garrytan/briefing | approve |  |  |
| garrytan/chat-connectors | other |  | maybe more chat integration or mcp related |
| garrytan/citation-fixer | approve |  |  |
| garrytan/cold-start | approve |  |  |
| garrytan/company-brainify | new |  | make a fusion of knowledge management and internal company knowledge generic or something |
| garrytan/correction-pipeline | approve |  | good skill |
| garrytan/cron-scheduler | approve |  |  |
| garrytan/cross-modal-review | approve |  |  |
| garrytan/daily-task-manager | approve |  |  |
| garrytan/daily-task-prep | approve |  |  |
| garrytan/data-loss-gate | approve |  |  |
| garrytan/db-repair | approve |  |  |
| garrytan/eiirp | approve |  |  |
| garrytan/enrich | new |  |  |
| garrytan/frontmatter-guard | new |  | fuse any frontend skill with knowledge management |
| garrytan/gbrain-advisor | decline |  | support |
| garrytan/gbrain-upgrade | approve |  |  |
| garrytan/google-loops | new |  |  |
| garrytan/idea-ingest | approve |  |  |
| garrytan/ingest | approve |  |  |
| garrytan/maintain | decline |  | maybe a support skill. |
| garrytan/mcp-access | approve |  |  |
| garrytan/media-ingest | approve |  | fusion of generative media and something |
| garrytan/migrate | decline |  | support skill. |
| garrytan/perplexity-research | approve |  |  |
| garrytan/postgres-adopt | approve |  |  |
| garrytan/publish | new |  | prereq, should be different from usual publish skill node |
| garrytan/query | new |  | hmm maybe a new search or query only lookup, prereq to the brain |
| garrytan/repo-architecture | other |  | maybe an architecture skill |
| garrytan/reports | approve |  |  |
| garrytan/resolve-before-asking | approve |  |  |
| garrytan/schema-author | approve |  |  |
| garrytan/schema-unify | approve |  |  |
| garrytan/setup | decline |  | support skill |
| garrytan/skill-creator | approve |  |  |
| garrytan/skillpack-check | decline |  |  |
| garrytan/skillpack-harvest | approve |  |  |
| garrytan/smoke-test | approve |  |  |
| garrytan/soul-audit | approve |  |  |
| garrytan/testing | approve |  |  |
| garrytan/voice-note-ingest | new |  | fusion of voice-agent and something |
| garrytan/webhook-transforms | other |  | hmm something else thats more webhook and fused with a brain related node |
| jpoutrin/create-plugin | approve |  |  |
| obra/diagnosing-superpowers | decline |  | support |
| obra/using-superpowers | decline |  | support |
| theqtcompanyrnd/qt-qml-review | approve |  | accepted but |
| yylo-dev/plan-ledger-tasks-yylo | approve |  |  |
| zhaoxuya520/reverse-skill | approve |  |  |

## Founder rulings 2026-10-30 (decision review page, verbatim from the store)

Recorded from https://claude.ai/artifact/W2YnN4Sa7Lgrki521tzbK3 (collection `choices`). Choice and note are the founder's own words.

| Decision | Choice | Note |
|---|---|---|
| challenger-outcome | Accept the negative result |  |
| core-2176 | Discuss | No core reviewers needed. There is only me who is maintaining this. Maybe nova-gaia or milim-gaia but those are also me. |
| fd-1 | Recommended: neutral, Explorer + API, all outcomes |  |
| fd-10 | Assign the four and review graphify | Graphify can be demoted if it fails 5 star. Review thoughtfully. |
| fd-11 | Promote to named |  |
| fd-12 | Raise to 4★ |  |
| fd-13 | Discuss | Review. This was one of the contributor skills named after them. Check if there really is a skill. If not, clear origin. |
| fd-14 | Gather evidence first | evidence |
| fd-15 | Regenerate |  |
| fd-16 | Recommended policy |  |
| fd-17 | Recommended |  |
| fd-18 | Review now |  |
| fd-6 | Yes, accept as offline proof |  |
| fd-7 | A · align leaderboard and ledger to the clamp | These skills should have trust magnitudes. Double-check what is causing this. Now for "frozen" skills leave them be. I know personal is a frozen skill. DO NOT touch frozen skills. Make sure any new closeout does not touch frozen. |
| fd-8 | Freeze | Gaia dev freeze. |
| fd-9 | Recommended: fix evidence, re-probe, no level action yet |  |
| issuer-env | Will create it now | created |
| main-merge | Discuss | Once meta audit is verified, merge is allowed. Dev calibration as a batch is the priority. |
| visual | Will review the preview | approved |

Standing rule from FD-7: **never touch frozen skills** in any batch calibration or closeout (e.g. `mattpocock/personal`).
L4 topology choices: none recorded yet.

## Pending founder decisions (accumulating packets)

- FD-6 sealed attested approval snapshot as durable offline approval proof (recommend yes).
- FD-7 39 named skills stored above the TM-grade ceiling (38×2★, 1×3★ ungraded): canonical calibration vs display reconciliation.
- FD-8 hyperframes: 12 components dropped upstream (all 3★, SHA-pinned links still resolve) — freeze or keep.
- L4: 59 intake candidates ready (`reconciliation/INTAKE-L4-PACKET.md` via #2199).
- Environment `challenge-receipt-issuer` settings (founder action, see `plans/issuer.md`).
- Machine: disk ≈2.7 GB free after removing finished worktrees; caches outside the campaign are the founder's call.

## Landed on `dev/yggdrasil-iv` (this campaign)

| PR | What | Review | Merge |
|---|---|---|---|
| #2190 | execution-control handovers + proof set | lead (docs only) | fa90e9d85 |
| #2191 | frontier match/dedupe | Sonnet HOLD → ACCEPT | 85fd1bf89 |
| #2193 | protocol-driven receipts | Sonnet HOLD → ACCEPT | 7d8f2d5f3 |
| #2196 | Meta verification record | Sonnet HOLD ×2 → ACCEPT-with-nits | 8279689cc |
| #2199 | intake triage + L4 packet (no admissions) | Sonnet ACCEPT-with-nits (fixed) | — |
| #2197 | October upstream sync (15 skills) | Sonnet ACCEPT-with-nits (fixed) | 9d3bdca35 |
| #2195 | W0 web consistency + content-engine fix + parity tests | Sonnet HOLD → fixed | 67a85524c |

Closed on dev: PRs #2170/#2171 (superseded by #2197); issues #1823 #2040 #2091 #2168 #2169 (synced by #2197); 38 stale intake issues (reconciliation lane).
In flight: #2192 W2 (ACCEPT, rebasing after #2195), #2200 W7 (ACCEPT-with-nits, fixing), #2198 issuer (HOLD: P0 bundled trust root, P1 unpinned post-approval code; repairing), cases C1–C4, sweep in verification.
Usage note: the session hit the account usage limit once (reset 07:40 Asia/Manila); sweep resumed automatically.
