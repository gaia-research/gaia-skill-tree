# October 2026 batch calibration: Meta verification record

- **Target:** PR #2251, `review/meta/yggiv-october-calibration` @ `153d3bc16` (17 commits, base `dev/yggdrasil-iv`, merge-base `7b672a854`).
- **Authority checked against:** `CAMPAIGN.md` §"Founder rulings 2026-10-30" (recorded `13269af82`, 2026-10-29T16:30:22Z), `adjudication/DECISIONS.md`, `adjudication/ledger.json`, META.md, GOVERNANCE.md, CLAUDE.md, the Yggdrasil II v4 amendment (Q3), `docs/agents/curation-guidelines.md`, `docs/agents/curation-authority-map.md`, and the live engine (`src/gaia_cli/trustMagnitude.py`, `promotion.py`).
- **Method:** read-only detached worktree. Class P generated with `gaia dev docs`. Every gate and TM was recomputed with the branch's own engine (`buildMergedSkillMap`, `computeTrustMagnitude`, `checkUniqueBranchGate`). Upstream sources were probed live. Probe window: 2026-10-30T05:28Z to 05:44Z.
- **Independence:** declared, not authenticated. The auditor is a separate agent session that did not perform the calibration. Nothing here proves that independence cryptographically.
- **Branch modified:** no.

## Overall verdict: **FAIL**

Most items check out. FD-8, the four FD-10 Origins, FD-12, FD-17 and FD-18 are correct, and so are the timeline, frozen-skill and surface-agreement checks. **FD-7 is refuted.** Its evidence rows are factually correct, but the TMs they produce double-count host-repo adoption. That happens because the 37 skills have no `suiteRef`, so they escape the 50-TM suite-component cap that every one of their siblings is held to. The branch would publish 37 inflated A grades, and those grades feed the FD-16 Origin winners. The PR's CI is also red because of FD-11, and graphify is still awaiting founder confirmation. Merge is **not** allowed until corrections C1–C4 are done. After that, only FD-7 needs a re-audit.

## Per-item verdicts

| Item | Verdict | Summary |
|---|---|---|
| FD-8 freezes (12) | **verified** | All 12 are absent at v0.8.209, at v0.8.220 (latest) and on `main`. Pinned blobs still return 200, levels are unchanged and the CLI shape is correct. |
| FD-10 four Origins | **verified** | Each skill is the unique merit winner of its bucket, has no other holder, and passes the 4★ Unique gate live. |
| FD-10 graphify 5★→4★ | **verified-with-notes** (gate reasoning) | The reasoning matches the ratified 5★ fusion-structure rule. The demotion is **already applied** while founder confirmation is still pending. |
| FD-11 workflow-skill-creator → named | **verified-with-notes** | The status change, the title (upstream H1) and the live link are all correct. The 4★ TM rests on one unverified `peer-review` row; without it, TM is 10.82. CI tests break because of this change. |
| FD-12 brag → 4★ | **verified** | TM 144.54 A ≥ 100, SHA-pinned blob 200, Unique branch, sole bucket Origin. The gate passes live. |
| FD-9 mattpocock/skills | **verified-with-notes** | 500 was wrong. OpenAlex shows 0 citations; Semantic Scholar returned 429 on 4 tries, so the value 2 is not independently confirmed. TM barely depends on it (280.19 at 0). The witness still returns 404, there is no level change, and the probes are scheduled. |
| FD-15 superpowers apex | **verified-with-notes** | `overallGradeS` true→false via `--refresh-apex`. The `apexPromotionPrSignedBy/At` annotations were dropped; they are kept only in the timeline text. |
| FD-7 37 skills evidence | **refuted** (TM basis) | The rows are correctly typed, live and accurate, and levels are unchanged. The TMs double-count: the skills lack `suiteRef`, so they bypass the suite cap. The founder's choice A is also not implemented. |
| FD-14 laravel, nielsen | **verified-with-notes** | Sources are live and the numbers match. The nielsen stars row sits at the repo root, which breaks guideline §5. One timeline event is misleading. |
| FD-17 8 relinks | **verified** | The 8 new URLs return 200 and their content is byte-identical to the pre-move upstream files. Three have upstream "Moved to" stubs. |
| FD-18 ADJ-119, ADJ-174 | **verified** | The grade A equals the `github-stars-own` gradeCeiling. Seventy cache refreshes changed no values. |

