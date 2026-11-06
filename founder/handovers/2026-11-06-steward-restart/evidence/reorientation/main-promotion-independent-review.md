# Independent first-main-promotion review — Lane C

## Status
blocked — **SOURCE ELIGIBLE**, but **normal protected main promotion is not presently cleared**. No new source correctness/security defect was found. Live protection is ineffective; exact-head main-PR CI and the terminal-output human gate below remain outstanding. This is not a rejection of the accepted seven engineering packages or a requirement to wait for routine-19 coordination/archive work.

- Candidate: **`2d9599c11ea91f303b5067c39fb8ea272f119072`**.
- Base, local `origin/main`, and freshly queried remote main: **`31b407db65c4e138896780a7319e4a4ce76884eb`**.
- Candidate tree: **`9b29681b44be112306f8502961f4e67787492d97`**, exactly equal to independently accepted preservation candidate **`b04a6c34974e0ce25a8a6ff43bc676dd864c3264`**.
- Reviewer: independent reviewer-shared. Observed `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=high`; no nested agents or fallback. Provider-side routing is not independently attested.
- Review checkout: `$HOME/.gaia-worktrees/steward-promote-review-2283`; initial/final tracked status empty. Final remote observation: **2026-11-05T17:10:24Z**.

## Findings

1. **GitHub `gaia-research/gaia-skill-tree`, main / ruleset `18124772` — warning, promotion blocker:** Live `GET /branches/main` reports `protected:false`; `GET /branches/main/protection` returns **404, “Branch not protected”**; `GET /rules/branches/main` succeeds with **`[]`**. The accessible active “Main Ruleset” has `conditions.ref_name.include:[]` and `exclude:[]`. Consequently its configured checks are not effective main protection. This is affirmative accessible evidence, **not** an inference from missing permission: the repository GET exposes admin/maintain permission and the ruleset detail is readable. The conditional mission requires a normal protected PR, not an unprotected merge. Parent must resolve this with the authorized maintainer and re-read effective protection; this review grants no settings change or bypass.
2. **`src/gaia_cli/steward/ledger.py:266-273` / `founder/CLAUDE.md:187` — warning, human constraint:** Website/rendering assets are exact main, but not every terminal output is inherited: accepted Lane A adds a size-warning diagnostic. Founder guidance explicitly gates visible CLI-output changes on before/after founder review. No such rendered-output approval is established by the supplied acceptances; GET reviews for #2284 and #2295 returned no reviews. This is a human approval evidence gap, not a source defect. Present the synthetic output below for founder confirmation (or obtain an explicit applicable-gate determination); do not call this output byte-identical to main or silently waive the rule. No new visitor-site design/layout review is needed on the inspected diff.

### Exact live gate inventory

All forge operations in this review were GETs through `gh api -X GET`; no tokens were printed.

| Read | Observed result |
|---|---|
| Repository | Default branch `main`; merge commits allowed, squash disabled, rebase allowed, delete-on-merge enabled. Repo setting allowing rebase does not override the local merge-commit requirement. |
| Classic main protection | Explicit “Branch not protected” 404. |
| Effective main branch rules | HTTP-success empty list, repeated at final observation. |
| Rulesets including parents | One active repository ruleset, ID 18124772. Detail readable, no bypass actors; `current_user_can_bypass:never`. |
| Configured but ineffective status rules | Strict up-to-date policy; `Schema + DAG + Integrity Checks` and `Verify branch scope matches changed files`, each represented both without and with GitHub Actions integration ID 15368. Also deletion/non-fast-forward rules. No required-review rule is present. **These are configured contexts, not currently enforced main requirements.** |
| PR #2295 | Merged into `dev/steward-campaign-2026-11-05`; head `b04a6c34974e0ce25a8a6ff43bc676dd864c3264`; merge commit exact `2d9599c11ea91f303b5067c39fb8ea272f119072`. |
| Prior #2295 head checks | 23 returned check runs: 18 success / 5 skipped; no returned failure or pending check. This freshly corroborates the integration receipt, **not main-PR CI**. |
| Candidate `2d9599c11` checks/status | Two successful push checks (PR guards, design-system lint); combined status says pending with zero legacy statuses. This is **not** a failing legacy check, nor evidence of full CI completion. |
| Open main PRs | One unrelated draft #2235; no main PR for the frozen promotion head was returned. Exact-head main-PR CI/reviews therefore cannot yet be certified. |
| PR #2296 | Still open against integration at head `6b914723004852a5f515f78ed6d536cccbe3a9bc`; excluded, regardless of its separate dormant source acceptance. |

