# Upstream Watcher — Design

**Status:** V1 design (2026-07-08), pre-implementation.
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

**Decision: umbrella issue + fan-out only for genuinely new components.**

- One `[upstream:release]` **umbrella** issue per release. Owns: version bump, component diff summary, link liveness report, deprecations.
- One `[intake]` **child issue** per new component, populated by the crawler using the existing `.github/ISSUE_TEMPLATE/new_skill_intake.yml` template. Reviewed via the same intake protocol human proposers use — no parallel review path.
- Removed components stay under the umbrella as checkbox entries; freezing them does not need a new issue.

**Cross-linking.** Umbrella body enumerates child issues (`Child intakes: #123, #124, #125`). Each child intake references the umbrella (`Umbrella: #122`). If umbrella is closed as `upstream:rejected`, an `on: issues.closed` workflow auto-closes children.

**Rejected:**
- *One consolidated issue* — new components need the full intake YAML schema. Cramming that into a "release delta" body means either reinventing the intake review protocol or losing the checklist. Both bad.
- *Full fan-out* (separate issue per version, per component, per drift) — admin overhead; cross-referencing pain; rejecting the umbrella orphans N child issues.

### F4. State storage — where does `upstream.version` live

**Decision: frontmatter `upstream:` block AND timeline events. Both. Same pattern as `level` today.**

Frontmatter answers "current version." Timeline answers "how did we get here." No orphan state files (rejected: `registry/upstream-state.json` would create a new file class outside Class P / Class S, invitation to drift).