## Evidence per item

### FD-8: 12 freezes (verified)
- `gh api repos/heygen-com/hyperframes/contents/skills?ref=v0.8.209` (05:28:42Z) lists only `figma hyperframes-cli hyperframes-registry hyperframes media-use remotion-to-hyperframes slideshow`. `ref=v0.8.220` (latest, published 2026-10-30T03:59:04Z) and `main` give the same list. Querying each of the 12 `skills/<name>/SKILL.md` at v0.8.209 returns 404. A recursive tree search shows the capabilities were folded into `skills/hyperframes/references/` (captions, motion, sound and others), so the freeze (not removal) is the right shape.
- All 12 SHA-pinned `links.github` (`7a2a691…`) return HTTP 200 (05:29:17Z). That keeps the Star Bar met at 3★.
- Each diff adds `installable: false` and one `upstream_deprecated` event citing FD-8. That matches `gaia dev freeze` output. Levels stay at 3★.
- Note: `heygen-com/general-video` is also absent at v0.8.209. It was correctly left alone because it is outside the authorized 12, and it needs its own ruling.

### FD-10: 4 Origins (verified)
Bucket scans parse the frontmatter of all 400 named files (raw, not the index):

| Skill | Bucket members (level, TM) | Other holders | Live gate 4★ |
|---|---|---|---|
| vercel-labs/vercel-react-best-practices | sole member (4★ 163.19) | none | passed, origin true |
| addy-osmani/code-simplification | 4★ 190.0; improve-codebase-architecture 2★ 45; migrate-to-shoehorn 2★ 41; component-refactoring 1★ (frozen) | none | passed |
| ayghri/i-have-adhd | 4★ 130.23; output-skill 3★ 50; make-pdf 2★ 36 | none | passed |
| dietrichgebert/ponytail | 4★ 225.42; rico-favor/implement-with-discernment 1★ 5.7 | none | passed |

The live TM equals the stored TM for all four. Each diff is `origin false→true`, plus a CLI `rank_up` event "Origin status set to true" and a `note` citing FD-10.

### FD-10: graphify (gate reasoning correct; action pending confirmation)
- `knowledge-graph-build` has prerequisites `extract-entities` and `logical-inference`, and **both buckets have zero named members**. Live `checkUniqueBranchGate`: 5★ passed=False, originPresent=False. 4★ passed=True (TM 318.14 S, bucket Origin held).
- The Yggdrasil II v4 amendment (2026-07-19) keeps the fusion-structure Origin rule for 5★+ and lifts it only at 4★. The reasoning is therefore correct as ratified. The amendment was written with graphify as its archetype. The author's note is accurate: the 5★ predicate is unsatisfiable when the prerequisites have no named members. That is a rule question for the founder.
- The timeline confirms the stored 5★ came from a plain `calibrate` on 2026-09-02T15:11:45Z with no gate.
- **Condition:** the demotion (commits `601ac2241`, `961f2226e`) is applied on the branch, but its founder confirmation is still pending. The founder confirms before merge, or those two commits are reverted.
- The user tree (`skill-trees/safishamsi/skill-tree.json`) is synced: level, `levelHistory` and a `demote` event with previous and new values. The Transparency Gate passes. However, the `skill-trees/safishamsi/skill-tree.md` mirror is not committed and still shows **5★ Ultimate** (see C7).

