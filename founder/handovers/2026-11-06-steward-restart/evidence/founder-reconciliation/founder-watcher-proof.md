# Founder lock + watcher proof — #2283 / #2278

## Status and authority

**Implemented and locally tested; not integrated. Partial operational reconciliation: gates below remain. Fresh independent Terra review is mandatory.**

Runtime verified from PI environment: `openai-codex/gpt-6.1-sol`, reasoning `high`. Dedicated branch/worktree: `dev/steward-founder-lock-2283`. No delegation, model fallback, task timeout or turn cap. Read root/founder CLAUDE, Steward policy documentation, watcher design and graft skill before implementation. Read founder lock/hygiene snapshots; refreshed live #2283 metadata, #1833 full body/comments, #2278 and historical failed-run logs read-only.

No GitHub writes, issue/label edits, closures, reopening historical trackers, live watcher apply, shared ledger/lease/action changes, canonical campaign scan/run, registry/trust/rank/evidence edits, main/integration merge, push, release, installation or global configuration changes. `issueHygiene.writesEnabled` remains false; closure authority record remains OPEN. Founder MEMORY and other workers' owned files were untouched.

## Exact local commits (Marcus identity, not pushed)

1. `d3908f6d5ee3fb6b46d005fb0c3d62eb210d47ce` — consume founder decisions and family holds.
2. `5be7e3af803d039471305d05c1e9d6dd69169e46` — exact typed count confirmation; cross-suite release/source guards.
3. `63181cb38087e37cf6d1e4ea1e530bb2e3ffd235` — strict dormant workflow source; source-shell proof and synchronization boundaries.
4. `6d3768096bd4cedfe577cb484ed5a72f87e97ba4` — additionally deny a missing verdict-reason field (not just a nonempty/unknown reason); focused source-shell regression. This is the handoff HEAD.

Working tree clean at handoff. No integration, live re-observation or campaign completion is claimed.

## Files

- `founder/steward/decisions/issue-question-q-{08ecd62d,2568173e,bfd37238,6720aecf}.json`: four existing-schema founder decisions, not new adjudications.
- `src/gaia_cli/steward/issuehygiene/questions.py`: exact scoped mappings and validation; no new schema keys.
- `src/gaia_cli/steward/issuehygiene/{reconcile,sensor,executor}.py`, `scripts/steward_issue_reconcile.py`: real consumption including independent closure re-derivation.
- `scripts/upstream_watcher/{live,finder,watcher,batch,issuer,releaseidentity}.py`: count proof and source/identity refusal.
- `.github/workflows/shared/steward-agent.md`: strict detection and affirmative outcome guard **in source only**.
- Tests: `tests/steward/issuehygiene/test_founder_locks_2283.py`, `tests/steward/test_founder_workflow_lock_2283.py`, `tests/upstream_watcher/test_{count_2278,identity_2283,list_truncation}.py`.
- Documentation: `founder/steward/decisions/README.md`, `founder/steward/FOUNDER_LOCK_2283.md`, `docs/agents/upstream-watcher.md`.

## C1–C4 records: schema and actual consumption

All four load via `loadIssueDecisions`; each returns `_check_record(record) is None`. No matching previous record existed. Existing historical decisions are unchanged. Each new record has only required `steward-decision-v1` fields plus existing optional `resolution`; exact target/debt mappings use allowed links/evidence. Every record links founder authority `#2283#issuecomment-6640916880` and hygiene receipt `#issuecomment-6640982938`, and explicitly separates the final ruling from unfinished implementation.

| Canonical record | Exact source debt | Resolution / effect |
|---|---|---|
| `issue-question-q-08ecd62d.json` | `debt:issue_founder_decision:q-08ecd62d:b46650ebeefbdb87` | C1 `technical-reconciliation-only`; #1833 becomes B technical proposal only, never a release/closure approval. |
| `issue-question-q-2568173e.json` | `debt:issue_founder_decision:q-2568173e:749fb275800fe372` | C2 `migration-deferred`; #2002 and published contributor family held. Canonical `addyosmani` is final; migration is not performed. |
| `issue-question-q-bfd37238.json` | `debt:issue_founder_decision:q-bfd37238:ac2f25b1b6af9db6` | C3 `curation-deferred`; GBrain #1835 and every existing child held; no skip-child-gate/intake/acceptance. |
| `issue-question-q-6720aecf.json` | `debt:issue_founder_decision:q-6720aecf:e5f9c70bc8f1e0c9` | C4 `manual-disabled-fail-closed`; #2126/#2127 held, evidence retained, no automation activation or tracker closure. |

Canonical targets `issue-question/q-<hash>` appear exactly in links/evidence. The schema had no family mapping fields or pre-existing question-record consumer: the explicit bounded consumer is new, not an invented schema extension. It recognizes only these four resolutions, validates exact debts/authority/affected links, and refuses malformed or contradictory targeted files. Missing/open records do not claim a ruling. Only the exact answered question is removed; unrelated new questions remain C. Held families/descendants emit neither B batch work nor closure authority. No lock upgrades any A proof. Ordinary `upstream:needs-info` also prevents non-C actionable routing.

