# Steward Issue Hygiene — architecture contract (#2130 / #2131 / #2132)

Status: working contract for the `dev/steward-issue-hygiene` integration branch.
Authors: Sonnet 5.5 High (architecture/integration lead); lanes by Haiku 5.5.
Ground truth (live census 2026-10-21, REST pagination of 4 pages): 224 open issues + 8 open PRs;
105 authored by `github-actions[bot]`; 96 `upstream:child` (#1835:72, #2002:17, #2020:4, #1823:3);
6 `upstream:release` (#1823 #1833 #1835 #2002 #2020 #2040) + bootstrap #2091. Exact-ID check of the
children against `registry/named/<id>.md`: 40 present, 56 absent (alias/contributor-slug differences
such as `addyosmani` vs `addy-osmani` are NOT resolved by exact ID and must not be auto-closed).

## 1. Principles (binding on every lane)

1. **Deterministic first, read-only first.** Reconciliation is a pure function of
   (census, registry index, PR evidence, policy). It never writes. Writes are a separate step that
   re-reads live state and compares it with the manifest snapshot.
2. **Fail closed.** Missing/truncated pages, auth failure, stale census (older than
   `maxCensusAgeSeconds`), an unreadable registry, or a missing `registry/named` directory => the affected
   scope is `not-evaluated` and Class A is blocked for the run. A missing census file is `notEvaluated`
   (SensorNotEvaluated): no closure is emitted. An incomplete or stale census is coverage unknown
   (SensorUnavailable): no closure is emitted either. A not-evaluated sensor is never healthy.
3. **Stale != resolved. Skip-child-gate != accepted. Similar title != same skill.**
4. **No work is discarded to make a counter go down.** Closing is allowed only when the underlying
   work is proven preserved (registry record, merged PR, or a still-open canonical item that carries the
   full original payload). Every closure receipt embeds the original title, labels, body sha256 and
   the candidate payload.
5. **New issue-write authority is explicit.** A5-style allowlist lives in `founder/steward/POLICY.yaml`
   `issueHygiene.closure.rules`, with per-run caps; nothing is inferred from existing local Class A
   repair executors. No rule => no closure.
6. **No new orchestration platform.** Class B rides the existing lane (maxInFlight 2,
   maxDispatchesPerRun 1, attempts/cooldown unchanged). Class C rides the founder desk.
7. **No API billing, no new cron.** Census collection uses `gh`/`GITHUB_TOKEN` REST only. The scheduled
   authenticated Claude routine that invokes `/gaia-steward-full` is the only scheduler.
8. Naming: avoid underscores in new Python function/variable names (repo rule); module dirs are
   lowercase without underscores.

## 2. Module map and ownership

New package `src/gaia_cli/steward/issuehygiene/`:

| Module | Owner lane | Responsibility |
|---|---|---|
| `census.py` | A | `steward-github-census-v1` schema, validation, completeness check, loader |
| `identity.py` | A | semantic keys, payload/body parsing, parent/child graph |
| `reconcile.py` | B | `reconcile(census, registry, policy, now) -> manifest` |
| `closure.py` | B | closure authority (rules A1-A5), plan, snapshot-compare, receipts, resume |
| `registryindex.py` | B | read-only index of `registry/named/**` + `registry/nodes/**` |
| `sensor.py` | D | Steward sensor wrapping reconcile; emits debt |
| `__init__.py` | D | exports |

Other files and owners:

| Path | Lane |
|---|---|
| `scripts/steward_issue_census.py` (collector, REST `Link` pagination, fail closed) | A |
| `scripts/upstream_watcher/*`, `.github/workflows/upstream-watcher.yml`, `docs/agents/upstream-watcher.md` | C |
| `founder/steward/POLICY.yaml`, `routine-coverage.json`, `routines/issue-hygiene.md`, decisions, `scripts/check_steward_coverage.py`, `src/gaia_cli/steward/{sensors,fullrun,routing,policy,desk}.py`, `scripts/steward_drive.py`, skills | D |
| `tests/steward/issuehygiene/**`, `tests/fixtures/issuehygiene/**` | E (A/B/C/D write their own focused tests under `tests/steward/issuehygiene/test-<lane>*.py`) |
| `gaia-research/skill-cost` | F |

Lanes must not edit another lane's files; if blocked, report it in the return value.

## 3. Data contracts

### 3.1 Census input — `steward-github-census-v1`
Written to `.gaia/steward/inputs/github-issues.json` (ignored path) by the collector or by a driver using MCP.

```json
{
  "schemaVersion": "steward-github-census-v1",
  "repo": "gaia-research/gaia-skill-tree",
  "fetchedAt": "2026-10-21T19:00:00Z",
  "source": "rest|mcp",
  "completeness": {
    "issues": {"complete": true, "pagesFetched": 4, "expectedPages": 4, "itemCount": 232, "lastLink": null},
    "pulls":  {"complete": true, "pagesFetched": 2, "expectedPages": 2, "itemCount": 8, "lastLink": null}
  },
  "issues": [{"number": 2091, "title": "...", "state": "open", "stateReason": null,
              "labels": ["upstream:approved"], "author": "github-actions[bot]",
              "createdAt": "...", "updatedAt": "...", "closedAt": null, "comments": 3,
              "body": "<full body, never truncated>", "bodySha256": "...",
              "isPullRequest": false, "mergedAt": null, "headRef": null, "baseRef": null}],
  "recentlyClosed": [ /* same row shape; closed within census.closedWindowDays (default 30) */ ]
}
```
`complete:false`, `pagesFetched != expectedPages`, any row missing `body`, a `bodySha256`
mismatch, or `fetchedAt` older than the policy age => census status `incomplete`/`stale`.
Merged PR evidence comes from `isPullRequest:true` rows with `mergedAt`.

**Collector completeness (fixed under lane E defects 1 and 2, 2026-10-21).** These rules
are in `scripts/steward_issue_census.py` and are binding on every collector:

* *End of a listing is proven two ways only.* A `rel="last"` link must equal the pages
  fetched. Without `next` or `last`, a non-empty page is followed by a probe of the next
  page, and the walk ends only when that probe is empty. The probe replaces a page-length
  test: `per_page` is a request the server may not honour, so a full page with no Link header
  is never the end. A non-empty probe fails closed as `unlinked-continuation`, and its rows are
  not adopted. An exact multiple of the page size still completes, because its probe is empty.
* *Mutation during the walk.* The open listing is walked twice. Completeness needs the same
  ordered numbers in both walks, else `mutated-during-walk`. Re-fetching page 1 alone is not
  enough: a close on a later page, already served, shifts the rest of the listing and skips one
  open issue while page 1 stays unchanged. The confirming walk is recorded as
  `completeness.*.confirmPagesFetched` and is not counted in `pagesFetched`. Residual, accepted:
  a mutation that repeats identically in both walks is not detected. The closed window is not
  re-walked. It is used only as positive evidence of closure, so a skipped closed row can only
  downgrade an item.

### 3.2 Semantic identity (`identity.py`)
Keys are stable across reruns and independent of issue number:

| Issue shape | Key |
|---|---|
| `[upstream] owner/repo → vX` umbrella (`upstream:release`) | `upstream-release:{owner}/{repo}@{version}` + suite `upstream-suite:{owner}/{repo}` |
| `[intake]` child (`upstream:child`) | `upstream-candidate:{owner}/{repo}:{slug}` (version independent; slug from `**Suggested ID:**`, evidence URL kept as separate field) |
| `[upstream:bootstrap]` | `upstream-bootstrap:{owner}/{repo}` |
| bot report (author `github-actions[bot]`, gh-aw family, not upstream) | `bot-report:{family}:{normalized-title-hash}` |
| anything else | `issue:{number}` with class `untracked` (hygiene never touches these) |

Parents: child body `Umbrella: #N`; umbrella `Child intakes:` list / checkbox lines; payload block
`<!-- gaia-upstream-payload ... -->`. A child whose parent number is absent from the census is an
`orphan-child` (=> Class B, never A).

**Listed numbers on an umbrella (fixed under lane E defects 3 and 4, 2026-10-21; the child-line rule is resolved in section 8.4).** Every number
the umbrella body lists is classified, and the umbrella's A2 proof depends on the result:

| Listed number is | Result | Effect on the listing umbrella |
|---|---|---|
| an open child owned by this umbrella | dependency | open child, so not A2 |
| an open child owned by another umbrella (`child-ref-parent-mismatch`) | dependency | `listed-child-owned-elsewhere:N`, so not A2. It is **not** an unknown: a reparenting listing is the lossless path A3 relies on, and an unknown would block that A3 |
| any other open issue, or an open pull request | known, not a child | none |
| any row in the recently-closed window | known closed | none (closed-window evidence) |
| none of the above (the census holds no row) | unknown `listed-child-unknown:N` | unknown, so B and never A |

Residual, recorded for the owners: the watcher writes umbrella listings as a *comment*
(`Child intakes: #N`, `scripts/upstream_watcher/issuer.py::_edit_umbrella_body`), and the census reads
bodies only. Such listings are invisible to the census. The per-child `Umbrella: #N` body line
therefore remains the only listing-independent proof of ownership.

### 3.3 Reconciliation manifest — `steward-issue-reconciliation-v1`
Pure output of `reconcile()`; deterministic key order; no timestamps except `censusFetchedAt`.

```json
{
  "schemaVersion": "steward-issue-reconciliation-v1",
  "censusFetchedAt": "...", "censusStatus": "complete|incomplete|stale|missing",
  "coverage": {"known": ["upstream"], "unknown": [], "notEvaluated": []},
  "stats": {"openIssues": 224, "botOpen": 105, "upstreamChildOpen": 96, "umbrellaOpen": 6,
            "classA": 0, "classB": 0, "classC": 0, "untracked": 0, "notEvaluated": 0},
  "items": [{
    "key": "upstream-candidate:garrytan/gbrain:foo",
    "issue": 1900, "kind": "child|umbrella|bootstrap|botreport|untracked",
    "state": "resolved|superseded|duplicate|actionable|awaiting-founder|not-evaluated|ambiguous",
    "parent": 1835, "canonical": null,
    "authority": "A|B|C|none",
    "ruleId": "A1-child-curated|null",
    "evidence": [{"type": "registry|pr|issue|workflow|policy", "ref": "registry/named/garrytan/foo.md", "sha256": "...", "detail": "..."}],
    "proposedTransition": {"action": "close|keep", "stateReason": "completed|not_planned|duplicate", "duplicateOf": null},
    "confidence": "proven|high|medium|low", "unknowns": [], "dependencies": [1835],
    "snapshot": {"updatedAt": "...", "bodySha256": "...", "labels": [...]}
  }],
  "batches": [{"suite": "garrytan/gbrain", "umbrella": 1835, "classB": ["upstream-candidate:..."], "size": 48}],
  "founderQuestions": [{"id": "Q-<hash8>", "question": "...", "affected": [1835, 1900], "options": ["accept","reject","defer"], "recommendation": null, "basis": "..."}],
  "manifestSha256": "..."
}
```
Rules: `authority:A` requires `confidence:proven`, an enabled policy `ruleId`, `censusStatus:complete`,
and every `unknowns` empty. Anything else downgrades A -> B -> C (never upgrades). An item with an
unresolved dependency (e.g. umbrella with open children) is never A.

### 3.4 Class A allowlist (policy `issueHygiene.closure.rules`)
| Rule | Closes | Hard proof |
|---|---|---|
| `A1-child-curated` | `upstream:child` | exact suggested ID has a readable registry record, status not draft, same contributor handle, whose registry repo and file path equal the child's evidence URL. Repo (case-insensitive) is `upstream.repo` when declared, else the `links.github` repo; path is `links.github`'s path. `tree/` vs `blob/`, a trailing slash, query and fragment are not differences. The git ref is not matched: a ref-only difference is still A and is recorded as `ref-differs: registry=<ref> intake=<ref>` with both full URLs. The ref-free comparison is trusted only when both refs are "simple" (`HEAD`, `main`, `master`, a semver-like tag, or a 7-40 char lowercase hex sha) or the normalized URLs are identical; otherwise `ref-split-ambiguous` => B. Known bounded residual (accepted 2026-10-21): a branch whose first segment looks simple (e.g. `v2/docs`) cannot be told from ref `v2` + path `docs/...` without a branch listing; the closure comment carries both full URLs and a closure is reopenable. Any repo or path difference, draft or missing status, or unreadable record => B (never A). Alias/near-match => B/C, never A |
| `A2-umbrella-synced` | `upstream:release` umbrella | registry suite record `upstream.version` == payload `newVersion` (or a merged `[upstream sync]` PR for it is in census) AND zero open children AND parent suite not frozen AND every body-listed number is known (§3.2: an unknown listed child, or an open child owned by another umbrella, is B) AND no unknown facts on the umbrella itself |
| `A3-umbrella-superseded` | older `upstream:release` of the same suite | a newer umbrella of the same suite is open and its payload `componentAdds` ⊇ the older's still-unresolved adds, older's open children reparented/listed in newer body (lossless). The superseder must carry no unknown facts and no identity reasons (checked from identity, because a higher-numbered superseder is evaluated later). The superseder must stay open after the pass: if it is A-closed in the same pass (for example by A2), the older umbrella is downgraded to B with `superseder-closed-in-pass:#N`, its A3 evidence is dropped and the planner refuses it too. The older umbrella then waits for a founder decision. Closing the superseder first is not done automatically |
| `A4-duplicate-child` | `upstream:child` | same candidate key + same evidence URL as a lower-numbered open child that stays canonical; closure `duplicate`, `duplicateOf` set |
| `A5-botreport-superseded` | `github-actions[bot]` gh-aw report | the failing automation is verifiably disabled in repo files (workflow has `if: ${{ false }}`/no active trigger, per policy list of paths), no `security` label, body not a security finding; otherwise B/C |

Closing comment body = receipt summary + proof links + original payload block (see 3.5). `maxClosuresPerRun`
(policy, default 10). Each closure: re-read issue, require `updatedAt`+`bodySha256`+labels equal manifest snapshot
(else `stale-skip`, no action), write comment, close with reason, record receipt, checkpoint.

### 3.5 Closure receipt — `steward-issue-closure-receipt-v1`
Per issue, appended (never rewritten) to `.gaia/steward/issue-hygiene/receipts/<runId>.jsonl` and attached to
the run record: `{runId, key, issue, ruleId, evidence[], parent, canonical, reason, before:{snapshot},
originalPayload:{title,labels,bodySha256,candidate}, commentUrl, closedAt, outcome:
closed|stale-skip|already-closed|failed|blocked, failure}`. Exactly-once: an issue already `closed` in the live
re-read with a matching receipt is `already-closed`, not an error. A crash between comment and close is
resumed by detecting our receipt marker `<!-- gaia-steward-closure:{key}:{manifestSha8} -->` in comments.

### 3.6 Runner integration
* New sensor id `issue-hygiene`, debt kinds: `issue_closure_ready` (Class A, per rule batch),
  `issue_suite_review` (Class B, per suite, dispatch rule `issue-suite-review`, guide
  `founder/steward/routines/issue-hygiene.md`), `issue_founder_decision` (Class C, per founderQuestion).
  Debt id: `debt:{kind}:{slug}:{digest}` as existing.
* New pending action type `forge.close_issue` (params: `issue`, `expectedSnapshot`, `reason`, `comment`,
  `key`, `ruleId`, `receiptPath`) owned by the atomic skill `gaia-steward-issue-hygiene`; outcome recorded with
  `gaia steward full record RUN STEP --input outcome.json`.
* The routine step "refresh driver inputs" runs `python scripts/steward_issue_census.py` before `run`
  (skill `gaia-steward-full` + `scripts/steward_drive.py`). Missing census => `notEvaluated`.
* Before/after backlog statistics: `stats` in each run's receipt; desk prints net open-issue change and
  the count of closures this run vs total.
* Resume: next pass re-reads census, recomputes manifest; closed issues are `already-closed`; incomplete
  group continues.

### 3.7 Upstream watcher — batch record (#2131)
Amends F3 (see §4). Umbrella payload gains `payloadVersion: 2` and `candidates[]`:

```json
{"id": "garrytan/gbrain:foo", "slug": "foo", "evidenceUrl": "...blob/...", "firstSeenVersion": "v1", "lastSeenVersion": "v2",
 "precheck": {"registry": "absent|present|alias-suspect", "tracked": "none|child:#N|batch", "priorDisposition": "none|rejected:#N|accepted:#N"},
 "status": "new|tracked|present|rejected|escalated", "child": null}
```
* One active umbrella per suite (idempotent key `upstream-suite:{owner}/{repo}`); new versions update it in place;
  rows are keyed by candidate id so version churn never duplicates them; an unchanged rerun performs zero
  writes (compare canonical payload hash, skip edit/comment).
* Default emission mode `batch`: no per-candidate child; the umbrella body carries a "Batch review" table with
  independently addressable rows (`cand:<id>` anchors). `--child-mode fanout` keeps the legacy behavior;
  `--escalate <candidate-id>` (also a `workflow_dispatch` input) creates the child for one row.
* Existing children are *adopted*: rows with `child: #N`.
* Prechecks before any write: registry exact-present, alias-suspect (same slug under another contributor handle
  or normalized-equal slug => never claim identical), existing child/umbrella (live list, not search, to avoid
  index lag), prior rejected/closed disposition. Unknown evidence (registry unreadable, GitHub list failure)
  => zero issue writes, nonzero-but-nonfatal exit with `unknownEvidence` in the JSON report.
* `skip-child-gate` keeps its meaning (bypass child-resolution gate in `upstream-approve.yml`) and never closes or
  accepts anything; update `upstream-close-children.yml` accordingly if needed (rejected-umbrella cascade must
  not drop rows: comment lists the row ids).
* Watcher emits `--report FILE` JSON `{issuesCreated, issuesUpdated, suppressedDuplicates, retainedCandidates,
  unknownEvidence}` consumed by Steward observation.

## 4. F3 policy amendment (record in `docs/agents/upstream-watcher.md`)
F3 ("umbrella + fan-out only for genuinely new components", consolidated issue rejected) is amended
(founder-authorized in the campaign brief, 2026-10-21): the default becomes **umbrella + lossless batch record**;
a per-candidate child exists only when escalated by a deterministic precheck exception or Class B curation. The F3
rejection reason ("cramming the intake schema into a release delta") is addressed because each batch row carries the
full intake fields (suggested ID, contributor, attribution, evidence URL, description stub) and can be escalated to a
full child with the standard template at any time. Prior intake semantics are not rewritten: existing children
remain valid and are adopted, not migrated.

## 5. Test matrix (owner E, plus lane-local tests)
Pagination & missing pages; delayed search index (watcher uses list); same component in several releases;
already-merged vs still-open; partially approved suite batches; rerun with no change = zero writes;
partial API failure; interrupted closure resume; watcher/Steward race (stale snapshot skip);
A-rule strict proof (each rule: positive + every missing-proof negative); B routing to verifier;
C non-mutation + one packet per question; exactly-once; second run yields zero new debt/noise;
full-entrypoint test: `/gaia-steward-full` runner discovers and executes issue-hygiene.
Realistic fixture: all four families trimmed from the live 2026-10-21 census (stored under
`tests/fixtures/issuehygiene/`).

## 6. Rollout order
dry-run manifest on live census -> watcher fix + dry-run proof (no recreation) -> pilot closure of a small
eligible A batch (<=5) -> re-read/replay idempotency check -> expand in checkpointed batches of <=10.

Status (lane B5, 2026-10-21, amended by lane B7 round 2, section 8): the shipped `issueHygiene.writesEnabled` is
`false`. The pilot procedure is the one in section 8.1. Test checkouts that exercise writes set `writesEnabled: true`
explicitly.

## 7. Lane B5 amendments (verifier blockers, binding)

These amend §§3.1 to 3.6 and are implemented in the code they name.

* **Census pagination (B1, §3.1).** GitHub omits `rel="last"` and `rel="next"` on the final page. The
  collector counts linked pages only. The end of a listing is proven by a `last` link that matches the
  pages fetched, or by an empty probe after a page with no `next` link. The probe is not a page. A linked
  page that comes back empty fails closed (`empty-linked-page`). Fakes answer as GitHub does.
* **Census shape (L8, §3.1).** `completeness.issues.itemCount` counts every open listing row, pull requests
  included (as GitHub's issues endpoint lists them). `completeness.pulls.itemCount` counts the pull-request
  rows. `validateCensus` checks both against the rows.
* **Workflow listing (M6, §3.1, §3.4 A5).** The collector writes `workflows` (GitHub's workflow listing with
  each state) as its own section. A failure there sets only `workflows.complete` to false and never fails the
  issue census. A5 is proven only by a complete listing that reports the named workflow in a `disabled_*` state.
  The checkout's workflow files are never trusted (`workflowProbesFor(census, policy)`).
* **Closed window (L5).** `issueHygiene.closedWindowDays` from POLICY is the collector's default. An unreadable
  policy refuses the collector with exit 2 and writes nothing.
* **Sync evidence (B2, §3.4 A2).** A merged sync PR proves A2 only when its title parses, exactly, to the suite
  and version: `[upstream sync] <owner>/<repo> -> <version>` (the arrow optional). Substrings never match
  (`v1.2` is not `v1.2.3`, `o/r` is not `o/r-fork`). The census carries no branch name or body for this check.
* **Listed children (M5, §3.2).** A child counts as listed in a superseder only on a markdown list or checklist
  item line (`- `, `* `, `- [ ] `, `- [x] `). Prose containing `+ slug` never lists a child.
  Resolved by lane B7 (M2, section 8.4): a `Child intake:` / `Child intakes:` line prefix also lists; a mid-sentence `child intake #N` never does.
* **Contributor aliases (B3, §3.4 A4).** A4 requires the exact candidate id (owner and slug) and the same evidence
  URL. A pair whose handles differ only by punctuation or case is alias-suspect: Class C, one question, never A.
* **Registry status and identity (L2, L3, L4, §3.4 A1).** A `draft` or `deprecated` record is never A. A
  declared `upstream.repo` that is not a non-empty string is never A. A missing `registry/named` directory is
  unknown coverage, never an empty registry.
* **v2 candidate rows (D4, §3.4 A2).** An umbrella with a `payloadVersion: 2` payload is A2 only when every
  candidate row is resolved: status `present` or `rejected`, or a child intake already closed. An unresolved
  `new` row, or a child the census does not hold, is Class B (`candidate-unresolved:<id>`).
* **Executor gate (B4, §3.5, §3.6).** `scripts/steward_issue_close.py` refuses (exit 2, no forge built, no write)
  unless writes are enabled, the rule is enabled, A5 names only listed workflows, the run is under
  `maxClosuresPerRun`, the receipts store is not a symlink, the census is complete and fresh, and the
  reconciled manifest reproduces the action's digest and still proves the same closure with the same comments.
  The driver treats exit 2 as a non-retryable skip and checks `writesEnabled` before each closure.
* **Emission with writes off (L6, §3.6).** With `writesEnabled: false`, a proven closure is reported as
  `issue_closure_ready` debt with status `ready (writes disabled)` and no plan. The runner emits nothing.
* **Proof of the closing comment (D3, §3.5).** A `closed` outcome carries exactly one proof: `commentUrl` that is a
  GitHub comment URL naming this issue and repo (`https://github.com/<owner>/<repo>/issues/<n>#issuecomment-<id>`),
  or `commentId`, or `markerVerified: true`. Two or more proofs are refused.
* **Closing marker (M3, §3.5). Deviation, flagged for review.** A closing comment is ours only when it carries
  the full marker and its author is the closer identity (`forge.whoami()`). The marker's digest is
  `closureSha8`: eight hex digits over the closure decision (key, rule, issue, transition, evidence and the
  preserved payload). It is not the manifest digest. The manifest digest includes the census fetch time and the
  issue's `updatedAt`, and our own comment changes `updatedAt`. Keyed on the manifest digest, a crash followed by a
  census refresh would post a second comment. A marker for another closure decision, a foreign author, or any
  marker when the closer is unknown is not proof, and we post our own comment.
* **Concurrency (M4, §3.5).** Each (key, issue) pair is serialized by an exclusive lock file under `receipts/.locks/`
  (POSIX `fcntl`; the Steward runs on Linux). Under the lock the closer re-reads the receipts and the live issue. Two
  closers produce one comment and one close.
* **Identity (M2, §3.5).** A locked issue, a pull request, a renumbered issue, or one no longer at the expected
  repository (transferred) is `blocked-identity`: nothing is written, and it is item-local (exit 1).
* **Close confirmation (M1, §3.5).** Any non-2xx answer, and any unfollowed 3xx, is an error. A close counts only
  when the response says `closed` with the requested `state_reason`. Otherwise no `closed` receipt is written.
* **Preservation (M7, D9, §3.5).** The closing comments carry the full original candidate information: the body,
  and for a v2 umbrella every `candidates[]` row. Titles and text are scrubbed of credential-shaped substrings and
  the title is capped at 200 characters. Preserved text above 30,000 characters is split across marker-linked part
  comments, each under 60,000 characters. The receipt records `preservedSha256` (over the preserved text) and
  `preservedParts`.
* **Diff tolerance (D7, §3.5).** `updatedAt` drift is ignored only when our own marker comment for this closure
  explains it. Title, body, labels and state drift still stop the closure as `stale-skip`. A crash between the
  comment and the close therefore completes on the same closure.
* **Receipts and already-closed (L7, D13).** A pair the receipts file already records as done is skipped with no
  forge call and no new receipt. An `already-closed` receipt is written only when a live re-read finds the issue
  closed without our receipt (for example, a concurrent closer or a person).
* **Sensor snapshot (§3.5).** The snapshot stores the title scrubbed and capped, with `titleSha256` for drift.
* **Coverage checker (D12).** A forge action is live only when its literal is the kind argument of an `_addAction`
  call site in `fullrun.py`.
* **Residual, accepted.** Our closer identity comes from `GET /user`. A GitHub App or Actions token cannot read it,
  so markers are never proof for it: a crash after our comment then posts a second comment before the close.
  Closures still happen once. The census collector cannot detect a mutation that repeats identically in both walks.

## 8. Lane B7 round-2 amendments (binding; they amend 3.2, 3.4, 3.5, 3.6, 6 and 7)

Each item below is implemented, and each has a test under `tests/steward/issuehygiene/test_b7_*.py`.

### 8.1 Pilot procedure and the single executor (H1, binding)

* There is one closure executor. `gaia_cli.steward.issuehygiene.executor.gateClosure` is the only gate. Both
  `scripts/steward_issue_close.py` (one action) and `scripts/steward_issue_reconcile.py --apply-closures` (every
  proven plan of a manifest) call it before any forge is built.
* `--apply-closures` requires `--receipts` inside the fixed store `.gaia/steward/issue-hygiene/receipts/` (no symlink on
  the way), `--i-understand-writes`, and `--repo OWNER/NAME`, which must equal the census repository. It refuses `--now`,
  `--policy` and `--census`, reads only the checkout's `founder/steward/POLICY.yaml` and census, and refuses (exit 2,
  zero forge calls) unless `issueHygiene.writesEnabled` is true. `--max-closures` may only lower the policy cap. The
  planner's old override that treated the flags as authority is removed.
* Pilot procedure: copy the checkout to a throwaway directory; in that copy only, set `issueHygiene.writesEnabled: true`
  and `maxClosuresPerRun: 5` in `founder/steward/POLICY.yaml`; never commit that edit; then run
  `python scripts/steward_issue_reconcile.py --apply-closures --receipts .gaia/steward/issue-hygiene/receipts/pilot.jsonl --i-understand-writes --repo gaia-research/gaia-skill-tree --max-closures 5`.
  The committed `POLICY.yaml` stays `writesEnabled: false`.

### 8.2 Caps, clock and identity (L2, L3, L4, L5)

* Hourly budget (L2): closures recorded in any run's receipts count. At most `maxClosuresPerRun` per UTC hour, and
  never more than 25 closures in any 60 minutes (`executor.hourlyBudget`). Emission and the executor both enforce it.
* `--now` is refused on `--apply-closures` and ignored by `scripts/steward_issue_close.py`. Freshness uses the real
  clock. `--now` remains for dry-run replays of the manifest only.
* The census repository, the action's `repo` and `--repo` must match case-insensitively (L4, D4).
* `closureProven` requires the repository and raises without one (L5). A proof is valid only when every present field is
  valid: a present-but-invalid `commentUrl`, `commentId` or `markerVerified` refuses the outcome. `null` means absent.

### 8.3 Locks (M1)

* Two locks per closure, taken in order: the (key, issue) lock beside the receipts store, then a (repo, issue) lock in the
  user-level lock directory `gettempdir()/gaia-steward-locks/` (`closure.userLockDir`). Two checkouts that share a
  repository on one machine serialize on the second lock.
* Across machines the lock does not reach. The guard there is the closing-comment marker check and the live re-read
  under the closer identity (3.5, M3). That is the accepted residual.

### 8.4 Listings and status (M2, M4, L1)

* Umbrella child listings (3.2): a child is listed only on a markdown list or checklist item (a line that starts with
  `- `, `* `, `- [ ] `, `- [x] `) or on a line that starts with `Child intake:` / `Child intakes:` (an optional list bullet
  first). A `child intake #N` that appears mid-sentence lists nothing.
* A1 status (3.4): an allowlist of the values in `registry/schema/namedSkill.schema.json` (`awakened`, `named`) read from the
  checkout. Any other value (`archived`, `draft`, `deprecated`, an unknown value), a missing status, or a missing or unreadable
  schema is not A (B, reason `registry-status-not-allowed`, `registry-status-missing`).
* A1 repository (3.4, L1): when `links.github` names a repository other than the declared `upstream.repo` (case-insensitive
  owner/repo), the child is not A (B, reason `links-repo-contradicts-upstream`).

### 8.5 Scrub (M3)

* `CREDENTIAL_PATTERNS` (`gaia_cli.steward.primitives.redact`) covers Hugging Face (`hf_`), npm (`npm_`), GitLab
  (`glpat-`), JWT (`eyJ` header, three base64url segments), `Bearer <token>`, credential assignments
  (`password|passwd|secret|token|api_key = value`, quoted or escaped), and a 40-character base64 string adjacent to an
  `aws` or `secret` keyword. The credential-assignment shape excludes code access such as `os.environ[...]`.
* The scrub is applied to the closing comments, the preserved original payload (`preservedTextOf` scrubs its text again),
  the snapshot title, the evidence details, the receipts and the ledger action params. The shared list is also the
  secret-scan sensor's list, so a new shape changes that sensor too.

### 8.6 Actions, debt plans and proof of the terminal outcome (D5, D6, D7, D2)

* Actions and debt plans are compact (`executor.compactPlan`): identifiers, digests, the expected snapshot and the evidence
  references. They carry no `original`, no `comment` and no `comments`. The executor re-derives the comments and the preserved
  payload from the census at execution time and checks `closureSha8` and `preservedSha256`. Test: a 300-candidate umbrella
  gives an action well under 8 KB, and the executor still posts every candidate.
* The runner records a `closed` or `already-closed` outcome only when this checkout's receipts hold a matching entry for the
  same (key, issue) and the same single proof. Otherwise the record is refused and the action stays pending.
* A repeat run on a pair this checkout already recorded prints the recorded outcome and exits 0 (`resumed-done`). It writes no
  new receipt.

### 8.7 Kill switch and driver (D3, D8, D10)

* When writes are off, or a closure rule is disabled, the runner cancels the pending `forge.close_issue` actions (status
  `cancelled`, reason `writes-disabled`) on every resume, re-reading the policy. Cancellation releases the run's wait, so the
  run settles and its lease is released. The driver reports `writes disabled`, not a stall.
* A malformed `issueHygiene` block disables only the issue-hygiene surface. The whole policy still loads. The sensor reports
  coverage unknown for issue hygiene, and the executor refuses (exit 2). Other steward work continues.
* The ready-but-disabled count (`ready (writes disabled): N proven closures`) appears on the desk backlog line, in the run list
  and in `steward full status`.

### 8.8 Transport (L6)

* The forge transport opens URLs with an opener that never follows a redirect. A 3xx on a comment or close is an error.

### 8.9 Documentation corrections (D12)

* The driver removes a census whose collector exits with any code other than 0 or 3 (exit 1, exit 2, or a crash). An exit 3
  file is kept so the sensor reports it incomplete. `founder/steward/README.md` says so.
* The decision record `founder/steward/decisions/steward-issue-closure-authority.json` states the own-marker `updatedAt`
  tolerance and the hourly budget.
* The steward-full skill's Class B line states `maxInFlight` as the policy value, with the code range 1 to 4. A step the executor
  refuses (exit 2) is skipped and reported, never re-sent. Closures without a token are listed as unperformed.

### 8.10 Clock (test-only seam)

* Every steward clock read goes through `gaia_cli.steward.clock.utcNow`. It honours the `GAIA_STEWARD_NOW` pin only while pytest
  runs (`PYTEST_CURRENT_TEST` set). `tests/steward/issuehygiene/conftest.py` pins the fixture window (2026-10-21T19:30:00Z) in
  every issue-hygiene test, so the suite does not depend on the wall-clock date. Production reads the real clock.