### FD-11: workflow-skill-creator (verified-with-notes)
- Diff: `status awakened→named`, `title: Workflow-to-Skill Distiller`, CLI `name` event plus a `note` citing FD-11. Upstream `SKILL.md` line 12 is `# Workflow-to-Skill Distiller`. The blob returns 200 (05:31:47Z). The skill has left `awaitingClassification` and now appears in the ledger and the leaderboard, consistently.
- **Evidence concern.** TM 100.82 A comes almost entirely from one row: `type: peer-review, grade: S, reviewers: 3`, whose `source` is the bare repo `https://github.com/google-deepmind/science-skills`. A repo is not a written review record (guidelines §5). Recomputed without that row, **TM is 10.82, ungraded**. The FD-11 packet said "do not rely on it before the rows are re-verified". The PR did not re-verify the row. Under Yggdrasil IV this is review debt, not a reason to demote (see C4). PR #2257 flags the same pattern on `browser-use/browser-harness`.
- **CI:** `Test, Build, and Smoke Test` fails on PR #2251 (run 41006328960) with exactly two failures, both caused by this change. `tests/test_public_projection_parity.py::test_no_public_level_entry_is_hidden_in_awaiting_classification` now passes while still marked as a strict xfail. `tests/test_shadow_corpus.py::test_cli_shadow_command_writes_into_scratch` asserts 48 awakened skills and now gets 47. See C2.

### FD-12: brag → 4★ (verified)
TM 144.54 A both live and stored. The `github-stars-own` row is at the SHA-pinned blob `c893c5e…/skills/brag/SKILL.md`, which returns 200 (05:36:04Z). The repo now has 19,508 stars against the 12,621 recorded, so the row is conservative. There are no `suiteComponents`, so the skill is on the Unique branch, and it is the sole member and Origin of `project-launch-video-production`. Live `checkUniqueBranchGate(4★)` passes. CLI `rank_up` plus a `note` citing FD-12. latent-spaces has no user tree.

### FD-9: mattpocock/skills (verified-with-notes)
- arXiv abs 200; export API title "An Empirical Study of Downstream Adaptation for Agent Skills", published 2026-07-03. OpenAlex `W7167605459` reports cited_by_count **0** (updated 2026-10-28; probed 05:36:13Z and 05:41:34Z). Semantic Scholar Graph API returned **HTTP 429** at 05:36:13Z, 05:36:40Z and 05:41:34Z, and again through Firecrawl at 05:42:04Z. The author's value of 2 is therefore **not independently confirmed**. The value 500 is refuted.
- Sensitivity: TM is 280.19 S with 0 citations, 280.39 S with 2 and 280.69 S with 5. The S grade and the 250 floor do not depend on the exact value.
- Witness `frontendmastery.com/posts/matt-pocock-claude-code-skills-architecture/` returns **HTTP 404** at 05:36:55Z with a browser user agent, while the site root returns 200. The Wayback availability API has **no snapshot ever**. Without the witness row, TM is 235.39 A, below the 5★ S floor. **The 5★ rests on this row.** The +24h probe is due 2026-10-30T16:40Z and the +72h probe 2026-11-01T16:40Z, neither run yet. No level change, which follows the Yggdrasil IV bounded-probe rule.
- The CLI removed the row's `grade: S` field, which is now absent. That is consistent with the recomputed `citationsCorrectedTo2` scenario in DECISIONS (280.39).

### FD-15: superpowers apex refresh (verified-with-notes)
`apexGateStatus.overallGradeS` true→false via `calibrate-trust-magnitude --refresh-apex`. The value matches the published named index (overallGradeS False, TM 221.52 A). Level stays 4★. The refresh deleted `apexPromotionPrSignedBy: mbtiongson1` and `apexPromotionPrSignedAt: 2026-06-20`. The old values survive only inside the timeline event's detail text. That is audit-provenance loss in the verb (see C9).

