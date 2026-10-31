# Yggdrasil IV launch campaign — handover (paused 2026-10-28, quota)

**Entry point for the next orchestrator.** Read this, then `CAMPAIGN.md` (rulings, defects,
landed table), then EPIC #2189. Mission and gates are in #2189; founder rulings in `CAMPAIGN.md`
§Founder rulings are binding. Lead was Opus 5.5 in Claude Code (macOS); roster Opus/Sonnet/Haiku
with explicit effort on every dispatch.

**Why paused:** the account hit its **weekly** limit (resets **2026-10-31 04:00 Asia/Manila** — the
same day as the October cutoff). Three agents died mid-task; their partial state is recorded below.
Nothing is half-merged. Machine disk ≈5 GB free after cleanup.

## ACTIVE CORRECTION — 2026-10-31, founder rejects invented worker gate

Founder explicitly corrected the attempted stop on optional worker availability: **it is not a campaign blocker**. The lead had misclassified a harness limitation as a hard dependency. Continue authorized engineering as lead; use Luna/Terra workers only where genuinely useful. No new founder ruling or permission questionnaire is needed, and the final report/merge approvals and genuine independent-verification requirements remain intact.

Origin's two observed checkpoint failures are repaired in **`cc700031b1e0c3bae0f88ba8248058d38a55f69b`**, pushed: restore the legitimate canonical-write guard import; prohibit Origin writes in the metadata writer; preserve frozen direct/suite member source bytes during metadata sync; replace the overbroad textual guard ban with guarded-runtime/unchanged-Origin/frozen-byte regressions; correct homepage/leaderboard Origin copy. Focused Origin/upstream/suiteRef regression: **59 passed in 0.59s**. Current verified schema/dev was then merged into the Origin branch without conflicts. Broader integration regression is in progress; **this is not a full Origin SHIP or PR/integration claim**.

The older route errors below are historical execution facts, **not a release gate and not justification to stop remaining work**. Resume at completion/verification of the Origin review findings, then the existing dependency spine.

## RESUME CHECKPOINT — 2026-10-31 UTC, Sol High (supersedes older state SHAs below)

Engineering is **not finished** and #2151 is **not founder-merge-ready**. No new governance decisions are requested. Existing founder rulings and all 76 L4 choices remain binding.

