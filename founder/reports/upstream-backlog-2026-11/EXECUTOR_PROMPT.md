# Executor handoff prompt — upstream backlog campaign, November 2026

Paste everything below the line into the executor session. The roster block is filled in by the founder.

---

# Gaia Skill Tree: Upstream Backlog Campaign — Execution

**Role:** Campaign Coordinator / Lead.
**Repository:** `gaia-research/gaia-skill-tree`.
**Mode:** Execution of an approved plan. Load `/gaia-orchestrator` first.

## Roster, limits and budget

Supplied by the founder. Do not start any phase until this block is filled in. Do not substitute a model, add a role or raise a limit on your own.

```
ROSTER:            <founder supplies: role -> model and effort>
CONCURRENCY:       <founder supplies>
BUDGET:            <founder supplies>
EXECUTION WINDOW:  <founder supplies>
```

Roles the plan expects: Coordinator / Lead, Infrastructure Builder, Synchronization Executor, Record Reconciler (may be the Executor), Curation Worker (only if phase P6 has rows), Independent Verifier, Reviewer. The founder is the Escalation Authority.

## Read these first, in this order

1. `founder/reports/upstream-backlog-2026-11/CAMPAIGN.md` — the control file and the founder rulings of 2026-11-15, verbatim. It is the authority for this campaign.
2. `founder/reports/upstream-backlog-2026-11/PLAN.md` — verified landscape, phases, gates, checks, definition of done.
3. `docs/agents/upstream-watcher.md` — watcher contract and the § F3a activation runbook.
4. `founder/steward/FOUNDER_LOCK_2283.md` and `founder/steward/decisions/issue-question-q-{08ecd62d,2568173e,bfd37238}.json` — locks C1, C2, C3.
5. `founder/steward/routines/issue-hygiene.md` and the `issueHygiene` section of `founder/steward/POLICY.yaml`.

Do not re-derive the landscape. PLAN.md is the baseline as of 2026-11-15 at `main` `9b4d9b98`. Confirm only that `main` has not moved in a way that changes it, then work from the watcher's dry-run report once it exists.

## What the founder approved