### FD-7: 37 skills (refuted: TM basis)
What checks out:
- **Rows.** Each of the 37 got one `github-stars-own` row at the skill's own blob URL and one `repo-own` row at the host repo root. Those are the canonical URL shapes in guidelines §5. The grades (A and B) sit within the meta.json gradeCeilings (A for stars, B for repo-own).
- **Live spot-checks, 10 skills (05:33:57Z–05:34:17Z).** All `links.github` and star-row URLs return 200 for addy-osmani/{api-and-interface-design, doubt-driven-development, source-driven-development}, garrytan/{context-audit, academic-verify, minion-orchestrator, skill-optimizer, two-tier-extraction} and obra/{test-driven-development, writing-skills}.
- **Host counts, live.** addyosmani/agent-skills: 111,796 stars (111,664 recorded), 772 commits, 83 contributors. garrytan/gbrain: 31,343 stars (31,330 recorded), 11,602 commits (11,443 recorded), 136 contributors. obra/superpowers: 308,774 stars (308,198 recorded), 686 commits, 37 contributors.
- **Levels.** Unchanged for all 37 (still 2★).

**The problem: double counting.**
- The methodology bounds shared host-repo evidence with the **suite-component repository cap of 50 TM** (`SUITE_COMPONENT_REPOSITORY_CAP`, `_isSuiteRootRepositoryEvidence`; authority map §45; guidelines §6). The cap only fires when the skill carries `suiteRef`.
- Every curated sibling in the same host repos carries `suiteRef` and is capped. Examples: gbrain's brain-ops, capture and concept-synthesis (50.0 B); 7 addy-osmani suite components (50–95 B); 12 obra components (36–117 A/B/C).
- **All 37 FD-7 skills have `suiteRef: None`.** The 12 addy-osmani skills even carry a `suite_ref_set` timeline event ("Set suiteRef to addy-osmani/agent-skills", from `ae99d443c`, 2026-09-23), but their frontmatter has no `suiteRef`. That is a pre-existing record that contradicts itself.
- **Result.** Skills with no skill-specific evidence now outrank their own capstones and their curated siblings. The 23 garrytan skills score 158.36 A against `garrytan/gbrain` at 121.94. The 12 addy-osmani skills score 177.68 A against `addy-osmani/agent-skills` at 176.04. obra/test-driven-development scores 202.11 A.
- **What-if with the host `suiteRef` set.** 36 skills score **50.0 B** and 1 scores **59.0 B**. That is a 3★ ceiling. The stored 2★ stays at or below the ceiling, so the D6 clamp disagreement still clears for these 37.
- **Cascade.** The PR body states that 12 of the 48 FD-16 Origin winners exist only because of these grades (for example `context-compression → garrytan/context-audit`). Leaderboard order and the ledger also move.
- **Ruling fidelity.** The founder chose **"A · align leaderboard and ledger to the clamp"** and asked for the cause to be double-checked. The PR found the cause, which is real (zero-evidence `gaia dev add` at a default 2★), but applied a different remedy. Option A was not implemented. `mattpocock/personal` (3★) and `heygen-com/general-video` (2★) still show different levels in the ledger and leaderboard than in the named index (1★).
- Side observation: the upstream watcher opened intake issues #2236–#2247 on 2026-10-29 for these 12 addy-osmani skills, which are already in the registry. That is consistent with them not being linked to their suite.

### FD-14: laravel and nielsen (verified-with-notes)
- **laravel.** The `UpgradeLaravelV13.php` blob returns 200 and declares `$name = 'upgrade-laravel-v13'`. laravel/boost has 3,671 stars (3,670 recorded). The YouTube video `CH8y8nR_uTI` is by Laravel Daily ("I Tried Laravel 13 Upgrade With Boost /upgrade vs Laravel Shift") with viewCount 5,096 (5,094 recorded). The Laravel 13.x upgrade guide links to Laravel Boost's guided upgrade prompt. Probes 05:37:33Z–05:37:37Z. Types are correct and no other laravel/boost skill shares the repo, so nothing is double-counted. The skill is still 1★ `named`, now with grade A. The FD-14 status question remains open for the founder.
- **nielsen.** The blob returns 200. mastepanoski/claude-skills has 59 stars (59 recorded) and 54 commits (51 recorded). The npm downloads API for 2026-10-22..28 returns 57 (57 recorded). The npm web page returns 403, which is anti-bot and normal. **Deviation:** the `github-stars-own` row is at the repo root, not the skill blob, in a 13-skill repo, which breaks guidelines §5 canonical URLs. This was a disclosed workaround for the `merge_evidence` bug, now fixed by #2257. **Misleading audit trail:** event 2026-10-29T16:59:36Z reads "Removed dead/invalid evidence: …/nielsen-heuristics-audit/SKILL.md", but that URL is live. The removed row was the just-added stars row, re-homed one second later.