- **C DONE:** #2176 repaired at `7baa3a148fa9e593e627744b449cbbf732875834`; parent independently reran 155 tests (15.83s), inspected schema/test diff and verified all current-SHA checks passed/skipped. Merged through `nova-gaia` as `5bccf831624ad7fc4c2fbd60557a4240d7ac8a45` (2026-10-31T07:02:37Z). Recorded founder r2 sign-off was cited, not impersonated. Engineering receipt: https://github.com/gaia-research/gaia-skill-tree/pull/2176#issuecomment-6540383537.
- **Checkpoint tests collected:** report presentation `b0a34be5e`: **6 passed**, whitespace/JS syntax exit 0 (no rendered acceptance). Origin `bcca9552a`: **2 failed, 51 passed**; undefined/unimported `guardCanonicalPath` call remains in generator writer and stale chronological-Origin copy remains on homepage/leaderboard. Exact failures and source evidence: `verification/CHECKPOINT-TESTS.md`. Do not integrate or weaken tests to hide these defects.
- **A remains HOLD:** initial independent Terra High source review in `verification/ORIGIN-AUTOMATION-REVIEW.md`; promised issue https://github.com/gaia-research/gaia-skill-tree/issues/2267 filed. Preserved Origin branch now **`bcca9552a`**, pushed, no PR. It includes `784e73ba3` (old dev merge), `043befcdb` (remove WIP source/generated churn), and an explicitly unreviewed repair checkpoint. It still needs completion, exact-SHA independent review, current-dev schema merge, full tests/build/parity/frozen-byte evidence, then PR/green integration. Do not treat the checkpoint as an accepted repair.
- **E remains founder-gated:** #2266 now **`b0a34be5e`**, pushed WIP presentation/source/generation checkpoint; no merge. Source work addresses table scrolling/count definitions, but real rendered acceptance, final facts/markers and independent verification remain. Separate draft era metadata PR **#2268**, `schema/yggiv-era` at **`5009a587e`**, has 2 focused tests and mirror-structure validation; held with report/era approval, not merged.
- **H preparation only:** new existing worktree `~/.gaia-worktrees/l4`, `review/meta/yggiv-l4-october` at **`53a99b0e3`**, pushed, no PR. Contains interrupted `scripts/prepare_l4_october.py` (syntax check passed) and source ruling copy. No completed packet/evidence batch, ratification or canonical L4 execution is claimed. Large generated embedding churn was preserved separately in Git stash **`f2cc12a42b849a477fd8362ffc0841ac79d1437c`** (apply only to this L4 worktree after inspecting it; do not drop it or confuse it with other stashes).
- **Launch proof:** schema/current-dev ancestry merged into the preserved launch branch at **`dbc19d05e`**; `verification/RELEASE-ROLLBACK.md` contains a truthful preparation runbook, not a completed final-SHA rehearsal.
- **Operational blocker:** authorized workers could not continue. OpenAI subscription-sharing and Codex routes exhausted; configured Vercel API route returns 403 billing-verification-required; GitHub Copilot Luna returns model-not-supported; configured OpenRouter route returns 401 User not found. No credentials, global configuration or billing were changed. Old child session JSONL files were distilled away, so resume IDs now fail before model use; consume the committed worktree diffs rather than repeatedly attempting those missing transcripts. Resume with a functioning authorized Luna/Terra route, without a new model fanout or configuration changes by the agent.
- Default checkout `~/gaia-skill-tree` has unrelated user edits and remains untouched. Agent GitHub writes use **nova-gaia**; active auth had reverted to founder across the pause and was explicitly switched back before integration. Never approve deployments or founder gates through agent auth.
- Clock at 2026-10-31T07:00Z is still before **2026-10-31T23:59:59Z** cutoff and **2026-11-01T16:40Z** witness deadline. No final snapshot/refresh or +72h completion is claimed.

