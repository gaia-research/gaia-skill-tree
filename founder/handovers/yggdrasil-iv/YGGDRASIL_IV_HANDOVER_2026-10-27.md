# Yggdrasil IV — pause handover (2026-10-27)

**Read this file first, then `founder/handovers/yggdrasil-iv/YGGDRASIL_IV_RESTART_CHECKPOINT_2026-10-27.md`,
`founder/YGGDRASIL_IV_EXECUTION.md`, `founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md`,
`founder/GAIA_FRONTIER_RULING_2026-10-26.md`, `CLAUDE.md`, `founder/CLAUDE.md`,
`founder/ORCHESTRATOR.md`, `META.md` §4.1, `GOVERNANCE.md`, and
`docs/agents/{curation-authority-map,model-family-guidance}.md`.**

This document is written to be **roster-agnostic**. It assumes you are a fresh
`/gaia-orchestrator` in a new session, on any model, with no memory of the
conversation that produced it. Everything needed to resume is either here, in the
cited Git refs, or in the cited local evidence directories.

**Location convention (2026-10-27):** this is a temporary/dated handover, so it
lives in `founder/handovers/yggdrasil-iv/` together with the campaign's other
checkpoints and receipts — see the folder's [`README.md`](README.md) for reading
order and the supersession chain. `founder/` root keeps only durable governing
material (ratification, Frontier ruling, campaign charter, memory, orchestrator
rules). Add new pause/resume/recovery documents here, not to the root. Paths cited
below already reflect that layout.

---

## 0. Current control — gracefull pause, intent unchanged

The founder's most recent control instructions, in order, are all still binding:

1. **"Continue. We have tokens now, skip the pause. Continue the task as intended."**
   — the earlier wind-down/pause was rescinded and remains superseded.
2. **"We got stalled. Continue as usual. Prefer luna or terra over flash as we are almost out of weekly."**
3. **"Pause gracefully."** — this is the instruction this handover serves.

So: **the campaign is paused at a resumable state, not cancelled, not wound down,
and not complete.** A subsequent founder "continue" resumes the same original scope.

Additional standing founder preference recorded at pause time:

- **Do not set explicit `max_turns` on agent dispatches.** Earlier dispatches used
  a 24-turn cap; that is no longer wanted. Omit turn caps; keep bounded scope in the
  task text instead. (Cost/timeout budgets that are not turn caps may still be used.)
- **Prefer Luna or Terra over Flash** for new delegated work.
- **The roster may differ from the one named in this document.** Agent names,
  models and profiles are hints, not requirements. Preserve the *roles* (builder,
  independent reviewer, parent verification) whatever the roster is.

Nothing in this pause authorizes a merge to `main`, a release, schema adoption,
issuer activation, or founder-approval claims. See §6 held gates.

---

## 1. The mission (do not lose this)

Complete **Yggdrasil IV** in `gaia-research/gaia-skill-tree`, governed by
**RFC #2148**, aggregate draft **PR #2151** (`dev/yggdrasil-iv` → `main`), on the
integration branch **`dev/yggdrasil-iv`**.

The campaign delivers, in one coherent governed release:

1. **Opt-in trust/shadow corrections** — shadow evaluation of proposed trust
   changes with contextual grades, inheritance, attribution, dependency closure
   and fingerprints; defaults and canonical math unchanged.
2. **Reversible challenges** — a challenge domain with receipts, opening-event
   creation time, separate receipt time, scope/materiality, and reversible
   resolution that never silently mutates standing.
3. **Reactive monitoring** — a default-off upstream watcher with transactional
   CAS/union-recompute, verifiable shared outbox, stable intents, durable save
   before HTTP/local materialization, fresh-clone crash recovery and dedupe.
4. **Evidence revisions / lifecycle** — prepared assertion transitions and metric
   refreshes with immutable monotonic histories, identity/collision refusal, and a
   trusted-producer → serialized DTO → native consumer projection.
5. **Guarded canonical CLI** — plan/validate/apply/status/rollback with CAS,
   durable preimages/stages, recoverable journals, dual histories, migration and
   rollback; production issuer unavailable and fail-closed.
