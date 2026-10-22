# Upstream Watcher — Design

**Status:** V1 design (2026-07-08). Behaviour below is current as of the founder canonical-issue correction (PR #2133, 2026-10-22), which supersedes the closed-umbrella suppression of C9 (H-A) and the closed-bootstrap suppression of H3. Before it, the #2131 round-5 remediation (C9, 2026-10-22) closed the round-5 verifier findings H-A, H-B, M-1 to M-4 (and documents the low items L-1 to L-5 in [Known limits](#known-limits)) on top of the round-4 remediation (C8, 2026-10-22), which closes the round-4 verifier findings H1-H2, M1-M4, M6, L1, L3-L5 and L9 on top of the round-3 remediation (2026-10-22, which closed D1-D12 and I3) and the round-2 remediation (H1-H4, M1-M7, L1-L6) and the 2026-10-21 fail-closed remediation (H1-H2, M1-M10, L1-L7). Where a later item supersedes an earlier one, the text says so (for example D4 replaces the in-place chunk edits of M7). Where this document and the live workflow disagree, the disagreement is named explicitly (see [Runtime](#runtime--trigger-cadence-notifications) and [Open questions](#open-questions-curation-policy-not-infra)).
**Owner:** infra.
**Related:** [issue-tracker.md](issue-tracker.md), [triage-labels.md](triage-labels.md), [domain.md](domain.md).

The upstream watcher is a background agent that polls the source repositories of curated Gaia skills for new releases and opens **GitHub issues** (not PRs, not branches) proposing version bumps, component adds/removes, and structural link liveness. Approved issues fire a small workflow that opens a draft `review/meta/` PR against the registry, keeping every registry mutation behind the standard human-merge boundary.

The watcher is deliberately narrow: it tracks known-existing skills; it does not discover new ones. Skill discovery remains the job of the `scripts/crawlers/` infrastructure and the `bot/*` branch flow. The two systems share no runtime code path and should not be conflated.

---

## Table of contents

1. [Motivation](#motivation)
2. [Scope — V1](#scope--v1)
3. [Design forks — settled](#design-forks--settled)
4. [Data model](#data-model)
5. [Issue shape](#issue-shape)
6. [Labels](#labels)
7. [Approval mechanics](#approval-mechanics)
8. [Runtime — trigger, cadence, notifications](#runtime--trigger-cadence-notifications)
9. [Shared plumbing (`scripts/lib/`)](#shared-plumbing-scriptslib)
10. [CLI — new verbs](#cli--new-verbs)
11. [Bootstrap protocol](#bootstrap-protocol)
12. [Deprecation policy — freeze, don't delete](#deprecation-policy--freeze-dont-delete)
13. [Open questions (curation-policy, not infra)](#open-questions-curation-policy-not-infra)
14. [Phased rollout — PR plan](#phased-rollout--pr-plan)
15. [Non-goals](#non-goals)
16. [Known limits](#known-limits)

---

## Motivation

**The pain.** When a curated suite ships a new release upstream (e.g. `mattpocock/skills v1.1.0`), our registry has no mechanism to notice. Version drift accumulates silently. Component adds/removes are missed. Broken `links.github` pointers surface only when a user's `gaia install` fails.

**The current gap.** The existing `scripts/crawlers/` infrastructure discovers *new* skills and proposes them via `bot/*` branches. It does not track *existing* skills for version updates. `scripts/stargazerHeartbeat.py` refreshes star counts monthly on evidence rows but touches nothing else.

**The desired shape.** A background agent that watches known-curated suites, opens issues for detected changes, and — on maintainer approval — opens a draft PR that atomically bumps `upstream.version` and appends the corresponding timeline event. Never mutates the registry outside a human-merged PR.

---

## Scope — V1

**In scope:**

- All named skills with `suiteComponents` (i.e. **suites**). ~15–20 skills today.
- Release-tag detection via `GET /repos/{owner}/{repo}/releases/latest`.
- Component-delta detection (adds / removes) between the previous synced release and the newly detected release.
- Link liveness check (HEAD request on each component's `links.github` URL).
- Deprecation of components dropped upstream via **freeze** (not delete).

**Out of scope — V1:**

- Non-suite skills (deferred to V1.1 once volume proves manageable).
- Skills with "custom installation instructions" (deferred to V1.1 — see [Non-goals](#non-goals)).
- Description drift detection (dropped entirely — see design forks below).
- README parsing (dropped — brittle, high-noise).
- Auto-merge to `main` (never — human review is invariant).

**Auto-derived scope adjustments:**

- **Version-only mode**: if a suite's upstream repo has no `skills/`-shaped component layout (e.g. a general-purpose framework/product repo), the watcher falls back to version-only tracking — no component diff, no link liveness on components (only the umbrella). Detected automatically; documented in the umbrella issue body.
- **Opt-out**: skills carrying `watchUpstream: false` in frontmatter are skipped. Not implemented in V1 (no known need); documented here for schema-forward compat.

---

## Design forks — settled

Every fork was walked in a grill pass on 2026-07-08. This section captures the decisions and the rejected alternatives, so future changes have context.

### F1. Upstream signal source

**Decision: GitHub Releases only.** `GET /repos/{owner}/{repo}/releases/latest`.

**Rejected:**
- *SHA-based content drift* — high noise (typo fixes, formatting churn). Fires on every push, most events have no semantic content.
- *Both (releases + drift)* — approval fatigue; duplicate events on release day (release + its own SKILL.md diff fire simultaneously); suite-root SKILL.md false positives from unrelated component commits.

Skills whose upstream never tags releases fall through V1's net. This is acceptable — the vast majority of curated suites tag. Content-drift channel is a documented V1.1 opt-in if the gap is felt.

### F2. Scope — which skills are watched

**Decision: suites only.** V1.1 expands to skills with custom installation instructions.

**Rationale.** Suites are the highest-leverage target: a single upstream release can add or remove multiple components. `mattpocock/skills` is the canonical example. Non-suite named skills at 3★+ are numerous (~100+), but most have stable single-repo tracking where a manual bump is fine. Custom-install skills, on the other hand, carry prose that goes stale when upstream changes — that's the real V1.1 pain, and it deserves its own design pass (comparing installation instructions is a distinct problem from tracking versions).

**Rejected:**
- *All named skills with `links.github`* — noisy at ≤2★ (provisional entries).
- *All 3★+* — too broad without clear leverage justification.
- *Opt-in via `watchUpstream: true`* — over-engineered; requires backfill on every existing suite.

### F3. Issue shape — one issue vs fan-out

**Decision (amended 2026-10-21, #2131): umbrella issue + lossless batch record by default. A per-candidate `[intake]` child exists only when a row is escalated.**

**Amendment record — 2026-10-21 (#2131; founder-authorized in the steward issue-hygiene campaign brief).**

- *Superseded:* the original F3 decision was "umbrella + fan-out only for genuinely new components": one `[intake]` child per new component, cross-linked by `Child intakes: #…` on the umbrella and `Umbrella: #N` on each child, with a reject cascade. That default is superseded by the batch record below. Its rejection of a consolidated issue still stands for the reason it was given: the batch rows carry the full intake fields (suggested ID, contributor, attribution, evidence URL, description stub), so any row can be escalated to a full child on the standard template at any time. Full fan-out per release stays rejected as the default.
- *Not rewritten:* existing `upstream:child` issues remain valid. The watcher adopts an open child for a suggested id (the row gets `child: #N`); it never migrates or duplicates one.
- *Consequence for the approve gate:* an umbrella in batch mode has no children, so the child-resolution gate in `upstream-approve.yml` passes for it. Approving it confirms the version bump. It does **not** accept candidate rows. A row needs its own escalated child, and that child gates approval while it is open.

Current behaviour:

- One `[upstream:release]` umbrella per suite, keyed `upstream-suite:{owner}/{repo}`. A new version updates that umbrella in place (title and payload) instead of opening a second one.
- The umbrella payload is `payloadVersion: 2` with a `candidates[]` batch record. Rows are keyed by candidate id `{owner}/{repo}:{slug}` and carry `firstSeenVersion`, `lastSeenVersion`, `precheck`, `status` and `child`. Rows are never removed; a component dropped upstream stays visible.
- Prechecks run before any write. They cover registry presence, alias suspicion, open children (read from a LIST snapshot, not search) and prior rejection. Rows that are `present`, `tracked` or `rejected` are suppressed from new work but retained.
- **Rejection settles childless rows (M3).** When the newest closed umbrella carries `upstream:rejected`, each of its unresolved rows with no child intake becomes status `rejected`, with `rejectedBy: "#N"` naming the umbrella that settled it. Such a row is suppressed in later umbrellas, stays visible in the record, and never reappears as new work. A settled rejection survives an umbrella that closes later as completed. Only an explicit human `--escalate` gives it a child. A rejection recorded by a child is still re-derived from the closed-child history on every run.
- **A closed child without a disposition does not resolve its row (M6).** A row is resolved when it is registry-present or rejected, when its child is closed with `upstream:rejected`, or when its child is closed without a disposition and the candidate is registry-present. Any other row whose child is closed without `upstream:rejected` stays unresolved, carries the note `child closed without a disposition`, and is carried forward (closing an umbrella never drops it). The note is recomputed on every plan.
- **Rejection memory does not expire (M6).** The closed `upstream:child` history is read in full, with list pagination and no 30-day window, so a candidate rejected months ago is still suppressed. A failed page is unknown evidence.
- **Canonical backlog issue per suite (founder correction, PR #2133).** Identity is the suite parsed from the umbrella title (`[upstream] <owner>/<repo> → <version>`), compared case-insensitively. A title is never matched as a substring, so `obra/superpowers` does not claim `obra/superpowers-extra`. At most one OPEN canonical umbrella exists per suite, and it is the lowest-numbered exact match. A new finding updates that issue in place. When no OPEN umbrella exists, a new one is created even if closed umbrellas exist for the suite. The closed issues are never edited, commented on, relabelled or reopened, and they are preserved with their receipts. The closed history is still read in full (no window), because carry-forward takes the unresolved rows of the newest closed umbrella. Other open exact matches are listed under `duplicateOpenUmbrellas` in the run report and left untouched for Steward to reconcile. An open title that names the suite but does not parse is ambiguous: the suite gets zero writes and the run exits 3. Before a create, the open list is read again, so a run that a concurrent run beat to the create adopts that umbrella instead of making a second one. Workflow `concurrency: upstream-watcher` (queued, never cancelling) serialises the runs themselves. **Closed history is evidence (hardening, PR #2133).** A closed umbrella or bootstrap records the finding it processed in its payload: the suite, the proposed version, and the candidate ids it adds (`owner/repo:slug`). Before a create, the planner classifies the finding against that closed history (`scripts/upstream_watcher/evidence.py`):
- **processed**: a closed issue of the same suite records the same version and every candidate id. Nothing is created, and the run report lists it under `suppressedProcessed`. This closes the daily re-creation loop, including a closed umbrella whose rows were left unresolved.
- **new**: a new version, or a candidate the closed finding did not record. A new open issue is created.
- **ambiguous**: a closed issue names this suite and version but its payload is missing, tampered or contradicts its own title. The suite is blocked: no write, exit 3, reported under `unknownEvidence`.
Identity comes from the payload, not from a title or an issue number. A title only selects which closed issues to read. Closure classification is unchanged, and the watcher never closes or reopens an issue.
- **Body limit (M5).** GitHub caps an issue body at 65,536 characters. A suite whose full inline payload renders above 60,000 characters is written in **records mode**: the body keeps a compact index (`id`, `status`, `child`) in `candidates[]` and `candidateRecords: {chunks, rows, sha256}`, and the full rows live in numbered `<!-- gaia-upstream-record gen=… chunk=i of=N sha256=… -->` comments, 50 rows each. `sha256` is the **generation**: the SHA-256 of the full ordered row set. Every chunk header names it (D4), and the body commits to the ordered rows by that digest. Rows are never dropped.

- **Record trust (H2, I3).** A record comment counts only when the watcher identity authored it: login `github-actions[bot]` (`WATCHER_LOGIN` in `records.py`) **and** user type `Bot` (I3). Anyone else's record-looking comment is ignored and counted in a `::notice::`, so no outside comment can wedge a run. For the named generation only (D4), every chunk 1..N must be present exactly once, each trusted chunk must match its own header digest, and the concatenated rows must match the generation digest. Two trusted copies of one chunk fail closed even when identical. The same comment listed twice by pagination is one copy. A trusted comment of another generation, or whose `of=` is not the current count, is never read and cannot fail a run.

- **Records ceiling (measured, D12).** Two GitHub limits apply, and the smaller one binds. (1) The **body**: the index repeats every slug in `componentAdds`, so each candidate row costs about `len(id) + len(slug) + 45` characters of the body. (2) The **65,536-character limit on each record comment**: a full 50-row chunk carries `suggestedId` and `evidenceUrl` as well, so its size grows with the id length. The figures below are measured with the real planner (`batch.layout` for the body) on unescalated rows with fixed-length synthetic slugs:

  | Candidate id length | Body ceiling, slug 8 chars | Body ceiling, slug 22 chars |
  |---|---|---|
  | 26 | 844 rows | 711 rows |
  | 46 | 666 rows | 580 rows |
  | 76 | 505 rows | 455 rows |
  | 106 | 407 rows | 373 rows |
  | 129 | 354 rows | 328 rows |
  | 200 | 252 rows | 239 rows |
  | 270 | 196 rows | 188 rows |
  | 290 | 185 rows | 177 rows |

  From about 298 characters of id (slug 8) or 284 characters (slug 22) the **65,536-character limit on each record comment** binds first: one full 50-row chunk is over the limit, so any suite with 50 or more rows fails closed. The planner renders every chunk before the first write, so a suite that cannot be written costs no writes. The earlier figures (about 900 rows, and 822, 541, 357 and 267 rows) were not reproduced by the measurement and are withdrawn. A suite over either limit stops with exit 3 for that suite and writes nothing for it. Its error names the suite, the row count and the limit, and says that a curation decision is needed. The watcher never drops rows, so the decision is to reject or escalate some rows, or to split the suite.

- **Generations and writes (D4, replaces the in-place edits of M7).** A change to the rows is a new generation. The writer (1) creates the new generation's missing chunks as NEW comments, (2) switches the umbrella body to name the new generation (`candidateRecords.sha256`), and (3) deletes the superseded comments, best effort: a failed delete is a `::warning::`, and a later run deletes it again. No chunk is ever edited in place. A crash at any step leaves the body naming a complete generation whose comments all still exist, so a reader never sees a mix of two generations. Recovery converges: a create that landed before its error is reused by the next run, because the planner finds the chunk by generation and index. A rerun with no change writes nothing, and a converged 600-row suite writes nothing on rerun either. Two trusted copies of a target chunk fail closed for a maintainer to delete one, as before. Before this change, M7 edited chunks in place, and a write that failed part way left a mix that no run could read: a permanent wedge.

- **Recovery: `--reset-records SUITE` (M4).** A deleted, edited or otherwise damaged record comment fails its suite closed, with zero writes for it, and the exit-3 message names this flag and the suite. `watcher.py --apply --reset-records <suite>` is apply-only: it rebuilds the suite's rows from the fresh poll, keeping every fresh row. A target-generation chunk that is present once and intact is kept, and a missing, damaged or duplicated chunk is rewritten. Every comment of another generation is deleted. A converged reset writes nothing, and a later run without the flag writes nothing. Per-row status and child links stored only in the lost comments are not recovered: an open child intake is re-adopted by the list lookup, a closed rejected child stays rejected, and a closed child without a disposition reverts to `new` with no link. Other suites are unaffected. **C9 (M-2):** the reset also reads the newest closed umbrella's rows, exactly as carry-forward does, so a rejection that closed umbrella settled (M3) survives the reset. That read is the same fail-closed read: if the closed umbrella's records cannot be read, the suite stops with exit 3 and nothing is written.
- **Approval reset before body (H1, L3).** While an umbrella carries `upstream:approved`, **any** change to its hashed payload resets the approval, before the body changes: one reviewer note, then the `upstream:approved` to `upstream:needs-info` label change (retried three times). The hash covers every payload field: versions, `componentAdds`, `componentRemoves`, `linkLiveness`, `nameDrift`, every candidate row and its precheck, and the records digest. Only metadata outside the hash (for example an `updated_at` timestamp) is exempt, and a timestamp-only change writes nothing. The note names the approved version, the new version and each changed field. It carries a marker per payload hash, so a retried reset does not post the note again. If the reset still fails, the body is left alone and the next run is non-noop and tries again.
  - **Representation-only exemption (decision for the lead).** A legacy (pre-v2) umbrella converted to v2 is exempt when every approved legacy field is unchanged (`representation_only` in `batch.py`). The conversion only adds `payloadVersion`, the candidate index and the digests, and the components it lists were already approved as `componentAdds`. Without this, the first run would de-approve the live approved umbrellas (`garrytan/gbrain`, `heygen-com/hyperframes`), which are legacy payloads today. Any changed legacy field still resets. Removing the exemption is a one-line change in `representation_only`.
  - An escalation (`--escalate`) of a row on an approved umbrella applies the same reset, because it changes a row's status.
- **Digest checked on every read (D1a).** The watcher recomputes the canonical digest of the body payload on every read and compares it with the stored `payloadSha256`. A mismatch means the body was edited after approval. The approval is reset (one reviewer note, the H1 reset) and the body is repaired from the fresh plan. The repaired rows keep no child link from the edited body: the fresh prechecks re-adopt open children, so a forged link can only make a row unresolved, never resolved. A payload with no stored digest is a legacy payload and is compared by content as before, so the live legacy umbrellas are unaffected. **C9 (M-3):** an **open** umbrella whose payload block is missing or does not parse (a body edited by hand, or a create that stopped before its body was written) is tampered as well. Its body is repaired from the fresh plan, an approved umbrella is reset (one note, then the labels), and every open child intake is re-adopted by the live list lookup (matched by suggested id), never duplicated. `--escalate` on the same row then reports `already-child`.
- **The reset note is suppressed only by the watcher's own comment (D9).** A note is skipped when a comment written by the watcher (login and `Bot` type) already carries the marker for that payload hash. A human who quotes the marker does not suppress it.
- **Fanout reset (D10).** The legacy `--child-mode fanout` update path applies the same reset: for an approved umbrella whose payload changed, one note per payload, then the labels move to `upstream:needs-info`, then the body is written. A failed read, note or label edit stops the run before the body is written.
- **Create race (L1).** A create that lands on an identical umbrella written by a racing run is a noop with zero writes.
- **Transient link errors (L2).** A component whose HEAD check hits a network error is not a broken link. It is left out of the hashed `linkLiveness`, and its previous recorded state, if any, is carried forward.
- A rerun with an unchanged payload hash performs zero writes. A changed approved umbrella loses `upstream:approved`, gains `upstream:needs-info`, and receives one comment (see Labels).
- Carry-forward: a new umbrella for a suite starts from the unresolved rows of the newest closed umbrella. That umbrella is found in the full closed `upstream:release` history (a labels-filtered LIST with no `since`, every page read), not the 30-day window that the prechecks use, so an umbrella closed months ago still carries its rows. A carried row keeps its `status`, `child` and `firstSeenVersion` and records `carriedFrom: "#N"`. A row is unresolved unless it is `present`, `rejected`, or linked to a closed child intake. Closing an umbrella therefore never drops candidates. A failed or incomplete history read is unknown evidence: zero writes, exit 3.
- Dead child links: a `candidates[].child` that GitHub answers with HTTP 301 (transferred), 404 or 410 is absent. The planner clears the link and returns the row to `new`, so it is visible as unresolved again. A `::notice::` names the number. Any other lookup failure (5xx, 403, timeout, parse) is unknown evidence: zero writes, exit 3, and the link is kept.
- Legacy fanout (`--child-mode fanout`): every duplicate check (umbrella, bootstrap and intake) reads one paginated open-issue snapshot taken before the first write. A failed list raises and the run exits 3 with `unknownEvidence` and zero writes. A failed lookup is never read as "no existing issue". A failed umbrella create or update writes no child intake for that suite and exits 3 (M10).
- `--escalate` on a row whose child is adopted marks the row `tracked` at once. A child it creates marks the row `escalated`. An absent child is replaced rather than reported as `already-child`.
- `--child-mode fanout` keeps the legacy one-child-per-component path for emergencies.
- `--escalate <candidate-id>` (CLI, or the `escalate_candidate` input of `upstream-watcher.yml`) creates one `[intake]` child from a row on the standard template, or adopts the open child that already exists.

### F4. State storage — where does `upstream.version` live

**Decision: frontmatter `upstream:` block AND timeline events. Both. Same pattern as `level` today.**

Frontmatter answers "current version." Timeline answers "how did we get here." No orphan state files (rejected: `registry/upstream-state.json` would create a new file class outside Class P / Class S, invitation to drift).

See [Data model](#data-model) for exact schema.

### F5. Cadence & trigger

**Decision: `workflow_dispatch` manual only for V1. Daily cron block written but commented out with V1.1 sunset TODO.** *Not the live state: the schedule is uncommented in `upstream-watcher.yml`. See [Runtime](#runtime--trigger-cadence-notifications) and [Open questions](#open-questions-curation-policy-not-infra).*

Why manual first: control, verify outputs are useful before making it ambient. Enabling cron is a one-line change once trusted.

**Notifications-inbox hybrid.** The bot account (`nova-gaia` or equivalent) watches each suite's upstream repo at "Releases only." The watcher's cheap wake-up signal is `GET /notifications` (one API call, aggregated across all watched repos). Authoritative version comparison is still `GET /releases/latest` per matched repo. Watch subscription state is synced from registry via `scripts/upstream_watcher/sync_watches.py` (separate `workflow_dispatch` invocation, not on the hot path).

**Rejected:**
- *Daily cron V1* — fine, but no reason to enable before manual runs prove outputs.
- *Weekly cron* — loses currency for no material CI savings.
- *Webhooks* — requires upstream repo owner consent (non-starter).
- *Manual-only permanently* — quiet rot. Sunset condition documented in workflow YAML.

### F6. Approval mechanics

**Decision: label-driven, gated on child intake resolution.**

- Maintainer applies `upstream:approved` to the umbrella issue.
- Workflow fires on `issues.labeled`, checks that all child intake issues are closed (accepted or rejected), then runs `gaia dev sync-upstream <skill-id> --tag <tag>` on a fresh `review/meta/upstream-<skill>-<version>` branch and opens a **draft PR**.
- If child issues are still open, workflow comments back: `Cannot sync yet — 2 child intakes still open: #123, #124.` No PR opened. Reapply label after children close (or a re-trigger workflow fires automatically on the last child's `issues.closed`).
- `skip-child-gate` label bypasses the check (documented, auditable, follows existing `skip-*` convention).

Draft PR is human-merged as normal. Auto-merge is never enabled.

**Rejected:**
- *Comment-command grammar (`/approve`)* — over-engineered for V1.
- *Issue-close as intent* — conflates intent-to-act with action-took-effect.
- *Checkbox-driven partial approval* — good V1.1 refinement; ship all-or-nothing first.

### F7. Description drift

**Decision: dropped from V1. Replaced with link liveness check.**

Rationale: the registry's `description` field is a **curatorial artifact** (our editorial voice), not a mirror of upstream text. Chasing upstream description changes is chasing noise. Suite-root `SKILL.md` presence is not a stable invariant across upstream repos (verified: `mattpocock/skills` has none at root; `garrytan/gstack` does). README parsing is brittle.

What we actually care about on release day:

- ✅ Version tag advanced
- ✅ Component list changed (adds / removes)
- ✅ Pointers still work (`links.github` HEAD-check)

Description staleness, if a maintainer feels it, is refreshed via a normal `review/meta/` PR. The watcher stays out of the editorial layer.

### F8. Deprecation of dropped components

**Decision: freeze, don't delete.** Set `installable: false`, append `timeline.action: upstream_deprecated`, keep the record. History, badges, TM leaderboard entries survive.

See [Deprecation policy](#deprecation-policy--freeze-dont-delete).

---

## Data model

New optional frontmatter block on `registry/named/<contributor>/<skill>.md`:

```yaml
upstream:
  repo: mattpocock/skills                          # derived from links.github; stored to catch config drift
  version: v1.0.3                                  # last synced release tag
  releasedAt: '2026-06-14T00:00:00Z'               # from GitHub release.published_at
  syncedAt: '2026-06-14T08:12:04Z'                 # when the sync commit landed on main
  sourceUrl: https://github.com/mattpocock/skills/releases/tag/v1.0.3
  mode: components                                 # "components" | "version-only" (auto-detected)
```

Timeline gains two new `action` values (add to enum in `registry/schema/namedSkill.schema.json`):

- `upstream_synced` — a new upstream release was recorded. `previousValue` = old version tag, `newValue` = new tag. Details includes bot-signed provenance.
- `upstream_deprecated` — a component was frozen because upstream dropped it from a suite. Details includes umbrella + version that removed it.

**Schema changes.** `registry/schema/namedSkill.schema.json`:
- Add `upstream` object property (optional).
- Extend `timelineEvent.action` enum with the two new values.

Both changes must ship on a `schema/` branch per `CLAUDE.md` branch-scope rules. Schema and its bundled snapshot in `src/gaia_cli/data/registry/schema/` move in lockstep.

---

## Issue shape

### Umbrella issue (`[upstream:release]`)

Structural mirror of `.github/ISSUE_TEMPLATE/new_skill_intake.yml`: markdown intro → machine-readable payload → human summary → label vocab → reviewer actions.

**Title:** `[upstream] mattpocock/skills → v1.1.0`

**Labels applied by crawler at creation:** `upstream:release`, `needs-triage`.

**Body sections** (in order):

1. **Intro** (static markdown block explaining what an upstream issue is).
2. **Machine-readable payload** — a JSON block inside `<!-- gaia-upstream-payload ... -->` HTML comments. Contains: `payloadVersion` (2), `skillId`, `previousVersion`, `newVersion`, `releasedAt`, `sourceUrl`, `componentAdds[]`, `componentRemoves[]`, `linkLiveness[]` (component id → HTTP status), `nameDrift[]`, `candidates[]` (the batch record, one row per added component) and `payloadSha256` (SHA-256 of the canonical payload without that field; equal hash = nothing changed). This is what the approval workflow reads to determine what to sync. Never edited by hand.
3. **Version** — human-readable "was v1.0.3 → is v1.1.0; released 2026-07-05."
4. **Batch review** — a table with one addressable row per candidate: `cand:<id>`, suggested ID, status (`new`, `tracked`, `present`, `rejected`, `escalated`), registry / tracked / prior-disposition prechecks, child link and seen versions. Removed components are listed as `- removed-old-component (freeze)`. Each row carries the full intake fields in the payload, so escalation needs no re-crawl.
5. **Link liveness** — human-readable table of any 4xx/5xx responses with the specific broken paths.
6. **Label vocab** — the [Labels](#labels) table copy-pasted verbatim into the body. Rationale: maintainers unfamiliar with the flow learn it in-context, not via a hunt for docs.
7. **Reviewer actions** — 4-row action table (apply `upstream:approved`, `upstream:rejected`, `upstream:needs-info`, or `skip-child-gate` + `upstream:approved`).

### Child intake issue (`[intake]`)

Created by the watcher **only when a batch row is escalated** (`--escalate <candidate-id>` or the `escalate_candidate` workflow input), or in `--child-mode fanout`. An open child that already carries the suggested id is adopted, never duplicated. Populated from the crawler's best guess (id from upstream path, name from SKILL.md title if present, `links.github` blob URL, upstream author from repo owner, evidence entry pointing at the SKILL.md).

Uses the existing intake template. Header note: `Auto-populated by upstream watcher. Umbrella: #122.` Labels: `intake`, `needs-triage`, `upstream:child`.

Reviewed via the standard intake protocol. Acceptance triggers a `gaia dev add` mutation on the same `review/meta/upstream-<umbrella>` branch (or a sibling branch — implementer's call, but simpler if shared).

### Bootstrap issue (`[upstream:bootstrap]`)

Fired once per suite on the crawler's first ever run. Body: "We've never tracked this suite. Approve to baseline at current upstream version `v1.0.3`." No component diff, no proposal — just a one-time human confirmation that the derived `owner/repo` is correct before the crawler starts baselining. Applying `upstream:approved` writes the initial `upstream:` frontmatter block via `gaia dev sync-upstream --bootstrap`.

**The watcher never applies `upstream:approved` to a bootstrap (M3).** It creates the issue with `upstream:bootstrap` only and never dispatches `upstream-approve.yml`, in either mode. A human reads the proposed baseline and applies the label. The body says so (M4): it does not claim the baseline is approved. When an open bootstrap moves to a newer version while a human holds `upstream:approved`, the approval is removed and `upstream:needs-info` applied, with one note (H1: approval never survives a version change). The reset reads the issue's labels live at reset time, not from the run-start snapshot, so an approval applied after the snapshot is seen (D8). A failed read stops the run before the body is written. The watcher does not re-approve it.

**Canonical bootstrap per skill (founder correction, PR #2133).** A bootstrap is identified by its skill, parsed from the title, and at most one is open per skill. A closed `upstream:bootstrap` never blocks a new one: when none is open, a new one is created and the closed issue is left alone. The open list is read again right before a create, so a concurrent baseline is adopted. A bootstrap update that GitHub refuses is unknown evidence (L4): the run exits 3.

Alternative implementation: a single consolidated bootstrap issue listing all suites. Faster to close, less audit granularity — implementer's call.

---

## Labels

Add to `.github/labels.yml` (create the file — repo currently has none; use `github-labeler`-compatible format) or a one-time `scripts/setup-labels.sh` if preferred.

| Label | Applied by | When | Effect |
|---|---|---|---|
| `intake` | crawler / human | new-skill intake issue creation | **Note: missing on repo today (latent bug); create alongside upstream labels.** |
| `upstream:release` | crawler | umbrella creation | categorization |
| `upstream:child` | crawler | escalation of a batch row, or fanout child creation | links to umbrella (`Umbrella: #N`) |
| `upstream:bootstrap` | crawler | first-poll baselining | one-time; distinct workflow trigger |
| `needs-triage` | crawler | any issue creation | standard triage flow |
| `upstream:approved` | maintainer (never the watcher) | after review | fires sync workflow (gated on child resolution). Required on an open issue; the workflow refuses a closed or unapproved one (L3). A labeler the Verifier guard denies loses it (L1) |
| `upstream:rejected` | maintainer | after review | closes the issue as not planned. On an umbrella, the cascade closes each open child whose body names it, labelling each child `upstream:rejected` first (L5). A rejected umbrella also settles its childless rows as `rejected` for the next umbrella (M3). A closed `upstream:rejected` bootstrap is never recreated for its version (H3) |
| `upstream:needs-info` | maintainer; watcher on approved reset | after review, or when an approved umbrella's hashed payload changes (H1: a new version, a removed component, a changed liveness or name-drift row, a changed candidate row) | holds; no automation fires. The watcher removes `upstream:approved`, adds this label and posts one comment (once per payload) naming the approved version, the new version and the changed fields |
| `skip-child-gate` | maintainer (rare) | with `upstream:approved` | bypasses the child-resolution gate only; never closes, accepts or rejects a child or the umbrella. Honoured only from a Verifier or an allowlisted actor (L5); any other labeler loses the label |

Cross-link this table into `docs/agents/triage-labels.md`.

---

## Approval mechanics

### Workflow: `.github/workflows/upstream-approve.yml`

**Trigger:** `issues.labeled` filtered to `upstream:approved`. Issue numbers from `workflow_dispatch` must be digits and reach the shell only through `env:` (M9). No workflow input is interpolated into a `run:` block.

**Steps:**

0. Build the base `registry/named-skills.json` index (`scripts/assemble_gaia.py`, `scripts/generateNamedIndex.py`). The file is gitignored, so it is absent from a fresh checkout (H1, same fix as #1815 in `meta-guard.yml`).
1. Guard: the labeler must be a Verifier, or allowlisted. `approval.verifier_status` decides against the freshly built index. A missing, unparseable, empty or non-list-bucket index is a denial. There is **no bootstrap grant** (M1): an index with no authorised Verifier denies every actor, and only the allowlist can authorize one. Star levels are normalised (int `4`, `'4'`, `'4★'` and `'★★★★'` are all 4-star), and handles match case-insensitively (L9). The subject is the **labeler of the approval** (D3). The allowlist (`approval.allowlisted`) is the lockout escape hatch, and it needs the sender's user type (M2). The bot logins `github-actions[bot]`, `github-actions`, `codex`, `jules`, `claude-bot` and `gemini-bot` are trusted only for a `Bot` sender. **C9 (M-1):** no other `[bot]` login is trusted, whatever its suffix. Any GitHub App can carry that suffix, so `dependabot[bot]`, `renovate[bot]` and an arbitrary app are not allowlisted and are denied unless the Verifier index authorises the labeler. The human handle `mbtiongson1` is trusted only for a `User` sender with id `153011150`. A human account named `codex` is refused. On a labeled or opened event the sender is the labeler. On a `workflow_dispatch` by a Bot (`github-actions[bot]`, which is how `upstream-close-children` re-fires), the run is accepted only when `refire=true` **and** the most recent `labeled` event for `upstream:approved` (paginated issue events, fail closed) was applied by an allowlisted actor or a Verifier. Otherwise it is denied. A human dispatch still needs a Verifier actor. **Every denial posts a comment and removes `upstream:approved` (L1)**, as the reject guard removes `upstream:rejected`. The reject guard applies the same rules. The allowlist is the only way to authorize an index that names no Verifier, so keep it short.
1a. Verify the issue is open and still carries `upstream:approved`, on every trigger including `workflow_dispatch` (L3). A closed issue or one whose approval was withdrawn syncs nothing.
2. Parse and verify the payload. The digest is recomputed from the extracted payload. A stored `payloadSha256` that does not match fails closed with a comment: the body was edited after its digest was written (D1b). The payload block ends at its own `\n-->` line, so `-->` inside a JSON string cannot end it early (D7). A legacy payload with no stored digest is accepted.
2a. **Approval covers this payload (D1b).** The approval marker `<!-- gaia-upstream-approval payload=<sha256> -->` is a comment written by the watcher's own login and `Bot` type, and it names the digest a reviewer approved. On a labeled event the guard has just authorized the labeling, so the job records the digest it sees as the approval, once. On a dispatch (a re-fire or a manual re-run), the payload syncs only when the latest watcher-authored marker names the same digest. Otherwise the run refuses with a comment. A marker written by a human is not an approval. An umbrella approved before this change has no marker, so its `upstream:approved` is re-applied once. **H1, the labelled body:** on an `issues` event the digest is also recomputed from `github.event.issue.body`, the snapshot the Verifier labelled. If it differs from the digest of the body re-read at extract time, the job refuses with `payload changed after approval; re-apply the label`. No marker is minted and nothing is synced, so an edit between the label and the run is never approved by that label.
3. Child gate. Find open child intakes with a paginated REST LIST of open `upstream:child` issues, keeping those whose body has the `Umbrella: #N` line for this umbrella (exact number match). For a `payloadVersion: 2` umbrella, also verify each `candidates[].child` number live by GET and count any that is open. The gate never uses `gh issue list --search`, because search lags issue creation and can hide a child. Batch rows without a child do not gate. If any child is open AND `skip-child-gate` is not applied, comment on the umbrella and exit 0 (no failure — this is expected state). A candidate child that answers HTTP 404 or 410 is absent: it does not block, and the job prints a notice naming the number. If a list or any other get fails, or a candidate child link is malformed, comment on the umbrella and exit 1: the gate fails closed, so no sync branch or PR is created. Once the gate blocks, every later step is skipped. Each step after the gate is guarded by `success() && steps.child_gate.outputs.gate_passed == 'true'` (H4): a step that declares its own `if:` drops the implicit `success()`, so the gate output alone would let a failed sync step be followed by a freeze, a commit or a PR. A test asserts this for every post-gate step. `skip-child-gate` bypasses this gate only. It never closes, accepts or rejects a child or the umbrella. **L5:** the bypass is honoured only when the most recent `skip-child-gate` labeling was by an allowlisted actor or a Verifier (`approval.skip_label_authorized`, read from the issue events). Any other labeler's label is ignored here, with a `::notice::`, and the gate applies. A lookup that fails is fail closed.
3a. Count unresolved candidate rows (same rule as carry-forward). When the count is above zero, the draft PR body uses `Refs #<umbrella>` and states `Umbrella stays open: N unresolved candidate row(s).` When it is zero, the body uses `Fixes #<umbrella>`. A v1 payload has no rows and keeps `Fixes`.
3b. **Re-verify before the sync (D6).** Immediately before the branch and the sync, the job re-reads the umbrella. It must still be open, still carry `upstream:approved`, hash to the digest that was verified in step 2, and have a marker for that digest. Any mismatch refuses the sync before the branch is touched.
4. Checkout `main`, create branch `review/meta/upstream-<skill>-<version>`. A remote branch is replaced only when every listed commit has the bot as its GitHub author **and** committer, so a null author or a name-only `github-actions[bot]` refuses the reuse (D5). If that branch already exists on origin (a re-run for the same version, M5), its commits are compared with `main` through the GitHub compare API. The remote branch is replaced only when the comparison lists every commit and all of them are authored by `github-actions[bot]`. Any other commit, or a truncated list, is refused before any sync, with a comment on the umbrella. The commit step then pushes with `--force-with-lease` against the exact sha that was read, so a racing push fails rather than gets overwritten. The draft PR lookup and the umbrella comment lookup both fail closed: a failed lookup stops the job rather than opening a duplicate PR or comment.
5. Run `gaia dev sync-upstream <skill-id> --tag <tag> --source-url <url>` (writes frontmatter block + appends timeline event atomically).
6. For each `componentRemoves[]`: run `gaia dev freeze <component-id> --reason "removed from <umbrella>@<version>"` (writes `installable: false` + timeline `upstream_deprecated`). A failed freeze fails the job, comments on the umbrella and opens no PR (L4).
7. Run `gaia dev docs` to regen Class S artifacts (per docs-cohesion Guard E). A failure fails the job and opens no PR (L4).
8. Commit, push, open **draft** PR titled `[upstream sync] <skill-id> → <version>`, body links back to umbrella and lists changes. The body states the freeze count that actually happened (L4). The body's Scope section states that approval confirms the version bump only. It does not accept any batch row, and rows not escalated to a child stay open candidates in the umbrella. The closing line is `Fixes #<umbrella>` only when no row is unresolved (step 3a); otherwise it is `Refs #<umbrella>` with the `Umbrella stays open` line.
9. Comment on umbrella: `Draft PR #999 opened: <url> -- Approval confirms the version bump to <version> only. Batch rows not escalated to a child intake stay open candidates here and are not accepted. Auto-closes this umbrella on merge (Fixes #<umbrella>).` When rows are unresolved, the last sentence reads `Umbrella stays open: N unresolved candidate row(s)` instead.

### Workflow: `skip-child-gate-guard` job (L5)

`upstream-approve.yml` runs a second job on `issues.labeled` for `skip-child-gate` only. It applies the step 1 rules to the labeler (a Verifier, or an allowlisted actor by sender type and id). A labeler who is not authorized loses the label, with a comment, and the job fails. The child gate above also ignores an unauthorized label, so a removal that lags an approval cannot bypass the gate.

**Concurrency (L4).** The approve workflow sets `cancel-in-progress: false`. A denied or superseded run never cancels a Verifier sync already in flight. A second approve run queues behind it in the same group.

**The shared payload block (L3).** Every reader of an umbrella body imports `PAYLOAD_RE` from `scripts/upstream_watcher/markers.py`: `approval.py`, `batch.py`, `records.py`, and the inline scripts in `upstream-approve.yml` and `upstream-close-children.yml`. A parity test fails if any copy reappears.

### Workflow: `.github/workflows/upstream-close-children.yml`

**Trigger:** `issues.closed`.

Filters to issues labeled `upstream:child`, finds the umbrella (from body reference), checks if all siblings are now closed, and if the umbrella already has `upstream:approved` applied, re-fires the approve workflow via `gh workflow run upstream-approve.yml` targeting the umbrella. Small; ~30 lines.

Both the sibling check and the reject cascade use the same paginated LIST and `payloadVersion: 2` candidate verification as the approve gate, never search. A failed lookup fails the job. The sibling check then does not re-fire approve, and the cascade closes nothing.

Also handles the reject cascade: if an umbrella is closed as `upstream:rejected`, auto-closes any still-open `upstream:child` issues that reference it, and comments the batch row ids (`cand:<id>`) that the rejection covers. Rows are retained in the payload and never removed.

**Lookups fail closed (M2).** The umbrella state read (Case 1) and the rejected-label read (Case 2) are errors when they fail, never read as "no action". Nothing is re-fired and nothing is closed on a failed lookup.

**Closed children keep their rejection (L5).** Before the cascade closes a child, it labels the child `upstream:rejected` (`gh issue edit --add-label`), then closes it with `not planned`. A closed child carrying that label is rejection memory: the prechecks suppress its row in later runs. The cascade acts with `GITHUB_TOKEN`, so its label and close events do not start new workflow runs, and `upstream-reject.yml` is not re-entered for these children.

**Ownership proof (M7).** A candidate row's `child` link can point at a child that another umbrella now owns. The cascade therefore closes a child only when that child's own body names `Umbrella: #<this umbrella>`. Any other child is skipped and logged, and a child whose body cannot be read is not closed and fails the job.

**Re-fire (M8, D3).** The re-fire passes `-f refire=true`. The approve guard accepts a bot re-fire only when the labeler of the approval is a Verifier (see step 1). The job holds `actions: write` (job scope only) so `gh workflow run` can re-fire approve. A failed dispatch is an `::error::`, a marker comment on the umbrella, and a failed job. It is never a silent warning.

---

## Runtime — trigger, cadence, notifications

### Trigger and inputs

`.github/workflows/upstream-watcher.yml` runs on manual dispatch and on a daily schedule (06:00 UTC, `--apply`). Dispatch inputs:

- `skill_id` — poll one suite only.
- `apply` — create or update issues (default dry-run).
- `escalate_candidate` — create or adopt one intake child for a batch row (for example `garrytan/gbrain:foo`), then exit. Uses the `apply` flag.

The run always uses `--child-mode batch` and writes `generated-output/upstream-watcher-report.json`, uploaded as the `upstream-watcher-report` artifact. The workflow builds its arguments as a bash array, so nothing is word-split (L1). Before any run, `skill_id` must match `^[A-Za-z0-9._/-]+$` and `escalate_candidate` must match `^[A-Za-z0-9._/:-]+$`. A value with other characters fails the job without running the watcher.

The workflow's token scope is `issues: write` and `contents: read` (L5). The watcher never pushes, opens PRs or dispatches workflows.

> **Live state versus the decision above (M4, founder call).** Section [F5](#f5-cadence--trigger) records the decision as manual dispatch only, with the daily cron "written but commented out". That is **not** the live state. `upstream-watcher.yml` has the `schedule` (`0 6 * * *`) uncommented, and every scheduled run passes `--apply`, so the watcher creates and updates issues daily. This change does not alter the schedule. Keeping it live, or commenting it out, is a founder decision. Until the founder rules, treat the schedule as live.

### Run report and exit codes

`--report FILE` writes JSON: `issuesCreated`, `issuesUpdated`, `suppressedDuplicates` (candidate rows suppressed as present, tracked or rejected), `duplicateOpenUmbrellas` (other open umbrellas per suite, listed for Steward and never written), `suppressedProcessed` (findings a closed issue already records, so nothing was created), `retainedCandidates` (total rows kept across touched umbrellas), `unknownEvidence`, `unavailable` (H2 and C9 H-B: suites skipped for the run, each with its `reason`, `permanent` with its HTTP status, or `tree-truncated`), `recordsReset` (M4: suites rebuilt by `--reset-records`) and `suites[]` (`suite`, `umbrella`, `newRows`, `totalRows`, `outcome`, where an ambiguous identity's outcome is `blocked-identity`). It is also written in dry-run.

| Exit | Meaning |
|---|---|
| 0 | Success, including no findings and no-op reruns. |
| 1 | Hard failure (import error, unrecoverable exception). |
| 2 | `--escalate` target not found in any open umbrella. |
| 3 | Unknown evidence or an incomplete write stage. The report lists the failing source (`unknownEvidence`). **Poll-stage** failures (a release or tree read, M1-M3) and registry failures make **zero writes for the whole run**. **Write-stage** failures (a list, a get, an umbrella write, a record write, M5-M10) stop the run at that point. Suites written earlier in that run are complete and idempotent, so a rerun is a noop for them. **Record-level** failures (H2: a suite's record comments fail verification) are different: that suite gets zero writes, the other suites are still processed, the bootstrap pass still runs, and the run exits 3 at the end. Each entry carries `"stopped": true` when it halted the run, so a reader can tell the two apart. |

**Retries (C9 H-B).** A transient read (no response, 5xx, 429, or a rate-limited 403) is attempted three times in all, with a wait of 1s after the first failure and 2s after the second. Only a failure that survives all three attempts is unknown evidence. A 404, a permanent refusal and a permission failure are never retried. The wait is injectable (`live.RETRY_SLEEP`) so the tests run without it.

Fail closed is absolute: no source of unknown evidence is treated as "absent". Pagination follows explicit pages and refuses to truncate. Searches are never used to decide whether something is already tracked, because the search index lags creation.

### Fail-closed reads (#2131 remediation)

| Read | Failure | Result |
|---|---|---|
| `GET /releases/latest` (M1) | HTTP 404 | "no releases tagged": the suite is skipped |
| `GET /releases/latest` (M1, C9 H-B) | a 403 (other than a repository refusal or a rate limit, see below), 5xx, 429, network, unparseable, or no tag | unknown evidence: zero writes for the run, exit 3, after the three attempts of the retry rule (see [Retries](#fail-closed-reads-2131-remediation)). Never "skipped, exit 0" |
| Component tree (M2, C9 H-B) | any failure after its retries, or a 404 on the tag | unknown evidence: no `componentRemoves` derived, exit 3. A missing `skills/` root is a legitimate version-only layout, not unknown |
| Component tree, truncated (C9 H-B) | the recursive listing is truncated | **not** a whole-run stop. The component root is walked one directory at a time (`GET git/trees/<sha>`), within **200 requests per suite**. The diff is the same as the full recursive read. If the budget runs out, or any sub-call still fails after its retries, the suite is `unavailable: tree-truncated`: a `::notice::`, an entry under `unavailable` with `reason: "tree-truncated"`, no finding, no removals, and the other suites proceed. The exit is unaffected |
| Component tree shape (M3) | `{}`, no `tree` list, a non-object entry, or an empty list without the tree's `sha` | unknown evidence, exit 3. An empty list is version-only only when the response identifies a resolved tree |
| Open `upstream:bootstrap` list | any page failure | unknown evidence (`IdempotencyLookupError`), zero writes. A closed bootstrap is not read and never blocks a create |
| Umbrella state, labels and candidate lookups in close-children and the approve PR steps (M2, M5) | any failed `gh` read | `::error::` and a failed job. Nothing is re-fired, closed, commented or created |
| Head check (L2) | network error | not a broken link: left out of the hash, previous state carried forward |
| Closed `upstream:child` history (M6) | any page failure | unknown evidence (`GhError`), zero writes |
| Record comments (M5, H2, D4) | a trusted (watcher-authored, `Bot`) comment of the named generation that is missing, duplicated, edited or unlisted | unknown evidence for that suite, zero writes to it, other suites still processed, exit 3 (`RecordError` is a `GhError`). A record-looking comment by any other user is ignored, not an error. Comments of other generations are never read |
| Stored payload digest (D1a) | the stored `payloadSha256` does not match the body payload | not trusted: the approval resets with one note and the body is repaired from the fresh plan. The repaired rows keep no child link |
| Umbrella payload at approval (D1b, D6) | the body was edited after its digest was written, or no approval marker covers the digest | the approve job refuses with a comment before any branch or sync |
| Labeling history for a bot re-fire (D3) | the issue events cannot be read, hold no `upstream:approved` labeling, or name a labeler who is not a Verifier | the re-fire is denied with a comment and nothing is synced |
| Tag in the tree URL (D11) | a tag with `#`, `?`, `/` or a space | percent-encoded whole, so `recursive=1` always reaches the request |
| Poll: release or tree, permanent refusal (H2, M-4): HTTP 451, 410, or a 403 whose body is the repository's own refusal (a DMCA takedown, a blocked or disabled repository) | **the suite is skipped.** A `::notice::` names it, it is listed under `unavailable` with `reason: "permanent"`, it has no finding, so it cannot produce a removal or an approval change. Its exit is unaffected and other suites proceed. An operator removes or repairs the suite's `links.github` or its entry. A bare 403 is **not** a refusal (M-4) |
| Poll: release or tree, transient (H2, C9 H-B): 5xx, 429, a rate-limited 403, a timeout, a network error, an unparseable body | unknown evidence, zero writes, exit 3, **after three attempts** (the retry rule below). A 403 is rate limited when it carries `X-RateLimit-Remaining: 0`, a `Retry-After`, or a rate-limit message |
| 403 naming a permission problem (C9 M-4): `Resource not accessible by integration` | unknown evidence, exit 3, **not retried**. The message names the permission problem and the fix (grant the watcher token or App read access to the repository, then re-run). It is never a skip. A bare 403 with no repository message is handled the same way |
| Closed `upstream:release` history (C9 H-A) | any page failure, including the second page of a full first page | unknown evidence (`GhError`), exit 3, zero writes. The history is never read as "no closed umbrella" |
| Record comments of a suite (M4) | exit 3 for that suite, zero writes for it, other suites still processed. The message names `--reset-records <suite>` and the flag rebuilds the suite from the fresh poll |
| Closed child without `upstream:rejected` (M6) | the row stays unresolved with the note `child closed without a disposition`, unless the candidate is registry-present |

### Notifications inbox as wake-up signal (optional cost optimization)

The bot account watches each suite's upstream repo at "Releases only." The watcher runs:

1. `GET /notifications?participating=false&all=false&since=<lastRun>` — one API call, returns aggregated release events across all watched repos.
2. Filter `subject.type === "Release"`, extract `repository.full_name`.
3. For each matched repo, cross-reference against registry: is any named skill's `links.github` pointing here?
4. For each match, `GET /repos/{owner}/{repo}/releases/latest` (authoritative comparator).
5. Compare against stored `upstream.version` in frontmatter.
6. Compute component diff, run link liveness HEAD checks.
7. Open umbrella + child issues via `gh issue create --body-file <path>`.

**Never marks notifications as read.** Notifications are treated as a pure wake-up signal, not a state store. Idempotency comes from comparing against frontmatter `upstream.version`.

**Fallback**: if the notifications API call fails or returns nothing, the watcher iterates the full suite list and does per-repo release lookups. Correctness identical; API cost higher (~15–20 requests vs ~2–3). Acceptable degradation.

### Subscription sync

`scripts/upstream_watcher/sync_watches.py` reads registry frontmatter, computes the set of `owner/repo` for all in-scope suites, and calls `PUT /repos/{owner}/{repo}/subscription` on the bot's token for each. `DELETE` for repos no longer in scope. Runs via separate `workflow_dispatch`. Not on the watcher's hot path.

---

## Shared plumbing (`scripts/lib/`)

New top-level shared module. Motivating overlap: `stargazerHeartbeat.py` already has ~30–40% of the primitives we need. Extracting prevents drift (two scripts parsing frontmatter slightly differently is a real 6-month-later bug).

**Structure:**

```
scripts/lib/
├── __init__.py
├── frontmatter.py       # _split_frontmatter, _load_yaml_simple, update_block_in_frontmatter
├── github_api.py        # parse_owner_repo, fetch_json, head_check
└── named_iterator.py    # walk registry/named/**/*.md → yield (path, parsed_frontmatter)
```

**Migration plan:**

- **PR 1** (this design): introduce `scripts/lib/` as new files. Heartbeat unchanged. No behavior change.
- **PR 2**: rewrite `stargazerHeartbeat.py` to import from `lib/`. Verify no regression against known-good monthly outputs. No new functionality.
- **PR 3**: implement watcher, importing from `lib/`. Watcher is the first "greenfield" client of `lib/`.

**Contract for future additions to `scripts/lib/`:** infrastructure primitives used by **≥2 scripts**. Not a dumping ground for one-script helpers. New primitives require justification in PR body.

---

## CLI — new verbs

Follows `CLAUDE.md`'s Programmatic-First Policy and CLI Pre-Flight Rule: every registry mutation atomic, every mutation logs to timeline, no hand-edits.

### `gaia dev sync-upstream <skill-id> --tag <tag> --source-url <url>`

Mutates `registry/named/<contributor>/<skill>.md`:

- Writes/updates the `upstream:` frontmatter block.
- Appends `timeline.action: upstream_synced` with `previousValue`, `newValue`, `details`.
- Atomic: both writes or neither.

**Flags:**
- `--bootstrap` — first-time write. `previousValue` is null. Timeline event details reads `"first-run baseline"`.
- `--dry-run` — prints the diff without writing.
- `--user <handle>` — same as other `gaia dev timeline` verbs (uses actor identity for signed provenance in timeline `details`).

**Pre-flight validation** (per CLI Pre-Flight Rule):

- `--tag` must match a valid GitHub release tag pattern (`v?\d+\.\d+\.\d+.*`).
- `--source-url` must be a `github.com/{owner}/{repo}/releases/tag/{tag}` URL that matches the derived `upstream.repo`.
- Refuses to write if the previous `upstream.version` equals the target (already synced) unless `--force`.
- Refuses to write if the skill is not currently 2★+ (below the reward-artifact threshold).

### `gaia dev freeze <skill-id> --reason <text>`

Mutates a named skill:

- Sets `installable: false` in frontmatter.
- Appends `timeline.action: upstream_deprecated` with `details: <reason>`.
- Does NOT delete the file, strip `links.github`, or otherwise remove history.

**Pre-flight validation:**

- Refuses if `installable: false` is already set (no-op).
- Warns (does not refuse) if the skill is 3★+ — 3★+ frozen skills fail META.md §2.4 Star Bar and need a curation-policy decision (see [Open questions](#open-questions-curation-policy-not-infra)).

### `gaia dev relink <skill-id> --new-url <url>`

Mutates `links.github`, appends a timeline event. Used when link liveness detects an upstream file was renamed/moved and the maintainer wants to point at the new location without opening a full-scale review.

**Not V1 core**, but the watcher will surface cases that need it. Implement alongside the watcher if trivial; defer to V1.1 if not.

---

## Bootstrap protocol

On the crawler's first ever run, no suite has an `upstream:` frontmatter block. Naive comparison (`null → v1.0.3`) would fire spurious "new version detected" issues on day one for every suite even though nothing changed.

**Fix.** First-run detects missing `upstream:` block and opens **one `[upstream:bootstrap]` issue per suite** (alternative: one consolidated issue listing all suites — implementer's call). Body: "we've never tracked this suite. Approve to baseline at current upstream version `v1.0.3`. No description or component diff proposed." Approving = `gaia dev sync-upstream --bootstrap` writes the initial frontmatter block.

Purpose: gives you a human-audited moment to verify the crawler correctly derived `owner/repo` from `links.github` before it starts producing real diff issues.

One-time cost: ~15–20 issues, closable in a day.

---

## Deprecation policy — freeze, don't delete

When a suite drops a component in a new release, the crawler proposes freezing (not deleting) the affected component.

On umbrella approval:

1. `gaia dev freeze <component-id> --reason "removed from <umbrella>@<version>"` runs on each dropped component.
2. Sets `installable: false` in the component's frontmatter.
3. Appends `timeline.action: upstream_deprecated`.
4. Does NOT strip `links.github` (per CLAUDE.md CONTRIBUTING.md §12 — the pattern already used for 2★-and-below skills with no public repo is `installable: false`, keep the link).

The component's badge, TM leaderboard entry, and `gaia tree` display all survive. Only new `gaia install` requests are blocked.

**Star Bar wrinkle:** META.md §2.4 requires 3★+ skills to carry a verified `links.github` blob URL. A frozen 3★+ component technically still has `links.github` — but its target has been deleted upstream. This is a curation-policy question, not an infra one. See [Open questions](#open-questions-curation-policy-not-infra).

---

## Open questions (curation-policy, not infra)

0. **Daily schedule (M4, founder decision).** The live workflow runs daily at 06:00 UTC with `--apply`, which contradicts the F5 decision above. Options: keep it live, or comment out the `schedule` block as F5 describes. Disabling it is a founder call. This remediation changed no schedule.

These deliberately do NOT block V1 implementation. They are questions the maintainer team resolves through curation practice, not infra design.

1. **Frozen 3★+ components and Star Bar.** When upstream deletes a component that we track at 3★+, freezing keeps the record but the `links.github` target 404s. Two policy options:
   - (a) Add a `frozen: true` flag that bypasses Star Bar validation.
   - (b) Auto-demote frozen skills to 2★.
   - Neither is picked by V1. Watcher flags the case in the umbrella issue and lets the maintainer decide per instance.

2. **Custom installation instructions drift.** V1.1 scope. `.claude/skills/update-suite-instructions/` handles this manually today. A future design pass will define what "installation-instructions drift" means (structured field? prose section? line-diff threshold?) and how the watcher surfaces it. Deferred entirely.

3. **Non-suite skills at 3★+.** V1 does not watch them. If maintainer pain accumulates ("suite X's non-suite children ship independently and we miss releases"), expand scope in V1.2 with a `watchUpstream: true` opt-in flag. Not scoped now.

---

## Phased rollout — PR plan

Each PR is scoped to be independently mergeable. CI must be green on each before the next merges.

| PR | Branch prefix | Content | Notes |
|---|---|---|---|
| 1 | `infra/` | `.github/labels.yml` (or `scripts/setup-labels.sh`); create missing labels including `intake`; add `.github/ISSUE_TEMPLATE/upstream_release.yml` (skeleton) | No behavior change; label metadata + template only |
| 2 | `infra/` | Extract `scripts/lib/{frontmatter,github_api,named_iterator}.py` from heartbeat, no changes to heartbeat behavior | Preparatory refactor; heartbeat unchanged |
| 3 | `infra/` | Rewrite `stargazerHeartbeat.py` to import from `lib/`; add tests confirming identical output on a known input set | Verify no monthly-heartbeat regression |
| 4 | `schema/` | Extend `namedSkill.schema.json` — add `upstream` object property, extend `timelineEvent.action` enum with `upstream_synced` + `upstream_deprecated`; mirror to `src/gaia_cli/data/registry/schema/` | Two schema dirs must move in lockstep (branch-scope rule) |
| 5 | `cli/` | New verbs: `gaia dev sync-upstream`, `gaia dev freeze`. Includes CLI pre-flight validation, `--dry-run`, `--bootstrap`, `--user` flags | Registry mutation atomic; no hand-edits |
| 6 | `infra/` | `scripts/upstream_watcher/watcher.py`; `.github/workflows/upstream-watcher.yml` (manual dispatch plus daily schedule; see Runtime); `.github/workflows/upstream-approve.yml`; `.github/workflows/upstream-close-children.yml`; `scripts/upstream_watcher/README.md` | The functional core |
| 7 | `infra/` | Run watcher in dry-run mode against all suites; produce & commit the initial bootstrap issue list; open bootstrap issues | First real-world exercise; produces the intake/version list the maintainer requested |

**PR cap on CI retries.** If a PR requires more than 2 rounds of "push a fix, wait for CI" iterations, stop and investigate — there is likely an underlying design issue, a broken test the PR didn't cause, or a schema-lockstep problem. Do not grind. Escalate.

**V1.1 (deferred to a later cycle):**
- Uncomment the cron schedule in `upstream-watcher.yml`.
- Add non-suite skill support.
- Add custom-installation-instructions drift (`upstream:instructions` label already reserved).

---

## Non-goals

The watcher explicitly does not:

- Discover new skills from GitHub search / trending / topics. That's `scripts/crawlers/`.
- Mutate the registry outside a human-merged PR. Every registry write goes through `gaia dev` verbs on a `review/meta/` branch.
- Track descriptions, README prose, or any editorial text. Description staleness is a human-refresh concern.
- Auto-merge PRs. Human review is invariant.
- Handle upstream repos that never tag releases (V1). They fall through the net silently. A `upstream:untracked` label might surface these in V1.1.
- Alter the star count / evidence refresh path. That remains `scripts/stargazerHeartbeat.py`'s job.
- Replace `.claude/skills/update-suite-instructions/`. That skill's automation is V1.1 scope.

---

## Known limits

Recorded in the round-5 remediation (C9, 2026-10-22). None of these is coded in that change.

- **Short or empty list page is trusted as the end of the list (audit, PR #2133).** `LiveGh.list_issues` stops at the first page shorter than `per_page`, and no total is checked. A page that comes back empty while more issues exist returns a truncated list without error. Consequences: a missing open canonical umbrella can lead to a duplicate create, and missing closed history can lead to a re-create. `tests/upstream_watcher/test_list_truncation.py` pins the defect as a strict xfail. Fix: continue on `rel="next"` and cross-check the total, as the census does. Each is a boundary an operator should know, not a defect that blocks a run.

- **L-1. The child gate counts only open children that carry `upstream:child`.** `upstream-approve.yml` step 3 lists open `upstream:child` issues and checks the candidate children that rows link to. An intake child without that label does not hold the umbrella's approval. The watcher and `--escalate` always apply the label, so this matters only for a child a human created by hand.
- **L-2. A name-drift check skips a component it cannot read, and does so silently.** `check_name_drift` skips a component whose SKILL.md cannot be fetched, or whose frontmatter has no `name`, because absence of a signal is not evidence of drift. Drift in that component is then missed for this release. The check runs only on an update finding, so it is not revisited until the next release.
- **L-3. A tag that moves backwards is proposed as an update.** `compute_finding` reports any stored version that differs from the live tag as an update, so a re-pointed or older tag opens an umbrella for a version below the one recorded. The approval is human-gated, so nothing is applied automatically.
- **L-4. A rate-limited link check is recorded as a broken link.** `check_component_liveness` records every non-2xx HEAD status, so a 429 or a 403 from `raw.githubusercontent.com` becomes a hashed `linkLiveness` row. Only a network error is excluded (L2). The umbrella then changes, and an approval resets, until the row clears. The status is visible in the row.
- **L-5. A child closed without a disposition leaves its row unresolved.** M6 keeps such a row unresolved and carried forward, with the note `child closed without a disposition`. The umbrella therefore stays open, and its approval PR says `Refs`, not `Fixes`, until a human labels the child `upstream:rejected` or the candidate becomes registry-present.

## References

- `CLAUDE.md` — Programmatic-First Policy, CLI Pre-Flight Rule, branch-scope rules, Class P vs Class S artifacts.
- `CONTRIBUTING.md` §12 — `installable: false` convention for non-installable named skills.
- `META.md` §2.4 — Star Bar (`links.github` requirement at 3★+).
- `META.md` §5 — Timeline transparency mandate.
- `.github/workflows/stargazer-heartbeat.yml` — CI pattern precedent.
- `.github/ISSUE_TEMPLATE/new_skill_intake.yml` — issue-shape precedent.
- `docs/agents/issue-tracker.md` — issue lifecycle docs.
- `docs/agents/triage-labels.md` — label registry (extended by this design).
