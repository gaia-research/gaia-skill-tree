# Strict generated-cache and marker repair — #2283

## Status / exact checkpoint

**Authorized source repair completed and locally tested; fresh independent review required. Builder is not its own independent verifier.**

- Base: `939d8ef4b4476535c558969b969238ead2762d61`.
- Final: `42322964ae5899712df5b492e98f37600e04bd89` (`fix(steward): strictly validate generated identities and require lock marker`).
- Dedicated branch: `dev/steward-founder-lock-2283`; existing history preserved, one new local commit, no push/integration. Worktree clean after final tests.
- Author and committer: Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>, supplied through per-command git flags.
- Runtime environment verified: `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=high`. No fallback, nested agents, or imposed task/turn cap.
- Read root/founder CLAUDE, graft instructions, original substantive shared assignment, original proof, corrective proof, and final independent review before repairs. Relevant native graft capability used; no Skill Heaven surface was available or installed, and no Skill Heaven validation is claimed.

## Exact file delta against base

`git diff --numstat 939d8ef4b4476535c558969b969238ead2762d61..42322964ae5899712df5b492e98f37600e04bd89`:

| File | Added / removed | Change |
|---|---:|---|
| `scripts/upstream_watcher/releaseidentity.py` | 18 / 10 | Explicit keyword-only generated-body strictness; require valid owner/skill strings and case-insensitive identity match; retain historical recovery by default. |
| `scripts/upstream_watcher/issuer.py` | 9 / 1 | Strictly validate rendered bodies before create/update/approval-reset; revalidate generated run-cache entries before every subsequent skip/update. |
| `src/gaia_cli/steward/issuehygiene/questions.py` | 6 / 2 | Recognized lock enablement requires marker document to be a file as well as all four valid finalized records. |
| `tests/upstream_watcher/test_identity_2283.py` | 77 / 0 | Invalid generated-body, zero-write, historical recovery, repeated identity/cache and case-insensitive validator controls. |
| `tests/steward/issuehygiene/test_founder_locks_2283.py` | 22 / 2 | Missing/renamed/non-file marker through real sensor, CLI and closure re-derivation; any expected record requires marker. Existing missing/renamed/open-record cases retained. |
| `founder/steward/decisions/README.md` | 7 / 4 | Document explicit marker prerequisite without treating it as a new decision. |

Total: six files, 139 additions / 19 removals. No decision JSON, schema, source-release guard, count code, workflow source/lock, security sensor, mirror, archive or ledger changes.

## Real BEFORE / AFTER evidence

### Identical selected regression command

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/upstream_watcher/test_identity_2283.py \
  tests/steward/issuehygiene/test_founder_locks_2283.py \
  -k 'generated_invalid_identity or final_lock_loss or any_expected_record'
```

**BEFORE:** new regressions applied while all production source was still at base: **41 failed, 3 passed, 37 deselected in 9.21s**.

- 34 generated-invalid-body create/update cases failed the refusal/zero-write contract. Historical permissiveness allowed absent/malformed identity into a new body/cache; valid conflicting identity could be refused only after the initial invalid write.
- Three missing/renamed/non-file marker cases did not make real sensor reconciliation unavailable despite four intact records.
- Four single-record cases already refused an incomplete set, but with only the all-four-records error; they did not enforce the separate marker prerequisite. These are prerequisite/error assertions, not four additional examples of permissive reconciliation.
- Existing missing/renamed/open-record cases passed before and remain unchanged.

**AFTER at exact final SHA:** **44 passed, 42 deselected in 3.16s**. Five additional positive cache/case-insensitivity controls were added after the initial before run, explaining the deselection difference. No existing substantive test was removed or relaxed.

### Direct base cache-gap reproduction

An additional offline probe executed the exact base `issuer.py` and `releaseidentity.py` bytes loaded with `git show`, with GH operations mocked. Rendering `<!-- gaia-upstream-payload\n{}\n-->` for two identical valid Ruflo findings produced:

- first result: umbrella `123`, not skipped;
- second result: `skipped: true`, issue `123`;
- **one fake create**, zero fake updates, no refusal.

This demonstrates the actual same-run missing-identity cache gap, rather than only a hypothetical parser concern. Final regression tests reject that body before its initial create and assert zero fake create/update/approval-reset/body-edit calls.

### Focused and final regressions

Focused two changed test modules: **86 passed in 3.59s** before commit.

At exact final SHA:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/steward/issuehygiene \
  tests/steward/test_founder_workflow_lock_2283.py \
  tests/upstream_watcher \
  scripts/upstream_watcher/tests/test_upstream_watcher.py
```