The absence of an effective GitHub required-review rule does not cancel repository human policy. Generic founder conditional promotion direction is not a claim that the founder has inspected a new CLI rendering. Existing lock comment 6640916880 was also read via GET: it is historical scoped implementation authority, explicitly not main-merge/release authorization; it does not establish this CLI review.

## Carried review proofs and source eligibility

Read **in full** `routine19-shared/preserve-main-verification-completion-review.md`, `preserve-main-accepted-merged-receipt.json`, and the six-unit evidence listed below, under the campaign root `$HOME/gaia-skill-tree/.gaia/steward/campaigns/2026-11-05/`.

Whole-tree equality to accepted `b04a6c349` carries its completed join/caller/resource/authority audit without redoing 650 builder cases, 120 completion cases, 39 semantic rows, official compatibility provenance, or scanner controls. Those remain prior evidence, not new executions here. Historical BLOCKED partial reviews remain historical; the completion report supplies their missing checks.

| Accepted package | Prior proof read; fresh binding |
|---|---|
| 1. 8 MiB/history preservation | `ledger-recovery/lane-a-ready.json`, `lane-a-live-assurance.json`; current ledger is accepted blob **`dae7b0d3bc2fd3f04ba82b978e66d2c0ca92b0cd`**. Historical campaign receipt/docs are preserved, not a claim of a fresh successful campaign. Main-relative fullrun difference is only the accepted no-op compactor. |
| 2. Unused import | `ledger-recovery/unused-import-composition-independent-review.md`; reconciliation equals accepted `42322964` minus exactly `from pathlib import Path\n`, and equals combined accepted `5cbe7e80`. The old import review is not misrepresented as independent review of later founder semantics. |
| 3. CI scope | `ledger-recovery/ci-scope-independent-review.md`; workflow and landing tests exactly equal accepted `c5de985cb18515ceb245fb91ebc3053b94c18ece` blobs. Normal same-repository `dev/*` promotion naming fits the existing unrestricted integration scope; no skip label is needed or authorized. |
| 4. Security/mirror/source triage | `founder-reconciliation/security-aggregate-independent-review.md`; both entire Impeccable trees equal audited `166e85514`; 39 current matrix sources equal reviewed `3f4c46fe` blobs and their SHA-256 bindings. No new adjudication or detector exception. |
| 5. Founder/watcher composition | `founder-reconciliation/founder-verification-completion-review.md`; operative founder/watcher changes retain combined accepted `5cbe7e80` bytes except separately accepted evidence prose. This supplies the changed-watcher caller/semantic gate, not merely an old standalone-security hash. |
| 6. Evidence prose/proof | `founder-reconciliation/evidence-prose-independent-review.md`; all four paths changed by accepted `bb9abb0f30988ad35d4e3ed6ccb6a43dda506c08` exactly match. Historical inventory/final-debt versus metadata-snapshot caveat remains; checker success is not identity/authority authentication. |
| 7. Main join + sidecar | Whole preservation completion at `b04a6c349` and merged receipt; **entire tree identical**, including the two sidecars. Main authority/policy/R19 additions are preserved, not re-ratified or activated. |

### Fresh complete diff/metadata checks

Independent read-only Python used actual Git trees/blobs, `git diff --name-only`, `git ls-tree`, SHA-256, JSON/YAML/TOML parsing and AST comparison; it did not trust the stat or run builder probe scripts.