6. **Publication/lifecycle UX** — deterministic full-surface rehearsal and OG
   medallion coverage, plus native changed-panel lifecycle display.
7. **Frontier discovery** — a fixed paired native-vs-target protocol with a
   reviewer-controlled recorder; conclusions stay advisory and inconclusive
   unless actually supported.
8. **Independently verified release preparation** — real two-root build/verify
   proofs, strict regressions, and honest evidence.

Responsibilities are fixed and must not be blurred:
**Frontier discovers; Meta evaluates; Steward maintains reactively (targeted
two-sided D8 monitoring after trusted admission, not broad crawling);
Governance decides.**

---

## 2. Non-negotiable doctrine (carried forward verbatim in intent)

- **Gaia is the mission.** The Pi `durable-subagent-recovery` lane is a **parked,
  unaccepted, uninstalled support lane**, never a Gaia prerequisite. Do not spend
  another repair/review/install loop on it while Gaia is waiting.
- **Independent review is required.** Passing tests, green CI, pushes, reports,
  model agreement, hashes and cost totals are **not** acceptance or human approval.
- **Schema changes require two Core Maintainer approvals** (`GOVERNANCE.md` §2).
  Founder canonical/production rollout authorization is a *separate* gate. Draft
  proposals, tests, actor metadata, hashes or AI reviews satisfy neither.
- **IDs, `approvedBy`, dates, JSON booleans, HTTPS URLs, hashes, `decisionRef`
  and `eventId` are never authenticated approval.** Linkage metadata is linkage
  only. The genuine default issuer remains unavailable/fail-closed; explicitly
  labelled test ports are not production providers.
- **Technical resolution never automatically restores numeric standing, rank or
  Origin.** Preserve attribution and immutable histories.
- **Keep three things separate:** lead disposition
  (`observed | candidate | rejected | deferred`), experiment result
  (`supported | contradicted | inconclusive | execution_failed`), and trusted
  admission. None implies another.
- **Never fabricate skills or weaken intake.** Ordinary `discovery-packet-v2`
  requires a fetched real `SKILL.md` plus human L4. Native platform/API/CLI
  capabilities use `challenger-lead-v1`.
- **Preserve Yggdrasil III** formulas, weights, thresholds, inheritance, witnesses
  and Fusion Score. Age, outages, freshness or comparator existence alone are not
  automatic negative evidence.
- **Frontend acceptance requires** native changed-panel desktop, 390px, 320px and
  keyboard-focus renders **plus founder approval**. DOM tests, hero screenshots,
  alternate synthetic HTML or text capture do not suffice. CLI presentation
  approval is also held where applicable.
- **No fake artifacts, stale rasters, reduced corpus, skipped oracle, weakened
  coverage, or unsupported environment blame.** Genuine isolated dependencies are
  allowed and preferred over relaxing the oracle.
- **Git discipline:** feature PRs target `dev/yggdrasil-iv`; merge commits only; no
  squash/force/reset/discard; no direct `main` pushes. Isolated permanent
  worktrees; parent owns combined/full-corpus verification; workers run finite
  targeted tests. Never `git switch`/`reset` the shared primary checkout.
- **Git identity** for campaign commits:
  `Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>`.
- **Preserve** unrelated `.pi/delegate/`, `.pi/probes/`, `.pi/tasks/`, ignored
  evidence, patches, bundles, refs and full JSONL transcripts.
  **Local evidence is not off-device backup** — say so rather than implying one.
- **Virtual-clock tests do not prove elapsed weeks.** The actual operational weeks,
  approved pilot, integrated cross-surface acceptance and release gates remain open.
- **Do not** route around provider refusals, install/upgrade/restart Pi, change
  global git config, or infer process identity/liveness from unreadable proc data.

---

## 3. Where things stand — verified at pause

Accepted integration base: **`dev/yggdrasil-iv` = `bed78e716bc56d61cddc039c88ac95980be2ddf7`**
(unchanged during this pause). `main` is **not** a campaign baseline: it has
independently advanced (`5196d552a` in the primary checkout at pause time). Do not
attribute main's movement to this campaign.