### FD-17: 8 relinks (verified)
Probes 05:38:41Z. Each old link returns 404, or 301 for the handoff directory, and each new link returns 200. Content identity:
- `taste-skill-classics` (brutalist, gpt-taste, minimalist, soft): the new `SKILL.md` is identical (ratio 1.0, equal length) to the last pre-deletion version in `Leonxlnx/taste-skill`.
- `imagegen-skills` (brandkit, image-to-code, imagegen-frontend-mobile): identical to the pre-move version (e.g. brandkit at `6d6096ef7`). The upstream author's own stubs (`825e30649`) say "Moved to github.com/Leonxlnx/imagegen-skills … The install name did not change."
- `mattpocock/handoff`: the directory URL now points to its own `SKILL.md`.

All 8 went through `update-named --github-link` with a CLI `note` and a ruling-citing `note`. Left as reported: the 9 leonxlnx evidence rows still cite the old dead URLs. output-skill and redesign-skill are still 404 and go to the founder.

### FD-18: ADJ-119 and ADJ-174 (verified)
- **ADJ-119.** Row #0 grade S→A, with a refreshed note and an `evidence_graded` event. `registry/schema/meta.json` sets the `github-stars-own` gradeCeiling to A. TM 227.51 and 4★ are unchanged.
- **ADJ-174.** Commit `777ea33c6` touches 70 files, each with only a `recalibrate_trust_magnitude` event, an input hash and `updatedAt`. Every TM/grade transition in the events is either equal or `(none)→value` (12 to 13 caches gained). In the public named index, base vs head, the only change across these files is `rico-favor/implement-with-discernment` grade `null→"ungraded"`, which is representation only. No strictly frozen skill is included.

## Global checks

| Check | Verdict | Evidence |
|---|---|---|
| Timeline event for every level, Origin, status or freeze change, citing the ruling | **verified** | The full set of frontmatter changes is exactly 4 Origins, graphify, brag, the workflow-skill-creator status and 12 `installable` changes. Each has a CLI event plus a `note` naming the FD. Rulings were recorded at 16:30:22Z; the first mutation was at 16:33:20Z. |
| No hand edits outside the CLI | **verified-with-notes** | All 128 named diffs are append-only on `timeline` (the prefix is unchanged), with no body changes and no `registry/nodes/` changes. Event shapes match `freeze`, `update-named`, `calibrate`, `evidence` and `calibrate-trust-magnitude` output. One disclosed exception: `skill-trees/safishamsi/skill-tree.json` was re-encoded by hand after `gaia dev timeline` ASCII-escaped it. The change is formatting only and semantically identical. |
| No frozen skill touched | **verified-with-notes** | 9 skills were strictly frozen at base (`upstream_deprecated` event plus `installable: false`): Manavarya09/design-extract, langgenius/component-refactoring, and mattpocock/diagnose, edit-article, obsidian-vault, personal, ubiquitous-language, write-a-skill and zoom-out. **None was touched.** `mattpocock/skills` (FD-9, ruled) and `mattpocock/productivity` (cache refresh only) carry a component-removal `upstream_deprecated` event whose text says "(not frozen)". The Steward sensor (`sensors.py:1756`) would nonetheless classify both as frozen. The definition needs a founder ruling (C10). No value changed on productivity. |
| `gaia dev validate` | **verified** | exit 0. 353 TM surfaces agree. |
| `scripts/validate_timelines.py` | **verified** | exit 0. Transparency Gate and migration-provenance checks pass. |
| `scripts/build_docs.py --check` | **verified** | exit 0. Only warn-only drift remains (badges, OG, trending). Version lockstep is in sync. |
| PR CI | **not-verified** | "Test, Build, and Smoke Test" is red with 2 failures, both from FD-11 (C2). Every other gate is green. |
| Class S consistent with registry | **verified-with-notes** | After `gaia dev docs`, tracked `docs/graph/*` and the ledger differ from the committed copies only by `generatedAt`. Exception: the `skill-trees/safishamsi/skill-tree.md` mirror is stale and still shows 5★ (C7). |
| Leaderboard and ledger agree with the named index for every changed skill | **verified-with-notes** | All 128 changed skills plus 2 controls checked. Everything agrees on level, TM, grade and Origin except `mattpocock/personal` and `heygen-com/general-video`: the residual D6 gap that the founder's choice A was meant to close. Five changed 1★ skills are correctly absent from both surfaces. |

