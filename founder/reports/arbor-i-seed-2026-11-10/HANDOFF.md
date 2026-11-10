# Arbor I — declaration-first behavioral seed: handoff

**PR:** [#2439](https://github.com/gaia-research/gaia-skill-tree/pull/2439) · **Branch:** `ccr-280a766f-1tkchh` · **Status:** ready for review. Founder review of 2026-11-11 applied. Not merged; no merge, benchmark, stamp or schema change is authorized.

## 1. What this PR does

It adds Arbor's first real body of behavioral knowledge: source-declared declarations for 20 canonical skills (27 conditional claims) and 3 source-declared relations between skills. Each record is pinned to exact canonical bytes and cites the exact upstream instruction bytes it was read from.

- Every claim and relation is `expert-declared`. Nothing is measured. The PR adds no receipt, interpretation, observation or Hell-Heaven record.
- The Hell-Heaven lens reads `absent-no-accepted-record` for all 22 subjects and `pairsEvaluated` is 0. Both must stay that way until evidence exists.
- No canonical skill, contract or pre-existing Arbor record changes. Arbor is additive.
- Skill Ultra (gaia-skill-heaven#126) is untouched.

Every canonical skill is an Arbor subject. This round drafted declarations for 20 of them. A skill with no record has nothing declared yet; it is not excluded.

## 2. Founder decisions, 2026-11-11

The project owner reviewed the 28-card review page by voice. The statements below are transcriptions supplied in the review decision log; hesitations are kept. Readings are the agent's and are labelled.

| # | Topic | Founder, verbatim | Reading applied |
|---|---|---|---|
| D1 | Attribution | "Okay, keep the pattern from Yggdrasil. So the pattern from Yggdrasil is the attribution is for the one who who actually proposed the skill, right? So if the skills are are like, Um .there's a link to the skill, the attribution will be the one who's fusing plus the one who owns the other two skills that are being compared to. And the agent will just be, you know, Uh. ,the the supporting Um. author" | The skill's owner is the primary attribution. The drafting agent is the supporting author. The project owner is governance, not author. |
| D1b | Vocabulary | "Don't use the term fuse. Um .The fuse mechanic is for Yggdrasil. Um .Just use a different term for Arbor." | Arbor records say relation or interaction. |
| D2 | Branch scope | "Just a skip scope check" | `skip-scope-check` applied to the PR after a scope check (§10). |
| D3 | Which uncertainty first | "It doesn't really matter. Next question" | No priority selected. No benchmark authorized. |
| D4 | Membership | "Of course it's admitted. ... All skills will be admitted to Arbor. It's just a matter of how we will stamp the skills. It's th- basically all skills in the tree are in Arbor and we are determining what their capabilities are with other skills. ... So skip all the questions that ask such questions" | No skill is voted in or out. The 20 skill cards are closed as not applicable. Claim text is still checked against sources. |
| D5 | Canon | "I'll be precise. If it's on the tree, it's canon. ... it should not be a question of whether it's a duplicate or not. If the Arbor Um .capability graph says that both are the same in essence, then both are the same in essence. That's part of the design of the graph" | A relation may say two skills share a behaviour. Both identities stand. |
| D6 | Data | "data should not be altered during Arbor. We are adding Um .capability through the graph of Arbor as a tree. We're not removing or or excluding data" | No canonical record is edited, merged or removed. |
| D7 | Doctrine conflicts | "there are already documents that it should read about Arbor. So it's not astray if if something is inconsistent, have it file an issue so that we can reconcile the docs" | Conflicts filed as issues (§9). No doctrine document was rewritten. |
| D8 | `context-save` / `context-restore` | "Yep, record that" (to: does save unlock restore when a checkpoint exists, restore having a fallback without one) | Relation kept, conditional on a checkpoint existing. |
| D9 | `systematic-debugging` with `diagnosing-bugs` | "that one's default, Um .not related, but it's interesting to see what happens if both are invoked at the same time. So this one is a benchmark. Uh .It's a call for a benchmark. ... not really Uh. a declared one." | No relation declared. Test candidate (§8). |
| D10 | `systematic-debugging` recovers `executing-plans` | "Yep, proceed" (to: record the recovery relation; the stop rules conflict) | Relation kept as source-backed. Which stop rule wins is unresolved and is not chosen here. |
| D11 | `guard`, `careful`, `freeze` | "Yep, unresolved. It will be filed Um .when the tests are batched together, Um .for later. Just record the decision now." | Both relations withdrawn from the store. Test candidates (§8). |
| D12 | `wayfinder` and `brainstorming` | "Yeah, they are not the same, but we should test what their relationship is." | Distinct. No relation declared. Test candidate. |
| D13 | `subagent-driven-development` and `verification-before-completion` | "Yep, and check our patterns now. Uh .I think we're answering the same things" (to: hold as a hypothesis only) | No relation declared. Test candidate. |

The founder's "Of course it's admitted" settles membership. It does not ratify the wording of any claim, and no record says it does.

### Card-by-card disposition

The review page had 28 cards: 3 seed-wide, 20 skill declarations, 5 relations. No choice was saved on the page; the decision log above is the record.

| Card | Disposition | Support type | Reference |
|---|---|---|---|
| Whose authority do the records carry? | Changed: owner primary, agent supporting, founder governance | founder ruling D1 | all 23 records re-issued |
| Branch-scope check | Label applied | founder ruling D2 | §10 |
| Where should telemetry look first? | No selection | founder ruling D3 | §8 |
| 20 skill declaration cards | Closed as not applicable: membership is not a decision | founder ruling D4 | claims stay `expert-declared`, source-declared |
| `grill-me` duplicates `grilling` | Kept. Both identities stand; the relation records shared behaviour | source-declared, untested | D5; record below |
| `guard` duplicates `careful` | Withdrawn; unresolved | proposal only | D11; §8 T1 |
| `guard` duplicates `freeze` | Withdrawn; unresolved | proposal only | D11; §8 T1 |
| `context-save` unlocks `context-restore` | Kept, conditional on a checkpoint | source-declared, untested | D8; record below |
| `systematic-debugging` recovers `executing-plans` | Kept; stop-rule precedence unresolved | source-declared, untested | D10; §8 T3 |

Raised in conversation, not cards on the page:

| Pair | Disposition | Support type | Reference |
|---|---|---|---|
| `systematic-debugging` with `diagnosing-bugs` | No relation declared | test candidate | D9; §8 T2 |
| `wayfinder` and `brainstorming` | Distinct; no relation declared | test candidate | D12; §8 T4 |
| `subagent-driven-development` and `verification-before-completion` | Hypothesis only | test candidate | D13; §8 T5 |

**Why the PR title once said seven relations.** Seven were drafted. An independent agent review judged two too weak before the review page was built, so the page showed five. The founder left two more unresolved. Three remain. The title now says three.

## 3. The doctrine this seed follows

Read from current `main`: `founder/ENDGAME.md` §4–§8, `founder/ENDGAME - SCHEMA.md` §9–§14, `founder/ENDGAME - MIGRATION.md` §2 and phases 1–4, `founder/ARBOR-DESIGN.md` (a visual design language, not the runtime contract), `registry/arbor/README.md`, and in the sibling repositories `docs/INTENT.md` §5, `docs/PLAN.md`, `docs/SPEC.md` §5 and the research ratification record.

On 2026-08-24 the owner retired the bulk R2 benchmark matrix and ruled (gaia-research `founder/RATIFICATION.md` §10):

- **A1** — "Arbor starts from Gaia expert operational declarations, never prestige. `human-led` and `model-led` are independent, non-exclusive behavioral claims."
- **A2** — "Telemetry identifies uncertainty; a targeted benchmark receipt confirms, qualifies, revises, or leaves a declaration inconclusive."

Four things are kept apart:

| Concept | What it is | Where it lives | State after this PR |
|---|---|---|---|
| Declaration | A conditional claim read from a skill's own instructions: who leads, under which conditions | `gaia.arbor-expert-declaration/v1`, projected `expert-declared` | 27 new claims, 3 new relation claims |
| Governed interpretation | A human curator's reading of named receipts against one claim | `gaia.arbor-interpretation/v1` | 1, pre-existing, unchanged |
| Hell-Heaven result and stamps | An earned behavioral profile and the labels derived from it | `gaia.hh-acceptance/v1` plus a research-owned payload not yet published (gaia-research#207) | none; lens absent for every subject |
| Invocation permission | Whether an agent may invoke a skill | the user, the harness, policy; a source's `disable-model-invocation` flag | not carried by Arbor |

Three evidence tiers are stated in every record's `authority.basis`: **source-declared** (true of every record here), **benchmark-observed** (none), **governed-interpreted** (none).

A `human-led` or `model-led` facet is read from instructions. It is not a `heaven-native` or `hell-safe` stamp, and this seed issues no stamp. The founder's endgame keeps a multidimensional Hell-Heaven profile (`ENDGAME - SCHEMA.md` §9) with stamps derived from it; nothing here pre-empts that. The R1 stamp taxonomy and its 20 seed labels were read as historical candidate material and appear in no record.

A `model-led` claim means the source text supports model leadership under the stated conditions. It never means the agent may invoke the skill, and every such claim says so in its `conditions`.

## 4. Attribution as recorded

Each claim's `authority` follows D1:

- `actor` — the skill's owner, taken from the canonical record's `contributor` field, as primary attribution; then the drafting agent and its session as supporting author. For a relation, the owner of both skills, since all three relations are stated in the skills' own instructions and each pair has one owner.
- `basis` — the evidence tier; the exact upstream commit, path, file hash and lines read; a statement that the skill owner wrote the instructions and did not write or review the claim's wording; the governance note; and the checks applied.

No record names the project owner as author, and none says a person ratified its text.

The import ran with `GAIA_OPERATOR_OVERRIDE=1`, the documented automation path, on this branch only. `gaia whoami` reports `denied` in this container because the generated authorization index is absent.

## 5. Delegation and review record

| Mission instruction | What happened |
|---|---|
| Preflight delegation with `@parke.dev/pi-subagent` | **Not available.** `pi` is installed with no configuration, the extension is not installed, and no provider credentials are present. Setting it up would have meant editing user-global configuration, so it was not done. |
| Haiku and Sonnet subagents, at most four at once | **Substituted:** Claude Code's native agent tool with an explicit Sonnet model on every dispatch. Four ran at once, never more. The harness session log confirms the model served to each. |
| Independent reviewer: Terra | **Not available** (no credentials for that provider). **Substituted:** one fresh-context Sonnet agent with an adversarial brief and no access to the author's reasoning. |

Four read-only inspectors extracted line-cited fact sheets from 43 upstream skill files. All 1,266 quotations were machine-checked against the pinned bytes; one did not match and was discarded. Selection, facets, claim wording, relations and this report are the lead agent's.

**The review is not cross-vendor.** Author and reviewer are models from one family. Treat it as a second reading.

**First pass: accept with changes.** No doctrine violation: no prestige, stamp, polarity or benchmark language, no implied permission, no impersonation, no relation worded as an observation.

| Finding | Problem | Resolution |
|---|---|---|
| B1 (blocking) | `obra/brainstorming`: the gate was described without its two stated exceptions | Both added; falsifier corrected |
| B2 (blocking) | `addy-osmani/source-driven-development`, model-led: said no step needs a person, though the text routes to the user on source conflicts and outbound endpoints | Conditions narrowed; both cases moved to the human-led claim |
| B3 (blocking) | `obra/systematic-debugging`, model-led: said no person need be reachable, though the text has an ask-for-help step and expects redirection | Both disclosed and cited; the sentence removed |
| N1–N15 | Six citation slips; missing unread-file caveats; an out-of-scope limit; an omitted condition; an unmentioned write; one non-verbatim quotation; authority wording; relations worded too firmly; falsifiers needing a comparison arm | All applied. Falsifiers are one-session observations. Two relations withdrawn |

The reviewer called `garrytan/qa` as model-led the closest call of the 27 and `caioribeiroclw-pixel/evidence-attestation` the weakest basis of the 20.

**Second pass** (fix verification, attribution wording, implementation): requested; result recorded here when it returns.

## 6. Records in this round

Forty-four upstream sources were resolved to a commit and hashed. One registry link returns 404 upstream.

| Skill (owner is the primary attribution) | Claims (facet) | Canonical pin | Upstream bytes read | Record |
|---|---|---|---|---|
| `mattpocock/grilling` | `interview-rounds-until-shared-understanding` (human-led) | `8d8a891fb9ef` | `mattpocock/skills@4ae2317ddb` (link ref `main`), sha256 `a146842ed93c` | `1a8b1adf2eea` |
| `obra/brainstorming` | `design-approval-before-build` (human-led) | `4b88547826ef` | `obra/superpowers@22f0b463e7` (link ref `main`), sha256 `2c9ca71f9488` | `67ffa164d18c` |
| `obra/systematic-debugging` | `root-cause-investigation-before-fix` (model-led)<br>`architecture-discussion-after-three-failed-fixes` (human-led) | `cab03ead911b` | `obra/superpowers@22f0b463e7` (link ref `main`), sha256 `51c6435d98c8` | `8e012de7720b` |
| `mattpocock/diagnosing-bugs` | `feedback-loop-before-hypothesis` (model-led)<br>`stop-and-ask-when-no-loop-can-be-built` (human-led) | `df77b1351da3` | `mattpocock/skills@4ae2317ddb` (link ref `main`), sha256 `849198df88cd` | `a22321edd9ff` |
| `mattpocock/wayfinder` | `decision-ticket-map-across-sessions` (human-led) | `eb07fcf50aea` | `mattpocock/skills@4ae2317ddb` (link ref `main`), sha256 `0c9fa96791ae` | `b183416f78f0` |
| `garrytan/cso` | `static-audit-through-trusted-launcher` (model-led) | `322f0a0f3193` | `garrytan/gstack@ee3bae4028` (link ref `main`), sha256 `ebf891082d33` | `0f9c4dbaec79` |
| `garrytan/qa-only` | `report-only-probing` (model-led) | `266f1bbb6ce9` | `garrytan/gstack@ee3bae4028` (link ref `main`), sha256 `1130fd5a80b0` | `e0dca77da67c` |
| `garrytan/qa` | `bounded-fix-verify-commit-loop` (model-led)<br>`user-decision-at-dirty-tree-and-loop-stop` (human-led) | `6e15d39020bd` | `garrytan/gstack@ee3bae4028` (link ref `main`), sha256 `1cda78da8e01` | `ac5f8111ad40` |
| `obra/executing-plans` | `continuous-inline-plan-execution-with-ledger` (model-led)<br>`four-stop-categories-and-main-branch-consent` (human-led) | `17b6dbb59037` | `obra/superpowers@22f0b463e7` (link ref `main`), sha256 `deaf176fa179` | `87db56ce7638` |
| `obra/subagent-driven-development` | `controller-dispatch-and-review-loop` (model-led)<br>`four-stop-categories-and-main-branch-consent` (human-led) | `1de89db64294` | `obra/superpowers@22f0b463e7` (link ref `main`), sha256 `1baf70e307bd` | `57890d8b3b18` |
| `obra/verification-before-completion` | `fresh-verification-before-completion-claim` (model-led) | `c5a7509a90d2` | `obra/superpowers@22f0b463e7` (link ref `main`), sha256 `2befe7fc55bc` | `69e565b88e5d` |
| `addy-osmani/source-driven-development` | `documentation-grounded-implementation` (model-led)<br>`surface-version-ambiguity-and-doc-conflicts` (human-led) | `c05a190b4edd` | `addyosmani/agent-skills@c004a74784` (link ref `0.6.10`), sha256 `c59faf851377` | `a6261bac6a4e` |
| `caioribeiroclw-pixel/evidence-attestation` | `structured-attestation-of-a-reused-claim` (model-led) | `b59455cde72e` | `caioribeiroclw-pixel/pluribus@b15a188628` (link ref `main`), sha256 `886ca4c1299b` | `13fe05cabc3b` |
| `garrytan/context-save` | `state-capture-without-code-changes` (model-led) | `a20c8177280f` | `garrytan/gstack@ee3bae4028` (link ref `main`), sha256 `8c182dd16eb5` | `59002318f900` |
| `garrytan/context-restore` | `resume-with-verify-first-sorting` (model-led)<br>`user-selects-among-ambiguous-checkpoints` (human-led) | `a835b396e4a8` | `garrytan/gstack@ee3bae4028` (link ref `main`), sha256 `86e2a4ac539f` | `43ad4fd30cb5` |
| `mattpocock/handoff` | `user-triggered-handoff-document` (human-led) | `fb23458098bb` | `mattpocock/skills@4ae2317ddb` (link ref `main`), sha256 `4cbb043950da` | `9b6f9ce1acbf` |
| `garrytan/careful` | `confirmation-before-destructive-commands` (human-led) | `3f338042745e` | `garrytan/gstack@ee3bae4028` (link ref `main`), sha256 `f3dfed24accc` | `3b2979628629` |
| `garrytan/freeze` | `user-set-edit-boundary` (human-led) | `1eb9392db883` | `garrytan/gstack@ee3bae4028` (link ref `main`), sha256 `b3fd0406df9e` | `0d911fd38ebf` |
| `garrytan/guard` | `combined-command-and-edit-guard` (human-led) | `924f2484f03b` | `garrytan/gstack@ee3bae4028` (link ref `main`), sha256 `74417889d310` | `6210a2f6e20d` |
| `garrytan/land-and-deploy` | `approval-gated-merge-and-deploy-verification` (human-led) | `3e4638a7937f` | `garrytan/gstack@ee3bae4028` (link ref `main`), sha256 `5082913d9df6` | `b6e2993f0b5c` |

Skills carrying both facets do so under different conditions, as A1 intends. Each `rationale` names the failure modes visible in the text and ends with a one-session observation that would falsify it.

### Relations

| From | Relation | To | Owner | Grounding in the two texts | Record |
|---|---|---|---|---|---|
| `mattpocock/grill-me` | **duplicates** | `mattpocock/grilling` | mattpocock | The `from` skill's linked file is a redirect to the `to` skill. Both canonical identities stand. | `fa8b852a2859` |
| `garrytan/context-save` | **unlocks** | `garrytan/context-restore` | garrytan | The `to` skill loads the checkpoint, commit and identity stamp the `from` skill writes. Conditional on a checkpoint existing; without one the `to` skill takes another route. | `3366428a6794` |
| `obra/systematic-debugging` | **recovers** | `obra/executing-plans` | obra | The `to` skill names the `from` skill as its route when a step fails because the code is wrong. Which skill's stop rule wins is unresolved. | `3342d4173a62` |

No relation is justified by a Yggdrasil structural link, and the builder reports `structuralOverlap: not-evaluated` for all three.

### Skills read with no declaration drafted this round

These remain Arbor subjects with nothing declared yet. The reasons are about what could be responsibly read, not about the skills' place in the Tree.

| Skill | Why no declaration was drafted |
|---|---|
| `mattpocock/grill-me` | Relation endpoint only. Its linked file is a seven-line redirect to `grilling` at the pinned commit. |
| `garrytan/investigate` | The registry link returns 404 at upstream `main`, so there were no bytes to read. |
| `upsonic/unittest-generator`, `laravel/upgrade-laravel-v13`, `rico-favor/implement-with-discernment` | The canonical record has no `links.github`, so there were no instruction bytes to read. |
| `garrytan/ship`, `garrytan/review` | Decisive steps (push, pull request, replies) live in section files that were not fetched. `ship` is publish-class, which Arbor cannot yet express (§11 F3). |
| `garrytan/fact-check`, `garrytan/data-loss-gate`, `garrytan/resolve-before-asking` | Depend on a gbrain store and describe their own gates as conventions. Worth a later round. |
| `addy-osmani/doubt-driven-development`, `mvanhorn/last30days`, `mksglu/context-mode` | Each has an egress, spend or command-routing property that needs its own reading. |
| `addy-osmani/deprecation-and-migration` | Explanatory guidance with no instruction that distinguishes who leads. |
| Twelve further skills | Fact sheets exist; they were not reached this round. |
| `obra/receiving-code-review` | Already holds Arbor's one governed record. Left as issued. |

Four R1 slots (review-only IaC checklist, decision matrix, gated auto-patch, chaos injection) still match no canonical skill.

Stars and Trust Magnitude played no part and appear in no record.

## 7. The hardest classification calls

1. **Guardrails are harness-enforced.** `careful`, `freeze` and `guard` act through a hook. I classed them `human-led` because every decision they create lands on a person, and declined `model-led`. The facet cannot say "harness-enforced"; the conditions do, and say the agent is unconstrained where the hook does not fire.
2. **`garrytan/cso` as model-led.** The text supports it: tool restrictions, a no-execution default, time budgets. The launcher binary and its phase sections were not read. Only the default mode is declared.
3. **Plan executors carry both facets, and the boundary is self-applied.** `executing-plans` and `subagent-driven-development` say "do not pause" and "four things stop you". The human-led claim states that the agent classifies each step itself.
4. **A boundary cannot be a claim.** A consumer cannot parse prose, so a `model-led` tag reads as positive whatever the text says. Unsuitability is recorded as an absent facet plus prose, never as a facet-tagged negative.
5. **`mattpocock/wayfinder` has agent-driven parts.** Kept human-led only: the source disables model invocation and writes to a shared tracker.
6. **`caioribeiroclw-pixel/evidence-attestation` as model-led.** A self-issued attestation. Declared with the claim narrowed to what the attestation records.
7. **The recovery relation has a known tension.** The text names it, and the two texts disagree about stopping after three failed fixes. It is declared with the conflict written into its rationale (D10).

## 8. Test backlog

Proposals only. None is authorized to run, none is filed as an issue, and no order was chosen (D3). They are to be deduplicated and batched later. Under A2 a focused benchmark is earned by a real runtime observation. None needs a model-graded evaluator.

| # | Question | Source | Observation that would settle it |
|---|---|---|---|
| T1 | `guard` active with `careful` and/or `freeze`: one check or two, one boundary or two? | D11; withdrawn relations | Prompts per flagged command; boundaries enforced |
| T2 | `systematic-debugging` and `diagnosing-bugs` invoked together | D9 | Which gates fire and in what order; fix attempts before any reproduction |
| T3 | Inside `executing-plans`, does `systematic-debugging`'s stop after three failed fixes hold, or do "only four things stop you"? | D10 | Fix attempts before a question is asked |
| T4 | `wayfinder` and `brainstorming`: what is their relationship? | D12 | To be designed; the founder ruled them distinct |
| T5 | `verification-before-completion` with the two plan executors: does it change what gets recorded as complete? | D13; withdrawn relation | A completion line for a task whose recorded test failed |
| T6 | `qa-only` leaves the repository as found | this seed | `git status` and `git diff` after a run on a seeded defect |
| T7 | `executing-plans` asks before a shared-branch push | this seed | Whether a push is attempted before a question |
| T8 | `careful` routes destructive commands to a person, or the agent rewrites them past the match | this seed | Commands run with no prompt; rewrites after a prompt |
| T9 | `context-save` then `context-restore` carries state across compaction | D8; this seed | Planted decisions recovered; finished tasks redone |
| T10 | `freeze` with a plan that spans directories | this seed | Denied edits; shell writes that replace them |
| T11 | `context-mode` with `careful` | this seed | Whether whitelisted commands bypass the check |
| T12 | `executing-plans` and `subagent-driven-development` on one plan | withdrawn relation | Cost and review depth; not the same behaviour |

One lesson from Arbor's first governed record applies to all of them: a listed skill is not a delivered skill. That record was `inconclusive` because the body was read in 3 of 5 treatment arms. Exposure must be measured.

## 9. Issues filed

| Issue | What it asks |
|---|---|
| [gaia-skill-tree#2440](https://github.com/gaia-research/gaia-skill-tree/issues/2440) | Reconcile four points with the founder review: every skill is an Arbor subject (undocumented); Arbor results from Yggdrasil structure (the contract forbids reading it); the attribution pattern and evidence tier (prose only today); what `duplicates` means |
| [gaia-skill-tree#2441](https://github.com/gaia-research/gaia-skill-tree/issues/2441) | Pin durability and CI coverage (§11 F1, F2) |
| [gaia-skill-heaven#253](https://github.com/gaia-research/gaia-skill-heaven/issues/253) | `SPEC.md` §5.1 and `PLAN.md` Lane G say Arbor has no relation contract or projection; upstream has both |

Not filed: any test proposal (§8).

## 10. Scope check and label

Changed paths against `main`: `registry/arbor/**` (sources, profiles, runtime, edge index), `docs/graph/arbor/**`, `founder/reports/arbor-i-seed-2026-11-10/**`, `tests/test_arbor.py`, `tests/test_arbor_committed_store.py`, and one bullet in `CLAUDE.md`. Nothing under `registry/named/`, `registry/nodes/`, `registry/schema/`, `skill-trees/` or `src/`.

The session's assigned branch name is not a recognized prefix, so `branch-scope.yml` reports every file. `skip-scope-check` was applied to PR #2439 on the founder's instruction (D2). It bypasses the branch-name gate only.

## 11. Architectural findings

- **F1 — The pin follows prestige, not behaviour.** `contentSha256` is the hash of the canonical record, which also holds evidence and timeline entries. An evidence edit changes the hash and a consumer's join then misses, though the instructions are unchanged. An upstream change behind a `main` link changes behaviour and leaves the pin valid. Twenty of the 21 pinned records link `main`. Each `authority.basis` records the upstream commit and hash, which shows the gap without closing it. Filed as #2441.
- **F2 — Relations couple Arbor's published files to curation.** `pairApplicable` follows current canonical bytes. In a trial, a one-byte edit to one endpoint's record changed four projection files and made `gaia dev arbor check` fail. `gaia dev docs` regenerates `docs/graph/arbor/` and its `--check` fails hard if stale; `registry/arbor` projections regenerate only on `gaia dev arbor replay`, and no workflow checks them. This PR adds `docs/graph/arbor/**` to the curation commit list in `CLAUDE.md`. Filed as #2441.
- **F3 — Arbor cannot express a boundary.** The facet enum is affirmative. "Not model-led" can only be an absent facet, and absence means unknown. Publish-class skills (research ratification T8) have no representation in Tree data.
- **F4 — Attribution and tier are prose.** A consumer cannot tell an owner-attributed, agent-drafted, source-declared record from any other except by reading `authority`. Filed in #2440.
- **F5 — The registry links one file; behaviour often lives in several.** `cso`, `qa`, `qa-only`, `land-and-deploy`, `context-restore` and both plan executors delegate decisive steps to files the canonical record does not link. Each affected claim says so.
- **F6 — Conditions are prose.** Skill Heaven's band judgment already abstains without a caller-supplied matcher. No conditions vocabulary was invented.
- **F7 — Founder direction and contract differ on structure.** The founder describes Yggdrasil composition as a source of Arbor results; the contract forbids reading it. Filed in #2440. This seed declares nothing on structural grounds.

## 12. How Skill Ultra should consume this

Use the existing `gaia.arbor-runtime/v1` envelope at `docs/graph/arbor/runtime/` and the existing provenance chain. No new contract is needed.

| Ultra needs to tell apart | Read it from | Rule |
|---|---|---|
| An applicable declared claim | `lenses.claims.profile.claims[]` with `support: expert-declared` and `interpretationSource: null` | A source-declared, unmeasured statement. Show it to the person with `conditions` and `authority` verbatim. It never licenses a direction: Skill Heaven's band judgment already abstains with `no-governed-claim`. |
| A governed empirical claim | The same list, with a non-null `interpretationSource` | `benchmark-confirmed`, `-qualified` and `-revised` are governed and conclusive; `inconclusive` is governed and unsettled. Never read a direction from `support`. |
| Missing behavioral evidence | No runtime file, a `contentSha256` join miss, or a lens status starting `absent-` | Unknown. Not negative, not neutral, and not "outside Arbor". After F1 this will be the common case. |
| A supported relation | `lenses.interactions.edges[]` with a non-null `interpretationSource` | None exists. |
| An unsupported relation hypothesis | The same list, `support: expert-declared`, empty `observationSources` | A hypothesis to disclose. Require `pairApplicable: true` and verify both endpoints' current bytes first. |
| A separate human authorization requirement | Not in Arbor | The source's `disable-model-invocation` flag, harness permissions and the ratified campaign charter. A `model-led` claim grants nothing; a skill with only a `human-led` claim is not thereby forbidden. |

Narrow consumer work this seed makes worth doing:

1. **Refresh the shipped Arbor cache and identity pins** at the Tree revision that contains this seed. Without that every join misses.
2. **Render declared claims as their own group** ("declared, not measured"), with attribution shown.
3. **Let the charter review be the conditions matcher** for declared claims. Do not build a prose matcher.
4. **Use relations only to annotate.** Never to filter or reorder retrieval results.
5. **Treat `human-led` claims as convergence-point candidates**, proposed to the person and never auto-invoked.

## 13. What remains for the founder

1. **Merge.** Not authorized by the review. If merged, use a merge commit; after the site publishes, `docs/graph/arbor/runtime/index.json` lists 21 new subjects.
2. **#2440 item 2**, the one open doctrine question: whether Yggdrasil structure may seed an Arbor hypothesis.
3. **The test batch** (§8), when wanted. Nothing runs until then.

To reword a claim before merge: edit `seed/seed.json`, remove that record's file from `registry/arbor/sources/`, run `seed/assemble.py`, then `gaia dev arbor import`, `replay`, `check` and the Arbor projection step, and commit. Records are immutable only once merged.

The review page (https://claude.ai/artifact/62WbCidAhDSzG46pKEvf5Q, private to the owner) now shows these dispositions and asks nothing.

## 14. Validation

All commands were run from the repository root on the PR branch.

| Check | Command | Result |
|---|---|---|
| Upstream bytes resolved and hashed | `git ls-remote` plus a fetch of each linked file at the resolved commit | 43 of 44 fetched; `garrytan/investigate` returns 404 |
| Fact-sheet quotations | each quotation searched in the pinned upstream file | 1,266 checked, 1,265 found, 1 discarded |
| Claim quotations and line citations | every quoted phrase in every `rationale` located in the upstream bytes; an inline citation must contain the line the quotation starts on | 0 not found; 2 benign repeats (a phrase that occurs twice) |
| Prestige, stamp and Yggdrasil-composition vocabulary | search of all authored prose | none; the only hits are source words such as "ranked hypotheses", "shell" and "refuse" |
| Owners | each record's owner compared with its canonical `contributor` field | 21 of 21 match |
| Pins against current `main` | each pinned canonical record hashed at `origin/main` `0121d509` | 21 of 21 unchanged |
| Standalone record validation | `gaia dev arbor check <record>` for each of 23 records, before import | 23 pass |
| Import | `GAIA_OPERATOR_OVERRIDE=1 gaia dev arbor import <record>` × 23 | 23 imported |
| Replay | `gaia dev arbor replay` | 21 profiles replayed |
| Store check | `gaia dev arbor check` | passed, 47 records (26 sources + 21 profiles) |
| Seed equals store | `python founder/reports/arbor-i-seed-2026-11-10/seed/assemble.py --check` | 23 ok |
| Canon and existing records preserved | `git diff` against `main` over `registry/named`, `registry/nodes`, `skill-trees`, the contracts and the earlier declaration, receipt, interpretation, profile and runtime file | no change |
| Site projection | `build_arbor_projection` write, then check | second run reports no change |
| Lens states | read of `docs/graph/arbor/` | 22 subjects; Hell-Heaven `absent-no-accepted-record` for all 22; 3 relations, all `expert-declared`, `pairApplicable: true`; `pairsEvaluated: 0` |
| Tests | `pytest tests/test_arbor.py tests/test_arbor_committed_store.py tests/test_build_docs_arbor.py` | 67 passed (60 before this PR, 7 added) |
| Lint | `ruff check` on the changed Python files | passed |
| Full docs check | `python scripts/build_docs.py --check` | **Not completed in this container:** the optional scientific stack and the generated `registry/named-skills.json` index are absent. It reported `named-index` and `docs-graph-assets` as drifting for that reason; `arbor-projection` was not among them, and the run left no file changed. CI is the authority. |
| Curation coupling (F2) | full import in a temporary store, then a one-byte edit to one endpoint's canonical record | 4 projection files change; `gaia dev arbor check` fails as stale |

Tests added:

- `tests/test_arbor.py::test_declared_edges_do_not_count_as_evaluated_pairs` — two authored relations are two edges and zero evaluated pairs; an observation makes one pair evaluated and still classifies nothing.
- `tests/test_arbor_committed_store.py` — six invariants over a replay of the committed store: replay leaves every immutable source untouched; committed profiles equal a fresh replay; un-interpreted claims stay `expert-declared`; declared relations never count as evaluated; the Hell-Heaven lens is absent without an acceptance source; every relation endpoint sees its interaction and no other.

## 15. Inventory

| | Count | State |
|---|---|---|
| Populated on this branch | 20 declarations, 27 claims, 3 relation declarations | `expert-declared`, source-declared, owner-attributed with the agent as supporting author |
| Pre-existing and unchanged | 1 declaration, 1 receipt, 1 interpretation | `obra/receiving-code-review`, `inconclusive` |
| Proposed only | 12 test questions (§8) | no record in the store |
| Unavailable | Hell-Heaven lens for all 22 subjects; any stamp; any governed relation; any measured claim in the seed | absent, and reported as absent |
| Production Arbor | unchanged | until PR #2439 is merged and published |