See [Data model](#data-model) for exact schema.

### F5. Cadence & trigger

**Decision: `workflow_dispatch` manual only for V1. Daily cron block written but commented out with V1.1 sunset TODO.**

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
- Workflow fires on `issues.labeled`, checks that all child intake issues are closed (accepted or rejected), then runs `gaia dev sync-upstream <skill-id> --version <tag>` on a fresh `review/meta/upstream-<skill>-<version>` branch and opens a **draft PR**.
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
2. **Machine-readable payload** — a JSON block inside `<!-- gaia-upstream-payload ... -->` HTML comments. Contains: `skillId`, `previousVersion`, `newVersion`, `releasedAt`, `sourceUrl`, `componentAdds[]`, `componentRemoves[]`, `linkLiveness[]` (component id → HTTP status). This is what the approval workflow reads to determine what to sync. Never edited by hand.
3. **Version** — human-readable "was v1.0.3 → is v1.1.0; released 2026-07-05."
4. **Components** — checkbox list: `+ new-component-a (child intake: #123)`, `+ new-component-b (#124)`, `- removed-old-component (freeze)`.
5. **Link liveness** — human-readable table of any 4xx/5xx responses with the specific broken paths.
6. **Label vocab** — the [Labels](#labels) table copy-pasted verbatim into the body. Rationale: maintainers unfamiliar with the flow learn it in-context, not via a hunt for docs.
7. **Reviewer actions** — 4-row action table (apply `upstream:approved`, `upstream:rejected`, `upstream:needs-info`, or `skip-child-gate` + `upstream:approved`).

### Child intake issue (`[intake]`)

Created by the crawler for each **new component** added upstream. Populated from the crawler's best guess (id from upstream path, name from SKILL.md title if present, `links.github` blob URL, upstream author from repo owner, evidence entry pointing at the SKILL.md).

Uses the existing intake template. Header note: `Auto-populated by upstream watcher. Umbrella: #122.` Labels: `intake`, `needs-triage`, `upstream:child`.

Reviewed via the standard intake protocol. Acceptance triggers a `gaia dev add` mutation on the same `review/meta/upstream-<umbrella>` branch (or a sibling branch — implementer's call, but simpler if shared).

### Bootstrap issue (`[upstream:bootstrap]`)

Fired once per suite on the crawler's first ever run. Body: "We've never tracked this suite. Approve to baseline at current upstream version `v1.0.3`." No component diff, no proposal — just a one-time human confirmation that the derived `owner/repo` is correct before the crawler starts baselining. Applying `upstream:approved` writes the initial `upstream:` frontmatter block via `gaia dev sync-upstream --bootstrap`.

Alternative implementation: a single consolidated bootstrap issue listing all suites. Faster to close, less audit granularity — implementer's call.

---

## Labels

Add to `.github/labels.yml` (create the file — repo currently has none; use `github-labeler`-compatible format) or a one-time `scripts/setup-labels.sh` if preferred.

| Label | Applied by | When | Effect |
|---|---|---|---|
| `intake` | crawler / human | new-skill intake issue creation | **Note: missing on repo today (latent bug); create alongside upstream labels.** |
| `upstream:release` | crawler | umbrella creation | categorization |
| `upstream:child` | crawler | child intake creation | links to umbrella |
| `upstream:bootstrap` | crawler | first-poll baselining | one-time; distinct workflow trigger |
| `needs-triage` | crawler | any issue creation | standard triage flow |
| `upstream:approved` | maintainer | after review | fires sync workflow (gated on child resolution) |
| `upstream:rejected` | maintainer | after review | closes issue with sync-skipped comment |
| `upstream:needs-info` | maintainer | after review | holds; no automation fires |
| `skip-child-gate` | maintainer (rare) | with `upstream:approved` | bypasses child-resolution gate |

Cross-link this table into `docs/agents/triage-labels.md`.

---

## Approval mechanics

### Workflow: `.github/workflows/upstream-approve.yml`

**Trigger:** `issues.labeled` filtered to `upstream:approved`.

**Steps:**

1. Guard: labeler must be a Verifier (reuse the meta-guard authorization check pattern from `.github/workflows/meta-guard.yml`).
2. Parse machine-readable payload from the issue body.
3. Check for open child intakes referenced in the payload. If any are open AND `skip-child-gate` is not applied, comment on the umbrella and exit 0 (no failure — this is expected state).
4. Checkout `main`, create branch `review/meta/upstream-<skill>-<version>`.
5. Run `gaia dev sync-upstream <skill-id> --version <tag> --source-url <url>` (writes frontmatter block + appends timeline event atomically).
6. For each `componentRemoves[]`: run `gaia dev freeze <component-id> --reason "removed from <umbrella>@<version>"` (writes `installable: false` + timeline `upstream_deprecated`).
7. Run `gaia dev docs` to regen Class S artifacts (per docs-cohesion Guard E).
8. Commit, push, open **draft** PR titled `[upstream sync] <skill-id> → <version>`, body links back to umbrella and lists changes.
9. Comment on umbrella: `PR opened: #999. Auto-closes umbrella on merge (Fixes #<umbrella>).`

### Workflow: `.github/workflows/upstream-close-children.yml`

**Trigger:** `issues.closed`.

Filters to issues labeled `upstream:child`, finds the umbrella (from body reference), checks if all siblings are now closed, and if the umbrella already has `upstream:approved` applied, re-fires the approve workflow via `gh workflow run upstream-approve.yml` targeting the umbrella. Small; ~30 lines.

Also handles the reject cascade: if an umbrella is closed as `upstream:rejected`, auto-closes any still-open `upstream:child` issues that reference it.

---

## Runtime — trigger, cadence, notifications

### V1 trigger: manual dispatch only

`.github/workflows/upstream-watcher.yml` — copy-pasted from `stargazer-heartbeat.yml` boilerplate, swapped:

```yaml
on:
  workflow_dispatch:
    inputs:
      skill_id:
        description: "Optional: single skill to poll (default = all suites)"
        required: false
  # V1.1 TODO: enable daily cron once outputs are trusted
  # schedule:
  #   - cron: '0 6 * * *'   # 06:00 UTC daily

concurrency: upstream-watcher   # prevents overlap between manual + eventual cron
```

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

### `gaia dev sync-upstream <skill-id> --version <tag> --source-url <url>`

Mutates `registry/named/<contributor>/<skill>.md`:

- Writes/updates the `upstream:` frontmatter block.
- Appends `timeline.action: upstream_synced` with `previousValue`, `newValue`, `details`.
- Atomic: both writes or neither.

**Flags:**
- `--bootstrap` — first-time write. `previousValue` is null. Timeline event details reads `"first-run baseline"`.
- `--dry-run` — prints the diff without writing.
- `--user <handle>` — same as other `gaia dev timeline` verbs (uses actor identity for signed provenance in timeline `details`).

**Pre-flight validation** (per CLI Pre-Flight Rule):

- `--version` must match a valid GitHub release tag pattern (`v?\d+\.\d+\.\d+.*`).
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
| 6 | `infra/` | `scripts/upstream_watcher/watcher.py`; `.github/workflows/upstream-watcher.yml` (manual dispatch only, cron block commented); `.github/workflows/upstream-approve.yml`; `.github/workflows/upstream-close-children.yml`; `scripts/upstream_watcher/README.md` | The functional core |
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

## References

- `CLAUDE.md` — Programmatic-First Policy, CLI Pre-Flight Rule, branch-scope rules, Class P vs Class S artifacts.
- `CONTRIBUTING.md` §12 — `installable: false` convention for non-installable named skills.
- `META.md` §2.4 — Star Bar (`links.github` requirement at 3★+).
- `META.md` §5 — Timeline transparency mandate.
- `.github/workflows/stargazer-heartbeat.yml` — CI pattern precedent.
- `.github/ISSUE_TEMPLATE/new_skill_intake.yml` — issue-shape precedent.
- `docs/agents/issue-tracker.md` — issue lifecycle docs.
- `docs/agents/triage-labels.md` — label registry (extended by this design).