**Actual dry-run consumption**, using the LEAD saved complete census, worktree code, fixed observation time and scratch output only:

```
PYTHONPATH=src python scripts/steward_issue_reconcile.py --root . \
  --census <lead>/founder-reconciliation/github-issues.json \
  --now 2026-11-04T20:45:00Z --out <scratch>/reconcile-after.json --summary
```

- Same 218 actual issue entries and 72 upstream children as before; no item disappeared.
- Before: A=0, B=76, C=4 issue rows; three generated questions (C3 had already lost its stale labels and incorrectly fell to B).
- After: A=0, B=5, C=0 issue rows; zero generated founder questions. This is **manifest-only**, not shared-ledger debt settlement.
- #1833: actionable/B with technical-only founder evidence; original contradictory payload remains preserved, not silently rewritten.
- #2002, #1835, #2126, #2127: `held` / `none`, proposed keep.
- **All 67 GBrain children**: `held` / `none`, preserved with their L4/history payloads.
- Every one of the 218 items has byte-equivalent `original` and `snapshot` objects against lead's pre-change manifest (including body hashes/full preserved candidates).
- The two unrelated existing proof-level closure proposals are still not authority-A actions; effective closure rules remain disabled. No closure execution occurred.
- Real sensor `_observations` tests establish locked questions do not reappear as C and held GBrain/Addy families do not become B dispatches. Executor and CLI re-derivation now read the same decisions. Old persisted debt still requires lead-authorized canonical re-observation.

C2 migration surfaces are recorded concretely in the decision and operational doc: named IDs/paths, contributor attribution, generic references, suiteRef/suiteComponents, children/suggested IDs/source URLs, user-tree IDs/timeline, graph/named projections, contributor/skill APIs, profiles, badges, public links, install/summon/share clients, old/new aliases or redirects and compatibility/dedup tests. No rename or update acceptance was attempted.

## #2278: evidence, repair and honest root-cause limit

Historical run `41641921681`, SHA `1963a47f480251d79d98c6a13b8c272444996467`, retained log confirms the exact 215 listed / 218 metadata mismatch after three attempts. It does **not** retain the missing row identities, full page responses or same-token typed counts. No evidence supports a hardcoded +3, dropping PRs, or calling the partial list complete.

Verified transport semantics: REST `/repos/{owner}/{repo}/issues?state=open` contains **issues and PRs** (PR discriminator `pull_request`); repository `open_issues_count` is also the combined aggregate, not an issues-only total. The list follows genuine Link continuations and independent terminal offset probes; it is not a search result. Repository aggregate metadata is not a transactionally bound listing snapshot. Today's worker read-only comparison does **not** reproduce the historical gap, so the exact historical omission/staleness/visibility cause remains unproven and #2278 must not be called resolved.

Engineering repair retains exact count/completeness checking:

1. Normal path requires exact repository metadata count before and after the complete REST walk.
2. On count disagreement, non-search GraphQL issue and PR connection `totalCount`s bracket a second full REST walk. Both typed counts must remain identical and equal the respective REST row-type counts; both walks must return the same ordered unique issue numbers.
3. No count offset/tolerance, search count, ignored pagination failure, or partial/error GraphQL result can authorize a list. Duplicate/malformed identities now fail closed even when the total length matches.
4. Failures remain unknown, retry then refuse; no writes are enabled.

Regression proof covers mixed issue/PR multi-page listing, stale aggregate metadata, swapped issue/PR totals with the same combined count, concurrent count changes/recovery, missing/empty/truncated/duplicate pages, terminal probe failures, partial/error/malformed/negative/boolean connection counts and unknown empty results. Existing closed-history fail-closed tests remain green.

**Read-only live comparison at `2026-11-04T21:53:32Z`:** metadata 222 before/after; non-search connection counts 218 issues + 4 PRs before/after; REST 222 rows / 222 unique numbers. PRs #2235/#2287/#2289/#2290. This differs legitimately from lead's earlier 218+5 snapshot; counts are point-in-time, not universal ground truth. The fallback itself is mocked-tested, not claimed exercised by this matching live sample. Genuine failed-page reads still fail; an exact-page-multiple ending in an empty linked page with stale metadata can still refuse before fallback (safe availability residual).

**Required remaining diagnosis:** independent read-only comparison in the failed runner's actual token visibility context (full page metadata/IDs and typed counts before/after). Do not schedule/activate or use live-write mode to obtain it. This patch is not proof of historical root cause or closure readiness.

## C1: #1833 identity/version counterfactual and registry gate

Read live #1833 full payload and comments: title `ruvnet/ruflo`, payload `skillId: ruvnet/agentdb`, source Ruflo `v3.63.8`. Both current named records point at Ruflo and contain Ruflo `v3.67.0` metadata; AgentDB retains `suiteRef: ruvnet/ruflo`. That topology/provenance is untouched.

