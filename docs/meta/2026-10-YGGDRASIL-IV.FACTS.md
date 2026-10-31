# Facts ledger: October 2026 Yggdrasil IV Meta Report

Companion to `docs/meta/2026-10-YGGDRASIL-IV.md` (rendered as `docs/meta/reports/2026-10-31-yggdrasil-iv-a-challenge-must-be-earned-and-standing-can-recover.html`). **Not linked from the site.** It is the founder's checklist for the final fact pass. Each entry gives the claim, its value as drafted (2026-10-30), the source, a one-line re-verify command and whether it moves.

Conventions:
- `L` = `origin/dev/yggdrasil-iv-launch:founder/reports/yggdrasil-iv-october-2026` (proof-of-work branch). Read with `git show "$L/<path>"`.
- Commands run from a worktree of this branch with `PYTHONPATH=src`, after `git fetch origin`.
- "Moves" values: **stable** (fixed record), **cutoff** (refreshed after 2026-10-31T23:59:59Z), **merge:<PR>** (changes when that PR lands), **L4** (changes when the L4 batch executes).
- Every `[[VERIFY]]` marker in the post maps to an entry marked ⚑ below. Resolve all ⚑ entries and remove every marker before merge.

```bash
L=origin/dev/yggdrasil-iv-launch:founder/reports/yggdrasil-iv-october-2026
```

## A. Framing and doctrine

**F1. Cutoff statement.** "Results through 2026-10-31T23:59:59Z; figures before the cutoff refresh are provisional."
- Value: cutoff 2026-10-31T23:59:59Z; snapshot label provisional-2026-10-28; registry revision `43797a441`.
- Source: `$L/CAMPAIGN.md` header; `$L/sweep/COVERAGE.md` line 3.
- Verify: `git show "$L/CAMPAIGN.md" | sed -n 6,9p`
- Moves: stable (text); the relabel to final is ⚑F2.

**F2 ⚑. Cutoff refresh ran; snapshot relabelled final.**
- Value now: NOT run (cutoff not reached).
- Source: `$L/HANDOVER.md` FINISH PLAN step 9 (upstream sync rerun, prepass diff, liveness re-probe at concurrency 3, relabel).
- Verify: `git log --oneline -10 origin/dev/yggdrasil-iv-launch -- founder/reports/yggdrasil-iv-october-2026/sweep founder/reports/yggdrasil-iv-october-2026/reconciliation`
- Moves: cutoff.

**F3. Ratification date and premise** (2026-10-25; "long-lived trust registry, not a fast-moving leaderboard"; time invites scrutiny, counterevidence justifies degradation, adjudication authorizes change).
- Source: `founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md` lines 1-9.
- Verify: `sed -n 1,9p founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md`
- Moves: stable.

**F4. Signals are not penalties; degradation needs counterevidence; recovery symmetric, no comeback bonus; history kept.**
- Source: ratification §I, §III; META.md line 7, 180.
- Verify: `sed -n 13,23p founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md`
- Moves: stable.