**Next:** finish A → B (#2251) → D (#2259) → fresh independent calibration PASS (`verification/CALIBRATION-REVERIFICATION.md`, not yet created) → G approvals-ledger regeneration/check → H full L4 CLI/evidence/topology batch. Then cutoff/witness refresh when due → resolve #2266 facts/markers → actual founder review + W8/W9 → final rollback/release proof/launch PR/#2189 update/#2151 readiness. No red-CI merges; do not merge #2266 or #2151 autonomously.

## PAUSE STATE — 2026-10-31 ~01:00 Manila (session tokens exhausted; supersedes the in-flight table below)

All subagents stopped. Nothing is half-merged. Every worktree's work is committed and pushed (WIP commits labelled).
`dev/yggdrasil-iv` = `f70b55e62` (includes #2264 dedup fallout: dev fast gate + Schema/DAG should be green again).
Founder rulings since the FINISH PLAN was written (all in CAMPAIGN.md, `17fd2ac93`): sibling cap unchanged + audit
issue #2263; Origin ties → all tied hold Origin; Origin is automatic, no manual path. October post drafted (#2266).

| # | Item | Branch / worktree | Exact state | Next action |
|---|---|---|---|---|
| A | Origin automation + rule fixes (Unique 5★ prereq-Origin removed, no Origin star floor, ties share Origin, suite-wide freeze, docs) | `dev/yggiv-origin-automation` @ `80150fff8`, `~/.gaia-worktrees/origin`, **no PR** | **WIP, UNREVIEWED.** One commit holding new `src/gaia_cli/origin.py`, `frozen.py`, `tests/test_origin_rule.py`, code in promotion/helpers/named/freeze/sensors/generateNamedIndex/leaderboard/build_docs/validate/run_meta_sweep, docs (META, GOVERNANCE, CLAUDE, CONTEXT, README, ratification notes, 4 skills ×2 mirrors), ~200 `registry/named/*` Origin-flag rewrites, and regen output | Merge dev in; split generated noise out; verify (a) no frozen file touched, (b) registry edits are what the automatic rule yields (ideally Origin is derived at build time so named files need no flag edits — confirm the design), (c) tie rule = all tied hold Origin, (d) ratification §IV superseding note present; file issue "Origin is automatic (highest merit)" (not yet filed); run tests; independent adversarial review; open PR; merge |
| B | #2251 October calibration | `review/meta/yggiv-october-calibration` @ `aa9bc3239`, `~/.gaia-worktrees/calib` | Done: FD-8/9/10/11/12/14/15/17/18, C1a+C1b suite links (all 37 now capped), C2 tests, graphify revert, general-video freeze, agent-reach re-derived, FD-17 leftovers (redesign-skill relinked, output-skill frozen), peer-review rows retyped honestly (workflow-skill-creator TM 100.82→59.65 B, stored 4★ = review debt; browser-harness similar) | Verify PR body is current; merge dev in after A lands; regen; merge |
| C | #2176 schema (founder Core sign-off) | `dev/yggdrasil-iv-evidence-schema-final` @ `1c9613aee` | CI red: 3 tests still assert the schema is UNadopted (`test_canonical_cli.py::test_production_refuses_unadopted_schema_without_writes`, `test_canonical_review_repairs.py::test_unadopted_schema_and_invalid_output_have_distinct_refusals`, `::test_schema_adoption_gaps_names_the_missing_fields`) | Update those tests to the adopted state (keep the refusal path tested with a synthetic unadopted schema fixture); CI green; merge |
| D | #2259 clamp alignment (option A) | `dev/yggiv-clamp-alignment` @ `3bd9de0cc` | Ready; must follow B | Merge dev in after B, regen ledger+leaderboard together, merge |
| E | #2266 October Meta Post (IV drop) + W8 era wording + Origin legend fix | `docs/yggiv-october-post` @ `9cba53f4e`, `~/.gaia-worktrees/post` | Draft with 13 `[[VERIFY]]` markers + facts ledger `docs/meta/2026-10-YGGDRASIL-IV.FACTS.md`; screenshots `~/.gaia-worktrees/post-evidence/`. **Founder-gated, do not merge.** | Before founder review: (1) fix shared report template table overflow at 390px (#2265) in `scripts/add_post.py`, re-render; (2) homepage stats strip shows "— NAMED / — ULTIMATES" dashes and hero "96 named" vs stats 352 — find cause/definitions; (3) contributor counts disagree (about 59 / API 43 / listing 65) — cite the public contributors page definition; (4) separate `schema/yggiv-era` PR adding era IV to `registry/schema/meta.json` + `src/gaia_cli/data/registry/schema/meta.json`. Then resolve every `[[VERIFY]]` after steps 6–9 below, re-render, preview, founder review |
| F | Calibration re-audit (founder's main-merge condition) | — | Not started | After A+B+D merge: fresh independent Opus-class auditor → `verification/CALIBRATION-REVERIFICATION.md`; must PASS |
| G | Adjudication ledger approvals regen | launch branch, `adjudication/tools/` (WIP `c35b1b69b`) | WIP edits from the A run, unreviewed | Review the WIP; add approvals input from CAMPAIGN rulings; regenerate; `--check` |
| H | L4 batch (76 founder choices) | — | Not started | FINISH PLAN step 8 |
| I | Cutoff refresh (after 2026-10-31T23:59:59Z) + mattpocock witness +72h (2026-11-01T16:40Z) | — | Not started | FINISH PLAN step 9 |
| J | W9 screenshot matrix, rollback plan, launch-branch PR into dev, #2189 update, #2151 handed ready | — | Not started | FINISH PLAN steps 11–12 |

Order: C (independent) · A → B → D → F → G → H → I → resolve E markers → founder reviews E (+ W9) → J.
Never merge on red CI; gate merges on `gh pr checks` with no `fail`. Founder merges #2151.

## FINISH PLAN — read this first (2026-10-30 21:30 Manila, roster-agnostic)

Any orchestrator (any model) can finish from here. Environment: macOS, `python3` (no `python`, no `timeout`),
`PYTHONPATH=src`, `GAIA_OPERATOR_OVERRIDE=1` for `gaia dev` verbs, worktrees under `~/.gaia-worktrees/`.
Commit identity: `git -c user.name="Marcus Rafael B. Tiongson" -c user.email="153011150+mbtiongson1@users.noreply.github.com"`.
Founder rulings are binding and recorded verbatim in `CAMPAIGN.md` (three tables, 2026-10-28 and 2026-10-30 x2, plus 76 L4 choices).
Founder review UI: https://claude.ai/artifact/W2YnN4Sa7Lgrki521tzbK3 (db collection `choices`; repo rule in CLAUDE.md
§ "Founder review packets", #2249). Read choices back with ArtifactData, record verbatim in CAMPAIGN.md, then act.

### Gap review against the original EPIC #2189 brief

| # | Outcome | State | What is left |
|---|---|---|---|
| 1 | October Meta re-audit + per-record ledger | ✅ provisional (`sweep/`, 701 records) | Cutoff refresh after 2026-10-31T23:59:59Z (step 9) |
| 2 | Upstream + PR reconciliation | ✅ ledger, #2197 sync, intake triage | Cutoff re-run of `reconciliation/upstream-sync-commands.sh`; **execute the 76 L4 choices** (step 8); close intake issues once landed on dev |
| 3 | Real challenger pipeline (+/− cases) | ✅ 4 real cases, Meta-verified, all non-admitted (founder accepted the negative); issuer env created | Boundary on record: watcher bridge does not pass proofSourceSha (#2256 comment); challenge watch stays gated off |
| 4 | Adjudication / consequence ledger | ✅ built (`adjudication/`) | Regenerate with an approvals input linking each candidate to the CAMPAIGN rulings (approved ≠ 0 now; FD-16 superseded by automatic Origin; FD-13 keep) (step 7) |
| 5 | Full IV website | ✅ W0, W2, W7, W3–W6 (#2250 founder-approved, merged) | #2259 clamp alignment (step 5); stale "first published" Origin copy (verify origin PR fixed site legend + GOVERNANCE:64); **W8** era III→IV messaging after the October post + founder approval; **W9** screenshot matrix 1440/390/320/focus across all IV surfaces, founder visual evidence (step 11) |
| 6 | October record + Meta Post (gaia-post), explicit Oct 31 cutoff | ❌ not started | Step 10 |
| 7 | Integrate to dev, release + rollback readiness, update #2189 | ⏳ | Rollback plan, land `dev/yggdrasil-iv-launch` into dev by merge-commit PR, update #2189, hand #2151 to the founder **ready** (founder merges; "Hand it to me ready") (step 12) |

Main-merge condition (founder): the calibration Meta audit must PASS. First audit = **FAIL**
(`verification/CALIBRATION-VERIFICATION.md`); corrections in flight; a fresh re-audit is required (step 6).

### In-flight at snapshot time (check each; agents may or may not have finished)

| Work | Branch / worktree | Done when |
|---|---|---|
| #2257 dedup fallout: refresh 6 TM caches + tests pinned to old dedup (dev fast gate + Schema/DAG are RED until this lands) | `dev/yggiv-dedup-fallout`, `~/.gaia-worktrees/fallout` | PR open, CI green, merged |
| #2176 schema (founder signed off as Core): add/add conflict `tests/test_evidence_lifecycle.py` | `dev/yggdrasil-iv-evidence-schema-final`, `~/.gaia-worktrees/schema` | conflict resolved, CI green, merged |
| Origin automation + rule fixes (provenance report already pushed `2ecf57fed`) | `dev/yggiv-origin-automation`, `~/.gaia-worktrees/origin` | PR open with Origin change list; GitHub issue "Origin is automatic" filed; reviewed; merged |
| #2251 founder items: graphify revert (stays 5★), general-video freeze, agent-reach re-derive, FD-17 leftovers (moved→relink, removed→freeze), peer-review research (workflow-skill-creator, browser-harness) | `review/meta/yggiv-october-calibration`, `~/.gaia-worktrees/calib` | commits pushed, PR body updated |
| #2259 clamp alignment (option A) | `dev/yggiv-clamp-alignment`, `~/.gaia-worktrees/clamp` | merge AFTER #2251 + regen |

### Ordered steps to the finish

1. Land the dedup fallout PR (dev green again). Never merge on red CI: gate merges on `gh pr checks` having no `fail` (lesson: #2257 merged red).
2. Land #2176 (schema) after its conflict fix.
3. Review (independent, adversarial) and land the Origin automation PR. Founder items it raises: the **tie rule**
   (proposed: incumbent among the tied keeps; else no Origin) and the IV ratification §IV "Class C Origin transfer"
   wording being superseded — put both on the review page as one card each.
4. #2251: merge dev in (merge commit), re-run `gaia dev docs`, drop anything the automation made redundant
   (FD-10 manual Origin flags stay harmless; hermes keeps Origin by merit). **FD-7 suite linking for 23 garrytan + 2 obra
   is blocked on the founder's sibling-cap discussion** (`verification/RULE-PROVENANCE.md` §(d): the 50-TM per-component
   cap is in META §2.1a since Ygg III PR #1629; founder recalls only the fusion being separated). Put that on the
   review page as a decision with both consequences; founder said FD-7 linking should then be automatic.
5. Merge #2251, then refresh #2259 (merge dev, regen ledger + leaderboard together) and merge it.
6. Fresh independent Meta re-audit (new session, Opus-class) of everything calibrated since the FAIL; write
   `verification/CALIBRATION-REVERIFICATION.md`. PASS is the founder's main-merge condition.
7. Adjudication ledger: add an approvals input (CAMPAIGN rulings) to `adjudication/tools/build_adjudication.py`, regenerate, `--check`.
8. L4 batch (curation PR on `review/meta/`): for the 76 choices in CAMPAIGN.md — 53 approve → `gaia dev ratify`
   with reviewer = founder and approval ref = CAMPAIGN.md L4 table; 5 "other" → map per note (pick the closest existing
   generic, list picks for the founder only if none fits); 10 "new" → new generics/fusions per the notes (prereqs as
   noted); prereq links for brain-ingest-gate / brain-link-discipline / brain-taxonomist; interview-me: rename the
   grill-me generic so both are named implementations; 8 decline (support skills) → close their intake issues with the
   reason. Skip frozen. Then evidence (`ev-*`), regen, Meta audit deferred to November (#2261).
9. After 2026-10-31T23:59:59Z: re-run `reconciliation/upstream-sync-commands.sh`, `sweep/tools/prepass.py` diff vs the
   provisional snapshot, liveness re-probe (`--concurrency 3`), mattpocock/skills witness +72h probe (due
   2026-11-01T16:40Z); relabel provisional → final without rewriting the frozen snapshot.
10. October record via the `gaia-post` skill (`.claude/skills/meta-post/`, `scripts/add_post.py`): Meta audit summary,
    per-skill ledger link, reconciliation, challenger results (all non-admitted), adjudication (proposed vs approved),
    calibration + audits, changelog, explicit cutoff. Draft first; founder approves. `/gaia-release` for notes only.
11. W8 era messaging (`docs/js/site-nav.js:54-60`, `docs/index.html:463,:564`, `docs/heroes/index.html:62`, hero post)
    after step 10 + founder approval; W9 screenshot matrix via `/gaia-preview` + local server; renders as throwaway
    local HTML (never Artifact); decision packets as Artifact.
12. Rollback plan (revert-merge recipe for #2151, registry restore point = main tip before merge), land
    `dev/yggdrasil-iv-launch` into dev, close issues genuinely closed on dev, update #2189, hand #2151 to the founder ready.

### Hazards
- Class P `registry/gaia.json` carries a stale version (8.28.1); regen stamps it into `ledger/data.json` — keep 8.29.1
  (the check normalizes it) and never commit `docs/graph/gaia.json` when only the stamp moved.
- Regen noise never to commit: `layouts_3d.json`, `docs/og/*`, `docs/api/v1/trending/*` (incl. untracked history),
  `docs/okf/`, `docs/badges/registry.json`.
- Frozen skills are never touched (frozen on the node or via a frozen suite; `gaia dev freeze` any node).
- Cite META/GOVERNANCE/ratification lines before enforcing any gate; three agent-invented rules were found (provenance report).
- Integration branches: merge, never rebase; check conflicts with `git merge-tree --write-tree --name-only`.
- This Mac's `gh` is the founder's account: agents could approve issuer deployments as the founder.
- Subagents hit session limits twice; resume them by message rather than restarting; commit per item.

## 0c. Resume log (2026-10-30, later)

- Merged to dev: #2234 cases `39eb288d9`; #2255 main sync (#2133, #2230, v8.29.1; least-privilege watcher split) `f92b887fb`;
  #2256 watcher admission + CI coverage + health `ba140cc39`; #2258 live-reviews test `8bfc540ff`. dev->main conflict-free.
- Independent Meta audit of #2251: **FAIL** (verification/CALIBRATION-VERIFICATION.md, `cc67dddb1`). FD-7 refuted (no suiteRef ->
  37 skills escape the 50-TM sibling cap). C2 tests fixed on #2251 (`4220b0af3`). C1 root cause: generateNamedIndex erases
  CLI-set suiteRef not listed in a suite manifest -> fix PR `dev/yggiv-suiteref-guard` in progress; then set suiteRef on the
  12 addy-osmani skills (timeline already says set); 23 garrytan + 2 obra await founder (review page Round 4).
- Open, held for founder: #2250 (visual), #2251 (graphify confirm, FD-16 48 Origins, audit corrections), #2257 dedup fix
  (SHIP; browser-harness peer-review row + META wording), #2259 option A clamp alignment (merge AFTER #2251, regen).
- Review page rounds 2-4 unanswered; L4 choices none. Main merge blocked until audit corrections pass a re-audit.

## 0b. Resume log (2026-10-30)

- Founder rulings recorded in CAMPAIGN.md §Founder rulings 2026-10-30 (review page https://claude.ai/artifact/W2YnN4Sa7Lgrki521tzbK3,
  db collection `choices`; Round 2 questions added, unanswered at time of writing; L4 choices: none yet).
- Repo rule landed (#2249): founder review packets ship as an Artifact. Memory: never touch frozen skills.
- Merged to dev: #2248 projection reads Frontier layout `61c2284d7`; #2249 rule `8547d23c5`; #2253 review channel +
  wording `087da01bf`; #2252 CLI gaps (apex refresh, calibrate gate pre-flight, actor fix, save_tree) `7b672a854`.
- Open, reviewed: #2234 cases (head `63201adbb`, --check 0; 4 neutral reviews), #2250 website W3-W6 (SHIP; founder visual
  approval pending; preview deployed from `8437cdcac`), #2251 October calibration (FD-8/9/10/11/12/7/14/17 committed;
  FD-15/16/18 in progress; graphify 5->4 awaits founder confirm).
- main moved (#2133, #2230, v8.29.1) -> #2151 conflicts in ~15 files. Sync PR `dev/yggiv-sync-main` (merge, not rebase)
  in progress. MERGE ORDER after it lands: #2234 -> #2251 -> #2250 (each: merge dev in, regen, --check, merge).
- Then: independent Meta verification of the calibration batch (founder's condition for main merge), FD-7 option A
  display alignment (code PR), October post (gaia-post), cutoff refresh after 2026-10-31T23:59:59Z, #2189 update.

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
