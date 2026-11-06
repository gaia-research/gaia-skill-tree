# Origin and gate rules: where each one came from

**Date:** 2026-10-30. **Scope:** EPIC #2189, Yggdrasil IV October campaign.
**Trigger:** the founder rulings recorded in `../CAMPAIGN.md` lines 71, 72, 79, 83, 85 and 87 (2026-10-30).
**Method:** each rule was traced in `META.md`, `GOVERNANCE.md`, `CONTEXT.md`, `CLAUDE.md`, the founder ratifications, `docs/agents/*`, the agent skills and the code at `origin/dev/yggdrasil-iv` (`30dd331fa`). The introducing commit came from `git log -S`, and the PR from the first merge on the ancestry path plus `gh pr list --search <sha>`. "Ratified" means a founder ratification document or a verbatim founder ruling states the rule. An agent-written summary inside a ratification handover is flagged as such.

Note on authorship: commits under the founder's git identity (`mbtiongson1`, `Marcus Rafael B. Tiongson`) include agent-authored commits. Agents in this repo are told to commit under that identity. A commit author is therefore not evidence of founder authorship.

## Summary

| Rule | Verdict | Introduced by | Founder ruling now |
|---|---|---|---|
| (a) 5★ Unique needs Origin on a fusion prerequisite | **Misapplied** (Suite rule moved onto Uniques). It appears in an agent-written decisions table, not in founder text | `c84fc330c` (PR #1170, Ygg II ratification handover, 2026-07-07). Code: `eb7d9ff4d` (#996, merged via PR #1185). Kept for 5★ by `5e7033440` (2026-07-19, PR #1185). Repeated in the #2252 pre-flight (`c71da5082`) | "Uniques dont need a fusion prerequisite origin at all … thats from suites." |
| (b) "A ≤1★ entry cannot hold Origin" | **Agent-introduced**. The rule cites §4.1, but §4.1 sets no star floor | `e11472321` (PR #584, 2026-06-05, author "Claude"). Copied into the meta sweep by `86c2bf7dc`/`34bf42935` (PR #1721/#1725) | "I have no rule about origins having a star requirement." |
| (c) Origin by first publication | **Stale**. META §4.1 replaced it with merit on 2026-06-02, and the Yggdrasil IV ratification §IV confirmed merit. Three public strings still say "first" | Site legend `f853ff109` (PR #887, 2026-06-30). `name.py` template `cfcbc9e33` (PR #27). GOVERNANCE line 64 `0a1d843b4` (PR #147) | "Origin is highest merit." |
| (d) Suite-component repository TM cap of 50 | **Ratified in the Yggdrasil III PR, but it is a different mechanism from the one the founder remembers.** It caps shared host-repository evidence on every component. It does not separate the fusion only | `6b64a07ee` (PR #1629 → #1651/#1688, 2026-08-25). Hardened by `d27f6c1b4` (PR #1721, 2026-09-04) | "Discuss the sibling cap. I dont recal having this." **This PR does not change it** |
| (e) Origin assignment | **Manual frontmatter flag** (`origin: true`), written by `gaia dev update-named --origin` (`c096d7f7e`, 2026-06-02) and defaulted to `true` by the `gaia propose`/`name.py` template. No code derives it from merit | — | "Remove manual work on origins, make them automatic." |

## (a) 5★ Unique gate requires Origin on a fusion prerequisite

**Where it is stated or enforced**

- `src/gaia_cli/promotion.py:122-136`: "5★+ Unique Ultimate -> FUSION-STRUCTURE origin: the creator must hold Origin on >=1 of the generic parent's `prerequisites`".
- `src/gaia_cli/promotion.py:138-164`: `_contributor_holds_origin_in()`. Lines `274-288` route `level != "4★"` to it with `generic.prerequisites`.
- `src/gaia_cli/commands/dev/helpers.py:203-211`: the #2252 calibrate pre-flight. It refuses with "5★ Unique Ultimate requires Origin on a node in the generic parent's prerequisites".
- `CONTEXT.md:64`: "Gates: 4★ = Origin + TM ≥ 100 (A); 5★ = Origin + TM ≥ 250 (S); origins counted in **fusion structure** (`prerequisites`), not `suiteComponents`." `CONTEXT.md:83`: "Unique gates count origins in fusion structure; Suite gates count origins in `suiteComponents`."
- `founder/handovers/archive/YGGDRASIL_II_RATIFICATION_2026-07-07.md:259` (Q3): "Origin counted in **fusion structure** (`prerequisites`), not `suiteComponents`." Lines 5-44 (v4 amendment) keep it "for 5★+ only". Line 261 (Q5): "Asymmetric-by-design — Unique counts fusion-structure origins; Suite counts suiteComponents origins."
- `founder/reports/yggdrasil-iv-october-2026/adjudication/tools/adjcore.py:117-119`: calls `checkUniqueBranchGate`, so the adjudication ledger inherits the rule.
- **Not in `META.md`.** META §4.1/§4.2 have no 5★ Unique Origin rule. §4.2 states only the Suite rule ("Proposer must hold Origin status on at least 1 of the ≥ 5 `suiteComponents`").

**Introduced:** in text by `c84fc330c` (2026-07-07, PR #1170, "ratify Meta Schema RFC … per the 2026-07-07 grill-me interview"); in code by `eb7d9ff4d` (2026-07-15, "'Origin' is counted in the fusion structure … mirroring the Suite-gate origin predicate but pointed at prerequisites", Refs #996, merged to main in PR #1185). `5e7033440` (2026-07-19) narrowed it to 5★+ after it wrongly demoted `safishamsi/graphify` at 4★, and wrote the v4 amendment. `c71da5082` (#2252, 2026-10-30) copied it into the calibrate pre-flight.

**Ratified?** Only as a row in the agent-written "Decisions locked (from grill-me interview)" table. No verbatim founder statement supports it. The commit message says it "mirrors the Suite-gate origin predicate". On 2026-10-30 the founder rejected it: "Uniques dont need a fusion prerequisite origin at all. Where did that come from? thats from suites." (`CAMPAIGN.md:71`).

**Verdict: misapplied.** The Suite 5★ predicate (Origin on a component) was pointed at `prerequisites` and applied to Uniques. The founder's rule is that a Unique needs only to be its bucket's Origin, with TM/grade as the gate.

## (b) "A 1★ entry cannot hold Origin"

**Actual META text** (`META.md:58-59`, inside §1.3 *Redaction*):

> - **Origin** — a ≤1★ entry cannot hold Origin standing (§ 4.1); it is never a bucket's champion/representative.

**What §4.1 actually says** (`META.md:219`):

> - **Origin Status**: The **most renowned** implementation in a generic bucket earns "Origin" — the highest-rated named skill (ties broken by most-attributed / Trust Score), **not** necessarily the earliest. … Exactly one Origin exists per bucket.

§4.1 sets no star floor. The §1.3 sentence cites a rule that does not exist there.

**Other places it is enforced**

- `scripts/generateNamedIndex.py:427-438`: "Per META § 1/4.1: Origin standing belongs to a *Named* (2★+) skill. A pre-named/demoted (≤1★) entry cannot be Origin, so clear any author-declared origin flag". It sets `origin=False` when `is_redacted(level)`.
- `scripts/run_meta_sweep.py:7,214-219`: "Skill holds Origin standing despite being ≤1★ … Strip origin flag (origin: false) per META §4.1".
- `.agents/skills/gaia-meta-sweep/SKILL.md:99` (and its `.claude` mirror): "≤1★ cannot hold Origin".

**Introduced:** `e11472321` (2026-06-05, author `Claude`, PR #584 "review-1star-redaction"). That commit made redaction universal, and its "Champion-mapping bug fix" added "generateNamedIndex clears origin on ≤1★ entries (Origin requires Named 2★+)". The aim was to keep a redacted handle from becoming a bucket's public representative. That is a redaction concern, and it was written up as a merit rule. The meta sweep copied it in `86c2bf7dc` (PR #1721) and `34bf42935` (#1725).

**Ratified?** No. No founder document states a star floor for Origin. The founder, 2026-10-30 (`CAMPAIGN.md:72`): "origin = 'the original' with the highest merit. It is still the origin, it is just not 'named'. 2 star up is 'named' and I have no rule about origins having a star requirement."

**Verdict: agent-introduced.** The redaction goal (do not show a ≤1★ handle in honor-red) is legitimate, and it stays enforced by `redaction.py`/`validate_redaction.py`. Removing Origin was never part of it.

## (c) Origin by first publication vs by merit

**Merit (current, ratified):** `META.md:219` (above; "Updated 2026-06-02: Origin is merit-based; this supersedes the earlier 'first contributor / earliest' rule"), introduced by `a68b245ef` (2026-06-02, author `Claude`). It was confirmed by the founder in `founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md:43-45` ("**`META.md` §4.1 is correct.** Current Origin belongs to the **most renowned qualified named implementation** … not necessarily the first person to claim it"). `GOVERNANCE.md:59` says "adjudicated according to merit and qualification, not earliest `createdAt`".

**First publication (stale), still shipped:**

- `docs/index.html:571` and `docs/trust/leaderboard/index.html:132`: "**Origin skills** — the canonical implementation by the contributor who first published the technique." Introduced by `f853ff109` (2026-06-30, PR #887 "10 superadmin nitpicks", merged via #863). That was four weeks after META moved to merit.
- `src/gaia_cli/name.py:105`: the template body for new named skills says "First published by @{contributor}. This is the origin implementation", and line 87 writes `origin: true` by default. From `cfcbc9e33` (2026-04-29, PR #27, v1.0.0).
- `GOVERNANCE.md:64`: "The first contributor to run `gaia propose` against an awakened intake record … automatically becomes the origin contributor". From `0a1d843b4` (2026-05-05, PR #147). It predates the merit rule.
- `scripts/generateProjections.py:639`: "The first contributor to submit a valid named implementation claims the title slot". This is about the title slot of an unclaimed Ultimate, not Origin. It is out of scope and left unchanged.

**Ratified?** Merit: yes (META §4.1, Yggdrasil IV ratification §IV, founder 2026-10-30 `CAMPAIGN.md:79`: "Origin is highest merit"). First publication: no. It was superseded on 2026-06-02.

**Verdict:** merit is the ratified rule. The legend, the `name.py` template and GOVERNANCE line 64 are **stale** copy that was never updated, and the legend was added after the rule changed.

## (d) Suite-component repository TM cap of 50 (report only; no change in this PR)

**Where it is stated or enforced**

- `src/gaia_cli/trustMagnitude.py:90-92`: `SUITE_COMPONENT_REPOSITORY_CAP = 50.0` with the comment "A suite component may inherit repository evidence from its suite root, but that shared repository baseline cannot by itself promote every component."
- `trustMagnitude.py:318-…` `_isSuiteRootRepositoryEvidence` (rows of type `github-stars-own`/`repo-own` whose repository is the `suiteRef` root or its owner. The component's own repository is exempt). `trustMagnitude.py:855-882` `_applySuiteComponentRepositoryCap` scales those rows proportionally so their sum is at most 50.
- `META.md:93` (§2.1a): "Suite components identified by `suiteRef` may also receive a limited inherited repository-wide baseline from `github-stars-own` and `repo-own` evidence at the suite capstone, with a combined cap of **50 TM per component**. This baseline cannot alone make a component A or S; component-specific `benchmark-result`, `peer-review`, and `verifier-attestation` rows remain fully eligible."
- `docs/agents/curation-authority-map.md:45`, `docs/agents/curation-guidelines.md:55`.

**Introduced:** `6b64a07ee` "feat(tm): ratify Yggdrasil III trust integrity rules" (2026-08-25). PR #1629 (into `dev/yggdrasil-iii-newmeta`), shipped in PR #1651 (v7.12.0) and integration PR #1688. The PR body says: "`suiteRef` component repository evidence is bounded to a combined 50 TM baseline per component; component-specific evidence remains fully eligible." It was hardened by `d27f6c1b4` (PR #1721, 2026-09-04) with `CANONICAL_ROOT_SUITES`, so that "intermediate categories and sub-suites [cannot evade] the 50.0 TM component adoption ceiling".

**Rationale given:** a megasuite's single star count (for example `garrytan/gstack`, 46 components) would otherwise give every component the same 100+ TM. That would mint A grades across a whole suite from one repository. This replaced the G7 "mothership discount" divisor (`founder/handovers/done/G7_TRUST_TAXONOMY_RFC.md:187`).

**Ratified?** Partly. It shipped as part of the "Yggdrasil III trust integrity rules" PR, which was founder-reviewed and merged, and META §2.1a states it. No founder decision log or ratification document records the 50 figure or the per-component design. The Yggdrasil III handovers (`YGGDRASIL_III_META_AUDIT.md`, `YGGDRASIL_III_FUSION_SCORE_PLAN.md`) do not mention it.

**Comparison with the founder's understanding.** The founder recalls that "some skills have high TMs, and only the fusion is separated". That matches the **fusion-recipe** rule from the same Yggdrasil III PR: `fusion-recipe` contributes 0 TM, and structure is reported separately as the Fusion Score (META §2.1e). The 50 cap is a different, second mechanism. It applies to **every component** carrying `suiteRef`, not to the fusion. As a result, components of a large suite cannot reach A from the host repository's stars alone, while a standalone skill in the same repository without `suiteRef` can. The October calibration audit (`CALIBRATION-VERIFICATION.md:11,81`) found 37 skills escaping the cap only because they lack `suiteRef`.

**Verdict: implemented and merged with a founder-reviewed PR, but the founder does not recall it, and it differs from "only the fusion is separated".** It needs the founder discussion that `CAMPAIGN.md:85` asks for. **This PR does not change it.**

## (e) How Origin is assigned today, and every consumer

**Assignment (manual)**

- `gaia dev update-named <id> --origin true|false` (`src/gaia_cli/commands/dev/named.py:107-131`, flag at `commands/dev/__init__.py:695`). Setting `true` strips `origin` from every other file in the same bucket and logs a `demote` timeline event on them. Introduced by `c096d7f7e` (2026-06-02, "Add --origin flag to dev update-named and enforce uniqueness").
- `gaia propose` / `name.py:87` writes `origin: true` on every new named file.
- `commands/dev/build.py:57` and `impl.py:1332` write `origin: false` defaults.
- Agent skills tell curators to set it by hand: `.agents/skills/gaia-suite-intake/SKILL.md:271-274` (`gaia dev update-named … --origin true`) and `.agents/skills/gaia-review-meta-close/SKILL.md:101-107` ("move competitors to a different generic … and set `--origin true`").
- Adjudication tooling: `adjcore.py:213-215` op `setOrigin`.

**Post-processing:** `generateNamedIndex.py:427-438` clears `origin` on ≤1★ (rule b) and fails the build on more than one origin per bucket (`:441-447`; also `scripts/validate.py:655`, `scripts/syncDocsGraphAssets.py:53`, `scripts/build_docs.py:400`).

**Consumers of the flag**

- Gates: `promotion.py` `_holds_bucket_origin` and `_contributor_holds_origin_in` (via `checkUniqueBranchGate`); `commands/dev/helpers.py:190-200` (Suite 5★ pre-flight); `adjcore.py:84-90` `holdsSuiteOrigin`. `scripts/migrate_taxonomy_v6.py:452-462` is a historical migration.
- Index and projections: `generateNamedIndex.py` (`championSortKey`, `role_for_entry`, the CLI summary); `scripts/generateProjections.py:382,523-525` (tree.md/registry.md representative and the ⭑ mark); `scripts/buildApiProjection.py`; `scripts/buildTrendingProjection.py:569` (sets its own `origin` on the first entry of a contested list); `scripts/publication_parity.py:130`; `src/gaia_cli/trustFreshness.py:334`.
- Leaderboard: `scripts/generateLeaderboardData.py:126`. This reads **frontmatter** `origin` directly, not the index.
- Profiles, badges, OG cards: `scripts/generateProfilePages.py:302-343,457,999,1090,1108,1320`; `scripts/generateBadges.py`; `scripts/generateOgCards.py:563,669`.
- Origin wreath UI (reads `docs/graph/named/index.json`): `docs/js/plaque.js:236,354,799,962`; `docs/js/skill-graph.js:3904,3914`; `docs/js/named-skills.js:131,673`; `docs/js/skill-explorer.js:577,3100,3129`; `docs/js/hoh-modal.js:503,903`; `docs/js/page-ia.js:273,316,394`.
- CLI: `src/gaia_cli/treeManager.py:93,408`; `impl.py:778,1208,1869`; `localContext.py:103,479`; `interactive.py:84,120` (all read `named-skills.json`).
- Audits and reports: `scripts/run_meta_sweep.py:203-241`; `scripts/contentEngine/generate_weekly_report.py:200` and templates.

**Verdict: manual and unratified as a process.** The ratified rule (META §4.1, Yggdrasil IV §IV) is "most renowned", but no code computes it. The flag drifts whenever TM or level changes, which is why agents kept asking the founder to adjudicate Origin. The founder (2026-10-30, `CAMPAIGN.md:87`): "Remove manual work on origins, make them automatic--only exceptions would be frozen contenders. Frozen skills lock the TM and grade, and they can beat live ones. Highest merit only."

## Related: definition of "frozen"

Today "frozen" has no single definition:

- `gaia dev freeze` (`commands/dev/freeze.py`) works only on named skills. It sets `installable: false` and appends an `upstream_deprecated` timeline event. It does not record TM/grade.
- `scripts/run_meta_sweep.py:124-136` `is_skill_frozen` checks `frozen`/`frozenAt` or an `upstream_deprecated` event. A suite with `installable` not `false` is never frozen.
- Nothing locks a frozen skill's TM or grade. The build recomputes it whenever the input hash changes.

The founder's definition (`CAMPAIGN.md:83`, 2026-10-30): a skill frozen itself or "suites whose upstream is frozen — gaia dev freeze any node". The founder's standing rule from FD-7 (`CAMPAIGN.md:196`): never touch frozen skills in batch calibration.

## Conflicts to flag for the founder

1. `founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md:45-47,64` treats an **Origin change** as Class C (an approved transfer) and says there is "exactly one current Origin per claimed eligible generic node, no vacancy". The 2026-10-30 rulings (automatic, highest merit) supersede the manual-transfer part. Automatic derivation also means a tie between equally ranked contenders has no merit winner. The implementation PR proposes "incumbent among the tied keeps; otherwise no Origin until merit separates them", which creates a vacancy only in the tie-without-incumbent case. **This needs founder confirmation.**
2. `founder/handovers/archive/YGGDRASIL_II_RATIFICATION_2026-07-07.md` Q3 and Q5 and `CONTEXT.md:64,83` still state rule (a). The implementation PR corrects `CONTEXT.md`. The archived ratification gets a superseding note, and its original text is kept.
