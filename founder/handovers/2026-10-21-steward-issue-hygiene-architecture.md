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
   `maxCensusAgeSeconds`), unreadable registry => the affected scope is `not-evaluated`, Class A is
   blocked for the run, and the sensor reports `coverageUnknown`. A not-evaluated sensor is never healthy.
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
| `A1-child-curated` | `upstream:child` | exact suggested ID has a registry record whose status is not draft AND whose `links.github` (blob-normalized) equals the child's evidence URL (or its `upstream.repo` + path matches); same contributor handle. Alias/near-match => B/C, never A |
| `A2-umbrella-synced` | `upstream:release` umbrella | registry suite record `upstream.version` == payload `newVersion` (or a merged `[upstream sync]` PR for it is in census) AND zero open children AND parent suite not frozen |
| `A3-umbrella-superseded` | older `upstream:release` of the same suite | a newer umbrella of the same suite is open and its payload `componentAdds` ⊇ the older's still-unresolved adds, older's open children reparented/listed in newer body (lossless) |
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