- Main and `8ad344a49926821d2c1b6d4e021b8de6f653649c` are candidate ancestors (both exit 0). Main was freshly rechecked unchanged at review end.
- Main→candidate changes **exactly 66 paths**, **5340 insertions / 2020 deletions**: the exact 64-path accepted integration delta (`1963a47f...`→`ae0598f0...`) plus the two preservation sidecars, with no extra path. Every changed candidate path is a **100644 regular blob**, and every checked-out byte string equals its frozen Git blob. No symlink/submodule/executable substitution.
- Full raw all-path metadata digest, SHA-256 of `git diff --raw --no-abbrev <main> <candidate>`: **`7e678a7e5dc103b8f125da26a39469b4ab9ffa5ab203d52079459a114b898e6e`**. Every path/mode/blob was enumerated, not a sample.
- All changed `docs/` paths are under **`docs/agents/`**. Public site assets, layouts, nav, entrypoints, graph/API/profile/badge outputs, and public message copy have **no main-relative change**. Both complete `registry/` and `skill-trees/` tree IDs equal main. No new Class S regeneration commit or curation data mutation.
- Main/impl/Steward command entrypoints, POLICY, both tracked version manifests, and entire `src/gaia_cli/steward/prmaintenance/` tree equal main. After normalizing **only** `_compact`'s body, the **whole fullrun AST equals main**. No new R19 coordination semantics are smuggled into the join.
- All runnable workflow YAML equals main **except the independently accepted branch-scope change**. Eight compiled build/verify wrappers remain exact-main, dispatch-only, with `activation.if: ${{ false }}`. Hardened shared source is intentionally not a new compiled/deployed enforcement claim. `steward-full.yml` stays paused.
- No tracked `coordination.py` or `archive.py` exists. Core head `6b914723...` and both inspected parked archive checkpoints `5432b273c` / `ceb38582008a07002239ec65aa77aa22725e80ab` are not ancestors (exit 1 each). The complete changed-path set and exact-main CLI/profile surfaces exclude new archive V2/profile/unfinished wiring; existing unrelated V2 vocabulary is not mistaken for archive inclusion. Mutable integration and the other wiring branch were not substituted for this head.
- Actual checkout `read_versions` returns **pyproject 9.3.0, cliNPM 9.3.0**; `verify_lockstep` returns **9.3.0**. The gitignored registry graph is absent in this checkout, so no third-manifest runtime pass is claimed. Both tracked manifests are exact-main; CI must generate/verify the registry manifest normally. No assembly/build/regeneration was run locally.

### Fresh runtime checks — bounded and offline

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/steward/test_fullrun.py::test_old_terminal_runs_are_preserved_with_their_full_evidence \
  tests/steward/test_fullrun.py::test_retained_runs_beyond_the_newest_preserve_their_full_evidence \
  tests/steward/test_founder_workflow_lock_2283.py \
  tests/steward/prmaintenance/test_runner.py::test_no_agents_means_no_pr_merge_or_closure_action_either