## Required corrections

| # | Severity | Correction |
|---|---|---|
| C1 | **Blocking** | FD-7: correct the double counting before merge. Restore `suiteRef: addy-osmani/agent-skills` on the 12 addy-osmani skills through `gaia dev update-named --suite-ref`, as their own `suite_ref_set` events already record. Have a curator confirm and set `suiteRef` for the 23 garrytan (gbrain) skills and the 2 obra (superpowers) skills, then run `calibrate-trust-magnitude`. The expected result is about 50 B each. If membership is disputed, hold commit `3c31f0042` instead. Then re-derive the FD-16 winner list. |
| C2 | **Blocking for the main merge** | Fix the 2 test failures FD-11 introduced: drop the strict xfail on `test_no_public_level_entry_is_hidden_in_awaiting_classification` and update the awakened count in `tests/test_shadow_corpus.py` (48→47), through an `infra/` PR in this sprint. |
| C3 | **Blocking (founder)** | Graphify 5★→4★: the founder confirms, or `601ac2241` and `961f2226e` are reverted before merge. |
| C4 | **High** | FD-11: re-verify or retype the `peer-review` S row (source is a bare GitHub repo, `reviewers: 3`) that carries 90 of the 100.82 TM. Record it as Yggdrasil IV review debt. Do not demote on this finding alone. Decide before the 4★ and Origin publish on `main`. The same check applies to `browser-use/browser-harness`, flagged by #2257. |
| C5 | **Medium** | FD-7 ruling fidelity: implement choice A (ledger and leaderboard publish the clamped level) within the sprint, or get the founder to re-rule now that the root cause is known. Two skills still disagree publicly. |
| C6 | **Medium** | Merge order with PR #2257 (engine dedup change, which also commits the ledger, leaderboard and named index): whichever lands second must regenerate Class S and refresh the affected caches (e.g. nateherkai/scroll-craft, mattpocock/productivity, heygen-com/hyperframes). |
| C7 | **Low** | Commit the regenerated `skill-trees/safishamsi/skill-tree.md` for graphify, the one real change, if C3 is confirmed. |
| C8 | **Low** | nielsen: once #2257 lands, move the `github-stars-own` row to the skill blob URL and append a `note` correcting the misleading "Removed dead/invalid evidence" event. |
| C9 | **Low** | File the CLI tech-debt issues the PR lists but did not file (search on 2026-10-30 found none): `--refresh-apex` drops `apexPromotionPrSignedBy/At`; `update-named --origin` writes a bare `rank_up` with no rationale and an `unknown` actor fallback; `gaia dev timeline --user` ASCII-escapes `skill-tree.json`; `gaia dev add` defaults to 2★ with zero evidence. The `merge_evidence` and installability gaps are covered by #2257. |
| C10 | **Low (founder)** | Define "frozen" for the never-touch rule: either strict (event plus `installable: false`) or the Steward sensor's "any `upstream_deprecated` event". The two disagree on mattpocock/skills and productivity. |

Open items that are not defects of this PR: the FD-9 +24h and +72h witness probes; FD-16 not applied (the stop rule fired); FD-13 complete (the skill exists, so the ruling's condition to clear Origin did not trigger); `heygen-com/general-video` freeze needs a ruling; leonxlnx output-skill and redesign-skill.
