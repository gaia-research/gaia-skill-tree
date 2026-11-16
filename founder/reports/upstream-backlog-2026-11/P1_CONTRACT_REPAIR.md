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
- Schema draft [PR #2469](https://github.com/gaia-research/gaia-skill-tree/pull/2469) now exists against the same integration branch. Existing P1 PR #2468 stays draft; this worker created no PR and merged neither integration nor main.
- Real-runner `apply=false` observation remains for the authorized operator **after** review. No workflow dispatch, upstream census, approval label, issue mutation, deployment or P2 activation was performed.
- Class S regeneration remains deferred to P7/canonical gate. No trust engine/config/policy, ranks, evidence metrics, registry history, skill trees, frozen state or source links changed in this repair.

## Terra ordinary-CLI compatibility finding — bounded continuation

**READY FOR TERRA REVIEW; not P1 complete or runner approval.** Verified clean local and remote starting heads exactly as dispatched: P1 `1e4558fb27f3b4d7b7af1f9dd58b3a3753c7247e`, schema `dda4c21520168df90ae1dc602f59159be0542c25`. Both PRs #2468/#2469 remain drafts targeting `dev/upstream-backlog-2026-11`. Luna's administrative commit/history was retained. No nested agent, provider retry, model/config change, campaign logging, upstream recrawl or new PR.

### One local compatibility inventory and diagnosis

Reloaded trust-methodology-consult, the authority map, methodology base-formula/structural-role sections and persistence schemas; used graft for eligibility/frozen helpers, writer searches and consumer/caller tracing. The completed CPU-local inventory parsed all **472** named records, used `_pf_min_two_stars` and suite-aware `namedFrozenIds`/`preflightNamedSkillMutable`, and classified **128** below-threshold records, **24** frozen records, **320** eligible unfrozen records. Eligibility here is the command's named-record/rank/frozen surface, not a claim that every record has an actionable release or that source guards may be skipped. The current raw schema/production format checker found **2 invalid records / 2 errors**; 318 already conformed. No new health/curation census or network evidence collection was performed. The stored inventory paths/hashes were revalidated after repair: **320 records, zero schema errors**, with every hash unchanged. No additional corrupt shape was found in this bounded eligible surface; arbitrary other invalid data remains rejected.

| Record | Exact failing persisted shape | Classification and existing authority |
|---|---|---|
| `google-deepmind/workflow-skill-creator` | `timeline[14]`, action `demote`, timestamp `2026-09-05T00:00:00Z`, `author: mbtiongson1`, string `notes`, `previousValue: 4★`, `newValue: 1★` | Legacy historical demotion provenance, not operator identity or approval. Current `timeline.py` emits `contributor`/`details`; no current writer producing `author`/`notes` was found. Retain the existing text, without guessing an authenticated contributor or rewriting history. |
| `ruvnet/v3-ddd-architecture` | **Root** `role: variant` (string), not `evidence.role` | Active persisted RFC C-2 structural role. `registryMaps.buildMergedSkillMap:34–93` explicitly preserves it and documents the distinction from generated bucket-display role; `tests/test_registry_maps.py` already tests preservation. `structuralGraph.isVariant:89–103` and `trustMagnitude._gradedOriginCount:404–451` / `checkAGradedOriginsGte5:1321–1394` consume it. META structural inputs and methodology role-guard sections explicitly exclude variants. |

The reported `evidence.role` premise was not reproduced: the stored evidence row has no role field. Current named/evidence/fuse writer searches found no producer for this stored root key; it is retained legacy structural inventory already supported by live read/compute contracts, not a new CLI flag or new evidence input. The TM engine **does not ignore the structural role**: it affects structural origin eligibility; fusion-recipe still contributes zero TM. No engine, role resolver, automatic Origin, scoring, diversity or gate semantics changed. `evidenceEntry` in **both** named and generic schemas is untouched; there is no reason to add `evidence.role`, a metric, generic root cache metadata, or generic evidence fields. Authority-map persistence symmetry for evidence is therefore preserved.

### Minimal alignment and compatibility boundary

- Named root `role` is a closed string enum `origin|variant`, grounded in the existing RFC structural contract; not an automatic Origin claim or generated display role.
- Timeline `author`/`notes` is a bounded **legacy demotion shape**, not a general second actor interface: if either appears, both plus string `previousValue`/`newValue` are required, action must be `demote`, author must match human-handle syntax, notes must be nonempty text, and mixed `contributor`/`details` is rejected. Timestamp and all other event checks still apply. These keys are stored verbatim, never mapped into contributor identity, approval or authorization. No date/record-ID grandfather list or arbitrary historical validation exemption.
- Canonical, bundled and public named-schema mirrors are identical. No runtime source change, normalization, `additionalProperties: true`, evidence widening, metric substitution or registry/history write.
- New tests exercise both actual non-suite records copied into isolated fixtures, positive zero-write sync proposals, and unknown root/evidence fields, negative commits, invalid role/legacy author/date/new actor/release date/Git-ref cases. Schema tests additionally reject incomplete legacy pairs, mixed identities, unsupported actions, unknown keys and malformed values.

### Before/after CLI proof and preservation

Actual `gaia dev sync-upstream ... --dry-run` subprocesses, with the normal operator override for these explicitly authorized read-only probes, reproduced **exit 1** before repair for both records (exact `timeline.14` unexpected author/notes and root unexpected role errors). After the schema merge, both returned **exit 0**, printed `DRY RUN — no files written`, and preserved every record byte. Synthetic tag `v0.0.0-contract-probe`, timestamp `2026-11-01T00:00:00Z`, source URLs under the existing known repositories: these are **format-valid synthetic proposals, not observed releases, release approvals or an instruction to apply**. No network source lookup or `--force` occurred.

Repro commands (set `PYTHONPATH=src` and the already-authorized `GAIA_OPERATOR_OVERRIDE=1` for each):

```bash
python3 -m gaia_cli.main dev sync-upstream google-deepmind/workflow-skill-creator \
  --repo google-deepmind/science-skills --tag v0.0.0-contract-probe \
  --source-url https://github.com/google-deepmind/science-skills/releases/tag/v0.0.0-contract-probe \
  --released-at 2026-11-01T00:00:00Z --user mbtiongson1 --dry-run
python3 -m gaia_cli.main dev sync-upstream ruvnet/v3-ddd-architecture \
  --repo ruvnet/ruflo --tag v0.0.0-contract-probe \
  --source-url https://github.com/ruvnet/ruflo/releases/tag/v0.0.0-contract-probe \
  --released-at 2026-11-01T00:00:00Z --user mbtiongson1 --dry-run
```

The previously documented real AgentDB `v3.9.0` historical-release safe dry-run also returned **0** before and after, without re-fetching that release or changing the current `v3.10.0` record. Before/after each probe batch, all **869** named/node/tree files retained aggregate SHA-256 `fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7` (the same sorted path/NUL/bytes/NUL algorithm above). Individual hashes also retained:

- Workflow-Skill-Creator: `f6f9574cea3519b6660623e679c95e3d7123b401783155d099d7eddaa99fbe75`.
- V3 DDD Architecture: `f78a250b272a3095e250cab673215c97e73ab7b9939e79b541b3127a4c0f654d`.

### Executed continuation checks

| Check | Actual result |
|---|---|
| Required `python3 -m pytest tests/upstream_watcher tests/test_upstream_approve_workflow.py tests/test_dev_upstream_verbs.py -q` | **1015 passed**, 214.66s |
| `python3 tests/upstream_watcher/parity_2283.py` | Exit **0**, both parity booleans **true** |
| `PYTHONPATH=src:. python3 -m pytest tests/test_upstream_persistence_contract.py tests/test_named_persistence_contract.py tests/test_dev_named.py tests/test_calibrate_trust_magnitude.py tests/test_curation_authority_map.py tests/test_canonical_event_schema_contract.py tests/test_registry_maps.py tests/test_fusion_score.py tests/test_dev_timeline.py tests/test_trust_magnitude_consistency_frozen.py tests/test_trust_freshness.py -q` | **410 passed**, 31.98s; no duplicate file in this composed focused run |
| Schema worktree: named persistence, registry maps, fusion score, authority map tests | **113 passed**, 6.35s |
| Schema worktree, after commit: canonical event-schema contract | **73 passed**, 0.78s |
| Stored 320-record eligible inventory, hashes and schema revalidation | **0 errors**, hashes unchanged |
| Existing 23 watcher suites, immutable pre-P1 schema vs repaired schema | **254 → 0**; AgentDB **11 → 0** |
| Bundled schema check / public mirror assertions / `git diff --check` | PASS |
| Diff from resumed P1 head limited to named/node/tree data | Empty; five AgentDB components unchanged |

Non-passes were not hidden: the first inventory attempt stopped at the first below-threshold record because the scratch classifier caught the wrong exception type; the corrected single completed inventory caught `DevPreflightError`. A combined shell command hit the tool's 30s search safety limit; the standalone probe batch subsequently completed. The first new timestamp-negative schema test exposed absent optional `date-time` support in plain `FormatChecker`; attempting to import P1's production checker into the standalone schema branch was invalid because that branch intentionally predates the helper. Removed that schema-branch dependency and tested the timestamp negative through the actual composed P1 preflight instead (all passed). No dependency/config was installed or changed.

Schema update pushed at **`6bed0edf324d49e42cd8953351deaccaa733d22f`**, merged into P1 by own-feature merge commit **`ca564c0afcd8a911b7ea51b704a31861c2d5a721`**. This continuation report and P1 tests/contract doc are in the subsequent P1 commit; the delivered P1 SHA is the containing commit, returned in the handoff. Both commit identities remain the approved author. No integration/main merge, rebase or history rewrite. Full `dev validate` is **not** claimed green: the previously observed missing Class P index remains ungenerated. Independent Terra review and actual-runner observation remain outstanding; no P2 advance.

## 2026-11-17 — Independent Terra verification receipt (supersedes only pending-review status)

Fresh independent Terra review **PASS; no actionable findings** at exact feature source `591264b3bc1d7607e1074411f1c0a77b541515d9` plus schema `6bed0edf324d49e42cd8953351deaccaa733d22f`. This is an independent CODE review, not founder release approval. Historical builder command/result attributions above remain unchanged; specifically the broader builder-focused **410 passed** result is not rewritten as Terra's focused check. Terra actually reran the required watcher/workflow/CLI command (**1015 passed**) and the two requested files `tests/test_named_persistence_contract.py tests/test_upstream_persistence_contract.py` (**70 passed**), plus parity exit 0/both true. Independent probes confirmed 320 eligible unfrozen named records with zero errors; 23 suites 254→0; two non-suite SAFE CLI probes and historical AgentDB dry-run with no writes; mirror, frozen, diff and negative controls; 869 protected files unchanged with digest `fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`. That digest check is from pre-contract checkpoint `1e7fcda223700cfbbe85cb790a1d55ed31b49fa0`, not original main; the canonical provenance appends were already present at that checkpoint.

Terra reproduced Google DeepMind author/notes as historical timeline provenance, not new operator identity, and `ruvnet/v3-ddd-architecture` root `role: variant` as a structural eligibility field read by canonical consumers—not `evidence.role` or automatic Origin. Unknown root/evidence keys, including `evidence.role`, still reject; legacy aliases are not authorization. Important contract precision: the repair **does add named-evidence `updatedAt` as bounded provenance**; it must not be described as no evidence-schema field change. No formula, rank, grade, Origin, Star Bar, gate, or actor-approval implementation changed; raw registry/history remained unchanged by contract repair. Full `gaia dev validate` remains unclaimed/not green because Class P `registry/named-skills.json` is absent.

State after this review: **REVIEW PASS — P1 REAL RUNNER PENDING; NO MERGES.** The single authorized generic non-writing `apply=false` runner is still outstanding. No P1 completion or P2 advance until artifact inspection.
