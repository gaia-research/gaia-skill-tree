# Yggdrasil IV launch campaign — handover (paused 2026-10-28, quota)

**Entry point for the next orchestrator.** Read this, then `CAMPAIGN.md` (rulings, defects,
landed table), then EPIC #2189. Mission and gates are in #2189; founder rulings in `CAMPAIGN.md`
§Founder rulings are binding. Lead was Opus 5.5 in Claude Code (macOS); roster Opus/Sonnet/Haiku
with explicit effort on every dispatch.

**Why paused:** the account hit its **weekly** limit (resets **2026-10-31 04:00 Asia/Manila** — the
same day as the October cutoff). Three agents died mid-task; their partial state is recorded below.
Nothing is half-merged. Machine disk ≈5 GB free after cleanup.

## 0. Resume log (2026-10-29, resumed session)

- Step 0 DONE: #2231 merged into dev `1e0a27984` (CodeQL regex). #2151 re-running.
- Step 1 DONE: adjudication ledger `adjudication/` (`ea47c5ed7`, `be42d5371`): 190 candidates, 65 proposed-with-numbers,
  125 needs-decision, 0 refuted, 0 approved, no level change proposed; packets FD-7, FD-9..FD-18 in `DECISIONS.md`.
- Step 2 IN REVIEW: PR #2232 (`dev/yggiv-challenge-admission`, worktree `~/.gaia-worktrees/admit`). First adversarial
  review HOLD (5 P1: receipt replay across cases, receipt not binding bundle digest, symlink writes, GAIA_RECEIPT_* env
  overrides honoured, machine-dependent bytes; 7 P2). Author agent repairing; needs re-review before merge.
- Step 3 DONE (not landed): cases on `review/meta/yggiv-challenger-cases` (worktree `~/.gaia-worktrees/cases`; uncommitted
  regen noise there is NOT to be committed). Runner: C1 contradicted (tie), C2 substantiated (narrow), C3 inconclusive,
  C4 rejected at triage. Independent Opus Meta verification `6807ef4be`: C1/C3/C4 upheld, C2 downgraded to
  inconclusive; recommendAdmission false for all → no issuer tag, no admission this month (truthful negative).
- Frontier tooling defects found by the verifier (copy check blocks honest reruns, receipt not binding trace, local-time
  timestamps labelled Z, batch-written events, no triage-stage meta record) → fix PR in progress
  (`dev/yggiv-frontier-verify-fixes`, worktree `~/.gaia-worktrees/fverify`).
- Next after those land: open cases PR into dev (after #2232), then steps 4–7.

- PAUSED AGAIN 2026-10-29 (usage limit). Landed on dev: #2231 `1e0a27984`, #2232 admission+projection `cf49bada5`
  (3 review rounds → SHIP), #2233 frontier verify fixes `f37562750` (2 rounds → SHIP).
- Cases PR #2234 open (`24d9e65d7`): Meta verdicts final (C1 contradicted, C2 inconclusive, C3 inconclusive, C4 rejected
  at triage; recommendAdmission false all; C4 triage record + timestamp errata). Public delta is ZERO because the
  #2232 projection rejects all 4 bundles (layout drift: receipts/experiment-receipt.json vs receipt.json; C3 id has
  uppercase L failing CASEIDRE; triage-only C4 has no request path; rejections not surfaced by `gaia dev docs`).
  NEXT: small dev PR making the projection read the frontier bundle layout (and lowercase-tolerant or alias for C3,
  triage cases → review entries) + surface rejections in `gaia dev docs`; then merge #2234. FD-1 still open.
- Website W3–W6 agent STOPPED mid-task on `design/yggiv-challenge-surfaces` (remote head: not pushed;
  worktree `~/.gaia-worktrees/web`, may hold uncommitted work — inspect before reuse). Re-dispatch with the same brief.
- Then steps 4 (W9 screenshots), 5 (October post), 6 (cutoff refresh after 2026-10-31T23:59:59Z), 7.

## 1. State