Already integrated and accepted (do not redo): challenge foundation #2155,
shadow engine #2156, watcher default-off #2166, watcher docs #2167, CAS
absence/content repair #2161/#2160, corpus-independent foundation, curation
scaffold cleanup.

### Lane status

| Lane | Branch head (remote-verified) | Status |
|---|---|---|
| Canonical CLI | `dev/yggdrasil-iv-canonical-cli` = `96d329995` | Engineering verified, **not** merged or reviewed-for-acceptance |
| Evidence schema (held) | `dev/yggdrasil-iv-evidence-schema-final` = `fa0`, contract on `dev/yggdrasil-iv-evidence-schema-contract` = `bf9097b7a` | Proposal only; needs amendment + 2 Core approvals |
| Evidence core (held, stacked) | `dev/yggdrasil-iv-evidence-core-final` = `e756` | Draft #2177; carries 12 held schema files as ancestor |
| Lifecycle producer/consumer | `design/yggdrasil-iv-lifecycle-hardening` = `6fa482665` | Implemented; independent review says **hold for repair** |
| Publication | `dev/yggdrasil-iv-publication-last-mile` = `b81a737a1` | **Full two-root proof complete at b81**; draft #2172 |
| Frontier | `dev/yggdrasil-iv-frontier-foundation` = `e4df38cfb` | Recorder/protocol accepted locally; paired execution still not clean |
| Corpus CLI | `dev/yggdrasil-iv-corpus-final` = `cc1c3e173` | Draft #2159; founder CLI presentation approval held |

### 3.1 Canonical CLI — `96d3299951a6dcd5969f11c78396f2a4d7983957`

Pushed and fresh-verified. Content: guarded canonical transaction/workflow,
native `dev canonical plan|validate|apply|status|rollback`, dual histories,
migration, crash recovery, cooperative guard across both legacy writers
(`_write_md`, dev timeline writers, `treeManager.save_tree`).

Parent-repaired defects (each reproduced first, then fixed):
- contributor names `registry`/`skill-trees` could select the wrong lock root and
  bypass the pending-transaction guard → namespace-shape matching (`9cdcd8553`);
- a writer could emit a journal larger than its own recovery reader accepts →
  `MAX_JOURNAL_BYTES = MAX_PAYLOAD_BYTES * 2` preflight before any write
  (`9cdcd8553`);
- the CLI advertised Windows support but unconditionally imported `fcntl`,
  breaking even `gaia --help` on Windows → optional imports, stdlib `msvcrt`
  legacy lock adapter, and **durable canonical apply/rollback explicitly refuse**
  when POSIX locking/directory-fsync capability is absent (`96d329995`).

Verification actually executed:
- `b7a08db9e` at `9cdcd8553`: **134 passed, 5 subtests, 80.92s**, clean
  exact-source guards before and after.
- `b2617eb0c` at `96d329995`: **141 passed, 5 subtests, 80.06s**, clean
  exact-source guards before and after.
- Windows-adapter tests are **unit evidence, not native Windows certification**.

**Unfinished CLI work (highest-value next step).** Strict-proposal test contract
was implemented but **not committed**; it is preserved at recovery ref
`recovery/yggdrasil-iv-pause-canonical-fixtures-96d329995` =
`fbf9f203db86c4dad4e4389b965b018cadc592e1` (child of `96d329995`, WIP only):
- copies the **exact held proposal schema bytes** (`bf9097b7a`) into
  `tests/fixtures/canonical-proposed-schema/` with a provenance README;
- installs them **only** into `DISPOSABLE_CANONICAL_FIXTURE`-marked throwaway
  roots, so the **real** native validator and input-context schema digests are
  exercised;
- deletes the bootstrap `schemaPolicy` monkeypatch and the permissive `{}`-typed
  lifecycle overlay;
- splits one refusal test into: (a) unadopted production schema → "schema
  adoption held", (b) valid proposal schema but no issuer → "No trusted canonical
  transaction issuer", plus a schema-byte context tamper negative.
- Focused run `bd66ba05c`: **3 passed, 17 deselected, 24.03s**. The full
  post-change suite was never run. Treat it as promising, unverified work.