| # | Ruling |
|---|---|
| 1 | Version syncs go through the umbrella approval workflow. Draft PRs are retargeted to one integration branch. `obra/superpowers` is the canary. |
| 2 | GBrain hold (C3) is lifted for record reconciliation and version-only sync. New GBrain candidates and the breadth audit (#2276) stay held. |
| 3 | Addy hold (C2) is lifted for record reconciliation and version sync under the existing `addy-osmani/*` identifiers. The handle migration stays deferred. |
| 4 | A small CLI change lets `gaia dev sync-upstream` re-point a record to a new repository, explicitly and with a timeline event. Then AgentDB gets its verified source and version. |
| 5 | Free records are closed by hand now. The released children are closed through Steward closure. |
| 6 | Weekly batching is activated before the watcher's first write, then monitored for two weekly windows. |

A ruling approves only what it states. Nothing else is implied.

## Phases

Follow PLAN.md § C and § F. In short:

- **P0.** Record rulings 2 and 3 in the Steward decision records so issue hygiene stops treating both families as fully held; record them as new founder rulings dated 2026-11-15, and keep the earlier text as history. Create `dev/upstream-backlog-2026-11` from `main`. Every campaign PR targets that branch, never `main`.
- **P1.** Repair the watcher. First read `ruvnet/agentdb` and `ruvnet/ruflo` at source to establish where AgentDB's five components live and AgentDB's own release. Then the CLI change and the AgentDB relink (ruling 4). Add the `upstream.repo` fallback so `gsd-build/get-shit-done` is polled. Then a dry run on the real runner with `apply=false`. Acceptance: exit 0, empty `unknownEvidence`.
- **P2.** Activate weekly batching by the documented runbook. The first batch dry-run report is the single census for everything after it.
- **P3.** One disposition table for all 81 open upstream records, generated from the census and local registry state, with the evidence URL matched to `links.github` on every row. Hand closures for the free records. Steward closure for the 71 released children.
- **P4.** Version sync by umbrella approval, canary first. Sibling records on the same upstream repository are synced on the integration branch with the same tag, citing the umbrella approval.
- **P5.** Structural rows: deleted upstream means `gaia dev freeze`; renamed or moved means `gaia dev update-named --github-link` or `gaia dev rename`. Check which it is before acting.
- **P6.** Only if the census reports added components that are absent from the registry: `gaia dev prefill`, `gaia dev assess`, one L4 review page for the founder, then `/gaia-full-pipeline` phases 3 to 6.
- **P7.** One `gaia dev docs` regeneration, the checks in PLAN.md § D, one PR from the integration branch to `main`, handed to the founder ready.

P1 is serial. P3, P4 and P5 run in parallel after P2. Update CAMPAIGN.md and push after every phase and at every founder gate.

## Steps only a person takes

Stop and ask the founder for each of these. Prepare everything around them so each is a single action.

- Applying `upstream:approved`, `upstream:rejected` or `skip-child-gate` to any issue.
- Setting the repository variables `STEWARD_ISSUE_HYGIENE_V2`, `UPSTREAM_STAGING_INITIALIZED` and `UPSTREAM_BATCH_STAGING`.
- Turning on `issueHygiene.writesEnabled`, which also needs the independent verification the 2026-11-06 ratification requires.
- Any L4 topology decision. Present these as one Artifact review page, as CLAUDE.md § Founder review packets requires.
- Merging the integration PR to `main`.

## Hard limits

- No approval label is applied by an agent. `skip-child-gate` is never used on GBrain.
- No trust, star, Origin or evidence change. No calibration. Frozen skills are never touched.
- Registry changes go through `gaia dev` verbs only. No hand edits to `upstream:` blocks or timelines.
- New GBrain candidates, the GBrain breadth audit and the Addy handle migration are out of scope.
- Rulings 2 and 3 release children for closure only with per-row proof. Registry presence alone is not the proof.
- No closure, sync or success is reported that a tool did not perform. If a step was skipped or failed, say so.
- Never push to `main`. Merge commits only; squash is disabled.
- Gaia Dynamic is not used unless the census shows more than about 30 new, absent components outside the held families, and then only after asking the founder.
- No follow-up issues for the campaign's own remainder. Genuinely new, out-of-scope work may be filed.

## Stop and return to the founder if

- AgentDB's components turn out to live in the Ruflo repository, so ruling 4's assumption does not hold.
- The #2278 open-issue count refusal reappears in the dry run.
- The watcher report contradicts PLAN.md in a way that changes a ruling's premise, for example a held family's children are not in the registry after all.
- A step would need an authority this prompt does not grant.
- The budget or a concurrency limit would be exceeded.

## Cost discipline

- Work from the census report and CAMPAIGN.md. Do not read issue threads; #1835 alone has 79 comments.
- Give every worker the same frozen census packet. No worker rescans the repository or upstream.
- Do not read generated Class S diffs. Regenerate once at P7 and rely on `python scripts/build_docs.py --check`.
- The integration branch may be red. Cap fix rounds at two per PR, then stop and diagnose.
- The verifier re-runs commands and compares results. It does not re-read the builder's output.
- Run `/ev-collection` at most once, and only if P6 ingests anything.

## Definition of done

1. A scheduled watcher run exits 0 and writes at most one umbrella update per repository.
2. Every tracked record matches its latest upstream release with a timeline event, or is listed as held with the reason.
3. Every one of the 81 records has a recorded disposition: closed with proof, or held with the ruling that holds it.
4. Every removed component is frozen or repointed. Every added one is present, rejected or in an L4 packet.
5. The integration PR is merged by the founder with `build_docs.py --check` green, and the closeout record in CAMPAIGN.md lists what was held and why.

Report token spend per model and date on the campaign PR at every push, as the founder's standing preference requires.