**F5. Yggdrasil IV changes no TM weight, cap, threshold, grade boundary or Fusion Score rule.**
- Source: ratification §I ("remain unchanged until explicitly approved work implements a different rule") and §VI.
- Verify: `grep -n "remain unchanged" founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md`
- Moves: stable. Note: the within-type dedup fix (#2257) is presented as an implementation correction, matching ratification §VI.

## B. Challenger mechanic

**F6. Pipeline steps (Frontier lead + registry match + dedupe; Meta triage; pre-registered protocol; receipt; separate-session Meta verification record; independence declared not authenticated).**
- Source: `$L/plans/challenger-pipeline.md`; PRs #2183, #2191, #2193, #2196, #2232, #2233; `evidence/frontier-challenges/*/meta-verification.json`.
- Verify: `python3 -c "import json,glob;[print(p,json.load(open(p))['outcome']) for p in sorted(glob.glob('evidence/frontier-challenges/*/meta-verification.json'))]"`
- Moves: stable.

**F7. Admission only through the trusted challenge-receipt issuer; founder approves each admission; issuer approval is not a blanket admission.**
- Source: `$L/CAMPAIGN.md` "Founder rulings this campaign" (2026-10-28 "approved issuer for dev"); `$L/plans/issuer.md`; PR #2198 (`d237c0839`); environment `challenge-receipt-issuer` created by the founder (CAMPAIGN decision `issuer-env`: "created").
- Verify: `gh pr view 2198 --json state,mergeCommit --jq '.state+" "+.mergeCommit.oid'`
- Moves: stable (production use rides the #2151 merge).

**F8. Only an admitted challenge can mark a skill contested; Origin-contested reserved for material challenges; held reviews never "contested".**
- Source: ratification §III; `docs/trust/challenges/index.html` copy; PR #2250 body (W3, W6).
- Verify: `grep -n "Admission held, no effect on standing" docs/trust/challenges/index.html`
- Moves: stable.

**F9. Held review has no effect on standing; numbers change only through an approved decision.**
- Source: `docs/graph/challenges/reviews.json` `disclosure` field on every record; ratification §V Class C.
- Verify: `python3 -c "import json;print({r['disclosure'][:40] for r in json.load(open('docs/graph/challenges/reviews.json'))['reviews']})"`
- Moves: stable.

**F10. 14-day contributor response window; unanswered challenge does not auto-demote.**
- Source: ratification §III paragraph 3.
- Verify: `grep -n "14 calendar days" founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md`
- Moves: stable.

**F11. Automated challenge watching stays switched off this month.**
- Value: gated off; watcher bridge does not pass proofSourceSha (#2256 comment).
- Source: `$L/HANDOVER.md` gap review row 3.
- Verify: `git show "$L/HANDOVER.md" | grep -n "challenge watch stays gated off"`
- Moves: stable for October. **Unsure:** I did not inspect the workflow file to confirm the gate mechanism; the claim rests on the handover.

## C. October cases

**F12. Four cases; three ran experiments; C4 rejected at triage; none admitted; founder accepted the negative.**
- Value: C1 contradicted (tie), C2 runner supported → Meta inconclusive, C3 inconclusive, C4 rejected at triage; all `recommendAdmission` false.
- Source: `docs/graph/challenges/reviews.json`; `evidence/frontier-challenges/*/RUN.md`; PR #2234 (`39eb288d9`); CAMPAIGN decision `challenger-outcome`: "Accept the negative result".
- Verify: `python3 -c "import json;[print(r['caseId'],r['status'],r['assessment']['outcome']) for r in json.load(open('docs/graph/challenges/reviews.json'))['reviews']]"`
- Moves: stable.

**F13 ⚑. No admitted challenge at the cutoff.**
- Value now: `docs/graph/challenges/index.json` `sourceStatus: unavailable`, `subjects: []`; `reviews.json` 4 records.
- Verify: `python3 -c "import json;print(json.load(open('docs/graph/challenges/index.json'))['sourceStatus'], len(json.load(open('docs/graph/challenges/reviews.json'))['reviews']))"`
- Moves: cutoff (re-confirm only).

**F14. C1 details** (5 targets by a mechanical rule; 27 ground-truth callers; identical caller sets; recall 0.727/1.0/0.75/1.0/0.667; precision 22/22 each; same 5 missed callers; Graphify registered as `safishamsi/graphify`).
- Source: `evidence/frontier-challenges/c1-graphify-vs-graft/RUN.md`, `meta-verification.json`.
- Verify: `sed -n 1,30p evidence/frontier-challenges/c1-graphify-vs-graft/RUN.md`
- Moves: stable.

**F15. C2 details** (18 commands; native 10/12 dangerous blocked, 6/6 safe allowed; hook 8/12, 5/6; Meta reproduced exactly, downgraded: fixture frozen after seeing hook results; `bash -c` wrapper blocked by hook, missed natively; held pending re-registered fixture).
- Source: `evidence/frontier-challenges/c2-claude-deny-vs-git-guardrails/RUN.md`, `meta-verification.json` `recommend.rationale`.
- Verify: `python3 -c "import json;print(json.load(open('evidence/frontier-challenges/c2-claude-deny-vs-git-guardrails/meta-verification.json'))['recommend']['rationale'])"`
- Moves: stable.

**F16. C3/C4 details** (C3 complementary scope, Git 2.50.1 executed vs 2.56.0 documented, protocol allows at most inconclusive; C4 ripgrep makes no caller-resolution claim, no experiment).
- Source: `evidence/frontier-challenges/c3-git-log-L-vs-graft/RUN.md`, `c4-ripgrep-vs-graft-callers/RUN.md`.
- Verify: `head -12 evidence/frontier-challenges/c4-ripgrep-vs-graft-callers/RUN.md`
- Moves: stable.

## D. Meta re-audit and reconciliation

**F17. 701 records (400 named incl. 48 awakened, 301 generic), 874 evidence rows, 13 survey dimensions.**
- Source: `$L/sweep/COVERAGE.md` §Coverage and §Survey dimensions.
- Verify: `git show "$L/sweep/COVERAGE.md" | sed -n 8,12p`
- Moves: cutoff (prepass diff may add records; the provisional sweep itself stays 701).

**F18. 930 raw → 817 surviving (≥2 of 3 lenses); P0 2, P1 90, P2 312, P3 354, P4 59; synthesis 810 replaced by deterministic replay 817.**
- Source: `$L/sweep/COVERAGE.md`.
- Verify: `git show "$L/sweep/COVERAGE.md" | grep -n "Findings:\|Surviving by priority\|810"`
- Moves: stable.

**F19 ⚑. Liveness: 962 URLs; first pass 211 HTTP 429s; re-probe 903 alive, 59 dead, 0 unknown; dead = review debt with t0/+24h/+72h probes.**
- Source: `$L/sweep/COVERAGE.md` §Exceptions; `$L/sweep/liveness-reprobe/evidence-health.md`.
- Verify: `git show "$L/sweep/liveness-reprobe/evidence-health.md" | head -20`
- Moves: cutoff (re-probe at concurrency 3).

**F20. Reconciliation: 313 items; 111 verified-in-dev, 53 equivalent, 99 pending-curation, 9 held-for-governance, 13 duplicate, 27 not-applicable, 1 needs-action, 0 rejected.**
- Source: `$L/reconciliation/RECONCILIATION.md` counts table.
- Verify: `git show "$L/reconciliation/RECONCILIATION.md" | grep -n "^| \*\*total"`
- Moves: cutoff (rerun of `reconciliation/upstream-sync-commands.sh`).

**F21. October upstream sync: 15 named skills (PR #2197, `9d3bdca35`); 38 stale intake issues closed.**
- Source: `$L/CAMPAIGN.md` lanes table and "Landed" table; `$L/HANDOVER.md` §2.
- Verify: `gh pr view 2197 --json title,state --jq '.state+" "+.title'`
- Moves: cutoff (upstream tags re-resolved; may add a sync).

**F22. Intake triage: 90 items: 59 ready-for-L4, 17 needs-info, 7 duplicates, 6 covered by sync, 1 reject; no admissions (PR #2199).**
- Source: `$L/CAMPAIGN.md` lanes table; PR #2199 title.
- Verify: `gh pr view 2199 --json title --jq .title`
- Moves: stable.

**F23 ⚑. L4 topology review: 76 choices: 53 approve, 10 new generic, 5 other (remapped), 8 decline; approved, not executed.**
- Value now: not executed. **Unsure:** the "(7 parked drafts)" approve row is one table row, so 53 approve rows cover 59 items. Counted with the command below; the post says "76 topology choices", matching CAMPAIGN's own heading "L4 topology choices (76; …)".
- Source: `$L/CAMPAIGN.md` §"L4 topology choices (76; reviewer: founder, via the review page)".
- Verify: `git show "$L/CAMPAIGN.md" | awk '/L4 topology choices \(76/,/decision review page/' | grep '^| ' | awk -F'|' '{gsub(/ /,"",$3);print $3}' | sort | uniq -c`
- Moves: L4.

## E. Adjudication and calibration

**F24 ⚑. Adjudication: 190 candidates, 65 with recomputed numbers, 125 needing decision; approved 0 at build; regeneration with approvals input pending.**
- Source: `$L/HANDOVER.md` §0 (2026-10-29); FINISH PLAN step 7.
- Verify: `git show "$L/adjudication/LEDGER.md" | head -30`
- Moves: after step 7 (approved count changes).

**F25 ⚑. First independent Meta audit of the calibration batch: FAIL; 37 skills escaped the 50 TM cap (no suiteRef); re-audit must PASS before the batch reaches main.**
- Value now: FAIL (`cc67dddb1`); re-audit not yet written.
- Source: `$L/verification/CALIBRATION-VERIFICATION.md`; CAMPAIGN decision `main-merge`: "Once meta audit is verified, merge is allowed."
- Verify: `git show "$L/verification/CALIBRATION-REVERIFICATION.md" | head -20`
- Moves: after re-audit (FINISH PLAN step 6).

**F26. Freezes: 12 hyperframes components (FD-8, absent at v0.8.209), `heygen-com/general-video` (r2), `leonxlnx/output-skill` (r3); installable false, links kept, stars unchanged.**
- Source: #2251 commits `1bd43e62c`, `f966b0408`, `01330babb`; `$L/verification/CALIBRATION-VERIFICATION.md` §FD-8.
- Verify: `git log --oneline origin/dev/yggdrasil-iv..origin/review/meta/yggiv-october-calibration --grep=freeze`
- Moves: merge:#2251.

**F27. Relinks: leonxlnx moved skills (brandkit, image-to-code-skill, imagegen-frontend-mobile, imagegen-frontend-web; brutalist, gpt-tasteskill, minimalist, soft, stitch) and `leonxlnx/redesign-skill` (superseded, folded into design-taste-frontend).**
- Source: #2251 commits `ce349fa4b`, `d4b9ddcd7`, `ca1c65219`.
- Verify: `git show --stat ce349fa4b d4b9ddcd7 ca1c65219 | grep registry/named`
- Moves: merge:#2251. Post says "nine leonxlnx skills that moved to new repositories" (7 in FD-17 + imagegen-frontend-web + stitch-skill).

**F28. Frozen skills keep TM and grade; no batch touches them.**
- Source: CAMPAIGN FD-7 note ("DO NOT touch frozen skills"); founder message 2026-10-30 ("Frozen skills lock the TM and grade, and they can beat live ones").
- Verify: `git show "$L/CAMPAIGN.md" | grep -n "Frozen skills lock"`
- Moves: stable.

**F29 ⚑. Origin automatic, highest merit; frozen contenders compete with locked TM; ties share Origin; no star requirement; manual Class C transfer path superseded.**
- Value now: rulings recorded; code NOT merged (WIP uncommitted in `~/.gaia-worktrees/origin` on `dev/yggiv-origin-automation`; no remote branch, no PR). Change counts unknown.
- Source: `$L/CAMPAIGN.md` "Founder rulings 2026-10-30, late" (items 2, 3) and r2-hermes, r3-origin-meaning; `$L/verification/RULE-PROVENANCE.md` (b), (c), (e).
- Verify: `gh pr list --head dev/yggiv-origin-automation --state all`
- Moves: merge:Origin automation PR. Also expected to fix META.md line 58 (≤1★ Origin sentence) and GOVERNANCE.md line 64.

**F30. Four Origins assigned (FD-10): vercel-react-best-practices, code-simplification, i-have-adhd, ponytail.**
- Source: #2251 commit `b336f6a31`; CALIBRATION-VERIFICATION §FD-10 (verified).
- Verify: `for s in vercel-labs/vercel-react-best-practices addy-osmani/code-simplification ayghri/i-have-adhd dietrichgebert/ponytail; do git show origin/review/meta/yggiv-october-calibration:registry/named/$s.md | grep -m1 '^origin:'; done`
- Moves: merge:#2251 (and recomputed by automation).

**F31. brag 3★ → 4★, TM 144.54 A, Unique, sole bucket Origin.**
- Source: #2251 `ce74246b2`; CALIBRATION-VERIFICATION §FD-12 (verified).
- Verify: `git show origin/review/meta/yggiv-october-calibration:registry/named/latent-spaces/brag.md | grep -E '^(level|trustMagnitude|overallTrustGrade):'`
- Moves: merge:#2251.

**F32 ⚑. workflow-skill-creator Named "Workflow-to-Skill Distiller"; peer-review row retyped; TM 100.82 A → 59.65 B; stored 4★ kept as review debt; displayed 3★ under the clamp.**
- Value now: frontmatter on #2251 head: `level: 4★`, `trustMagnitude: 59.65`, `overallTrustGrade: B`. The displayed 3★ is inferred from the clamp table (B → 3★), not yet observed on a regenerated surface.
- Source: #2251 `c241eec51`, `77703692d`; CAMPAIGN fd-11 "Promote to named", r4-peer-review-rows.
- Verify: `git show origin/review/meta/yggiv-october-calibration:registry/named/google-deepmind/workflow-skill-creator.md | grep -E '^(level|status|title|trustMagnitude|overallTrustGrade):'`
- Moves: merge:#2251, merge:#2259.

**F33 ⚑. graphify stays 5★ (TM 318.14 S); Unique 5★ prerequisite-Origin rule was borrowed from Suites and never ratified; demotion reverted.**
- Value now: revert commits `7fc346b67`, `949c3eded` and ruling note `035754bd8` on #2251. Code rule (`promotion.py` `checkUniqueBranchGate`, `helpers.py` pre-flight) not yet corrected on dev.
- Source: CAMPAIGN r2-graphify; RULE-PROVENANCE (a).
- Verify: `git show origin/dev/yggdrasil-iv:src/gaia_cli/promotion.py | sed -n 118,140p`
- Moves: merge:#2251 and merge:Origin automation PR.

**F34. agent-reach evidence re-derived: TM 53.86 B → 260.83 A; stays 3★.**
- Source: #2251 `5abb29637`; CAMPAIGN r3-adj-judgement.
- Verify: `git show origin/review/meta/yggiv-october-calibration:registry/named/panniantong/agent-reach.md | grep -E '^(level|trustMagnitude|overallTrustGrade):'`
- Moves: merge:#2251. Not covered by the first audit (added after it) → in scope of the re-audit.

**F35. Within-type evidence dedup (PR #2257, `30dd331fa`).**
- Verify: `gh pr view 2257 --json state,mergeCommit --jq '.state+" "+.mergeCommit.oid'`
- Moves: stable.

**F36 ⚑. mattpocock/skills: citations 500 → 2; TM 374.99 → 280.39 S; 5★ unchanged; witness URL 404; last bounded probe due 2026-11-01T16:40Z.**
- Source: #2251 `753f4bb8a`; CALIBRATION-VERIFICATION §FD-9 (2 not independently confirmed; S does not depend on the exact value; the 5★ rests on the witness row).
- Verify: `git show origin/review/meta/yggiv-october-calibration:registry/named/mattpocock/skills.md | grep -E '^(level|trustMagnitude|overallTrustGrade):'`
- Moves: after 2026-11-01T16:40Z (+72h probe), which is after the cutoff.

**F37 ⚑. 37 zero-evidence skills got host-repo evidence; 12 addy-osmani relinked to suite → 50.0 B; 23 garrytan + 2 obra suite linking automatic under the cap.**
- Value now: addy-osmani done (`a55cdf5a4`); garrytan/obra NOT linked (C1b open; projected 50.0 B each, obra/test-driven-development 59.0 B).
- Source: #2251 `3c31f0042`, `a55cdf5a4`; CAMPAIGN "Founder rulings 2026-10-30, late" item 1; PR #2260.
- Verify: `git show origin/review/meta/yggiv-october-calibration:registry/named/garrytan/context-audit.md | grep -E '^(suiteRef|trustMagnitude|overallTrustGrade):'`
- Moves: merge:#2251.

**F38. Caches refreshed: obra/superpowers apex (FD-15), 70 TM caches with no value change (ADJ-174).**
- Source: #2251 `e8a01f494`, `777ea33c6`; CALIBRATION-VERIFICATION §FD-15, §FD-18.
- Verify: `git show --stat 777ea33c6 | tail -1`
- Moves: merge:#2251.

**F39 ⚑. Grade clamp (S 6, A 4, B 3, C 2, ungraded 1) applied on ledger and leaderboard; stored values unedited; ledger carries stored and displayed.**
- Value now: PR #2259 OPEN (head `3bd9de0cc`); its body lists 39 display changes computed BEFORE #2251. After #2251 the set shrinks (37 skills now graded) and gains new ones (e.g. workflow-skill-creator 4★/B, output-skill 3★/C).
- Source: `$L/adjudication/DECISIONS.md` FD-7; CAMPAIGN fd-7 "A · align leaderboard and ledger to the clamp"; PR #2259.
- Verify: `gh pr view 2259 --json state,mergeCommit`
- Moves: merge:#2259 (must merge after #2251, with ledger + leaderboard regenerated together).

## F. Deferred and site

**F40. Deferred to November: #2261, #2262 (ADJ-152, ADJ-179, ADJ-090), #2263 (sibling cap audit).**
- Source: CAMPAIGN r3-adj-evidence "Defer all three to November", r3-structural, late ruling 1.
- Verify: `gh issue view 2261 --json state,title; gh issue view 2262 --json state,title; gh issue view 2263 --json state,title`
- Moves: stable.

**F41. Site surfaces: lifecycle panel on every explorer page (#2192), evidence provenance renderer (#2200), /trust/challenges/ (#2250 W5, linked from Trust Methodology and lifecycle panel), contested marks on leaderboard/ledger/explorer with byte-identical bars (#2250 W3, W4, W6), none contested today.**
- Verify: `for n in 2192 2200 2250; do gh pr view $n --json number,state,mergeCommit --jq '"\(.number) \(.state) \(.mergeCommit.oid[0:9])"'; done`
- Moves: stable on dev; public only after #2151.

**F42. Era stamp and meta-shift notes read Yggdrasil IV (this PR).**
- Verify: `grep -n "Yggdrasil IV" docs/js/site-nav.js docs/index.html docs/heroes/index.html`
- Moves: this PR.

**F43 ⚑. Cutoff counts remain pending. Current generated figures use distinct, documented populations.**
- Value observed on this branch before regeneration: 301 generic graph nodes; 352 classified named entries in `buckets`; 268 ledger rows; 229 skills in the skills API. The public contributors directory's canonical population is **65 contributors with 400 skill records**, counting both classified buckets and `awaitingClassification` (48 entries across six handles). `generateProfilePages.collect_by_contributor()` defines that population and `build_directory_page()` renders its total. The about-page contributor tally is being aligned to the same 65-handle `byContributor` projection by `scripts/build_docs.py`.
- The contributors API lists **43 contributors with non-redacted API-projected skills** (229 skills); `scripts/buildApiProjection.build_contributors()` receives that narrower visible-skill set. This is a different population, not an alternate count of everyone in the public directory.
- Homepage ledger definitions: named = all classified bucket entries (352); ultimates = named entries at rank 5★+ (3 at this snapshot). The live JS count and first-paint generator both use those definitions. These figures are provisional and must be refreshed after the cutoff; do not substitute them for final counts.
- Sources: `registry/named-skills.json` (`buckets`, `awaitingClassification`, `byContributor`); `scripts/generateProfilePages.py` `collect_by_contributor` / `build_directory_page`; `scripts/buildApiProjection.py` `build_contributors`; `docs/api/v1/contributors/index.json`; `docs/api/v1/skills/index.json`; `docs/graph/ledger/data.json`; `scripts/build_docs.py` `build_docs_index` / `build_about_stats`.
- Verify: `python3 -c "import json; n=json.load(open('registry/named-skills.json')); print(len(n['byContributor']), sum(map(len,n['byContributor'].values())), sum(map(len,n['buckets'].values())), len(n['awaitingClassification']))"`; then inspect API `totalContributors`, API `totalSkills`, ledger `summary.total`, generated homepage stat markers and about tally.
- Moves: L4, merge:#2251, merge:#2259, cutoff. All values in this entry are provisional.

## Keep or remove

This file is a pre-merge checklist. Recommendation: **remove it before the integration merge to main** (it duplicates proof-of-work that lives on `dev/yggdrasil-iv-launch` and contains internal commands). The PR body states this.