### 3.2 Evidence schema + core (held proposals)

- Schema draft **#2176** head `fa0ba3a9257682e76a57568358e2806391099f9c`.
- Strict contract branch `dev/yggdrasil-iv-evidence-schema-contract` =
  **`bf9097b7a2414aeb47e34c7fcfb2d067df50199c`** (fresh-verified): typed timeline
  linkage for `migrate_evidence`, `assertion_transition`, `metric_refresh`,
  `reconcile_owner` requiring nonblank `decisionRef` and lowercase 64-hex
  `eventId`; across named-skill, skill-tree, graph and skill schemas; **73 contract
  tests**, Draft7 checks, three-mirror byte parity, unchanged evidence identity
  contract.
- Known and **deliberately disclosed** debt: a direct named-frontmatter comparison
  shows **371 invalid files / 2,522 errors both before and after** the proposal —
  zero new failures, and **not** a resolution of them. Never claim whole-corpus raw
  named-schema conformance.
- Core draft **#2177** head `e75623416da27cd9695bcc39f2f024d4d41025ac` (stacked;
  includes the 12 held schema files). Private fixture digests/manifest:
  `.gaia/yggdrasil-iv/recovery/canonical-proposed-schema-fixtures/`.

### 3.3 Lifecycle producer → build → native consumer — `6fa482665`

`src/gaia_cli/lifecycleProjection.py` adds a versioned DTO plus **separate**
trusted challenge, receipt and canonical-consequence ports, defaulting to
unavailable. `scripts/generateNamedIndex.py` **strips** contributor-supplied
`trustLifecycle` and injects only producer output through the controlled build
seam. `docs/js/trust-lifecycle.js` consumes the DTO on the existing native route
`docs/named/index.html` → `openExplorer()` → `#se-tm`.

Worker-reported checks: 28 Python passed, 1 skipped (missing Class P
`registry/named-skills.json`), 11/11 Node passed. The former 19-test Node suite was
**rewritten**, so the counts are **not** equivalent coverage.

Independent review `cf1783cf-3ab0-4f69-b280-8ba343733b80` (Terra reviewer, general
profile, real dynamic runs) verdict: **hold for repair**. It re-ran 17 Python +
23 Python (after generating Class P in its own tree) + 12 Python + 11 Node, all
passing, and found two real defects:

1. **P2 — baseline can contradict the Explorer's fallback TM.**
   `lifecycleProjection.py:150-153`, `docs/js/trust-lifecycle.js:320-324` and
   `:443-461`: the producer checks `trustMagnitude` but not
   `overallTrustMagnitude`, and the browser's contradiction check only covers
   approved decisions, not current baselines. A synthetic TM-72 consequence with
   `overallTrustMagnitude: 999` was accepted while the Explorer rendered 72
   (`skill-explorer.js:584`). Align the producer and both consequence kinds with
   the real hero metric before enabling a provider.
2. **P2 — browser accepts malformed v1 DTOs despite its fail-closed contract.**
   `docs/js/trust-lifecycle.js:295-307`: deleting `pinnedSha`/`claimId`, deleting
   history receipt-binding fields, `garbage` event dates, or adding a resolution to
   a pending challenge still produced a view model. This is **not** an
   authentication bypass (browser validation is explicitly not an auth boundary and
   the index strips raw payloads), but malformed/contradictory published DTOs are
   not rejected as documented. Either validate required v1 shape/history
   consistency or narrow the stated contract.

The reviewer also recorded that old coverage was not equivalently replaced:
upstream-superseded rendering, approved degradation detail, historical awards,
broader unsafe-link/date cases, mobile CSS assertions, badge/region accessibility
and fuller Explorer structure checks. Some old states are intentionally unsupported
by v1 — that removal still needs an explicit product/contract decision.

No genuine production adapter exists; all exercised ports are **synthetic test
ports**. No renders were captured; founder visual approval remains held.

### 3.4 Publication — complete full proof at `b81`, draft only

