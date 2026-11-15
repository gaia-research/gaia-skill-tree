# P1 canonical persistence contract repair

**Delivery: READY FOR TERRA REVIEW, not P1 complete.** Founder reassigned the sole repair-author role from exhausted Opus (founder-reported) to `worker-sol-shared`, pinned `openai-codex/gpt-6.1-sol`, medium. The dispatch states its non-mutating live probe and child model/effort records were verified. This worker did not change provider/effort, retry a provider, invoke another agent, or act as reviewer. Independent Terra review and the subsequent real-runner `apply=false` / exit-0 / empty-`unknownEvidence` gate remain pending. P2–P7 have not started.

## Branches and authority

- Verified initial P1 checkout: `dev/upstream-backlog-watcher-2026-11`, clean at `1e7fcda223700cfbbe85cb790a1d55ed31b49fa0`; existing draft [PR #2468](https://github.com/gaia-research/gaia-skill-tree/pull/2468).
- Freshly fetched `origin/dev/upstream-backlog-2026-11`: exactly `bfed2d777b76448f6ede5d40e1a834050dff07d0`.
- Created separate worktree `upstream-backlog-contract-2026-11` and branch `schema/upstream-contract-2026-11` at that exact integration tip. Schema/test commit, pushed: `dda4c21520168df90ae1dc602f59159be0542c25`.
- Merged only this own feature into the existing P1 feature, with merge commit `b6d220073654f49c4ad241ad31de99bd28baffde`. No integration/main merge.
- P1 test/documentation source commit: `9056227669045638ab3f778ed6593b70b417d0c5`. This report is a subsequent report-only commit; its containing commit is the delivered final P1 HEAD.
- Commit and push identity verified: Marcus Rafael B. Tiongson `<153011150+mbtiongson1@users.noreply.github.com>`.
- Founder authorization covers technical persistence alignment, not new trust policy, formulas, grades, rank gates, Origin, evidence semantics or calibration. No actual registry operation was replayed.

## Diagnosis and smallest decision

Loaded AGENTS/CLAUDE, graft, the six campaign/handoff/reconnaissance documents, watcher contract, canonical trust-methodology-consult skill, authority map §4, methodology cache/formula sections and META §2.1c/§4/§5. Traced callers before multi-file work. The concept/compute/persist gap is in **named persistence bounds**, not the trust engine or watcher preflight.

Fresh pre-edit read-only validation found all **23** existing finder-scoped suites raw-schema-invalid: **254 errors**, including AgentDB's **11**. Ten AgentDB errors predate P1; the additional `note` was emitted by P1's `da255f0ee136226be434fe486e1d07e3d547616b` canonical `update-named` operation. It is not described as pre-existing. Existing selected-field validation is not an authority to bypass full-record validation.

The repair declares bounded shapes already grounded in current writers/authority:

| Persisted shape | Authority / producer | Bound / meaning |
|---|---|---|
| `trustMagnitudeInputHash` on named root | META §2.1c; authority map §4; `computeTrustMagnitudeInputHash`; `calibrate.py` | Exactly 64 lowercase hex SHA-256 characters. Cache reuse still requires an input match. Not an evidence field. |
| `apexGateStatus.crossOrgVerifier`, `systemWideCap` | `passesSuiteApexGate`, calibration writer `--refresh-apex`, archived migration | Boolean/null engine keys; null means skipped. Retains older schema spellings too. No predicate activated. |
| `apexPromotionPrSignedBy`, `apexPromotionPrSignedAt` | `founder/handovers/done/G7_RFC_V3_RATIFICATION_2026-06-20.md` sign-off effect | Human-handle syntax / ISO date. Historical provenance, not authenticated approval. |
| `migrate_trust_magnitude`, `recalibrate_trust_magnitude` | Archived `migrateTrustMagnitude.py:213`; current `calibrate.py:510` | Explicit action vocabulary, not arbitrary historical-error exemptions. |
| `note`, `suite_ref_set`, `installation_updated` | Current `commands/dev/named.py` writer | Explicit actions; actual GitHub-link writer output tested with the real timeline helper. |
| Timeline `github-actions[bot]` | Canonical workflow bot provenance; watcher contract; CLAUDE authorization distinguishes bot actors | Exact literal alternative to existing human-handle syntax, only on timeline contributor. No arbitrary bot strings, root-owner widening, or authorization change. |
| Root `installable` | `freeze.py`, `named.py`, META Star Bar and watcher freeze contract | Boolean, independent of rank. |
| Root `attribution` | Canonical intake provenance shape (`skillBatch.schema.json`), retained source attribution | Closed object with upstream author, source URI, and existing four attribution types. Not evidence strength. |
| Named evidence `updatedAt` | `stargazerHeartbeat.py:184` | ISO date of metric refresh; not substantive verification/freshness. No generic evidence-schema change. |
| Null timeline `newValue` for `upstream_deprecated` | Freeze contract: no successor, retained frozen personal suite history | Conditional compatibility only for this action; null `upstream_synced` remains invalid. |

All root/object unknown-field rejection, required fields, dates, existing cross-field constraints, active registry/schema selection, source/repo/tag/URL checks, frozen refusal, atomic write and dry-run paths remain intact. No normalizer, historical skip list, alternative validation engine or `additionalProperties: true` was introduced. No runtime CLI/watcher source change was needed: its existing strict preflight now consumes the aligned canonical schema.

### Files changed

Schema branch:
- `registry/schema/namedSkill.schema.json` — bounded named persistence additions above.
- `src/gaia_cli/data/registry/schema/namedSkill.schema.json` — byte-identical bundled mirror via `scripts/sync_bundled_schemas.py`.
- `docs/schema/namedSkill.schema.json` — targeted `shutil.copy2` using the existing `syncDocsGraphAssets.py:211–222` public-schema mirror contract, without invoking graph generation.
- `tests/test_named_persistence_contract.py` — positive writer/engine shapes, negative field/type/actor/action bounds and three-way mirror checks.

P1 branch:
- `tests/test_upstream_persistence_contract.py` — all 23 current finder-scoped raw records; real named writer/timeline output on an isolated fixture; actual frozen-suite refusal with byte hashes.
- `docs/agents/upstream-watcher.md` — persistence compatibility limits alongside the unchanged full-record preflight contract.
- This report only. No CAMPAIGN/COSTS/PR-body administration.

## Executed verification

Commands below ran on the composed P1 stack unless explicitly marked schema worktree.

| Command / probe | Actual result |
|---|---|
| `python3 -m pytest tests/upstream_watcher tests/test_upstream_approve_workflow.py tests/test_dev_upstream_verbs.py -q` | **1015 passed**, 176.14s. Includes empty-name/root/cross-field, selected `.gaia/registry`, absent/invalid schema, invalid actor/releasedAt, Git refs/encoded tags, URL fragments/garbage links, atomic failure and implicit repo drift regressions. |
| `python3 tests/upstream_watcher/parity_2283.py` | Exit **0**; `stagedRowsEqualBatchRows` and `stagedRowsEqualDailyUnstagedRows` both **true**. |
| `PYTHONPATH=src:. python3 -m pytest tests/test_upstream_persistence_contract.py tests/test_named_persistence_contract.py tests/test_dev_named.py tests/test_calibrate_trust_magnitude.py tests/test_curation_authority_map.py tests/test_canonical_event_schema_contract.py -q` | **160 passed**, 15.31s. |
| `PYTHONPATH=src:. python3 -m pytest tests/test_dev_timeline.py tests/test_trust_magnitude_consistency_frozen.py tests/test_trust_freshness.py -q` | **179 passed**, 3.12s. |
| Schema worktree: `PYTHONPATH=src python3 -m pytest tests/test_named_persistence_contract.py tests/test_curation_authority_map.py -q` | **62 passed**. |
| Schema worktree, after commit: `PYTHONPATH=src python3 -m pytest tests/test_canonical_event_schema_contract.py -q` | **73 passed**. |
| `python3 scripts/sync_bundled_schemas.py --check` | Exit **0**, mirrors in sync; public mirror equality also tested. |
| `git diff --check` | Exit **0**. |
| `git diff 1e7fcda223700cfbbe85cb790a1d55ed31b49fa0 --exit-code -- registry/named registry/nodes skill-trees` | Exit **0**, empty. Every real record, metric, evidence row, timeline, component link and frozen state unchanged since worker start. |
| `GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev validate` | **Exit 1**, not full PASS. `scripts/validate.py` 11/11 passed; redaction/timeline/TM consistency gates lack generated `registry/named-skills.json`. Known missing Class P dependency remains; no index fabricated, gate bypassed or Class S regeneration invoked. |

Initial local test corrections were test-fixture issues, not hidden passes: the new synthetic evidence row initially omitted required evaluator/date; the first real-scope test passed the repository rather than `registry/named` as the iterator root. Both were corrected and rerun. The event-contract test compares against `HEAD` and initially reported the intentional named evidence timestamp addition as an uncommitted delta; it passed after the schema commit. An initial log redirection to `/tmp` was refused by this environment; the required watcher command then actually ran with its log in `$TMPDIR`. No dependencies or global configuration were changed.

### Read-only old/new schema comparison, reproducible

This repeats the original pre-edit failure against immutable Git schema bytes and unchanged records, without a new upstream census:

```python
import json, subprocess
from pathlib import Path
from jsonschema import Draft7Validator
from scripts.upstream_watcher.finder import iter_suite_skills
from gaia_cli.commands.dev.sync_upstream import _schema_format_checker
old = json.loads(subprocess.check_output([
    'git', 'show', '1e7fcda223700cfbbe85cb790a1d55ed31b49fa0:registry/schema/namedSkill.schema.json']))
new = json.loads(Path('registry/schema/namedSkill.schema.json').read_text())
validators = [Draft7Validator(s, format_checker=_schema_format_checker()) for s in (old, new)]
counts = [0, 0]
suites = list(iter_suite_skills())
for path, meta in suites:
    errors = [list(v.iter_errors(meta)) for v in validators]
    for i, rows in enumerate(errors):
        counts[i] += len(rows)
    print(meta['id'], [len(rows) for rows in errors])
assert len(suites) == 23 and counts == [254, 0]
```

Run with `PYTHONPATH=src:. python3`. Actual result: **23 suites, 254 → 0 errors**; AgentDB **11 → 0**. Frozen `mattpocock/personal` also conforms, but its sync remains refused by canonical frozen protection (tested). No records were rewritten to obtain this result.

### Real AgentDB CLI dry-run and zero-write proof

Current AgentDB already records its verified `v3.10.0`; that same-tag operation correctly refuses. To exercise a real proposal without force/repoint or a fabricated release, read only the single known earlier own-source release:

```bash
gh api repos/ruvnet/agentdb/releases/tags/v3.9.0 \
  --jq '{tag_name,published_at,html_url}'
# v3.9.0, 2026-11-10T18:30:11Z,
# https://github.com/ruvnet/agentdb/releases/tag/v3.9.0

GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev sync-upstream ruvnet/agentdb \
  --repo ruvnet/agentdb --tag v3.9.0 \
  --source-url https://github.com/ruvnet/agentdb/releases/tag/v3.9.0 \
  --released-at 2026-11-10T18:30:11Z --user mbtiongson1 --dry-run
```

Actual CLI **exit 0**, printed `=== DRY RUN — no files written ===`, proposed upstream block and `upstream_synced` event. This historical-release probe is **not a rollback recommendation or release approval**. It never ran without `--dry-run`; current source/version remains AgentDB `v3.10.0` and its five components remain untouched. No `--force` was used.

A Python wrapper hashed all **869** files recursively under `registry/named`, `registry/nodes`, and `skill-trees` immediately before/after the CLI subprocess: SHA-256 over sorted `path + NUL + bytes + NUL` was identical:

`fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`.

## Remaining gates / delivery boundary

- Independent Terra review of the schema repair and composed P1 stack; author has not declared an independent PASS.
- Administrator opens the separate schema draft PR against the same integration branch. Existing P1 PR #2468 stays draft; this worker created no PR and merged neither integration nor main.
- Real-runner `apply=false` observation remains for the authorized operator **after** review. No workflow dispatch, upstream census, approval label, issue mutation, deployment or P2 activation was performed.
- Class S regeneration remains deferred to P7/canonical gate. No trust engine/config/policy, ranks, evidence metrics, registry history, skill trees, frozen state or source links changed in this repair.