- `dev/yggdrasil-iv` = `d237c0839` (merge of #2198). Contains all of `main`.
- **#2151 (dev → main) is NOT green**: one CodeQL high alert, `tests/test_trust_lifecycle.js:473`
  `assert.doesNotMatch(html, /<script>|<img/)` — "bad HTML filtering regexp (no upper-case)".
  Test-only. Fix: `/<script|<img/i` (and the matching `assert.match` if needed). First task.
- Only open PR into dev: #2176 (schema, held on two Core approvals; #2177 stacked, held).
- Proof-of-work branch: `dev/yggdrasil-iv-launch` (this directory). It is based on `43797a441`
  and only adds `founder/reports/yggdrasil-iv-october-2026/**`; land it into dev with a merge-commit
  PR once the October record is assembled (it is not yet a PR).
- Worktree kept: `~/.gaia-worktrees/yggiv-launch` (clean, Class P generated). All others removed.

## 2. Done (all on dev unless noted)

| Item | Ref |
|---|---|
| Execution-control handovers + proof set | #2190 `fa90e9d85` |
| Frontier match/dedupe → protocol receipts → Meta verification record | #2191 `85fd1bf89`, #2193 `7d8f2d5f3`, #2196 `8279689cc` |
| Intake triage + L4 packet (90 items: 59 ready-for-L4, 17 needs-info, 1 reject, 7 dup, 6 by-sync; no admissions) | #2199 |
| October upstream sync (15 skills; superseded #2170/#2171) | #2197 `9d3bdca35` |
| W0 web consistency, content-engine fix, parity tests (2 strict xfails pin real data defects) | #2195 `67a85524c` |
| W2 lifecycle panel on every explorer page | #2192 `8fd9a8387` |
| W7 evidence provenance renderer | #2200 `491306053` |
| Challenge-receipt issuer for dev (founder-approved; 3 adversarial rounds) | #2198 `d237c0839` |
| Full October Meta Sweep (701 records, 817 verified findings) | `sweep/` on this branch |
| Reconciliation ledger (313 items) | `reconciliation/` |
| Issues/PRs closed on dev | #2170 #2171; #1823 #2040 #2091 #2168 #2169; 38 stale intake issues |

Every merged PR had an independent Sonnet review; HOLDs were repaired and re-verified before landing.

## 3. Next steps, in order (nothing below has started unless stated)

0. **Fix the CodeQL alert** (above) in a tiny PR into dev; confirm #2151 all green.
1. **Adjudication / consequence ledger (EPIC outcome 4).** Partial: `adjudication/tools/adjcore.py`
   (deterministic in-memory recompute core). Build `tools/build_adjudication.py`, `ledger.json`,
   `LEDGER.md`, `DECISIONS.md` from `sweep/findings.json` (surviving findings in dimensions rank,
   unbacked-star, unique-isolation, origin, origin-attribution, champion(-cluster),
   reclassification, grade-mismatch, structural, plus the two `mattpocock/skills` P0s) and the D6
   39-skill set. Per candidate: before (stored + every public surface) → proposed (Gaia-code
   recompute) → affected deps → verified evidence (finding keys/votes) → required decision →
   approved = held (0 approved). Packets to write: FD-7 (39 skills), mattpocock/skills evidence +
   witness, Unique-branch 4★/5★ without bucket Origin (graphify, vercel-react-best-practices,
   addy-osmani/code-simplification, ayghri/i-have-adhd, dietrichgebert/ponytail), workflow-skill-creator
   awakened@4★, latent-spaces/brag 3★ meeting 4★ (promotion also needs approval), xquik 1★ origin.
2. **Challenge admission + projection** (merged plan: challenger C-4/C-6, issuer slice 2, website W1).
   Not started (the agent died before editing). Brief: `gaia dev challenge admit|build-request`,
   `committedChallenges.py` ports wired into `scripts/generateNamedIndex.py`, `challengeProjection.py`
   → `docs/graph/challenges/index.json` + `docs/api/v1/challenges/index.json` (`gaia-challenge-projection/v1`,
   `sourceStatus` unavailable|verified-empty|verified; held reviews only as labelled `reviews[]`),
   parity test (numbers byte-identical with/without challenges), no-synthetic guard. See
   `plans/website.md` §Data contract, `plans/issuer.md`, `plans/challenger-pipeline.md` slices 4/6.
3. **Real challenger cases C1–C4** (`plans/challenger-pipeline.md` §Real cases). Not started.
   Runner (Sonnet) builds leads/protocols/receipts on `review/meta/yggiv-challenger-cases` from dev;
   a SEPARATE fresh Opus session writes `meta-verification.json` (independence is declared, not
   authenticated). Then, if a case recommends admission: founder creates the environment, a tag
   `challenge-receipt/<case>-r1` is pushed by `nova-gaia`, founder approves in the web UI, `admit`.
4. **Website W3–W6** after step 2 (leaderboard contested mark with byte-identical bars, ledger/history,
   challenge detail page under `trust/`, Origin surfaces), then **W9** screenshot matrix
   (1440/390/320/focus) via `/gaia-preview` one at a time; renders shared as throwaway local HTML
   (never Artifact). **W8** (III→IV era messaging: `docs/js/site-nav.js:54-60`, `docs/index.html:463,:564`,
   `docs/heroes/index.html:62`, hero post) only once a truthful IV report exists + founder approval.
5. **October record (EPIC outcome 6)** via the `gaia-post` skill (`.claude/skills/meta-post/`,
   `scripts/add_post.py`): Meta Audit report from `sweep/`, per-skill ledger link, upstream/PR
   reconciliation, challenger findings, adjudication (proposed vs approved = 0), changelog, explicit
   cutoff. Draft only; do not claim IV live. `/gaia-release` for changelog/readiness only.
6. **Cutoff refresh on/after 2026-10-31T23:59:59Z:** rerun `reconciliation/upstream-sync-commands.sh`
   (ruflo already at v3.63.6), re-run `sweep/tools/prepass.py` and diff vs the provisional snapshot,
   re-probe liveness (`--concurrency 3`), relabel provisional → final. Do not rewrite the frozen snapshot.
7. Update #2189 with exact evidence + remaining founder decisions; refresh `/gaia-preview`; leave
   #2151 ready (founder merges to main).

## 4. Founder decisions pending

Create environment `challenge-receipt-issuer` (reviewer mbtiongson1, prevent self-review off,
admin bypass off, tags `challenge-receipt/*` only, no secrets) **before any tag push**; FD-6 sealed
approval snapshot as offline proof (recommend yes); FD-7 39 skills above grade ceiling; FD-8
hyperframes 12 dropped components freeze/keep; L4 on 59 intake candidates; FD-1 held-review
disclosure on dev; two Core approvals for #2176/#2177; visual acceptance; main merge; release.
Security note: this Mac's `gh` is logged in as `mbtiongson1` (repo+workflow scope) — any agent can
approve deployments as the founder; switch agent sessions to `nova-gaia` before issuer use.

## 5. Lessons for the next run

- Budget: the 701-record sweep cost ~52M subagent tokens (642 agents). Remaining lanes are smaller;
  dispatch serially after the reset, Sonnet `medium` where possible.
- Never trust a model synthesis of large data: rebuild from the workflow journal
  (`sweep/tools/rebuild_from_journal.py`); the synthesis agent's counts were wrong (810 vs 817).
- First review round HOLD'd almost every security-relevant PR; keep independent adversarial review.
- Disk fills fast with worktrees (~160 MB each + Class P); remove on merge.