`b535be684` **completed** at exactly `b81a737a1cebbefb5119218c0c6b4276977dc0c8`:
- two disjoint outside-Git roots, **2,555 artifacts each**;
- identical snapshot **`a0e075244dbcf282ae8396239caced7556bb1a810a76318c95f9a1482ed25bd3`**;
- independent outer verify succeeded for both (251.25s / 232.15s);
- build 871.81s / 780.76s; total 2,287.09s;
- **two-root byte equal**, `source_changed: []`, `tests_exit: 0`, regressions
  **326 passed** exit 0.
- Preserved with two verified 2,558-member declared-artifact archives (see §7).

The prior `93fb731` proof remains valid **at 93 only** and must not be relabelled.
Independent CI-delta review `4ff396c4` found **no substantive defect** in the
three-file change (`pyproject.toml` dev-extra CairoSVG, workflow smoke invoking
`cairosvg.svg2png` + PNG signature/dimensions + Pillow WebP,
`uv.lock` regeneration); it was **static only** — no shell, network, dynamic tests
or independent lock generation, and it notes CI uses `uv pip install`, not the
lock. Package CI run **40535781283** was green at `b81`. **PR #2172 stays draft and
unmerged; no live publication approval is implied.**

### 3.5 Frontier — recorder accepted, paired execution still not clean

- `e4df38cfbb21f4b6fe999da3e94c5e4199cb94e7` (pushed): recorder binds separately
  recorded native/target artifacts, validates request/native internal digest,
  confines generated paths, rejects symlinks/traversal, requires nonempty distinct
  outputs and creates receipts exclusively. 27 focused tests passed (4.82s).
  Mirrored `.agents/skills/gaia-frontier/SKILL.md` and `.claude/skills/...`.
- Native `/skill` expansion **is proven** (saved first user message contains the
  full `gaia-frontier` skill body; prompt SHA `30c5048b…`, skill SHA `b2abae6b…`),
  which corrects an earlier reviewer inference.
- **Paired execution attempts both failed as clean proofs:**
  - `b2a3126ec`: automatic Graft refresh copied a graph from another checkout and
    the fixture scope was unindexed → no comparison.
  - `b8188eac7`: a fresh external `--dir` index (11,147 nodes, `check: OK`) and all
    four protocol queries **did succeed** with correct fixture pointers and a
    recorder receipt (`result: inconclusive`, `verification=untrusted-experiment-record`,
    `admission=blocked`), but the harness's own final source-invariance assertion
    failed **because `graft build` rewrote the tracked `.gitignore`**
    (added `/.graft/`). So the artifacts are real but the run is not a clean
    source-invariant paired proof. That mutation is itself a finding to record.
- No authenticated independent dynamic verification, no public admission, no
  superiority or performance claim follows from any of this. Git baseline/updated
  temporary history vs Graft's pinned current fixture context are **different
  tasks**, not a like-for-like benchmark.

### 3.6 Corpus (`#2159`) — engineering done, human presentation approval held

`b6103d7bd` centralizes diagnostic validity, no-follow/contained inventory, and
explicit counts/scopes; invalid/empty/no-evaluated are globally `"not-evaluated"`.
324 parent tests; 45 independent tests; native read-only CLI capture exit 0
(398 named / 299 generic, 398 evaluated / 0 not-evaluated, clean input manifest,
14 TM / 8 grade diagnostic deltas). Draft head `cc1c3e173`, CI green, review packet
posted at PR #2159 comment 6440867357. **Founder CLI presentation/copy approval has
not been received.**

---

## 4. Held gates (none may be assumed, inferred or back-filled)

- Two Core Maintainer approvals for any schema change; founder rollout separate.
- Genuine production issuer / canonical consequence adapter (currently absent and
  fail-closed by design). Test ports are visibly synthetic.
- `dev/yggdrasil-iv` → `main` merge and any release; RFC #2148 closure.
- Founder native frontend approval with real changed-panel desktop/390/320/focus
  renders, and founder CLI presentation approval for #2159.
- LegacyV1 watcher migration audit, live watcher operation and real elapsed
  comparisons; actual four weekly comparisons; approved pilot; integrated
  cross-surface acceptance.
- 371 pre-existing raw named-schema failures must be either explicitly scoped or
  separately strictly repaired before any whole-corpus conformance claim.