Independent read-only release evidence during this pass: `ruvnet/agentdb` exists and publishes `v3.3.0` (2026-11-01); Ruflo publishes `v3.71.2` (2026-11-04). These are not interchangeable baselines.

Tests prove:
- Ruflo release routed to AgentDB, or the reverse, is unknown even if the tag coincides with the stored version.
- Current AgentDB→Ruflo mapping is refused **before fetching**; a relink alone cannot reuse a contradictory stored upstream.repo/version.
- Batch and fanout refuse overwriting a readable umbrella naming another skill; even a same-version fanout noop must validate identity.
- Two correctly sourced distinct findings select only their own umbrellas; input metadata, nested topology and issue history are unchanged.

**Unresolved canonical registry operation:** independently reviewed source/baseline reconciliation for `ruvnet/agentdb` (links and declared upstream repo/source/version, with retained mixed historical provenance) through `gaia dev relink` / `sync-upstream` or their current supported playbook. A simple relink is insufficient and explicitly refused when upstream.repo remains Ruflo. No command was used to rewrite registry metadata or trust/evidence. No live title/body repair to #1833 occurred. Polling the current conflicted AgentDB record intentionally remains unknown rather than inventing an independent version; do not claim fully healthy watcher polling yet.

## C4: current disable and threat-detection proof / handoff

All eight compiled build/verify wrappers are `workflow_dispatch` only, with `activation.if: false`; tests assert that posture. Live read-only Actions workflow listing reports their API state `active`, not `disabled_manually`. Internal pause is real but **must not** be used as A5 API-disable/closure evidence.

Verified pinned upstream v0.92.6 behavior: `safe-outputs.threat-detection.continue-on-error` defaults true; missing/parse/engine failures can produce warning and exit 0. Existing custom `steward_outcome` persistence only gated job success, not complete threat clearance. Upstream no-threat conclusion is `success` with an empty reason.

Source-only repair in `.github/workflows/shared/steward-agent.md` sets `enabled: true`, `continue-on-error: false` and requires detection actually run, conclusion success, and an explicitly present empty reason before outcome persistence. Offline tests execute that exact shell with synthetic output and prove warning, skipped, unknown, blank, failed and conflicting-reason cases cannot persist an outcome. Strict source configuration covers standard safe outputs upon compilation.

**Compiled locks deliberately unchanged. No compile, activation, credential/billing setup or schedule change.** `gh aw` is absent; no extension installed. Established synchronization requires a reviewed release compiler matching the reviewed gh-aw-actions tag, generated-lock review proving strict detection and preservation of manual-only/default-disabled posture. The current wrapper generator does not encode the manually applied lock activation pause: blind recompilation could lose it. `python scripts/gen_steward_agent_workflows.py --check` passed for current wrappers, which is not lock synchronization proof.

Exact security-worker/lead handoff: no `sensors_security.py` or mirrored skill files touched. Review the shared workflow source delta above; compiled threat enforcement and default pause must be independently verified before any separately founder-authorized non-Copilot activation. Never manually close #2126. A complete synchronization/engine authorization receipt is still required.

## Verification

- Full relevant actual suite: `PYTHONPATH=src python -m pytest -q tests/steward tests/upstream_watcher scripts/upstream_watcher/tests/test_upstream_watcher.py` → **3,173 passed in 1006.85s**, at the content committed through `63181cb38`.
- Final narrow missing-reason denial commit `6d3768096`: `PYTHONPATH=src python -m pytest -q tests/steward/test_founder_workflow_lock_2283.py` → **19 passed**. The full suite was not rerun after this additional fail-closed source-shell assertion.
- Watcher suite separately: **595 passed**.
- Focused decisions + reconcile/CLI/executor/desk + workflow-source shell checks: **206 passed**.
- New count/identity/decision tests: **36 passed**.
- `python scripts/gen_steward_agent_workflows.py --check` → 0.
- `git diff --check` → 0; clean worktree.
- Read-only live `LiveGh.list_issues` and before/after REST/GraphQL count comparison → 222 unique combined items, exact typed 218/4 match; no write calls.
- Lead census dry-run + all-item original/snapshot equivalence comparison → complete, 218 entries preserved, all four locks consumed.

Local scratch proof is under the worker's `$TMPDIR/founder-watcher-proof/`: `full-tests.txt`, `watcher-tests.txt`, `reconcile-after.json`, `reconcile-after-summary.txt`, `live-comparison.json`, historical run log/report and pinned detector reference files. These are local working evidence, not portable shared archives or campaign receipts.

## Resume / independent review

Review the four exact commits on the dedicated branch. Lead alone decides publication/integration after **fresh independent Terra review**. Do not run this worker's tests as a substitute for that review. Resolve the runner-context #2278 diagnosis, canonical AgentDB metadata/baseline operation and C4 release-compiler/pause-preservation gate before claiming corresponding operational completion. Existing Class B and archive lanes continue independently; no campaign ownership was adopted here.