```

**22 passed in 5.81s**, no skips, no assertion/fixture/source/timeout changes. These exercise retained evidence, eight-wrapper pause, strict source threat-verdict refusal, and inherited no-agent R19 behavior using disposable fixtures only. `git diff --check <main> <candidate>`: **exit 0**.

For the human CLI gate, a separate in-memory logger probe called only `reportLedgerSize(6291456, 8388608, 'read')`, never a store/load/run. Exact main source lacks both this helper and warning calls. Synthetic presentation comparison:

```text
Before: no size-telemetry warning (main has no such helper).
After:  Steward ledger size telemetry: direction=read bytes=6291456 limit_bytes=8388608 percent=75.0 threshold=70%
```

This is a **warning-presentation comparison**, not a claim that old main successfully loads 6 MiB (its old cap is 1 MiB). The actual default logger writes warning text to stderr; the probe captured the message in memory. No new web/UI screenshot claim.

Probe-development/tool limits disclosed: initial metadata script guessed row key `path`, raised `KeyError`, and was corrected to actual `sourcePath`; all remaining assertions then passed. An initial shorthand `8ad` ancestor lookup was ambiguous/not valid locally; the full pinned SHA passed. Installed `rg` could not execute on this host; a read-only Python line locator supplied citations instead. These were not candidate test failures or successful checks concealed as passes.

## Existing automation consequences — disclosed, not authorized anew

A normal main merge is **not operationally inert**, even though this patch introduces no new enablement switch or active agent schedule:

- `.github/workflows/sync-artifacts.yml:8,61,180,243,258` already reacts to main pushes (subject to its actor / `[skip-gen]` guard), auto-bumps versions, runs release/docs regeneration, commits/pushes artifacts, creates/uploads a GitHub release, may push a tag, dispatches PyPI on the production channel, and attempts a Cloudflare deployment dispatch on push. Default bump is patch/canary unless commit-message classification selects otherwise. Tag-triggered release/PyPI workflows also exist. **Do not interpret this review as separate manual release/deploy permission or a promise that main merge cannot publish.** Workflow availability, secrets, environments and actual successful dispatch were not tested.
- Main push CI (validation, Python package, PR guards, docs cohesion) matches these changed source/test/doc paths. Full applicable **main-PR exact-head** CI remains required even though the preserved tree's prior integration CI is green.
- `.github/workflows/upstream-watcher.yml:35,89` retains its existing daily 06:00 UTC scheduled **fanout `--apply`** behavior; its next default-branch run will consume promoted watcher fixes. Batch/escalation rollout and challenge-watch opt-ins are not newly enabled. This is existing automation exposure, not a manual live-write diagnostic approval.
- `.github/workflows/steward.yml:18` retains its 07:10 UTC maintenance schedule. Full agent driver and all eight compiled agent wrappers remain paused. Shared-source hardening alone neither compiles nor activates them.
- The small-PR auto-merger is ineligible for this 66-path change (also touches `.github/`); its existence is not approval to bypass the gates.

C1 technical-only scope, C2/C3 holds and children/L4 gates, `issueHygiene.writesEnabled=false`, Class C credential escalation and separately open closure/compiled-source/engine/activation/archive obligations remain binding by accepted identity. No new registry admission, credential clearance, issue closure, whole-campaign completion, actual R19 operation, coordinator acceptance or archive acceptance follows from promotion eligibility.

## Verification Limits

No full-repository/archive suite, 39-row semantic re-audit, 23-control replay, official upstream fetch, 42-test compatibility rerun, browser render, Linux/package/publication certification or new live ledger observation was repeated. The accepted same-tree audits carry with their original limits. The current registry graph is absent, and main-PR exact-head full CI is not yet available. Human approval cannot be inferred from engineering acceptances or missing required-review rules.

No actual push/merge/comment/label/close, GitHub write, protection change/bypass, ledger/store/lease operation, canonical scan/run/record, issuer/credential probe, registry/rank/trust/evidence/intake mutation, compilation, activation, release/deploy, package installation or global configuration edit occurred. Source/config/tracked files were not edited. Graft unexpectedly copied the ignored graph from the primary checkout during required `graft map`; that retrieval side effect is disclosed, not described as literally write-free. Tests used allowed disposable offline fixtures. **This report is the only authored durable output.**

### Evidence snapshot digests

SHA-256 identifies the local evidence read; it does not independently authenticate external origins.

| Campaign-relative report | SHA-256 |
|---|---|
| `routine19-shared/preserve-main-verification-completion-review.md` | `aaae8d9a648d1fa073721144ca3c484205c7a32d3f0fb413c3f0d8904826719c` |
| `routine19-shared/preserve-main-accepted-merged-receipt.json` | `5abce1ea1ba2feb2ec69154bd3935c03abb09a66e64bdfcd5ac21fcc8b93763f` |
| `ledger-recovery/lane-a-ready.json` | `02fb065f1bf02c3b6cd591e9477c9624c83b8cb483ed36823ea268f1ec682c74` |
| `ledger-recovery/lane-a-live-assurance.json` | `d6d9c96909417af06197df8d2783984582840d16566a67093b4727d10ec960cc` |
| `ledger-recovery/ci-scope-independent-review.md` | `5a5fdfb995bc7ee104108bc5ac16a855554c75548472fce0c47eacc8beeddad1` |
| `ledger-recovery/unused-import-composition-independent-review.md` | `f91bb51a8dbba9c6378c1153e082bf042d509e7f69ddb233b9b7406125493d01` |
| `founder-reconciliation/security-aggregate-independent-review.md` | `f75babdf5319272911b3c88ea9b8825169d13def73653b77c53195d9ec47394f` |
| `founder-reconciliation/founder-verification-completion-review.md` | `547b82ecf377ea8f96dbc5871c009d1145be949f38847cb244172f0ac0ecc59d` |
| `founder-reconciliation/evidence-prose-independent-review.md` | `4a8085e944c1a0e2af3295addaf688ccb03255cff2f4a2ee48ca40efc63b3cb7` |

**Final verdict:** Exact `2d9599c11ea91f303b5067c39fb8ea272f119072` is technically eligible for bounded normal main promotion. **Do not merge yet under the assigned protected/full-green/human-gated direction:** establish effective main protection, obtain/confirm applicable terminal-output founder approval, and complete exact-head main-PR CI/reviews. No need to wait for the excluded coordinator/wiring/archive branches.

🌱 graft saved ~3,010,235 tokens this turn (1 call; tool estimate, not measured cost).