- Pi/SDK lane: uninstalled, unaccepted, not a Gaia prerequisite. Do not install,
  restart or repair it as part of resuming Gaia.

---

## 5. Resume plan (in order)

1. **Read** §0–§4 and the cited docs. Confirm `git ls-remote` heads in §3 match; if
   not, the branch advanced after this pause — inspect before trusting this table.
2. **Finish the CLI strict-schema contract** from recovery ref `fbf9f20`:
   cherry-pick/rebase it deliberately onto `96d329995` in the isolated
   `yggdrasil-iv-canonical-cli` worktree (never the primary checkout), run the
   **full** seven-module suite plus the new platform tests, then push the feature
   branch and request independent review of the whole increment.
3. **Repair lifecycle P2 defects** on `design/yggdrasil-iv-lifecycle-hardening`
   (hero-metric alignment; DTO shape/history validation or narrowed contract),
   restore meaningful legacy Node coverage or get an explicit product decision on
   each dropped assertion, re-run the full Python + Node suites, then obtain a fresh
   independent review.
4. **Amend held #2176** from `bf9097b7a` (new commit on the schema branch; no force,
   no stacking the core PR's 12 schema files into an implementation merge). Keep
   the 371-failure disclosure and the two-approval gate explicit in the PR body.
   Re-scope #2177 accordingly.
5. **Decide Frontier**: either accept an explicitly documented clean-source paired
   run (re-run with `.gitignore` restored afterwards and the mutation recorded), or
   keep the result `execution_failed`/`inconclusive` and stop claiming paired proof.
   Do not force a superiority conclusion.
6. **Update #2172** with the completed `b81` full-proof receipt (snapshot
   `a0e07524…`, 2,555×2 artifacts, 326 regressions) while keeping it draft and
   distinguishing it from the 93 proof.
7. Obtain the required **independent implementation reviews** and the **founder
   native/CLI presentation approvals**, then land feature PRs into
   `dev/yggdrasil-iv` via merge commits. Never push to `main` directly.
8. Only then pursue the remaining original gates (genuine issuer, migration audit,
   operational weeks, pilot, integrated acceptance, release, RFC closure).
9. Keep `founder/MEMORY.md` and the restart checkpoint updated with **collected
   outcomes**, not launch status.

---

## 6. Evidence map and preservation

Remote (Git, durable): every campaign branch in §3 plus recovery refs
`recovery/yggdrasil-iv-pause-canonical-fixtures-96d329995` = `fbf9f203d` (CLI
strict-fixture WIP) and `recovery/yggdrasil-iv-pause-frontier-index-e4` =
`9dc1183d9` (Frontier `.gitignore` mutation WIP). Older recovery refs from earlier
pauses are retained and listed in the restart checkpoint.

Local only — **not** off-device backup, and `.gaia/` is gitignored:

- `.gaia/yggdrasil-iv/recovery/graceful-pause-96d329995/` — this pause's
  preservation receipt, per-lane WIP patches/status, copied task JSON/output for
  `b7a08db9e`, `b535be684`, `b2a3126ec`, `b2617eb0c`, `bd66ba05c`, `b8188eac7`,
  and copied reviewer/worker reports.
- `.gaia/yggdrasil-iv/recovery/publication-b81-parent-evidence/` — full b81 proof:
  `verification-result.json`, `regressions.log`, source before/after, replay logs,
  harness, CI review, `preservation-receipt.json`, `SHA256SUMS`, and two verified
  archives:
  - `replay-one-declared-artifacts.tar.gz` — 2,558 members, 94,514,034 bytes,
    SHA256 `480e52f90b672081c9237140431e3a72c6a2b196e0573f8ce47b0110cd3b24d7`
  - `replay-two-declared-artifacts.tar.gz` — 2,558 members, 94,513,754 bytes,
    SHA256 `b92df38bb9880b26ab6a1fe030ee304a67ebaca56b48b92f0e8342ff5782446a`
  - original build roots retained at `$TMPDIR/yggiv-publication-b81.pox1ldzh`