**1,400 passed in 299.28s (0:04:59).** Includes identity/source, #2278 count/pagination, historical headless recovery, issue-hygiene reconciliation/closure safety and C4 workflow-pause/source-shell regressions. The entire 3,173-test suite was intentionally not blindly rerun.

`git diff --check` passed. AST syntax checks passed for all five changed Python files. Final `git status --porcelain` was empty; HEAD unchanged after tests.

Local scratch evidence (not canonical receipts): `/data/data/com.termux/files/usr/tmp/founder-watcher-strict-repair/` contains `before-tests.txt`, `after-selected-tests.txt`, `after-focused-tests.txt`, `final-regressions.txt`, `base-cache-gap.json`, and `base-marker-holds.json`.

## Generated strictness / legacy compatibility

`validateUmbrellaIdentity(..., generated=False)` preserves the historical existing-issue repair behavior: absent payload marker, invalid JSON, non-object payload, missing/non-string skillId remain recoverable; an affirmative string identity conflict still refuses. Eleven legacy recovery cases execute the real fanout update path with mocked GH. Batch headless recovery remains on the historical default and passed the broader suite.

New bodies use `generated=True` before the first create/update and before approval-reset writes. The new body must contain a JSON object with a nonempty, syntactically valid owner/skill string matching the incoming valid identity. Non-string/null/bool/list/object identity, absent identity/payload, malformed JSON, empty strings, missing/extra slash segments, whitespace/newline and a different valid skill identity are rejected. No headless newly generated entry is accepted simply because historical repair permits one.

Run-cache provenance is explicit: cache entries pass `generated=True` before every subsequent skip or update, while an original snapshot may use legacy recovery. Positive tests spy on all validation calls across initially created and updated umbrellas, repeated same-version skips and new-version updates; only original historical snapshot reads are non-strict. Repeated identical valid identity still produces one create, with later skips and only necessary version updates. Case-insensitive matching is independently asserted. Existing two-different-skills/same-source preflight and zero-write regressions remain intact.

While authoring the cache control, mixed-case source keys exposed an existing fanout cache-key inconsistency (extra create with an empty snapshot, or redundant update with an existing snapshot). That is not a generated-payload identity bypass and is outside these two bounded repairs. The committed control uses the requested exact repeated identity; it does not claim mixed-case fanout routing is repaired. No source expansion was made for that observation.

## Marker prerequisite / holds / no new authority

Enablement is still recognized by the existing marker OR any canonical expected record. Once recognized, reconciliation now requires BOTH a real `founder/steward/FOUNDER_LOCK_2283.md` file AND all four exact finalized, schema-valid mapped records. Marker missing/renamed/replaced by a directory refuses through sensor, standalone CLI (no manifest emitted), and independent closure re-derivation. Missing/renamed/open/malformed/mismapped records still fail closed; marker present with all records absent still fails. An unrelated fresh checkout with neither marker nor expected records retains ordinary behavior.

**Important qualification confirmed directly:** base `loadIssueDecisions` with four valid records and no marker loaded all four and still consumed holds. An offline temporary-fixture reconciliation using that exact base loader produced `held/none` for #2002, #1835, synthetic GBrain/Addy children #1836/#2003, and #2126/#2127. This finding is explicit-enablement-contract hardening, NOT recovery of previously lost holds and NOT new founder authority.

All four existing decision records still validate and map exactly. Final tests preserve C1 technical-only B, C2/C3/C4 family/descendant holds, original body digests/history, unrelated questions as independent Class C, and no release/closure authorization. The prior independent 218-object / 67-child saved-census replay was not rerun; no fresh canonical census/ledger settlement is claimed.

## Boundaries and residual gates

- Fresh independent review of `42322964ae5899712df5b492e98f37600e04bd89` is required before lead publication/integration. No self-review substituted for it.
- C1 AgentDB canonical registry metadata/baseline reconciliation remains separately authorized and independently reviewed; no registry/topology/trust/rank/evidence/intake changes.
- Historical #2278 runner-context diagnosis remains unproven and separately gated. Existing typed-count and release-source guards are unchanged; their regressions passed.
- C2 migration and C3 founder curation remain deferred; no issue/child/history/label changes.
- C4 compiled synchronization, release compiler/threat-engine proof, pause preservation, credentials and any future explicitly authorized non-Copilot activation remain separately gated. No compilation, activation or workflow edits; no closure of #2126/#2127.
- `writesEnabled=false` and open closure authority were untouched. No live issue closure authority is granted.
- No shared ledger, canonical scan/run/record/migrate/rollback, lease/action ownership, GitHub/forge writes, package/global configuration changes, credentials, main/integration merge, push, release/deploy, history reset or rebase. Test fixtures and mocked GH only; no live network verification was needed or claimed.