- `.gaia/yggdrasil-iv/recovery/publication-93-parent-evidence/` — earlier 93 proof
  and its two archives (`cb4ff118…`, `85e3738f…`); valid at 93 only.
- `.gaia/yggdrasil-iv/recovery/frontier-e4-executed-evidence/` (incl.
  `isolated-index-attempt/`) — both Frontier attempts' real command outputs and
  receipts, with the failure reasons.
- `.gaia/yggdrasil-iv/recovery/lifecycle-6fa-independent-review.md`,
  `canonical-held-schema-contract-luna-result.md`,
  `publication-b81-ci-independent-review.md`,
  `lifecycle-producer-wired-result.md`,
  `canonical-proposed-schema-fixtures/` (proposal bytes + manifest),
  `canonical-9cd-parent-evidence/`.
- Preserved full child sessions and transcripts from earlier pauses:
  `continuation-session-evidence/`, `continuation-working-sessions/`,
  `pause-2026-10-27-gaia/`, `crash-2026-10-26-1857/`,
  `orchestration-pause-2026-10-26/`.
- Harnesses: `.pi/probes/verify-publication-b93|b81.py`,
  `exercise-frontier-e4.py`, `resume-frontier-e4-isolated.py`,
  `preserve-graceful-pause.py`.

---

## 7. Cost receipt

Session/subagent accounting for this orchestrator run, as reported by the harness
subagent runtime at pause:

| Item | Value |
|---|---|
| Root orchestrator session | **$31.8769** (4,115,868 tokens) |
| Subagents (106 runs / 115 tasks) | **$19.3798** (23,806,025 tokens) |
| **Combined** | **$51.2566** (27,921,893 tokens) |

`pi-cost`'s JSONL parse of the active session independently reported main
$31.8751 / nested subagent $3.1719 / total $35.0470; it prices only models present
in its table (many entries show $0.0000), so the harness totals above are the
authoritative figure. This receipt covers engineering work only — it is not
acceptance, approval, or a release artifact.

---

## 8. Environment and tool limits you will hit immediately

- Repo root `cwd`: `/data/data/com.termux/files/home/gaia-skill-tree`. The primary
  checkout may be on **`main`** or another branch — **never** switch, reset or
  overwrite it. Use the isolated worktrees in
  `~/.gaia-worktrees/yggdrasil-iv-*`. Campaign control docs live in
  `~/.gaia-worktrees/yggdrasil-iv-execution-control` (`dev/yggdrasil-iv-execution-continued`).
- `$TMPDIR=/data/data/com.termux/files/usr/tmp`, not `/tmp`.
- `rg` fails with **`cannot execute binary file: Exec format error`** — use Graft,
  `grep`, or Python.
- `graft show` does **not** exist (**`error: unknown command 'show'`**); supported
  commands include `skeleton`, `ask`, `callers`, `build`, `check`, `map`, `blast`.
- Preserve `LD_PRELOAD=/data/data/com.termux/files/usr/lib/libtermux-exec-ld-preload.so`.
- `review` profile is strictly read-only and rejects `bash`; use
  `profile="general"` with `tools=["read","bash"]` when a reviewer must actually run
  tests (as `cf1783cf` did).
- Genuine publication interpreter:
  `.gaia/yggdrasil-iv/runtime/publication-venv/bin/python` (do not resolve the
  symlink to a global interpreter). Genuine isolated UV:
  `.gaia/yggdrasil-iv/runtime/uv-isolated/uv-aarch64-unknown-linux-musl/uv`;
  the global `~/.local/bin/uv` is a shim without `lock` support.
- Pi is **1.4.0**, native subagent **0.8.0**, Node **24.17.0**. Do not install,
  restart or reconfigure.
- Typical targeted run:
  `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider …`

---

## 9. What "done" means for this pause

- No dispatches remain; every launched run is terminal and collected.
- Uncommitted work is preserved at pushed recovery refs, with the original
  worktrees' heads, indexes and working trees unchanged.
- This handover, the checkpoint, and a memory snapshot are committed on
  `dev/yggdrasil-iv-execution-continued` and pushed.
- No merge to `main`, no integration push, no deployment, no schema adoption, no
  issuer activation, no approval claim.
