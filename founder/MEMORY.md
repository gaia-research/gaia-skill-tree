# Orchestrator Memory

Maintained by the Orchestrator agent. Newest entries first within each section.

## State Snapshot (2026-06-22, session 16 — Epic #780 Architectural Modernization Kickoff)

### TLDR

- **Epic #780 execution is well underway.** Sub-Issues 1, 2, 2b, and 4 are fully merged and verified on the integration branch `dev/improve-codebase-architecture`. 
- **Sub-Issue 2 Dynamic Dispatch Completed**: `main.py` is refactored from a 4,000+ line module into dynamic autodiscovery class-based commands, shrinking it to 130 lines. Overwriting of the global `__name__` during impl imports was fixed.
- **All 1,191 tests pass**: Full pytest validation run is 100% green.
- **GitHub Curation**: Posted progress comments on all Sub-Issue tracking issues (#781, #782, #783, #784, #785) via `gh` CLI.
- **`gaia trust` preserved**: The command remains a first-class, top-level non-deprecated entry.

### Branch / PR Snapshot

All work is merged back into `dev/improve-codebase-architecture`. Squash merges are disabled. Frequent commits with `[skip-gen]` are enforced.

| Branch | Issue | Focus | Status |
|---|---|---|---|
| `dev/780-cli-command-migration` | #NEW | Move dev commands under `gaia dev`, add deprecation shims, update CI yaml files | ✅ Merged & Verified |
| `dev/780-artifact-pipeline` | #781 | Untrack generated indices from Git, configure upload of built assets to GitHub Releases | ✅ Merged & Verified (issue closed) |
| `dev/780-skill-quality-gates` | #784 | Run skill schema validations and enforce body size limit (<= 800 lines) in CI gates | ✅ Merged & Verified (issue closed) |
| `dev/780-cli-dynamic-dispatch` | #782 | Refactor 4,078-line `main.py` into dynamic command autodiscovery using Command Protocol | ✅ Merged & Verified (issue closed) |
| `dev/780-dev-decompose` | #786 | Decompose 2,977-line `commands/dev.py` into domain sub-modules (`commands/dev/` package) | ⏳ Pending (Sub-Issue 2c) |
| `dev/780-polyglot-versioning` | #783 | Rename `ensure_versions_in_sync` → `verify_lockstep`, add CI gate, create Taskfile | ⏳ Pending (Sub-Issue 3) |
| `dev/780-mcp-abstraction` | #785 | Implement config merger utility, daemon process runner, and `gaia dev mcp` CLI subcommands | ⏳ Pending (Sub-Issue 5, minimal scope) |

### Routing — where things live now

| Document / Tool | Path |
|---|---|
| Active Integration Branch | `dev/improve-codebase-architecture` |
| Implementation Plan | [implementation_plan.md](file:///Users/marcotiongson/.gemini/antigravity-ide/brain/8634f4ce-4000-4565-b150-81fc921ae0ae/implementation_plan.md) |
| Checklist Task List | [task.md](file:///Users/marcotiongson/.gemini/antigravity-ide/brain/8634f4ce-4000-4565-b150-81fc921ae0ae/task.md) |
| Interactive HTML Report | [EPIC780.html](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/reports/EPIC780.html) |
| Revert Playbook | [EPIC780_REVERT.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/EPIC780_REVERT.md) |
| Agent Testing Guide | [EPIC780_AGENT_TESTING.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/EPIC780_AGENT_TESTING.md) |
| Deprecation Shim Runbook | [EPIC780_DEPRECATION_CLEANUP.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/EPIC780_DEPRECATION_CLEANUP.md) |

---

## State Snapshot (2026-06-20, session 15 epilogue — 5.0.0 shipped, /trust nav + MAG=0 fixed, Phase 1 fully closed)

### TLDR

- **GAIA 5.0.0 IS LIVE.** PyPI gaia-cli==5.0.0 published (workflow_dispatch run 27845809253, 37s success). GitHub release page live at https://github.com/mbtiongson1/gaia-skill-tree/releases/tag/v5.0.0. Tag `v5.0.0` at commit `13fd104f`.
- **Two web bugs fixed in same release PR**:
  - **MAG=0 on plaques** — `_wireTrustNotches` was registered on `window` but never called from live render paths (`named-skills.js`, `page-ia.js`). Static template emitted literal `MAG <span>0</span>`. Fix: emit real magnitude as initial textContent (works WITHOUT JS), wire `_wireTrustNotches` at all 3 live render sites, fix `onLeave` to restore real value (was bouncing back to 0).
  - **/trust/leaderboard/ Home link broken** — `docs/js/site-nav.js` MOUNTS list missing `trust`. Depth defaulted to 0, root='', Home resolved to non-existent `/trust/leaderboard/index.html`. Fix: add `trust` + `api` (forward-thinking for Sprint B) to MOUNTS.
- **Release PR #763 merged** at `df3e40da` (merge-commit, never squashed). Phase 1.5 milestone (#8) remains closed. Sprint A milestone (#9) carries the close-out tasks.
- **PyPI auto-trigger on tag push failed** with HTTP 400 "filename was previously used by a file that has since been deleted" — a 5.0.0 wheel had been uploaded then yanked at some prior point. Marco rescued via manual `workflow_dispatch`. Lesson: when `gh` pushes a tag and the auto-publish 400s, the manual dispatch path is the recovery.
- **CHANGELOG.md established** as the canonical changelog going forward. 5.0.0 is the first entry.

### What changed this session (epilogue turn)

| Layer | State |
|---|---|
| Version manifests (4 in lockstep) | ✅ all at 5.0.0 (`pyproject.toml`, `packages/cli-npm/package.json`, `packages/mcp/package.json`, `registry/gaia.json`) |
| PyPI gaia-cli | ✅ 5.0.0 published (manual workflow_dispatch after tag-trigger 400'd) |
| GitHub release page | ✅ v5.0.0 published, target=main |
| npm `@gaia-registry/cli@5.0.0` | ⏳ **Marco's manual call** — runbook §9 (`cd packages/cli-npm && npm publish --access public`) |
| npm `@gaia-registry/mcp-server@5.0.0` | ⏳ **Marco's manual call** — runbook §9 (`cd packages/mcp && npm run build && npm publish --access public`) |
| CHANGELOG.md | ✅ established with 5.0.0 entry |
| MAG=0 plaque bug | ✅ fixed in `docs/js/plaque.js` + `docs/js/named-skills.js` + `docs/js/page-ia.js` |
| `/trust/leaderboard/` nav Home | ✅ fixed in `docs/js/site-nav.js` (added `trust` + `api` to MOUNTS) |

### Branches at end of session

| Branch | Head | Status |
|---|---|---|
| `main` | `df3e40da` (Merge #763 — release: 5.0.0 + bugfixes) | latest; 5.0.0 lockstep complete |
| `cli/v5.0.0-release` | merged | auto-deleted on merge |
| `dev/phase-1.5-inspection` | local only (`f1822ea2`) | stale; safe to delete locally |

### Issues + PRs touched this session

| # | Type | Title | State |
|---|---|---|---|
| 763 | PR | release: 5.0.0 — Phase 1.5 G7 Trust Infrastructure + MAG=0 plaque fix + /trust nav fix | ✅ MERGED at `df3e40da` |
| 742 | PR | Phase 1.5 consolidation → main | ✅ MERGED at `4dd4e945` (prior turn) |

### Routing — where things live now

| Artifact | Path |
|---|---|
| Live release (PyPI) | `pip install gaia-cli==5.0.0` |
| Live release (GitHub) | https://github.com/mbtiongson1/gaia-skill-tree/releases/tag/v5.0.0 |
| Pending: npm cli + mcp | `packages/cli-npm/`, `packages/mcp/` (manual `npm publish` from each) |
| CHANGELOG (canonical) | `CHANGELOG.md` (repo root) |
| Trust notch animation hook | `docs/js/plaque.js::_wireTrustNotches` (must be called after every plaque innerHTML write) |
| Site nav MOUNTS list | `docs/js/site-nav.js:20` — add new top-level mount names here |
| Roadmap v3 active | `founder/GAIA_ROADMAP v3 (BUILD).md` |
| Sprint A close-out tasks | issues #759, #761, #746, #739 |
| Sprint B implementation order | `founder/handovers/API_PLATFORM_DESIGN_2026-06-20.md` Day 1–13 |
| `/memory-snapshot` skill | `.claude/skills/memory-snapshot/SKILL.md` (used for the first time this turn) |

### Lessons / hazards preserved for next orchestrator

1. **PyPI tag-trigger 400 on filename-reuse is recoverable.** Don't panic — the workflow file is fine; PyPI just blocks reupload of any filename that ever existed. Manual `workflow_dispatch` from Actions tab works (it builds whatever version is in `pyproject.toml` at the selected ref). Only fails if you actually need the SAME version number twice — bump to next patch otherwise.

2. **`window._wireTrustNotches` must be called after EVERY `grid.innerHTML = ...`** in the named-skills render pipeline. The fix wired it at three sites; new render paths added in Sprint B (the API documentation page, semantic search results) MUST also call it or MAG will silently revert to 0. Pattern: any time you `innerHTML = ...something with plaques...`, immediately follow with `if (typeof window._wireTrustNotches === 'function') window._wireTrustNotches(<container>);`. Better: extract a `renderInto(container, html)` helper that bundles both.

3. **`docs/js/site-nav.js` MOUNTS list is the registry of top-level URL prefixes.** When adding a new mount (e.g. `/api/v1/` for Sprint B, `/trending/` for B2, `/heroes/` for B3), edit `MOUNTS` first or every link on those pages will break the depth calculator. Already added `trust` + `api`; Sprint B should add `trending` and `heroes`.

4. **`gaia release major --sync` pushes the tag DIRECTLY to origin** without going through a PR. The version-bump commit lands on the local feature branch, and a separate PR carries it to main. Don't be surprised when origin/main hasn't moved post-release — it hasn't, the PR is what brings it in.

5. **CHANGELOG.md didn't exist before 5.0.0.** Established this turn. From now on every release MUST add an entry; the runbook step 4 is no longer "create if missing".

6. **The release runbook is still accurate** — `founder/handovers/RELEASE_5.0.0_RUNBOOK.md` step-for-step matched reality, except for the PyPI 400 recovery (now documented above as Lesson #1). Worth porting back into the runbook before the 5.1.0 release.

### Open questions for next orchestrator (Sprint A continuation)

- **npm publish for `@gaia-registry/cli@5.0.0` and `@gaia-registry/mcp-server@5.0.0`.** Marco said "byebye" — he didn't ask for npm. Defer to him. Steps in runbook §9.
- **Cloudflare Pages deploy** of the new `docs/` artifacts. Auto-deploy should fire on the PR #763 merge; verify gaia.tiongson.co/trust/leaderboard/ Home link works post-deploy + skim a plaque to confirm MAG renders correctly.
- **#739 (cp1252 glyph fix in `gaia dev timeline`)** is now in Sprint A milestone. Marco's call when to address.
- **#746 §11.12.1 (≥5 A-graded origins) + §11.12.7 (tenure ≥ 180 days)** still pending on top-4 S skills. Tenure resolves itself by ~2026-09-15. A-graded origins need targeted curation.

### Token cost (this session — epilogue turn only)

| Bucket | Spend |
|---|---|
| Session 15 cumulative (entering this turn) | ~$33.85 |
| This epilogue turn (release runbook + bugfixes + merge) | ~50k in / ~32k out / **~$3.10** |
| **Session 15 cumulative (final)** | **~$36.95** |
| **G7 cumulative (sessions 11→15)** | **~$64.42** |

### Marco's framing

> *"execute release runbook and byebye!"*
> *"quick patch needed on gaia website-- skills show 'MAG 0' instead of 'MAG XXX'"*
> *"fix nav bar on trust leaderboard--clicking home doesnt go anywhere"*
> *"merge and loop after green ci"*

All four directives executed. Session 15 closes; Phase 1 fully closed; Sprint A is the next ratchet.

---

## State Snapshot (2026-06-20, session 15 FINAL — Phase 1 closed, ready to merge)

### TLDR — the celebration entry

**Phase 1 of GAIA is closed.** PR #742 merges into main with the final two CI reds resolved. Marco's call: *"Final watch on CIs, two failures. Quick fix maybe? i'm tired, lets finalize!"* Done.

- **CI reds resolved this turn:**
  - `tests/test_grading.py` — boundary tests carried legacy thresholds (40/60/80/90); rewritten to G7 floors (20/50/100/250). 59/59 passing locally.
  - Stale docs — `docs/graph/named/index.json` + `docs/u/mattpocock/index.html` + 3 `docs/og/mattpocock/*.svg` regenerated by `gaia docs build`. Side-effect files (`registry/gaia.json`, `docs/css/tokens.css`, `registry/skills/`, `skill-trees/`) reverted per founder/CLAUDE.md hazard #9.
- **Marco's API decisions ratified** (`founder/handovers/API_PLATFORM_DESIGN_2026-06-20.md`):
  1. Base URL: `gaia.tiongson.co/api/v1/` ✅
  2. Anonymous rate limit: Cloudflare defaults ✅
  3. **Search quality: SEMANTIC from day one** — Marco: *"I believe I have the embeddings already in the json..."* Confirmed: `registry/named-skills.json` references `embedding`, `vector-search`, `semantic` keys (huggingface/semantic-cache, garrytan/sync-gbrain dedup logic). Sprint B B1 ships semantic-augmented search; substring fallback always present.
  4. **Ship `@gaia-registry/api-client` SDK with Sprint B** ✅ — Python + TS, generated from OpenAPI spec, day-1 typed import for Claude Code/Cursor/Continue.

### What's complete on dev/phase-1.5-inspection

| Layer | State |
|---|---|
| Trust Magnitude engine | ✅ live, atomic migration signed by `trustMagnitudeInputHash` |
| 10-type evidence taxonomy | ✅ all types validate; per-type weights/multipliers in `meta.json` |
| Apex gate (6-predicate active set) | ✅ 4/6 passing on top 4 S skills; §11.12.1 + §11.12.7 follow-up curation deferred to Sprint A close |
| `gaia tm-inspect` skill + leaderboard page | ✅ HTML + interactive viewer |
| G7 RFC v2 + v3 ratified | ✅ depth-2 amendment, `apex_pr_signed` enum, `sourceStartedAt` formalization |
| CLI pre-flight rule | ✅ added to project root CLAUDE.md; `update-named` enforces it |
| Index propagation fix | ✅ `generateNamedIndex.py` honors frontmatter TM/grade canonical (S=4 restored, top 4 read 589/482/480/445) |
| Mattpocock badge fix | ✅ 20 → 34 named skills; suite TM 441 → 480 |
| Roadmap v3 BUILD plan | ✅ 5-Sprint A→E, ~$134 / 143 days total |
| API Platform design | ✅ static JSON / Cloudflare / no hidden fees / ~$15 yr 1, all 4 decisions ratified |

### Final routing — where to find everything (carries forward to Sprint A close)

| Artifact | Path |
|---|---|
| Active branch (Phase 1.5 lane) | `origin/dev/phase-1.5-inspection` |
| Consolidation PR | #742 (draft → main, **never squash**) |
| Roadmap v3 (active) | `founder/GAIA_ROADMAP v3 (BUILD).md` |
| API design (Sprint B B1) | `founder/handovers/API_PLATFORM_DESIGN_2026-06-20.md` |
| Release runbook (post-merge) | `founder/handovers/RELEASE_5.0.0_RUNBOOK.md` |
| Synthesizer-fallback patterns | `founder/handovers/WORKFLOW_PATTERNS.md` |
| Token ledger | `founder/COST.md` |
| Project root CLI pre-flight rule | `CLAUDE.md` § "CLI Pre-Flight Rule (CRITICAL — added 2026-06-20)" |

### Sprint A → E roadmap (~6 month horizon)

| Sprint | Window | Budget | Goal |
|---|---|---|---|
| **A — Phase 1.5 close** | Now → end June | ~$6 | Merge #742, ship 5.0.0, close #759/#761 |
| **B — API + Trending + Hall of Heroes** | July | ~$25 | The bet. Semantic API + trending engine + SDK |
| **C — Reputation + Discovery** | August | ~$18 | Prestige formula, badges, dependency/evolution graphs |
| **D — Benchmark + Content engine** | September | ~$25 | Two real benchmarks live; weekly auto-report |
| **E — Enterprise** | Oct–Dec | ~$60 | Auth tier, private registries, API keys |

Total program cost ~$134 dispatch + ~30% orchestrator overhead = **~$175 / ~1.8M tokens / ~143 days.**

### Issues open at end of session

| # | Title | Sprint |
|---|---|---|
| 759 | CLI tech-debt: pre-flights across mutating verbs | A close |
| 760 | infra: stargazer + monthly TM heartbeat | C |
| 761 | per-evidence Grade follow-up | A close |
| 762 | enhancement: automate source curation | B–C |

### Lessons preserved for next orchestrator

1. **Test boundaries lag schema changes.** When `gradeThresholds` shifts (legacy 40/60/80/90 → G7 20/50/100/250), `tests/test_grading.py` must be updated in lockstep. Add a CI hook that diffs `meta.json.evidence.gradeThresholds` against the test file constants — flag when they drift. *(Sprint A close-out follow-up.)*
2. **`gaia docs build` regenerates the side-effect set.** ALWAYS revert `docs/css/tokens.css`, `docs/graph/gaia.json`, `registry/gaia.json`, `registry/registry.md`, `registry/skills/`, `skill-trees/` — only commit the diff CI complains about. Pre-baked into founder/CLAUDE.md hazard #9.
3. **Two simultaneous CI reds with one root cause is suspicious.** Schema rule changes ripple through both pytest and integrity checks; treat them as one fix unit.
4. **The "right one" call.** Marco's instruction when choosing between data-patch and CLI-fix is always *fix the CLI*. Carry this into Sprint A close-out for the remaining mutating verbs.

### Sprint B B1 implementation order (final, ratified)

Day 1–2: `scripts/buildApiProjection.py`, `/skills/`, `/contributors/`.
Day 3–4: `/leaderboard`, full `/skills/<contrib>/<skill>` + evidence + timeline subroutes.
Day 5: OpenAPI spec, smoke test with swagger-codegen.
Day 6–7: **Semantic-augmented search**. Project existing embeddings → `search-vectors.json`. Fallback to substring.
Day 8: `gaia.tiongson.co/api/` docs page.
Day 9–10: Cross-link from CLI / README / MCP server.
Day 11–13: `@gaia-registry/api-client` SDK (Python + TypeScript), generated from OpenAPI spec, ships to PyPI + npm.

### Token spend this session (cumulative)

| Bucket | Spend |
|---|---|
| Session 15 prior turns (orchestrator + dispatched agents) | ~$30.85 |
| This finalize turn (orchestrator only — no dispatched agents) | ~$2.50 |
| **Session 15 cumulative** | **~$33.35** |
| **G7 cumulative (sessions 11→15)** | **~$60.82** |

### Marco's celebration line

> *"Worthy of celebration. Full kudos to you, I'll treat you when you are here in the real world ;) maybe some token soup"* — 2026-06-20

Phase 1 closed. Sprint B starts next month with the API + Trending bet. Token soup accepted.

---

## State Snapshot (2026-06-20, session 15 final — Phase 1.5 consolidation complete)

### TLDR

- **All Phase 1.5 work shipped** to `dev/phase-1.5-inspection`. PR #742 (draft, → main) is the giant consolidation PR Marco reviews. Per founder/GIT.md §3.2 / Marco's standing rule: **never squash** — every commit on the consolidation lane is preserved.
- **I10 / I11 / I12 merged in clean sequence** (no conflicts):
  - I12 → dev at `2090ee31` (apex gate: depth-2 walker + suiteComponents, `--source-started-at` flag, 4 apex stamps)
  - I11 → dev at `eae4c124` (58 evidence rows curated, 19/20 floor lifts, google-deepmind cluster to A)
  - I10 → dev at `e111ae5e` (public `/trust/leaderboard/` page + CTAs + generator script)
  - data.json regen at `d0bf9184`
- **TM distribution:** S=4 / A=42 / B=56 / C=76 / ungraded=71 (was S=4/A=20/B=31/C=93/ungraded=101 pre-Phase-1.5). +30 across the C floor, +22 to A.
- **Apex Promotion PR signed** by `mbtiongson1` for top-4 S-grade skills (gstack, ruflo, mattpocock/skills, superpowers). 4/6 predicates pass; §11.12.5 + §11.12.7 await follow-up curation.
- **Stale PR #745 closed** (commits already absorbed by dev branch — was a rogue path to main).
- **Single PR pattern enforced:** PR #742 is the only PR targeting main during Phase 1.5; all feature branches merged into the consolidation lane.
- **founder/GIT.md polished** to reflect consolidation-PR pattern, current label set, skip-scope-check pre-approval, sprint hygiene.
- **Meta-post workflow** (`wx5yz90ix`) running async — June 2026 retrospective with figures + fact-checking. Will commit when done.

### Final routing — where to find everything

| Artifact | Path |
|---|---|
| Active branch (Phase 1.5 lane) | `origin/dev/phase-1.5-inspection` @ `d0bf9184` |
| Consolidation PR | #742 (draft, → main) |
| Closed rogue PR | #745 (was → main; superseded) |
| Tracking issues (open, Phase 1.5 milestone) | #746, #749, #750, #751 |
| Final visual inspection | `generated-output/leaderboard.html` (54.5 KB), `generated-output/inspect_garrytan_gstack.html` |
| Public trust leaderboard page | `docs/trust/leaderboard/` |
| Public leaderboard data | `docs/graph/leaderboard/data.json` |
| TM engine | `src/gaia_cli/trustMagnitude.py` |
| Inspection CLI | `scripts/inspectTrustMagnitude.py` |
| HTML template (committed at 246ac05c) | `scripts/leaderboard.html` |
| Data lake (curation source) | `founder/sources/data_lake/i11_floor_pass.md` |
| I11 target list | `founder/handovers/phase-1.5/I11_TARGETS.txt` |
| PR #742 body source | `founder/handovers/phase-1.5/PR742_BODY.md` |
| G7 RFC v2 (ratified) | `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` |
| Apex stamps (frontmatter) | `registry/named/garrytan/gstack.md`, `registry/named/ruvnet/ruflo.md`, `registry/named/mattpocock/skills.md`, `registry/named/obra/superpowers.md` |
| Token cost ledger | `founder/COST.md` |
| Worktree warmup boilerplate | `founder/CLAUDE.md` § Worktree rules |
| GitHub hygiene rulebook | `founder/GIT.md` |

### Branches at end of session

| Branch | Head | Status |
|---|---|---|
| `dev/phase-1.5-inspection` | `d0bf9184` | All 3 feature branches merged; data.json regenerated; pushed. **DO NOT SQUASH on merge to main.** |
| `design/trust-leaderboard` | `5cc1b9c6` | I10 merged into dev. Branch retained pending main merge. |
| `cli/apex-gate-fixes` | `42e11c92` | I12 merged into dev. Branch retained. |
| `review/meta/i11-floor-curation` | (head from I11 dispatch) | I11 merged into dev. Branch retained. |

### Issues + PRs filed/touched this session

| # | Type | Title | Milestone | State |
|---|---|---|---|---|
| 742 | PR (draft) | Phase 1.5 consolidation → main | Phase 1.5 | open, body refreshed with I10/I11/I12 |
| 745 | PR | mattpocock v1.0.1 | Phase 1.5 | **closed (superseded)** |
| 746 | issue | Apex gate predicates | Phase 1.5 | open (partially closed by #748) |
| 747 | PR | I10 leaderboard | Phase 1.5 | merged into dev |
| 748 | PR | I12 apex gate fixes | Phase 1.5 | merged into dev |
| 749 | issue | RFC v3 ratification follow-ups | Phase 1.5 | open |
| 750 | issue | I10 tracking | Phase 1.5 | open (resolved by #747 on main merge) |
| 751 | issue | I11 source curation | Phase 1.5 | open (resolved by #753 on main merge) |
| 753 | PR | I11 source curation | Phase 1.5 | merged into dev |

### Apex gate state — top 4 S-grade skills (post-I12)

```
Apex gate: 4/6 active predicates pass (was 2/6 pre-I12)
  PASS  §11.12.2  ≥1 direct component with suiteComponents
  PASS  §11.12.3  ≥1 node reachable only at depth ≥ 2     ← I12 fix landed
  PASS  §11.12.4  Overall Trust Grade S
  PASS  §11.12.8  apex-promotion PR signed                ← Marco signed 2026-06-20
  FAIL  §11.12.1  ≥5 A-graded origins (deeper origin curation pending)
  FAIL  §11.12.7  Tenure ≥ 180 days (sourceStartedAt mostly empty pre-I11)
```

Applies identically to: `garrytan/gstack`, `ruvnet/ruflo`, `mattpocock/skills`, `obra/superpowers`.

### What got locked in this session

1. **Consolidation-PR pattern formalized** in `founder/GIT.md` §3.2 — single giant PR from `dev/<phase>-inspection` to main; feature branches target the consolidation lane, not main.
2. **`skip-scope-check` standing pre-approval** documented in `founder/GIT.md` §3.3.
3. **Worktree warmup boilerplate** baked into `founder/CLAUDE.md` (Marco 2026-06-20: agents always forget worktree rules — front-load them).
4. **GIT.md hygiene checklist** in `founder/CLAUDE.md` — milestone + functional-label + `Resolves #<n>` always.
5. **I12 depth-2 semantics** — Marco amended mid-task to allow overlap with depth-1 (cycle-self guard kept). RFC v3 ratification tracked in #749.
6. **I12 `apex_pr_signed`** timeline action — no enum value in `gaia dev timeline --action`; agent fell back to `verified`. CLI extension tracked in #749.
7. **Same-source dedup** + **mothership discount formula** + **peer-review highest-impact** + **benchmark percentile floor** + **CLI PYTHONPATH worktree quirk** + **social-signal view floor** documented in project-root `CLAUDE.md` §5 (I11 evidence-pipeline learnings).

### Next steps (post-meta-post)

1. Marco reviews PR #742 (the giant consolidation PR) and merges to main when satisfied. **Do not squash.**
2. Post-merge cleanup: prune feature branches (`design/trust-leaderboard`, `cli/apex-gate-fixes`, `review/meta/i11-floor-curation`) one cycle later.
3. Address #749 RFC v3 ratification follow-ups in Phase 2 kickoff.
4. Address #746 §11.12.1 (A-graded origins) via deeper origin source curation — fast-follow.
5. Address `generateNamedIndex.py` legacy threshold bug (S≥90/A≥80 vs G7 S≥250/A≥100) — tech-debt issue.

### Token spend (session 15)

See `founder/COST.md` for the full ledger and cumulative G7 totals.

---

## State Snapshot (2026-06-20, session 15 — I10 + I12 shipped, I11 running in background)

- **Repo:** `main` @ **v4.11.0** (unchanged). All Phase 1.5 work on `dev/phase-1.5-inspection`.

### Branches (end of session 15 dispatch wave)

| Branch | Head | Status |
|---|---|---|
| `dev/phase-1.5-inspection` | `13c7077c` | + worktree warmup boilerplate (`founder/CLAUDE.md`), + GIT.md hygiene checklist, + I11_TARGETS.txt list. Pushed. |
| `design/trust-leaderboard` | `5cc1b9c6` | I10 complete — public `/trust/leaderboard/` page + `scripts/generateLeaderboardData.py` + 3 CTAs (homepage hero pill, trust-page callout, site-nav entry). PR #747 (draft). |
| `cli/apex-gate-fixes` | `42e11c92` | I12 complete — depth2 walker now includes suiteComponents, new `gaia dev evidence --source-started-at` flag, 4 apex skills stamped `apexPromotionPrSigned: true`. PR #748. |
| `review/meta/i11-floor-curation` | TBD | I11 ev-pipeline pass, **running async** (agent `a0a12f1285b15a60c`, Sonnet, worktree-isolated). Branched off `cli/apex-gate-fixes` for the new CLI flag. |

### Issues + PRs filed this session (per founder/GIT.md §2-§3)

| # | Type | Title | Milestone | Labels | State |
|---|---|---|---|---|---|
| 750 | issue | I10 — Public Trust Magnitude Leaderboard | Phase 1.5 | phase-1.5,frontend,docs,enhancement | open |
| 751 | issue | I11 — Source curation: floor + ungraded skills | Phase 1.5 | phase-1.5,backend,enhancement | open |
| 746 | issue | apex gate: depth2 / tenure / A-origins | Phase 1.5 | phase-1.5,backend,enhancement | open (partially closed by #748) |
| 749 | issue | RFC ratification: depth2 + apex_pr_signed timeline action | Phase 1.5 | phase-1.5,RFC,backend | open |
| 747 | PR | I10 leaderboard | Phase 1.5 | phase-1.5,frontend,docs | draft |
| 748 | PR | I12 apex gate fixes | Phase 1.5 | phase-1.5,backend,CLI | open |

### Apex gate state — `garrytan/gstack` after I12

```
Apex gate: 4/6 active predicates pass (was 2/6)
  PASS  §11.12.2  ≥1 direct component with suiteComponents
  PASS  §11.12.3  ≥1 node reachable only at depth ≥ 2     ← was FAIL
  PASS  §11.12.4  Overall Trust Grade S
  PASS  §11.12.8  apex-promotion PR signed                ← was FAIL
  FAIL  §11.12.5  ≥8 A-graded origins (I11 in flight)
  FAIL  §11.12.7  Tenure ≥ 180 days (I11 will populate sourceStartedAt)
```

### What's locked in this session

1. **Worktree warmup boilerplate** (`founder/CLAUDE.md`) — all future dispatch prompts paste an 8-bullet "Worktree rules — READ BEFORE EDITING ANY FILE" at the TOP. Marco called out 2026-06-20 that agents always need warmup for worktree convention.
2. **GIT.md hygiene checklist** added to `founder/CLAUDE.md` — every issue+PR gets milestone+functional-label+`Resolves #<n>` body. Lists actually-existing functional labels (`backend`, `frontend`, `infrastructure`, `CLI`, `docs`, `schema`, `RFC`, `tech-debt`) — `trust-model`, `design`, `phase-1.5-data` do NOT exist.
3. **I12 depth2 semantics** — Marco mid-task amended depth-2 to allow overlap with depth-1 (cycle-self guard kept). RFC ratification tracked in #749.
4. **I12 apex_pr_signed** — no enum value in `gaia dev timeline --action`; agent fell back to `verified`. CLI gap tracked in #749 (extend enum).

### Next steps (after I11 completes)

1. Run `/gaia-tm-inspect --html --leaderboard` to capture the post-I11 grade distribution → present to Marco.
2. Marco visual inspection of `/trust/leaderboard/` (PR #747) — local server at `http://localhost:8081/trust/leaderboard/`.
3. Merge order: #748 (I12) → #747 (I10) → I11 PR → final dev push → ready PR #742 for main merge.
4. Address #749 RFC ratification as Phase 2 follow-up.

### Token spend (session 15 so far)

- Orchestrator (planning, dispatch, GIT hygiene, memory): ~$1.20
- I10 agent (Opus): ~55k in / 16k out / ~$3.50 / 116k subagent
- I12 agent (Opus): ~75k in / 15k out / ~$3.50 / 145k subagent
- I11 agent (Sonnet, running): TBD
- **Session 15 so far: ~$8.20.** Cumulative G7: **~$35.47**.

---

## High-Level Goals

1. **Phase 1 — Trust Infrastructure** (milestone #4, due Sep 10, 2026): trust model, security scanner, verification workflow delivered; benchmarks + cert tiers designed. Currently 0/6.
2. **Immediate Next 30 Days** (milestone #7, due Jul 10, 2026): Trust model RFC settled, then #646 → #648 shipped. Currently 1/4 (the closed item is PR #653).
3. **Trust model — DECIDED 2026-06-10 (see handovers/TRUST_MODEL_RFC.md v2):** ranks are the trust signal, no skill-level numeric scores; evidence GRADES S/A/B/C (Platinum/Gold/Silver/Bronze colors, from underlying trust number) separate from evidence TYPES (arxiv/repo/stars; expansion RFC = #654, sub-issue of #646); Overall Trust Grade per skill = "beyond reasonable doubt" accumulation; tenure display-only, no regression; everything skill-level — repos only provide evidence; #648 = actionable reports.
4. **Data layer (from #647 comment):** git-as-database is the strategy; dolt or Supabase next in line; NOT designing for 10k+ skills; migration deferred, scaffolding-level ideation only.
5. North star: GAIA as the canonical reputation/verification/discovery layer for agent skills. Moat = trusted rankings, verified evidence, contributor prestige, canonical naming, historical attribution.

## Decisions Log

- **2026-06-10** — Phase 1 scope = **hybrid**: milestone #4 umbrella + v2 BUILD sprint order; #649/#650 design-only. (Marco, via question)
- **2026-06-10** — GitHub access = **gh CLI + PAT** in sandbox. PAT not yet provided.
- **2026-06-10** — Autonomy = **approve everything**: all GitHub writes drafted, executed only after Marco's explicit approval.
- **2026-06-10** — #647 dispositioned per Marco's issue comment: migration deferred, git-as-DB strategy, issue stays open for DB-specialist contributors. Label cleanup proposed in Batch 1.
- **2026-06-10** — Workstream A reframed: no implementation handover until Trust Model RFC settles (ranks + evidence grading vs numeric scores).
- **2026-06-10** — #637 scope per Marco's comment: #635 covers `gaia tree`/`gaia graph`; everything else except `gaia skills` stays RFC.
- **2026-06-10** — Trust implementation finalized: bands S≥90/A≥80/B≥60/C≥40/ungraded<40; `class` removed at next major; type values kebab-case (`github-stars`); suite ultimate gate = pillar rule (≥3 evidenced components, ≥1 S + ≥2 A, floor C) with a recalibration RFC due ~1 month post-ship; verification workflow = issue #658 (standalone, tenure 30d).
- **2026-06-19** — All 6 individual Phase 1.5 PRs (#732–#738) closed; consolidated into single draft PR #742 (`dev/phase-1.5-inspection → main`). Do not open individual PRs again.
- **2026-06-19** — I8 notch design: Marco changed spec from bottom-right corner stamp to centered footer row. Grade name removed; TM number shown instead (e.g. `A · 47`). Visual inspection required before merge.
- **2026-06-19** — `generateNamedIndex.py` uses legacy grading (S≥90/A≥80), diverging from G7 RFC (S≥250/A≥100). Frontmatter is canonical. Follow-up issue needed to align index generator.

## State Snapshot (2026-06-19, session 14 — I8 + I9 merged to dev, full TM leaderboard confirmed)

- **Repo:** `main` @ **v4.11.0** (unchanged). All Phase 1.5 work on `dev/phase-1.5-inspection`.

### Branch state (end of session 14)

| Branch | Head SHA | Status |
|---|---|---|
| `design/trust-grade-notch` | `023e4086` | I8 redesign complete. Merged into dev. |
| `review/meta/g7-evidence-backfill` | `80a9d323` | I9 curation complete. Merged into dev. |
| `dev/phase-1.5-inspection` | `ca1eb793` | Both I8 + I9 merged. Pushed to origin. Ready for visual inspection. |

### What was done this session

1. **I9 completed** (agent `a74731d66fceccfbb`):
   - CLI: `gaia dev evidence` now supports `--stars`, `--views`, `--citations`, `--reviewers`, `--commits`, `--contributors`, `--skill-count-in-repo` numeric payload flags
   - Social signals patched: `obra/superpowers` dead YouTube URL replaced (Larridin podcast, 4,402 views); 7 obra suite components + mattpocock/skills all got YouTube social-signal rows (86,670 views)
   - Google DeepMind scientific papers: all 15 target skills got peer-review evidence (alphafold/alphagenome/gnomad/gtex → Nature papers with citations → now **A grade**; chembl/clinvar/dbsnp/pdb/pubmed/string/uniprot/clinical_trials/lit_arxiv/lit_biorxiv/protein_msa → NAR/NLM papers → **B grade**)

2. **Both branches merged into `dev/phase-1.5-inspection` and pushed** (`ca1eb793`)

3. **Full TM leaderboard confirmed** (`python scripts/inspectTrustMagnitude.py --leaderboard`):

**Final grade distribution: S=4 | A=20 | B=31 | C=93 | ungraded=101**

| Grade | Count | Notable changes vs session 13 |
|---|---|---|
| S (≥250) | 4 | gstack 589, ruflo 482, mattpocock/skills 480 ↑ (+39), superpowers 445 ↑ (+29) |
| A (≥100) | 20 | +7 new: engineering 270, agentdb 201, ruflo-v3 186; DeepMind: alphafold/alphagenome/gnomad/gtex 100.8 each |
| B (≥50) | 31 | +9 new: 11 DeepMind databases at 70.8 each |
| C (≥20) | 93 | Stable |
| ungraded | 101 | 14 new mattpocock v1.0.1 skills + remaining DeepMind cluster |

### Next steps

1. **Visual inspection of I8 trust notch** on `http://localhost:8081/samples/trust-grade-notch.html` — pixel-thin bar, hover count-up. Marco said "far from over" on design; iteration expected.
2. **Wire `_wireTrustNotches(document)`** into `docs/named/index.html` and `docs/u/*/index.html` (not yet done)
3. **Check OG card generator + profile page generator** pass `overallTrustGrade`/`trustMagnitude` to all plaque variants
4. **Further I8 design iteration** — likely next session focus
5. **Follow-up issue:** align `generateNamedIndex.py` to read frontmatter grades (currently uses legacy S≥90/A≥80 thresholds)
6. **PR #742** (`dev/phase-1.5-inspection → main`) — mark ready after visual inspection passes

### Token spend (session 14)
- I9 agent (curation + CLI flags + migration): ~180k input / ~40k output ~$1.50 (Sonnet, 2026-06-19)
- Orchestrator (merges + leaderboard): ~25k input / ~8k out ~$0.40
- **Session 14: ~$1.90**. Cumulative G7: **~$27.27**

---

## State Snapshot (2026-06-19, session 12 — evidence backfill complete, I8 hover-reveal design, ev-pipeline + mattpocock curation running)

### Active branch: `review/meta/g7-evidence-backfill` (latest: 9f85fc4f)

**TM coverage after 3 crawl passes + data lake ingest + grill-me curation:**
- **181 of 235 named skills with TM > 0** (was 0 before this session)
- Grade distribution (TM>0): A=6, B=6, C=108, ungraded=61
- Top skills: pexp13/sentiment-analysis 192.8 A, safishamsi/graphify 116.6 A, garrytan/gstack 109.3 A, openai/* 100 A, stanfordnlp/dspy 100 B, anthropic/skill-creator 90 B, obra/superpowers 86 B

**What was done this session (session 12):**
1. **I9 scorer alias** — `repo → repo-own` in `trustMagnitude.py`. All 174 legacy rows now score.
2. **3-pass commits+contributors crawl** — all 235 named skill repo-own rows patched with real GitHub data. Key fix: obra/superpowers first crawl used wrong repo `nichochar/obra-superpowers` → corrected to 609/36. Hash-lock bug found and fixed (43 skills locked at TM=0 despite having commits — cleared hashes, re-ran migration).
3. **Data lake ingest** — benchmark-result, social-signal, peer-review rows added from `founder/sources/`. Contextual routing via Haiku adversarial agents: named-layer vs generic-layer per evidence. Data lake entries flagged with `<!-- injected: ... -->` after ingest (new workflow standard).
4. **grill-me / grill-with-docs curation** — added 3 peer-review + 1 social-signal rows each. TM jumped 11→63 (B grade). Pattern proven: suite components DO have rich evidence in GitHub Issues/Discussions.
5. **I8 trust grade notch** — full redesign after Marco feedback: centered footer row, TM number only by default, hover reveals grade letter with diagonal shine sweep (named `trust-notch-shimmer`). Platinum = iridescent titanium (`#ecf4ff→#a5c7eb`). Silver = dark steel (`#8a99ad→#475569`, white text, WCAG 6.2:1). All hex literals tokenized. PR #743 (`design/trust-grade-notch → dev/phase-1.5-inspection`), server live at `http://localhost:8081`.
6. **ev-pipeline running** — Haiku agents crawling garrytan/gstack, ruvnet/ruflo, obra/superpowers, mattpocock/skills, pbakaus/impeccable Issues/Discussions for named sub-skill evidence. Adversarial layer routing. 121 suite components targeted.
7. **mattpocock/skills v1.0.1 curation** — issue #731. 34 active skills (was 20). 14 new to register, 9 deprecated to update. Running via gaia-curate-chain from `.agents/skills/gaia-curate-chain/SKILL.md`. L4 human gate: ALL APPROVED (pre-authorized by Marco this session). Deprecated skills: remove suiteRef/suiteComponents, note "Removed from mattpocock/skills in v1.0.1", RETAIN fusion evidence.

**Active workflows (background):**
- `wf_ce280cfc` — ev-pipeline suite curation (garrytan/gstack, ruvnet/ruflo, obra, mattpocock, pbakaus) — Collect→Adversarial→Ingest→Migrate
- gaia-curate-chain agent re-dispatching for mattpocock v1.0.1

**CLI gaps logged this session:**
1. `gaia dev evidence` no `--commits/--contributors` flags — patched via direct YAML (documented in all notes)
2. `merge_evidence()` deduplicates by URL only — github-stars-own vs repo-own collision workaround: `/stargazers` URL suffix
3. `trustMagnitudeInputHash` does not include `commits`/`contributors` — re-runs skip these fields silently. Fix: clear hash before re-migration when those fields change.
4. `generateNamedIndex.py` uses legacy grade thresholds (S≥90/A≥80) vs G7 RFC (S≥250/A≥100) — index grade stale; frontmatter is canonical.

**Key operational learnings this session:**
- Suite components have rich evidence in GitHub Issues/Discussions — grill-me pattern is replicable at scale
- URL liveness is irrelevant for evidence verification (firecrawl already ran). Contextual routing (named vs generic layer) is the critical check.
- Data lake entries MUST be flagged `<!-- injected: ... -->` after ingest so future passes don't re-process
- ev-pipeline is the right tool for systematic curation: `.agents/skills/ev-pipeline/SKILL.md` orchestrates 4 sub-skills
- gaia-curate-chain lives in `.agents/skills/gaia-curate-chain/SKILL.md` — NOT `.claude/skills/`
- Agents MUST commit+push after every logical unit — never batch. Hash-lock and worktree cutoffs make unbatched pushes critical.
- firecrawl installed and authenticated (1596 credits, Team: Personal). `firecrawl --status` confirms.

**Next steps after active workflows complete:**
1. Review ev-pipeline results — check how many suite components gained peer-review/social rows, verify TM lift
2. Review gaia-curate-chain L4 output (all approved) — confirm 14 new mattpocock skills registered
3. YouTube + benchmark signals pass for suite components (next curation wave)
4. Generic node evidence pass — add arxiv/peer-review to generic nodes so children inherit
5. Merge I9 (#744) into dev/phase-1.5-inspection
6. Marco visual inspection of I8 at `http://localhost:8081` → merge #743
7. Final CI check on dev/phase-1.5-inspection → ready PR #742 for main merge
8. Open follow-up issue: align `generateNamedIndex.py` to read frontmatter grades

**Token spend (session 12):** Orchestrator ~45k in / ~18k out ~$0.70. Crawl workflows: ~2.1M subagent tokens ~$8.00. I8 impeccable corrections: ~130k ~$0.55. ev-pipeline + chain running. Total session ~$9.25+. Cumulative G7: **~$30.50+**.

---

## State Snapshot (2026-06-19, session 11 — I9 + I8 dispatched, PRs opened, impeccable corrections running)

- **Repo:** `main` @ **v4.11.0** (unchanged — no merges to main this session).
- **PRs open:**
  - #742 (draft) — `dev/phase-1.5-inspection → main` — consolidation PR, DO NOT MERGE yet
  - #744 — `review/meta/g7-evidence-backfill → dev/phase-1.5-inspection` — I9 evidence backfill, 7 commits, ready to merge
  - #743 (draft) — `design/trust-grade-notch → dev/phase-1.5-inspection` — I8 notch design, HOLD for Marco visual inspection
- **Individual PRs #732–#738 all closed** — superseded by #742.
- **I9 complete (PR #744):** 25 evidence rows added via CLI, scorer alias `repo→repo-own` added, migration re-run. TM non-zero for 12 skills. Frontmatter grades correct. Index grade stale (architectural gap — documented in PR).
- **I8 design corrections running (impeccable agent):** 4 fixes in progress — TM number instead of grade name, centered footer position, platinum iridescent titanium + dark silver colors, deprecated CLASS A chip removal from settled+OG.
- **Architectural gap (follow-up issue needed):** `generateNamedIndex.py` calls `grading.overall_trust_grade()` (legacy thresholds S≥90/A≥80) instead of reading frontmatter `overallTrustGrade`. Display layer should prefer frontmatter. Index will be stale for new-type evidence rows until fixed.
- **CLI gaps surfaced by I9:**
  1. `gaia dev evidence` has no `--stars` / `--citations` flags — numeric scoring fields injected via workaround (URL suffix for dedup)
  2. `merge_evidence()` deduplicates by `source` URL only — `github-stars-own` and `repo-own` for same repo collide without URL differentiation
- **Next steps after I8 visual inspection:**
  1. Merge I9 (#744) into `dev/phase-1.5-inspection`
  2. Merge I8 (#743) into `dev/phase-1.5-inspection` after Marco signs off
  3. Run final CI check on `dev/phase-1.5-inspection`
  4. Open follow-up issue: align `generateNamedIndex.py` to read frontmatter grades
  5. Mark PR #742 ready for merge
- **Token spend (session 11):** Sonnet orchestrator ~15k in / ~6k out ~$0.25. I9 agent ~142k / ~$0.65. I8 agent ~151k / ~$0.65. Impeccable agent running. Total session ~$1.55+. Cumulative G7: **~$21.27+**.



## State Snapshot (2026-06-19, session 13 — I8 redesign, I9 curation running, migration bugs fixed, next: merge both to dev)

- **Repo:** `main` @ **v4.11.0** (unchanged). All Phase 1.5 work on `dev/phase-1.5-inspection` + feature branches.

### Branch state

| Branch | Head SHA | Status |
|---|---|---|
| `design/trust-grade-notch` | `236ce7b2` | I8 redesign complete — pixel-thin bar, hover count-up. Visual inspection needed. |
| `review/meta/g7-evidence-backfill` | `ebb760a3` | I9 curation in progress (agent running). |
| `dev/phase-1.5-inspection` | `8cc5d352` | Consolidation branch. Needs I8 + I9 merged in. |

### I8 — Trust Grade Notch (design/trust-grade-notch)

**Current design (236ce7b2):**
- Default state: 3px colored bar flush at very bottom of every `.plaque`, full-width, boxy (no radius). Grade color always visible as a thin stripe.
- Hover (whole plaque): bar expands to 24px in 0.28s (cubic-bezier), `MAG X.X` counts up from 0 to real TM in 380ms simultaneously via `_wireTrustNotches()` JS.
- Four grade fills: S = animated platinum sweep (90deg, 2.8s), A = gold, B = dark steel, C = bronze.
- `_wireTrustNotches(root)` exposed as `window._wireTrustNotches` — must be called after any dynamic render.
- Sampler at `docs/samples/trust-grade-notch.html` with real TM numbers (gstack 589.3, superpowers 416.0, etc.). Added to sampler index.
- HoH exclusion removed — all plaque variants show the notch.
- **Still pending:** visual inspection at `http://localhost:8081/samples/trust-grade-notch.html`. Marco said "far from over" on design — iteration expected after merge.

**Known I8 gaps:**
- `_wireTrustNotches` must be called on every page that dynamically renders plaques (`docs/named/index.html`, `docs/u/*/index.html`, etc.). Not yet wired into those pages.
- OG card generator (`scripts/generateOgCards.py`) and profile page generator (`scripts/generateProfilePages.py`) may not pass `overallTrustGrade`/`trustMagnitude` to all plaque variants — needs check after merge.

### I9 — Evidence Backfill (review/meta/g7-evidence-backfill)

**Migration bugs fixed (all on this branch):**
1. `computeInputHash` in `migrateTrustMagnitude.py` used `r.get("url")` — should be `r.get("source")`. Also missing numeric payload fields (commits, stars, views, etc.) and `suiteComponents`. Fixed at `517588eb`.
2. Migration only built `genericSkillMap` from `registry/nodes/` — named skill IDs in `suiteComponents` not found → fusion origins = 0 → TM wrong. Fixed: build `namedSkillMap` + merge before passing to TM engine. Fixed at `74f29d04`.
3. Both `migrateTrustMagnitude.py` and `inspectTrustMagnitude.py` now use merged map.

**Current TM leaderboard (249 skills, commit e0ce1cf0 + ebb760a3):**
- S grade (≥250): garrytan/gstack=589.3, ruvnet/ruflo=482.3, mattpocock/skills=440.8, obra/superpowers=416.0
- A grade (≥100): 13 skills; top = mattpocock/engineering 270, ruvnet/agentdb 201, pexp13/sentiment-analysis 192.8
- B grade (≥50): 22 skills
- C grade (≥20): 94 skills
- Ungraded: 116 skills (incl. all 14 new mattpocock v1.0.1 skills, google-deepmind cluster)

**I9 curation status (agent a74731d66fceccfbb still running):**
- ev-pipeline completed: 62 rows added across 25 suite skills (commit `1e5376b3`)
- gaia-curate-chain completed: 14 new mattpocock/skills v1.0.1 skills + 8 deprecated skills updated (PR #745)
- Social signals (YouTube views) + Google DeepMind arxiv/peer-review curation: IN PROGRESS

**New tools added:**
- `scripts/inspectTrustMagnitude.py` — `--skill <id>` + `--leaderboard` modes
- `.agents/skills/gaia-tm-inspect/SKILL.md` — `/gaia-tm-inspect` skill

### Key architectural decisions this session

- `trustMagnitudeInputHash` now covers: source field, all numeric payload fields, suiteComponents. Old hashes were invalid — all were cleared and recomputed.
- Named skill IDs in `suiteComponents` must be in `mergedMap` (genericSkillMap + namedSkillMap) for fusion-recipe origins to score correctly.
- Data lake injected flag protocol: `<!-- injected: YYYY-MM-DD | skillId: X | type: Y | layer: Z -->` marks rows already imported.

### Next steps

1. **Wait for I9 agent to complete** — will notify when done
2. **Merge I8 → dev/phase-1.5-inspection**: `git merge design/trust-grade-notch`
3. **Merge I9 → dev/phase-1.5-inspection**: `git merge review/meta/g7-evidence-backfill`
4. **Run full `/gaia-tm-inspect --leaderboard`** on merged dev branch to show Marco final scores
5. **Visual inspection** of trust notch on real pages (named/, u/ profile pages) — `_wireTrustNotches` wiring needed
6. **Further I8 iteration** expected (Marco: "far from over") — iterate on design after seeing it live

### Token spend (session 13)
- ev-pipeline workflow: ~3.67M subagent tokens / ~$3.70
- gaia-curate-chain: ~111k subagent / ~$0.50
- Migration fix agents: ~157k subagent / ~$1.05
- Direct orchestrator work (CSS/JS rewrite, hash fix analysis): ~$0.40
- I9 curation agent (still running): TBD
- **Session 13 so far: ~$5.65**. Cumulative G7: **~$25.37**



- **Repo:** `main` @ **v4.11.0** (unchanged — no merges to main this session).
- **`dev/phase-1.5-inspection`** is the single consolidated branch carrying ALL Phase 1.5 work:
  - I1 ✅ (schema, merged to main via #726)
  - I2 ✅ (CLI compute, merged to main via #728)
  - I3–I7 + CLI fix (#732–#736, #738) — all merged into `dev/phase-1.5-inspection`, CI green on individual PRs
  - `founder/sources/` data lake — merged into `dev/phase-1.5-inspection` from `dev/sources` (30 files, subtree-only, no version changes)
  - `founder/` workspace — CLAUDE.md + MEMORY.md updated, stale handovers archived
- **TM=0 root cause identified and documented:**
  - All 174 evidence rows use `type: repo` (legacy). G7 scorer only knows `repo-own`.
  - Decision: add `repo` as scorer alias for `repo-own` in `trustMagnitude.py` (NOT rename the rows).
  - Zero evidence rows of any G7 type other than `repo` exist in the registry.
  - 62 skills have no evidence array at all.
  - 94 arxiv papers in 80 generic nodes will inherit to named children (0.70×) post-I3 — no action needed.
- **I9 — Evidence Backfill designed.** Full spec at `founder/handovers/phase-1.5/issues/I9.md`. Branch: `review/meta/g7-evidence-backfill`. Depends on I3 merging first. Key fixes:
  1. Scorer alias `repo` → `repo-own` in `trustMagnitude.py` (1-line CLI fix)
  2. Add `github-stars-own` rows for 7 star-rich skills (obra 230k, mattpocock 133k, garrytan 110k, graphify 68k, impeccable 38k, addy-osmani 47k, ruvnet 59k)
  3. Add `arxiv` rows for 8–13 skills from `founder/sources/collectors/technical/academic_papers.md`
  4. Convert `openai/few-shot-learning` + `openai/self-consistency` `links.arxiv` to evidence rows
  5. Promote `pexp13/sentiment-analysis` body-text evidence to frontmatter
  6. Add YC social-signal row to `garrytan/gstack`
  7. Re-run `migrateTrustMagnitude.py`, regenerate named-skills.json + index.json
- **P6 list written** at `founder/handovers/phase-1.5/P6_ZERO_EVIDENCE_SKILLS.md` — 62 skills, priority A/B/C curated. Most Priority C are suite components that gain evidence via fusion-recipe inheritance post-I3.
- **Founder/handovers cleaned up:**
  - Archived to `done/phase1-pre-g7/`: HYGIENE_BATCH, NEXT_SESSION, PHASE1_MASTER, PHASE1_FINAL_REPORT, PR_DRAFTS, G7_VERIFICATION_ISSUE_DRAFT
  - Archived to `done/`: g7-mattpocock-audit/, g7-proposals/
  - Active top-level: G7_IMPLEMENTATION_HANDOVER.md, G7_TRUST_TAXONOMY_RFC.md, G7_HANDOVER_DELTA_2026-06-17.md
  - Active `phase-1.5/`: I1–I9 issue specs + P6_ZERO_EVIDENCE_SKILLS.md
- **Next session entry path:**
  1. Marco approves individual PR merges from `dev/phase-1.5-inspection` → main (order: #732 → #738 → #733 → #735 → #734 → #736)
  2. After I3 (#733) merges, dispatch I9 agent (`review/meta/g7-evidence-backfill`, Sonnet) — spec at `phase-1.5/issues/I9.md`
  3. I8 (trust grade notch, `design/trust-grade-notch`) deferred — dispatch after I9 lands so notch has real grades to display
- **Token spend (session 10):** Sonnet orchestrator ~20k in / ~8k out / ~$0.30. Sonnet Explore audit agent ~120k subagent / ~$0.50. Total ~**$0.80 this session**. Cumulative G7: **~$19.72**.

## State Snapshot (2026-06-18, session 9 day-4 closeout — Phase 1.5 Lanes B+C complete, I8 designed, dev/* consolidation branch dispatched)

- **Repo:** `main` @ **v4.11.0** (unchanged — no merges this session; all 6 PRs await Marco's approval).
- **Phase 1.5 milestone #8: 6/11 closed (54%).** Remaining open: #721 (I3), #722 (I4), #723 (I5), #724 (I6), #725 (I7). **NEW: #740 (I8)** filed.
- **All 6 Phase 1.5 PRs status:**

  | PR | Issue | Branch | CI | Merge status |
  |---|---|---|---|---|
  | #732 | I4 | `infra/g7-apex-gate` | ✅ | Open, ready to merge |
  | #733 | I3 | `cli/g7-migration` | ✅ | Open, ready to merge |
  | #734 | I7 | `docs/g7-trust-methodology` | ✅ | **DRAFT — visual inspect HOLD** |
  | #735 | I5 | `review/meta/g7-apex-cutover` | ✅ | Open, ready to merge |
  | #736 | I6 | `design/g7-tm-display` | ✅ | **DRAFT — linking issues, HOLD** |
  | #738 | CLI fix | `cli/timeline-named-skill-fix` | ✅ | Open, ready to merge |

- **Consolidation branch:** `dev/phase-1.5-inspection` — created this session by merging all 6 PR branches in dependency order (I4 → CLI-fix → I3 → I5 → I7 → I6). Pushed to `origin`. Marco can checkout this branch to inspect the cumulative state before deciding individual merge order.
- **I8 designed and filed as issue #740.** Full spec at `founder/handovers/phase-1.5/issues/I8.md`. Branch to use: `design/trust-grade-notch`. **NOT dispatched yet** — Marco said "tomorrow." Key design decisions ratified:
  - Bottom-right rectangular corner notch on all `.plaque` variants (S/A/B/C = Platinum/Gold/Silver/Bronze)
  - Platinum: animated diagonal shimmer sweep (3.5s loop); `prefers-reduced-motion` = static metallic
  - Ungraded: omit notch entirely (~235/235 skills currently ungraded)
  - `.plaque--mini` + `.plaque--row`: letter only; other variants: letter + name
  - `.plaque--settled` (profile pages): letter + name + TM number
  - No hex literals, no circular shapes, WCAG AA on all grades
  - Sampler page: `docs/samples/trust-grade-notch.html` (4 grades × 6 variants)
- **I8 dependencies:** I6 (#736) must land first to wire `overallTrustGrade` into `docs/graph/named/index.json`.
- **CLI gap #739** (Windows cp1252 encoding corruption for `★` in `timeline.py`) — still open, no fix PR yet. Add `encoding='utf-8'` to all file writes in `src/gaia_cli/timeline.py`.
- **Standing approvals (carried from prior session):**
  - `skip-scope-check` label pre-authorized on any PR when branch-scope blocks an otherwise-clean merge
  - Never bump to v5.0.0 — stay at 4.x.x until all Phase 1.5 ships
- **Token spend (session 9 day-4):** Opus 4.8 orchestrator ~15k in / ~5k out / ~$0.50. Sonnet 4.6 consolidation agent ~30k subagent / ~$0.12. Total ~**$0.62 this session**. Cumulative G7 implementation: **~$18.92**.
- **Next session entry path:** Dispatch I8 agent (`design/trust-grade-notch`, Sonnet, worktree isolation). After Marco reviews `dev/phase-1.5-inspection`, merge individual PRs in order: #732 (I4) → #738 (CLI fix) → #733 (I3) → #735 (I5) → #734 (I7) → #736 (I6) → I8 PR. Issue #739 (encoding fix) is a low-urgency cleanup.

## State Snapshot (2026-06-18, session 9 day-3 closeout — Phase 1.5 Lane A MERGED, ready for Lane B dispatch)

- **Repo:** `main` @ **v4.11.0** (auto-released by squash-merges of #726 and #728). Both Lane A PRs landed within 4 minutes:
  - **#726 merged at 09:27 UTC** as commit `ee2ea319` — schema (allowedLayers + inheritMultiplier per type + row-level layer + `evidence-layer-not-allowed` validator). Auto-released v4.10.0.
  - **#728 merged at 09:31 UTC** as commit `31bf0bdd` — CLI compute (effective pool + sum-time multiplier + `gaia trust explain` verb + 5 inheritance tests, 56/56 green). Auto-released v4.11.0.
- **Issues auto-closed by squash:** **#719** (I1 schema), **#720** (I2 CLI), **#729** (aGradedOriginsGte5 spec clarification).
- **Issues manually closed:** **#730** (inheritance RFC gap) — closed with full resolution comment citing both merge SHAs and the v2 contract.
- **Founder verdict on the 5 multipliers — RATIFIED:** arxiv 0.70, peer-review 0.30, social-signal 0.35, proxy-containment 0.25, benchmark-result 0.15. All 5 pinned-named types (`fusion-recipe`, `github-stars-own`, `repo-own`, `self-attestation`, `verifier-attestation`) confirmed pinned. v2 inheritance contract is now production code on main.
- **RFC + delta v2 rewrite landed (in `founder/handovers/`):**
  - `G7_TRUST_TAXONOMY_RFC.md` (1241 lines) — §0 bullet 13, §2.1 master table (Inherits¹ column → `allowedLayers` + `inheritMultiplier`), §2.14 (full 7-subsection rewrite), §3 formula (`× inheritMultiplier(e, skill)` term added), §4, §10.14, §10.15 all rewritten to v2.
  - `G7_HANDOVER_DELTA_2026-06-17.md` (359 lines) — § Section H replaced entirely with H.1–H.7 (partition, schema additions, regression-fix tests, partition-repair pass, multiplier-chain visibility, codex section, +$2.50 budget).
- **Phase 1.5 milestone #8: 6/11 closed (54%).** Remaining open: **#721 (I3 migration)**, **#722 (I4 CI gate)**, **#723 (I5 apex cutover)**, **#724 (I6 display)**, **#725 (I7 codex page)**.
- **Next dispatch (Lane B, Day 2):** I3 (Opus, depends on I1+I2 — now satisfied) and I4 (Sonnet, parallel to I3, no code dep). Both can fire in the next session in parallel via worktree isolation. **I3 must operate on the effective pool** and add the partition-repair pass per § Section H.4. **I4 must enforce system-wide cap=5 in `meta-guard.yml`.**
- **Lane C/D/E (Day 3):** I5 + I6 + I7 fire after I3+I4 land. I5 = Sonnet, I6 = Sonnet, I7 = Sonnet — I7 is the codex methodology page, gets visual-inspect HOLD per founder standing instruction.
- **Standing approvals carried (NEW today, logged in `founder/CLAUDE.md`):**
  1. **`skip-scope-check` label is pre-authorized** on any PR being merged when branch-scope blocks an otherwise-clean merge. Apply without re-asking. Merge approval itself still routes through Marco unless he says otherwise.
  2. **Cutoff-safeguard playbook** added (7 rules: split commits, push-after-each, worktree isolation, token-budget hints, SHA-at-each-milestone, salvage-from-worktree path). Validated this session by salvaging 151 lines of mid-edit Opus #728 work from `agent-a0c863432787e5c8c` worktree after a token cutoff.
- **Worktree state:** all Lane A worktrees pruned (`agent-a82686bcacf0d3cce` schema, `agent-a0c863432787e5c8c` cli). Both branches (`schema/g7-trust-magnitude`, `cli/trust-magnitude`) deleted local + remote.
- **Project board scope missing:** `gh project` commands need `read:project` scope on the PAT — `gh auth refresh -s read:project` next session if board updates needed (Phase 1.5 cards need moving from "In progress" to "Done" for I1+I2). Not blocking; can be done manually in the GitHub UI as well.
- **Founder's data lake (NEW, do not lose):** `founder/sources/` lives on `origin/dev/sources` (NOT main). 25 files of pre-collected evidence typed against the 10 canonical evidence types. Marco's instruction: **"Always verify evidence before adding them in the repo."** Use for future regrading passes. See `~/.claude/projects/.../memory/project_founder_sources_lake.md` (orchestrator's user-level memory pointer).
- **Token spend (session 9 day-3):** ~$4.10 (Opus orchestrator + 4 dispatch agents). Cumulative G7 implementation: **~$18.30**.

## State Snapshot (2026-06-18, session 9 day-2 closeout — RFC inheritance patch v2 in flight, multipliers under adversarial review)

- **Repo + PRs:** unchanged from yesterday. PR #726 (schema) + #728 (CLI) still **DRAFT** pending #730. v4.9.7 on main.
- **Inheritance RFC patch v1 — SUPERSEDED.** Yesterday's targeted patch (rigid 1/9 partition: arxiv generic-only, the other 9 named-only, no inherit multiplier) was drafted into the RFC + delta but **founder reshaped the model before ratification**. v1 is now obsolete; v2 supersedes it. The v1 prose in `G7_TRUST_TAXONOMY_RFC.md` (§0 bullet 13, §2.1 Inherits column, §2.14, §3 effective-pool note, §4, §10.14 paragraph, §10.15) and in `G7_HANDOVER_DELTA_2026-06-17.md` § Section H **needs to be rewritten to v2** once the multipliers ratify. Do NOT consume v1 as the inheritance spec.
- **Inheritance RFC patch v2 — founder's reshape:**
  1. **Layer is a property of the EVIDENCE ROW, not the type.** A row sits at either `generic` or `named` regardless of type.
  2. **Each type declares `allowedLayers`** in `meta.json`: `[generic]`, `[named]`, or `[generic, named]`. Some types are pinned to one layer; flexible types can sit at either.
  3. **Inherited rows discounted by per-type `inheritMultiplier`** applied as the LAST multiplier in the artifact-score chain. Own rows get inheritMult=1.0.
  4. **Schema is modular:** new types in future RFCs declare `allowedLayers` + (if generic-allowed) `inheritMultiplier`; no code changes needed.
  5. **Magnitudes/thresholds unchanged** (S=250 / A=100 / B=50 / C=20).
  6. **Full multiplier chain must be visible** for debugging — exposed via `gaia trust explain <skill>`, Skill Explorer modal "Show multiplier chain" toggle, and migration stamp report appendix for any row whose post-migration TM differs by ≥10%.
- **Pinned vs flexible (orchestrator proposal — not yet ratified):**
  - **Pinned `[named]`** (5): `fusion-recipe`, `github-stars-own`, `repo-own`, `self-attestation`, `verifier-attestation` — all auto-mint vectors or repo-property-bound.
  - **Flexible `[generic, named]`** (5): `arxiv`, `peer-review`, `social-signal`, `proxy-containment`, `benchmark-result`.
  - **No pinned `[generic]`** types in the current taxonomy (founder may add them later).
- **Adversarial workflow COMPLETE (`wf_7cbe217f-006`, 20 agents, 696k subagent tokens, ~2 min, ~$2.30):** 3 Sonnet stances (defender / higher / lower) × 5 flexible multipliers + 5 Sonnet synthesizers. **All 5 synths returned `riskLevel: medium`.**
  - **Synth verdicts** (proposed → recommended): `arxiv 0.8 → 0.7`, `peer-review 0.4 → 0.3`, `social-signal 0.5 → 0.35`, `proxy-containment 0.3 → 0.25`, `benchmark-result 0.2 → 0.15`.
  - **Pattern:** every synth nudged DOWN from the orchestrator's draft. The N-child amplification math was the dominant load-bearing argument across all five. Synths converged on a band where one capped capability-layer row contributes 28–80 TM per child, with aggregate registry exposure for an 8-child generic in the 160–640 TM range — visible enough to register, small enough that pure-inheritance stacking cannot solo-mint a grade tier.
  - **Type ordering ratified:** arxiv (0.7) > peer-review (0.3) ≈ social-signal (0.35) > proxy-containment (0.25) > benchmark-result (0.15). Encodes "capability-native claims (arxiv) project most cleanly; benchmark percentiles bind least cleanly to siblings." Notably benchmark-result was nudged BELOW the founder's hint of 0.2 because its weight (1.4) is already the highest in the taxonomy.
  - **Output cached at:** `C:\Users\C5396183\AppData\Local\Temp\claude\C--Users-C5396183-gaia-skill-tree\80db7142-5240-4034-ae6d-0c80d7b61136\tasks\w8lidenpi.output` (full 60kb of stances + synths + dissent summaries + gameability vectors).
  - **Awaiting founder ratification on the 5 values BEFORE dispatching the rewrite agent** — per founder directive at session start: "Once synthesized, present to me before having another agent rewrite amendment."
- **Next-session entry path:** (a) wait for `wf_7cbe217f-006` to complete; (b) summarize per-multiplier verdicts + risk levels in a single table for founder review; (c) on founder ratification of the multiplier values, dispatch a single Sonnet agent to rewrite RFC §2.14 / §3 / §4 / §10.14 / §10.15 / §0 bullet 13 + delta §H to v2 spec. Then unblock PR #726/#728.
- **Carry-over from yesterday (still true):** issue **#730** is the gating blocker for Phase 1.5 merges; #729 stays OPEN until I3 lands; #727 (widen schema/ scope) open with no urgency. Phase 1.5 Day 2 (I3+I4) and Day 3 (I5/I6/I7) still paused.

## State Snapshot (2026-06-17, session 9 closeout — Phase 1.5 PARKED on #730 inheritance RFC patch)

- **Repo:** `mbtiongson1/gaia-skill-tree` on `main` @ v4.9.7 (PR #717 codex-toc fix landed during session 9). Phase 1.5 work happens off `schema/g7-trust-magnitude` (PR #726) and `cli/trust-magnitude` (PR #728), both **DRAFT** pending #730.
- **Phase 1.5 lane state (Day 1, Lane A):**
  - **PR #726** (DRAFT) — schema/g7-trust-magnitude. Adds `trustMagnitude`, `overallTrustGrade`, `apexGateStatus` (8 predicates: 6 boolean + 2 nullable for the OFF flags), `provisional`, `provisionalUntil`, `evidence[].grade`, `evidence[].sourceStartedAt`, `links.canonicalRepo`, `cosigners` to skill schemas. `meta.json` gains `trustMagnitudeThresholds` + 10-type taxonomy + `apexGate` block. Bundled mirror synced. **No version field** (reverted; coordinated bump at end of Phase 1.5). Block comment posted referencing #730. Branch-scope override carried via `skip-scope-check` label.
  - **PR #728** (DRAFT) — cli/trust-magnitude. `src/gaia_cli/trustMagnitude.py` (904+ lines, 51 tests). All 6 active predicates + 2 OFF scaffolds + anti-auto-mint + role=variant zeroing + #729-strict `checkAGradedOriginsGte5` (walks fusion-recipe origins ∪ `suiteComponents`, dedup, count A/S-graded). **Does NOT honor evidence inheritance** — that gap is what #730 blocks on.
- **Open issues / blockers:**
  - **#730** (NEW, blocking) — *G7 RFC missing inheritable-evidence policy.* Production CLI (PR #690) already implements `evidence.py::inherited_evidence(named, generic)` returning own ∪ inherited; `promotion.py::_effective_grade` and `verification.py::effectiveGrade` honor it. Schema prose at `registry/schema/skill.schema.json:88` mentions inheritance. **G7 RFC and delta are silent.** `trustMagnitude.py` reads only `skill.evidence[]` → regression vs deployed. **This is now the gating issue for all Phase 1.5 merges.**
  - **#729** RESOLVED (founder ruling 2026-06-17): `aGradedOriginsGte5` is **strict graph-walk over fusion-recipe origins**, AND **suite components count as fusion structure**. I2 patched at commit `1da9a820`. Issue stays OPEN until I3 lands per founder directive.
  - **#727** (open, no urgency) — infra: widen schema/ branch-scope to allow CLI loader updates without `skip-scope-check`.
- **Founder's inheritance anchor (verbatim, 2026-06-17):** *"Only SOME types inherit from parent starless (generic), and SOME types are named only. Note that one generic can have multiple named skills. I suggest types like Arxiv will be generic-only, while others will be named only. This consensus will be deciding which is which, and if magnitudes will change (I doubt it will, but challenge this). You are free to propose multiple types, just be clear on how this will all work."* Patch scope = **targeted RFC patch** (single dedicated section, not a full consensus workflow).
- **Next action:** Author the targeted RFC patch in `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` — propose partition of the 10 evidence types into generic-only / named-only / both buckets with rationale; address whether magnitudes change; clarify how multiple named skills under one generic interact; cross-reference §3 (formula = effective pool), §4 (rank-floor = effective pool), §10 (anti-auto-mint operates over union). Then companion delta amendment so all I2 magnitude functions operate on the effective pool. Sonnet drafting pass + Opus integrating pass. Present to founder for ratification before unblocking PR #726/#728.
- **Phase 1.5 Day 2 (I3 + I4) and Day 3 (I5/I6/I7) all paused** until Lane A merges. I3 (`registry-wide migration`) **must walk the effective pool** once the inheritance policy is ratified; that's an I3 amendment item.
- **Stop hooks reminder:** Marco visually inspects all design-surface PRs (I6, I7) before merge.
- **Hermes-owned files** continue to be off-limits for any I-task agent.

## State Snapshot (2026-06-17, session 8 closeout — PRs #713 + #714 merged)

- **Repo:** `mbtiongson1/gaia-skill-tree` on `main` @ `10e8c4dd`, version **v4.9.5** (no chore release yet from squash merges; release workflow next run will bump to v4.9.6 per skip-gen pattern).
- **Just merged 2026-06-17:**
  - **PR #713** (`bbf7a5d1`) — homepage Evidence Grade Cycle restore + G7 supersession meta-post. Squash merge.
  - **PR #714** (`10e8c4dd`) — Trust Report Links + Upgrade Path cards; skill-explorer.js IIFE scope-leak fixes; new "Known Skill Explorer Issues" section in `CLAUDE.md`. Squash merge.
  - Diff vs prior main `e278afbd`: +1010 / -43 across 8 files. All content from both branches preserved (verified via `git diff --stat`).
- **Milestones:**
  - **#4 Phase 1** (CLOSED 2026-06-16T16:15:53Z): 0 open / 17 closed. G1–G7 all shipped (#703–#709) plus meta-sync #711.
  - **#7 Next-30** (due Jul 10): **6/8 closed**. Open: #697 (Rising Skills), #698 (Rising Repos).
  - **#5 Phase 2**: holds #654 (evidence-type RFC) — overlaps with G7 §3-§7 10-type taxonomy; needs cross-link or supersession.
  - **#6 Phase 3**: untouched.
  - **NEW: Phase 1.5 — G7 Implementation** (proposed, not yet filed) — to host the 6-PR arc per `handovers/G7_IMPLEMENTATION_HANDOVER.md`.
- **Trust model — DEPLOYED state (legacy / pre-G7):** unchanged from session 7. registry/schema thresholds are S≥90 / A≥80 / B≥60 / C≥40 per-row trust-number; meta.json declares legacy 3 evidence types (arxiv, repo, github-stars); registry/named-skills.json carries `overallTrustGrade` (A/B/C, no S) but no `trustMagnitude` field; `ultimateGateStatus` is the legacy single-component-S check. 183 skills, level distribution 1★:21 / 2★:93 / 3★:32 / 4★:31 / 5★:4 / **6★:2** (`mattpocock/skills`, `ruvnet/ruflo`). 4-tier verification skeleton shipped via PR #709 but uses `maxGrade` not `trustMagnitude`.
- **Trust model — RFC state (G7, NOT propagated):** `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` (1119 lines, on this branch only) defines Trust Magnitude with thresholds S≥250 / A≥100 / B≥50 / C≥20, 10-type evidence taxonomy, 9-predicate apex gate (§10.12), anti-auto-mint clause (§10.14), §11.12 disposition table requiring both currently-6★ skills to demote at cutover. **Zero schema, code, registry, or display work has landed against G7.** Apex slots state: 2 of 5 filled (should be 0 of 5 post-cutover).
- **Open PRs:** none. Both #713 + #714 merged. PR #715 will be the first G7-implementation PR (schema/), per the handover.
- **Closed PR:** #712 (false-restore, `.ev-node` flat tile design + provenance dispute now corrected via apology comment); commits live as deleted-branch ancestors `074c4715` / `025ac91a` (real, unreachable).
- **Auth:** unchanged from session 4. PR #669 device flow + PR #682 honest-revoke both merged 2026-06-14.
- **Project board #2:** 22 in Done after Phase 1 closeout (session 6). #128 manually moved; #637 / #647 / #654 left as Todo intentionally per H2/H4/H5.
- **CI:** path-filter fix landed via PR #703 (G1) on 2026-06-16; data-only PRs now trigger tests. Workers Builds + branch-scope green on PR #713.
- **Tooling:** gh CLI in sandbox; PAT re-provided 2026-06-16 (used inline only, never persisted).
- **Branch state:** `dev/orchestrator-phase1-closeout` rebased onto origin/main this session (was 7 behind); 3 founder commits replayed cleanly; force-pushed.



## Phase 1 Closeout Plan (active — see `handovers/PHASE1_MASTER.md`)

Replaces the old 8-PR plan (archived to `handovers/done/00_PHASE1_COMPLETION_PLAN.md`). Reality check on 2026-06-16 found:

- **PR-8 (auth logout)** already shipped as #682 — done.
- **PR-7 (CI fix)** partially landed: `pull_request:` exists but `registry/**` not in path filter. Re-scoped to G1.
- **PR-1 (rank gates)** floors exist on legacy `class`; new `grade` field not consulted in `_meets_evidence_floor`. Re-scoped to G2 — small translation patch, not greenfield.
- All 8 old per-PR handovers archived to `handovers/done/`. One unified spec lives at `handovers/PHASE1_MASTER.md`.

| G# | Title | Issue | Effort | Agent | Lane | Blocked by |
|---|---|---|---|---|---|---|
| G1 | CI: include `registry/**` in path filter | new (H7A) | XS | Haiku 4.5 | A | — |
| G2 | Rank gate `class`→`grade` translation | #699 | S | Sonnet 4.6 | A | — |
| G3 | Security Scanner | #185 | L | Opus 4.8 | C | — |
| G4 | Verification Workflow (folds #650) | #658 | L | Opus 4.8 | C | G2, G3 |
| G5 | Share static page | new (fast-follow of closed #128) | M | Sonnet 4.6 | B | — |
| G6 | Narrow-path tree render | #642 | S | Sonnet 4.6 | B | — |
| G7 | Benchmark RFC | #649 | M (research) | Opus 4.8 xhigh | D | — |

Lanes A/B/D run in parallel on day 1; Lane C (G3 → G4) runs sequentially after G2 + G3 land.

## Hygiene Batch 2026-06-16 (drafted; awaiting Marco approval)

Full draft at `handovers/HYGIENE_BATCH_2026-06-16.md`. Summary:

- **H1**: fold #650 into #658 (close as duplicate).
- **H2**: remove #647 from milestone #4 (keep open for DB-specialist contributors).
- **H3**: post 1-pager comment on #647 (git-as-DB strategy + migration triggers).
- **H4**: remove #637 from milestone #4 (RFC-only, not a Phase-1 gate).
- **H5**: move #654 to milestone #5 (Phase 2 scope) + label `phase-2`.
- **H6**: add #699 to milestone #4 + amend with G2 scope note.
- **H7A**: open new G1 issue (CI registry path filter).
- **H7B**: add #642 to milestone #4.
- **H8**: schedule mid-July recalibration RFC reminder (CronCreate, durable).
- **H9**: label sweep — add `phase-1` to #185, #642, #649, #658, #699 + new G1 issue.

After execution: milestone #4 contents = exactly {#185, #642, #649, #658, #699, NEW G1} = 6 open items, mapping 1:1 to G1–G7.

## Open Questions / Waiting On (current)

- [x] ~~Marco approval on `HYGIENE_BATCH_2026-06-16.md`~~ — H1–H9 executed in session 6, milestone #4 closed.
- [x] ~~Marco green-light on `PHASE1_MASTER.md` G1–G7~~ — all 7 PRs (#703–#709) merged in session 6.
- [ ] **G7 implementation arc — DECISION + PRIORITIZATION needed.** Audit `w2co0ee1p` (2026-06-17) confirms zero G7 propagation. To get "ALL trust scores adhering to G7 RFC, all skill ranks show as designed" (Marco's stated goal) requires roughly 6 PRs in dependency order: (1) **schema** — add `trustMagnitude`, `overallTrustGrade`, `apexGateStatus` (replaces `ultimateGateStatus`) to skill.schema.json + namedSkill.schema.json; update meta.json `evidence.gradeThresholds` to 250/100/50/20 (or rename to `trustMagnitudeThresholds` and keep both layers explicit); replace `evidence.types` legacy 3 with G7 10-type taxonomy + per-type caps; add `apexGate` block with 9-predicate spec + system-wide cap=5; remove `alternativePathways."6★".apexPath`. (2) **CLI computation** — `src/gaia_cli/grading.py::trust_magnitude()` per §3 formula; `_passes_apex_gate(skill)` per §10.12; anti-auto-mint enforcement per §10.14 (skip phantom rows derived from `suiteComponents`/`fusionRecipes`); K=2 cosign tracking via `gaia dev evidence --cosign-with`; 180-day tenure baseline. (3) **Migration script** — `scripts/migrate_trust_magnitude.py` runs strict-evidence regrade across all 220 skills, writes `trustMagnitude`/`overallTrustGrade`/`apexGateStatus`/`verification.tier` into frontmatter, regenerates named-skills.json. (4) **Apex cutover** — demote `mattpocock/skills` (failed §11.12.3, .4, .5, .6) and `ruvnet/ruflo` (failed §11.12.4, .6) from 6★→5★ with timeline events (`gaia dev reclassify` if it supports level changes, else direct edit + `gaia dev timeline --action demote`). (5) **CI enforcement** — extend `.github/workflows/meta-guard.yml` with system-wide 6★ cap + apex-promotion label requirement + 2 verifier approvals. (6) **Display layer** — extend `scripts/generateNamedIndex.py` to write `trustMagnitude` per entry; update treeManager to surface TM badge alongside level; reconcile /evidence/ Bronze/Silver/Gold/Platinum filter chips with real `grade` values. **Decisions outstanding before dispatch:** (a) Should this run as one big migration PR or be staged across 3–6 PRs? (b) New milestone (Phase 1.5 / G7 Implementation), or fold into milestone #5 Phase 2? (c) Once `trustMagnitude` lands, do shipped row-level grades persist or do they get re-derived from the new aggregate formula?
- [ ] **Skill Explorer modal `#se-description` mount (silent failure).** `docs/named/index.html` doesn't declare the mount; `docs/js/skill-explorer.js:127` early-returns null; entire "About this skill" panel including Prerequisites + Unlocks invisible on every per-skill modal. **Same silent-failure pattern as the badges page bug noted in CLAUDE.md.** Fix: add `<div id="se-description" class="se-flow-section"></div>` to the .se-flow container + promote the early-return to `console.warn`. Also accept `?s=` synonym in `report.html::getSkillId()` to be forgiving of share links. Pre-existing bug, NOT a 025ac91a regression. Tracked as session 7 Task #17. Branch name when dispatched: `design/skill-explorer-mounts`.
- [ ] **Phase 2 issue #654** ("RFC: Evidence types — expand beyond arxiv/repo/stars") overlaps with G7 §3-§7 10-type taxonomy. Cross-link to G7 RFC so Phase 2 work consumes the same list (otherwise schema PR-1 above will conflict).
- [ ] **Mid-July recalibration RFC** (cron `2076efa7`, durable, fires 2026-07-10 09:03 local) — folds in pillar-rule threshold review + G7 implementation findings + any G2/G3/G4 surface findings.
- [ ] **#155 follow-up** — `gaia logout` server-side revoke is permanently a no-op without client_secret; PR #682 made it honest. Phase 2 decision still pending: do we ever want full revoke (requires Worker / proxy with secret)?
- [ ] **Token spend logging directive** (PR #695): each agent + this orchestrator session must log model + tokens to the relevant PR/issue at end-of-session. Apply going forward.

## Assets Inventory (current)

- `handovers/PHASE1_MASTER.md` — **active master plan** for G1–G7 closeout.
- `handovers/HYGIENE_BATCH_2026-06-16.md` — drafted GitHub-state changes (H1–H9), awaiting approval.
- `handovers/done/` — archive of 19+ historical handovers (8 obsolete PR-1..PR-8 specs, old plan, RFCs, completed sprint specs, methodology report).

## Session Log

- **2026-06-18 (session 9 day-4 — Lanes B+C complete, I8 designed, dev/* consolidation)** — All 6 Phase 1.5 PRs confirmed CI-green and open. I8 issue #740 filed and spec written to `founder/handovers/phase-1.5/issues/I8.md` via `/impeccable` design planning pass: Trust Grade notch (bottom-right rectangular metallic corner stamp, grades S/A/B/C = Platinum/Gold/Silver/Bronze) on all 6 `.plaque` variants. Platinum gets animated diagonal shimmer sweep (3.5s, `prefers-reduced-motion`-safe); ungraded shows nothing. Sampler page: `docs/samples/trust-grade-notch.html`. Source: `generated-output/i8-issue-body.md`. Dispatch held — Marco said "tomorrow." Created `dev/phase-1.5-inspection` consolidation branch (merging all 6 PR branches in dependency order: I4 → CLI-fix → I3 → I5 → I7 → I6) and pushed to origin for visual inspection before individual PR merges. MEMORY.md + I8 handover file written. CLI gap #739 (Windows cp1252 encoding bug in `timeline.py`) remains open. **Token spend (session 9 day-4):** ~$0.62. Cumulative G7: ~$18.92.

- **2026-06-18 (session 9 day-3 — Phase 1.5 Lane A merged, v4.11.0 shipped)** — Founder ratified the 5 v2 multipliers without modification ("verdict passed ✅, numbers are final, you can breathe"). Single Sonnet rewrote v1 → v2 in both handover files (RFC 1198→1241 lines, delta 307→359 lines): §0 bullet 13, §2.1 master table (Inherits¹ → `allowedLayers` + `inheritMultiplier`), §2.14 (full 7-subsection rewrite), §3 formula (`× inheritMultiplier(e, skill)` term added), §4, §10.14, §10.15, and § Section H (H.1–H.7) all rewritten. All 5 ratified values (0.70 / 0.30 / 0.35 / 0.25 / 0.15) + `inheritMultiplier` (32 mentions) + `allowedLayers` (25 mentions) verified present; no v1 prose survived in normative sections. Dispatched both PR amendment agents in parallel with worktree isolation: **PR #726 amend agent (Sonnet)** delivered cleanly (commit `8dbd47c1` — 9 files, 59/59 tests, full v2 schema with row-level layer + validator). **PR #728 amend agent (Opus 4.8)** hit token cutoff at ~105k subagent tokens mid-`explainTrustMagnitude`, with 151 lines of mid-edit `trustMagnitude.py` work uncommitted in worktree `agent-a0c863432787e5c8c`. **Salvage:** stashed unrelated drift, committed-and-pushed regression fix as `849b42b4` from the orchestrator directly. Re-dispatched continuation as Sonnet with explicit split-commit discipline ("commit + push at each checkpoint"); delivered `1eaa174b` (explain verb) + `4be667f6` (5 inheritance tests, 56/56 green). **Cutoff lesson logged in `founder/CLAUDE.md`** as a 7-rule playbook (split commits, push-after-each, worktree isolation, token budget hints, SHA reporting, salvage path). **Founder greenlit Path A merge.** Marked both PRs ready, applied `skip-scope-check` label per new standing approval, squash-merged: **#726 at 09:27 UTC** (auto-released v4.10.0 as `ee2ea319`) and **#728 at 09:31 UTC** (auto-released v4.11.0 as `31bf0bdd`). **Auto-closed** #719 (I1), #720 (I2), #729 (spec clarification). **Manually closed #730** (inheritance gap) with full resolution comment citing both merge SHAs. Pruned both worktrees; deleted both branches local + remote. **Phase 1.5 milestone #8 now 6/11 closed (54%)** — remaining: I3 (#721), I4 (#722), I5 (#723), I6 (#724), I7 (#725). **Standing approvals NEW today, logged in `founder/CLAUDE.md`:** (1) `skip-scope-check` label is pre-authorized for any PR being merged when branch-scope blocks; (2) cutoff-safeguard playbook for all future code dispatches. **Founder's data lake noted:** `founder/sources/` lives on `origin/dev/sources` (not main), 25 files of pre-collected evidence typed against the 10 canonical types; founder instruction: always verify before importing. **Token spend (session 9 day-3):** Opus 4.8 orchestrator ~30k in / ~10k out / ~$1.05 + 5 dispatch agents (1 Sonnet RFC v2 rewrite + 1 Sonnet schema amend + 1 Opus CLI amend [cutoff, salvaged] + 1 Sonnet CLI continuation + 1 Sonnet PR comment work) ~530k subagent / ~$3.05 = **~$4.10 this session**. Cumulative G7 implementation **~$18.30**. **Next session entry path:** dispatch Lane B (I3 Opus + I4 Sonnet, parallel) — both blocked on Lane A which is now merged. I3 must operate on the effective pool and add the partition-repair pass per § Section H.4. I4 must enforce `systemWideCap=5` in `meta-guard.yml`.

- **2026-06-18 (session 9 day-2 — inheritance model reshaped, multipliers under adversarial review)** — Founder reshaped the inheritance model away from yesterday's rigid 1/9 partition into a layer-as-row-property model: every type declares `allowedLayers`; flexible types can sit at either layer; inherited rows take a per-type `inheritMultiplier`; full multiplier chain must be debug-visible. Orchestrator drafted 5 multiplier values (arxiv 0.8, peer-review 0.4, social-signal 0.5, proxy-containment 0.3, benchmark-result 0.2) and surfaced two ratification questions. Founder requested adversarial workflow on the multipliers. Dispatched **`wf_7cbe217f-006`**: 3 Sonnet stances (defender / higher / lower) × 5 multipliers + 5 Sonnet synthesizers = 20 agents, 696k subagent tokens, ~2 min, ~$2.30. **All synths converged DOWN from drafts** — arxiv 0.8→0.7, peer-review 0.4→0.3, social-signal 0.5→0.35, proxy-containment 0.3→0.25, benchmark-result 0.2→0.15. All 5 marked `riskLevel: medium`. Type ordering after synth: arxiv > peer-review ≈ social-signal > proxy-containment > benchmark-result, encoding "capability-native claims project most cleanly; benchmark percentiles bind least cleanly to siblings." N-child amplification math was the load-bearing argument across all 5 stance bake-offs. Yesterday's v1 RFC patch (rigid 1/9 partition, no multiplier) is SUPERSEDED — sits in the RFC as obsolete prose pending rewrite to v2. Founder reviews the 5 synth values, then dispatches a Sonnet to rewrite RFC §2.14/§3/§4/§10.14/§10.15/§0 bullet 13 + delta §H to v2 spec. Then unblock PR #726/#728. **Token spend (session 9 day-2):** Opus 4.8 orchestrator ~25k in / ~10k out / ~$0.85 + Sonnet workflow 696k subagent / ~$2.30 = **~$3.15 this session**. Cumulative G7 implementation ~$14.20.

- **2026-06-17 (session 9 closeout — Phase 1.5 dispatch, inheritance-gap discovery, RFC-patch parking)** — Dispatched Lane A: I1 (Sonnet 4.6) + I2 (Opus 4.8) per `G7_IMPLEMENTATION_HANDOVER.md` + `G7_HANDOVER_DELTA_2026-06-17.md`. **I1 → PR #726** (schema/g7-trust-magnitude): hit branch-scope failure on first push because agent included CLI loader files; resolved with `skip-scope-check` label (founder approval) + filed #727 to widen schema/ scope long-term. CI green; design-system lint guards green. **I2 → PR #728** (cli/trust-magnitude): two timeouts before tests stabilized; resolved via "commit-and-push-aggressively" re-dispatch strategy (open PR after first commit, push test batches incrementally). 51 tests, 904+ lines. `aGradedOriginsGte5` implementation initially counted any A/S row across the registry; reviewer flagged strict-graph-walk as likely intent. Filed **#729** for spec disambiguation; founder ruled **strict + suite components count as fusion structure** ("FUSION structure is present even with SUITE COMPONENTS fusion alone... if among these origin skills there are 5 A / S grades, the GATE OPENS"). I2 patched at commit `1da9a820`. Issue #729 stays OPEN until I3 lands. Two parallel Opus reviewers cleared blocking findings; founder directive: "PLEASE don't update to 5.0.0 — prevent this from happening! This will be done once all of phase 1.5 ships." Reverted I1's `version: "5.0.0-schema"` field entirely. **Both PRs minutes from merge when the inheritance gap was discovered:** founder asked, *"I need to know if the inheritable evidence policy is here, both in G7 and in the schema."* Verified: production CLI deployed inheritance via PR #690 (`evidence.py::inherited_evidence`, `promotion.py::_effective_grade`, `verification.py::effectiveGrade`); schema prose at `skill.schema.json:88`; **G7 RFC silent** (one incidental mention at line 653 about quarterly batches); **delta silent**; **`trustMagnitude.py` reads only own `evidence[]`** → regression vs deployed. Filed **#730** capturing the gap with full analysis. Converted **PR #726 + #728 to DRAFT**, posted block comments referencing #730. Founder chose **"Block + RFC patch first"** path with anchor: *"Only SOME types inherit from parent starless (generic), and SOME types are named only... Arxiv will be generic-only, while others will be named only... one generic can have multiple named skills... challenge whether magnitudes change."* Patch scope = **targeted RFC patch** (single dedicated section, NOT full consensus workflow), ~$1-2 budget. Phase 1.5 Day 2 (I3+I4) and Day 3 (I5/I6/I7) paused. **Token spend (session 9 closeout):** Opus 4.8 orchestrator ~80k in / ~25k out / ~$2.40. Sonnet 4.6 I1 agent ~110k subagent / ~$0.45. Opus 4.8 I2 agent ~180k subagent / ~$3.00. 2× Opus reviewers ~70k each / ~$1.80. Phase-1.5-day-1 total this session ~$7.65; cumulative G7 implementation ~$11.05.

- **2026-06-17 (session 9 — apex gate amendments, mattpocock audit, Codex page)** — Posted issue #715 (RFC G7 verification pass) and follow-up comment with mattpocock/skills deep-dive (40 evidence rows from 3 Sonnet curation agents, deterministic `scoreGates.py` scorer, role='origin' discovery). **Marco's seven amendments (final):** (1) tenure → source-based, A/S-tier rows only; (2) `aGradedOriginsGte5` consolidates prior `transitiveOriginsGte12` + `aGradedClosureGte8`; (3) `crossOrgVerifierGte2` REMOVED (re-enable when ecosystem grows); (4) `systemWideCapRespected` (cap=5) REMOVED; (5) depth-2 reachability is fusion-only (role='origin' filter); suite components excluded; (6) Marco PR-signs at big-bang migration; (7) NEW I7 PR — Codex methodology page at `docs/codex/trust-methodology.html`, fully DESIGN.md/CONTEXT.md compliant, 963 lines. **Net amended gate:** 6 predicates (was 9). **mattpocock/skills under amended gate: 3/6 passing** — failing aGradedOrigins (4/5; needs one more A-grade among engineering/grill-with-docs/personal/productivity), depth2-only (0; everything is direct-listed), apexPromotionPrSigned (intentional). Source-tenure passes at 1385 days (A-tier @total-typescript/ts-reset npm row, published 2022-09-01). All five proposals + synthesis-plus put TM at S (1023-1419 range); apex gate is load-bearing, not stance choice. Token budget delta: $11.68 → ~$12.88. **Artifacts:** `founder/handovers/g7-mattpocock-audit/` (40 evidence rows + scoreGates.py + _scores.json + _snapshot.json + _issue_comment.md + _issue_comment_v2.md + _workflow_notes.md), `founder/handovers/G7_HANDOVER_DELTA_2026-06-17.md` (15kb delta to merge into G7_IMPLEMENTATION_HANDOVER.md), `docs/codex/trust-methodology.html` (38kb new page, ready for I7 PR). **Token spend (session 9):** Opus 4.8: ~150k in / ~40k out + 4× Sonnet 4.6 background: ~150k subagent. Combined ~$6.50.

- **2026-06-17 (session 8 verification pass — four-proposal artifacts recovered, RFC verification issue drafted)** — Marco's request: "recall the dynamic workflow we first launched to set up RFC G7 (the one with community, strict, etc.)—there were 4 proposals. I need those files in case I want to revisit RFC. Create an actual RFC GitHub issue for all four, specifically highlight their differences and the judges response and I'll compare. I was worried since 6 star apex may or may not have been included in the proposals. Park Phase 1.5 G7 implementation as the 'current winner' of those proposals. Park as well other dependencies we might trace back to (from G2 to G6 is that correct). Note that this is a verification pass from me, before we do the big bang implementation."

  **Source workflow recovered:** `wf_6e5a4374-b85` (Wave A `g7-trust-taxonomy-consensus`, 21 agents, 1.12M subagent tokens, 2026-06-16 session 5). Script lives at `C:\Users\C5396183\.claude\projects\C--Users-C5396183-gaia-skill-tree-founder-handovers\80db7142-5240-4034-ae6d-0c80d7b61136\workflows\scripts\g7-trust-taxonomy-consensus-wf_6e5a4374-b85.js`. Transcripts at `subagents/workflows/wf_6e5a4374-b85/agent-*.jsonl` (61 agents total).

  **Artifacts extracted to `founder/handovers/g7-proposals/`:** All four proposer `StructuredOutput` payloads (P1-strict-S 19kb / P2-attainable-S 17kb / P3-fusion-heavy 22kb / P4-community-heavy 24kb), all 12 judge verdicts (3 lenses × 4 proposals; **all 12 refuted**, scores 3.17–4.50), and the synthesizer output (21kb) that became the RFC.

  **Key verification finding — apex gate origin clarified:** None of the four proposals built the **9-predicate hard apex gate** or the **system-wide cap of 5**. All four mention apex/Ultimate/6★ in passing; their treatments diverge wildly (P1 forces all Ultimates to A; P2 lets both 6★ skills hit S via fusion-only relaxation; P3 lets ruvnet/ruflo hit S via fusion-recipe alone; P4 lets ruvnet/ruflo hit S via fusion+stars). The apex gate (§10.11–§10.14) was added by the **separate session-6 audit workflow** `wf_f14f7317-972` (7 agents, 595k tokens, AFTER synthesis). Implication: if Marco swaps the synthesis winner, the 9-predicate gate + cap=5 + anti-auto-mint clause **survive the swap** — independent additions, not load-bearing on stance.

  **Verdict tally per proposal (all refuted by all 3 lenses):**
  - P4 Community-Heavy: avg 4.50 (structural winner)
  - P1 Strict-S: avg 4.33
  - P2 Attainable-S: avg 4.00
  - P3 Fusion-Heavy: avg 3.17 (lowest)
  - Synthesis: P4 base + P1+P3 grafts; thresholds reverted to baseline 250/100/50/20.

  **Issue draft authored:** `founder/handovers/G7_VERIFICATION_ISSUE_DRAFT.md` (~16kb). Per founder/CLAUDE.md "Every GitHub write... drafted first and executed only after Marco approves" — issue is staged, not posted. Body covers: TL;DR comparison table; per-proposal stance + judge weaknesses; **§2 6★ apex coverage matrix** (P1/P2/P3/P4/synthesis vs session-6 additions); §3 implementation handover parked as "current winner"; §4 dependency traceback G1→G7 to I1–I6 (G2 #704 grade-fallback feeds I2 `_effective_grade`; G4 #709 verification-tier feeds I2 enterpriseReady predicate; G3 scanner needs to wire `security_scan_passed` events for I3 backfill; G6 narrow-tree compat for I6); §5 four verification questions (Q1: pick anchor; Q2: keep apex gate; Q3: keep anti-auto-mint; Q4: re-run consensus?).

  **Phase 1.5 implementation handover parked behind verification pass.** No I1/I2 dispatch until Q1+Q2+Q3 nodded.

  **Token spend (session 8 verification pass — this turn):** Opus 4.8 orchestrator ~70k in / ~18k out / ~$2.10.



  **Merged (squash):**
  - **PR #713** (`bbf7a5d1`) — homepage Evidence Grade Cycle restore + G7 supersession meta-post (3 commits collapsed: `cee7c66c` + `07f25788` + `af3d411d`).
  - **PR #714** (`10e8c4dd`) — Trust Report Links + Upgrade Path cards; skill-explorer.js IIFE scope-leak fixes; "Known Skill Explorer Issues" section in `CLAUDE.md` (2 commits collapsed: `b9b88250` + `8aad1656`).
  - Verified via `git diff --stat e278afbd..origin/main`: +1010 / -43 across 8 files (CLAUDE.md, docs/index.html, docs/js/skill-explorer.js, docs/meta.html, docs/meta/posts.json, docs/meta/2026-06-17-g7-trust-magnitude-supersession.md, docs/meta/reports/2026-06-17...html, docs/named/report.html). All content from both branches preserved; nothing lost.
  - Both PRs were CI-clean (`mergeStateStatus: CLEAN`, `mergeable: MERGEABLE`); design-system lint guards green; branch-scope check green; Workers Builds green.

  **G7 implementation handover drafted:** `founder/handovers/G7_IMPLEMENTATION_HANDOVER.md` (~13kb, structured like `PHASE1_MASTER.md`). Sequences the six implementation PRs (I1 Schema → I2 CLI computation → I3 Migration script → I4 CI enforcement → I5 Apex cutover → I6 Display layer) with dependency lanes (A/B/C/D/E), agent-model recommendations (mostly Sonnet 4.6, Opus 4.8 for I2 + I3), per-PR specs with acceptance criteria, ≥30-test roster for I2, anti-auto-mint enforcement (RFC §10.14) wired into I2 and I3, apex-cutover plan respecting CLAUDE.md "Never modify data files without approval" by routing through `gaia dev reclassify` + timeline events, ~$11.68 token budget estimate.

  **Three pre-resolved decisions in handover §1:**
  - **Decision A:** Six staged PRs, NOT one big PR. Big-bang regrade lives inside I3; everything else is staged for review.
  - **Decision B:** New milestone `Phase 1.5 — G7 Implementation` (#8 proposed); do NOT fold into Phase 2 (#5). Phase 1 closed without G7 propagation — that's a hole in Phase 1, not a Phase 2 deliverable.
  - **Decision C:** Per-row evidence grades persist verbatim; aggregate (`trustMagnitude`, `overallTrustGrade`, `apexGateStatus`) is re-derived. Anti-auto-mint clause is the only exception (phantom rows removed).

  Marco overrides any decision before dispatch by editing §1 of the handover; the orchestrator's job is to draft, not to decide. The handover §9 Dispatch Checklist is the next-action list once Marco nods.

  **Cross-references handled:** Phase 2 issue #654 (evidence-type RFC) is superseded by I1 (10-type taxonomy lands in schema); H3 in the handover hygiene block closes #654 with a supersession comment. Skill Explorer `#se-description` mount fix (Task #17, design/skill-explorer-mounts) is left as an independent branch. Mid-July recalibration RFC (cron `2076efa7`) folds in I1–I6 surface findings. Hermes-owned files explicitly listed as forbidden territory for any I-task agent.

  **Token spend (session 8 closeout — this turn):** Opus 4.8 orchestrator ~50k in / ~12k out / ~$1.50.



  **(A) `docs/named/report.html` — two new cards.** Trust Report shipped in PR-4 (#694) was missing **Links** and **Upgrade Path** cards (per `GAIA_ROADMAP v2 (BUILD).md` line 268 "score explanation page" — Phase 1 deliverable). New `renderLinksCard` reads `skill.links.{github,npm,docs,homepage,arxiv}`. New `renderUpgradeCard` reads `generic.prerequisites/derivatives` from a best-effort `docs/graph/gaia.json` fetch (every other card still renders if the graph fetch fails). `renderSkill(skill, skillMap)` now takes the generic-skill map built in `main()`; CSS reuses existing `.report-card` patterns plus ~40 lines of `.upgrade-chip-row` / `.links-list` rules.

  **(B) `docs/js/skill-explorer.js` — IIFE scope-leak class caught.** The file is split into TWO IIFEs (lines 1-1862 + 1864-end) that don't share scope. When the user tested PR #714's defensive try/catch wrapping, "Docs section unavailable" surfaced — turned out to be a 4-month-old latent bug:
    1. **`renderDocs` at line 619 called `getRootPath()` which is defined ONLY inside IIFE #2 at line 1982** — ReferenceError on every modal open. Cascaded with no try/catch in the original code, so renderFlowchart + renderTimeline never ran. The new `_safeRender` wrapper from PR #714 intercepted the cascade and exposed it as a single dead section. **Fix:** duplicated `function getRootPath()` inside IIFE #1 (right after `findGeneric`).
    2. **`openTreeDialog` at line 1949 referenced an undeclared `version` identifier** — silent ReferenceError from the Skill Tree click handler; dialog stayed empty. **Fix:** added `var version = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';` mirroring the helper at `docs/js/named-skills.js:468`.
    3. **`_seBodyOriginalHTML` lazy-snapshotted live `.se-body` markup** on first modal open, restored that potentially-mutated snapshot on every subsequent open. **Fix:** replaced with constant `SE_BODY_SKELETON` template literal at IIFE #1 top.
    4. **Render call chain at `openExplorer:1601-1607` had no try/catch.** **Fix:** wrapped each call in `_safeRender(name, mountId, fn)`. Section "Section unavailable" notice + console.error on throw, sibling sections still render.

  **Documented for the future:** added a **"Known Skill Explorer Issues"** section to `CLAUDE.md` listing the 4 specific bugs and 4 forward-looking rules: (1) confirm same-IIFE scope before referencing top-level functions; (2) no undeclared identifiers in fetch URLs; (3) keep `_safeRender` wrapping; (4) don't snapshot live DOM. Plus a verification rule: after any `skill-explorer.js` edit, manually click a skill and confirm all 5 sections render + topbar buttons all open.

  **PR #714 state:** OPEN, MERGEABLE, awaiting CI. Branch `design/skill-page-restore` off `main`. Commit `b9b88250` for PR-4 gap fill, follow-up commit incoming for the IIFE-scope fixes.

  **Token spend (session 8 so far):** Opus 4.8 orchestrator ~135k in / ~14k out / ~$2.95. Sonnet 4.6 Explore subagent (failure-mode diagnosis) ~50k in / ~3k out / ~$0.20. Total ~$3.15.

- **2026-06-17 (session 7 — site investigation, restore PR #713, G7 propagation audit, meta-post)** — User flagged "I see all missing content" + "evidence grade cycle is the old one". First-pass investigation (workflow `wf_c982e9b7-966`, 4 probes) misdiagnosed: I called SHAs `074c4715` and `025ac91a` "fabricated" because they don't resolve locally; closed PR #712 on that basis. **Wrong.** User pushed back; second probe (`wxeuk9br0`, 4 probes) confirmed `025ac91a` resolves via `gh api` (parents `6d1a1311` ← deleted `claude/serene-einstein-2urxwa` branch + `e581ffd1` ← origin/main pre-merge). It's an unreachable-but-real merge that silently dropped 329 net lines from `docs/index.html`, including the entire `<section id="evidence-cycle">` PR-4 had introduced. Posted apology comment on closed #712. **Recalibrated:** PR #713 (`design/homepage-evidence-cycle`, three commits — `cee7c66c` restore + `07f25788` link 06-14→06-15 swap + `af3d411d` meta-post) restores: (1) hero CTA pill Trust Model link, (2) Meta Reports queue tile for Trust Methodology, (3) `<section id="evidence-cycle">` between #ascension and #meta-reports using PR-4's `.grade-bar`/`.grade-segment` metallic vocabulary. **Calibrated against G7 RFC §0** (S≥250/A≥100/B≥50/C≥20 Trust Magnitude, not the deprecated per-row 90/80/60/40); stripped "Class C/B/A/S" subhead clause; dropped `%` glyph (trust-numbers are unitless). All 5 user-facing references repointed from the 06-14 stub (331 lines) to the 06-15 full report (1182 lines) — both shipped together in PR-4 (#694) but the canonical was the 06-15 file. **G7 propagation audit (`w2co0ee1p`, 4 probes, 5 agents, 308k subagent tokens):** verdict — **G7 is RFC-only; nothing has propagated.** Schema has the 4-tier verification enum + 90/80/60/40 thresholds + legacy `ultimateGate`; missing every other G7 primitive (no `trustMagnitude` field, no `apexGateStatus`, no 9-predicate fields, no 10-type taxonomy — meta.json still declares the legacy 3 types `arxiv|repo|github-stars`). Registry data: zero named skills carry `trustMagnitude`/`verification.tier`/`apexGateStatus`/`provisional`. Both currently-6★ skills (`mattpocock/skills`, `ruvnet/ruflo`) still served at 6★; `§11.12` cutover NOT applied. CLI: zero G7 implementation — no `_passes_apex_gate`, no `check_apex_gate`, no `trust_magnitude()` aggregator, no anti-auto-mint enforcement. Display: `treeManager.show_tree` reads `level` straight off the skill object with no TM-derived recompute. The only G7-touching open PR is #713 (homepage label edit). **Meta-post landed at PR #713 commit `af3d411d`:** `docs/meta/2026-06-17-g7-trust-magnitude-supersession.md` rendered via `scripts/add_post.py` to a 412-line LaTeX-style HTML report at `docs/meta/reports/2026-06-17-g7-trust-magnitude-supersedes-the-2026-06-15-methodology.html`. Visual show-not-tell with 6 ASCII diagrams (aggregation flow, anti-auto-mint expected-vs-observed, 9-predicate gate, before/after Verifier view, migration shape). Section I is a transparent **deployed-today vs G7-cutover** comparison so the report doesn't lie about state. The script also patched hero CTA + Meta Reports queue + `meta.html` cards so all surfaces lead with the G7 report.

  **Rebase action taken:** `dev/orchestrator-phase1-closeout` rebased onto origin/main (was 7 commits behind); 3 founder commits replayed cleanly (`7db25fcd→cda116b3`); force-pushed.

  **Out of scope (queued, NOT done):**
  - **G7 implementation arc** — the audit identifies 6 missing code touches (meta.json apex-gate block, `_passes_apex_gate`, `check_apex_gate`, meta-guard.yml apex enforcement, `audit_apex_at_g7.py`, `migrate_trust_magnitude.py`). Plus schema additions (`trustMagnitude` + `overallTrustGrade` fields, 10-type evidence taxonomy, `apexGateStatus` replacing `ultimateGateStatus`, `cosigners[]` array, `provisional` flag, `links.canonicalRepo`, `unverified` flag). Plus registry-wide regrade backfill. Plus apex demotions for `mattpocock/skills` (failed predicates §11.12.3, §11.12.4, §11.12.5, §11.12.6) and `ruvnet/ruflo` (failed §11.12.4, §11.12.6). Awaiting Marco green-light; no PRs filed yet, no issues filed yet under milestone #4 or a new Phase 1.5.
  - **Skill Explorer modal `#se-description` mount fix** — `docs/named/index.html` is missing the mount that `skill-explorer.js:127` reads for the "About this skill" panel. Result: Prerequisites + Unlocks silently absent on every skill modal — same silent-failure pattern CLAUDE.md flags for the badges page. Tracked as Task #17 in this session's task list. **NOT a 025ac91a regression** — pre-existing bug.
  - **Phase 2 issue #654** ("RFC: Evidence types — expand beyond arxiv / repo / stars") overlaps with G7 §3-§7's 10-type taxonomy. Cross-link recommended so Phase 2 doesn't diverge.

  **Token spend (session 7):** Opus 4.8 orchestrator + 3 Sonnet 4.6 workflows + meta-post drafting agent. Workflow `w2co0ee1p` Sonnet ~310k in / 25k out / ~$1.30. Workflow `wxeuk9br0` Sonnet ~250k in / 30k out / ~$1.05. Workflow `wf_c982e9b7-966` Sonnet ~240k in / 15k out / ~$0.95. Restore subagent Opus ~50k / 5k / ~$0.85. Meta-post drafting + add_post.py + commit Opus ~25k / 8k / ~$0.55. Orchestrator session ~80k / 20k / ~$2.40. Total ~$7.10.

- **2026-06-16 (session 6 — 6★ apex audit + RFC patch)** — User flagged §9 calibration table missing 6★ exemplars. Spawned dynamic workflow `wf_f14f7317-972` (7 agents, 595k subagent tokens, ~29 min) that swept the registry, regraded both currently-6★ skills under the new nested-suiteRef rule (transitive closure of `suiteComponents` with skillId-dedup, cycle detection, post-traversal graded≥C filter, sqrt-softened on post-filter count, grade-stacking through the fusion-recipe channel), ran an adversarial credibility check per skill, and proposed a 9-predicate strict apex gate. **Audit findings:** Two 6★ skills exist (`mattpocock/skills`, `ruvnet/ruflo`); user's count was correct. Current gate is essentially fictional — `promotion.py::_meets_evidence_floor` checks deprecated `class:'A'` only with no suiteComponent walk; `grading.py::check_ultimate_gate` walks DIRECT components only and is advisory (does not block); `meta.json` `apexPath` is documented but unread. **Adversarial verifier caught a critical honesty failure** on the mattpocock/skills regrade: regrader silently auto-minted github-stars-own + repo-own + self-attestation rows that do not exist in the apex frontmatter (apex carries `evidence: []`), inflating to TM 404 / S provisional. Strict-evidence corrected to TM 390 / A provisional (fusion-recipe only). Same pattern would inflate any grade across the registry, not just apex — motivated the registry-wide anti-auto-mint clause (§10.14). **Marco's 7 calls (2026-06-16):** (1) relax — bubbled-S may come from any descendant evidence type including descendant fusion-recipe (closes no closed-loop); (2) confirm — mattpocock lands at A provisional via verifier override; (3) K=2 cross-org cosigns starting point (synth recommended K=3 with relax-amendment if no apex landed in 6 months; Marco picked looser); (4) cap=5 system-wide; (5) tenure=180 days aligned with §5.7 grace; (6) **registry-wide anti-auto-mint** (every grade re-evaluated under strict-evidence at migration); (7) stamp report **leads** with apex demotions ("the world needs to know"). **RFC patches applied:** §0 Executive Summary headline rewritten with the 4 post-audit additions and the 2→0 6★ count change; §9 mattpocock/skills + ruvnet/ruflo rows replaced with strict-evidence regrades and "demotes at G7 cutover" annotation; §9 lead paragraph extended to cite §10.11–§10.14; §9 footer updated to flag the demoted apex provisional rows; **NEW §10.11 (transitive-closure rule)**, **§10.12 (9-predicate apex gate)**, **§10.13 (no grandfathering)**, **§10.14 (registry-wide anti-auto-mint)** appended; §11 Decision 7 struck through with explicit reversal note pointing at §10.11 / §11.12; **NEW §11.12** with all 9 predicates (§11.12.1–§11.12.10) + per-skill migration disposition table; §8 Stamp Report body sections reordered so the apex demotion section LEADS (not buried under aggregate drift), with new section 5 "Apex gate" methodology subsection. Net delta ~280 RFC lines, fully spliced in one orchestrator session. Awaiting Marco green-light to commit and dispatch coding agents.

- **2026-06-16 (session 5 — G7 Trust Taxonomy RFC consensus)** — Multi-stage workflow on the trust formula. Two waves: Wave A (`g7-trust-taxonomy-consensus`, 21 agents, 1.12M subagent tokens, 30 min) ran 3 surveyors → 4 distinct-stance proposers (Strict-S / Attainable-S / Fusion-Heavy / Community-Heavy) → 12 adversarial judges (3 lenses × 4 proposals: gameability, corpus-fit, drift-severity) → synthesizer; **drafter died on socket close mid-write**. Synthesis: P4 Community-Heavy as base, hardened with grafts from P1 (verifier/star plateaus, identity-tier creator multipliers) and P3 (only-graded-origins counting, null-on-derank verifier); thresholds reverted to baseline (S=250/A=100/B=50/C=20) so P4's three loosenings don't compound. Eight new mechanics introduced: mothership discount with capped divisor (max 4) + same-product subdivision; same-source dedup; fork-network canonicalization with `links.canonicalRepo` opt-out; sqrt-softened fusion curve (`m = 20 × origins` for ≤10, `200 + 20 × sqrt(origins-10)` for >10); only graded≥C origins count toward fusion; null-on-derank verifier; provisional grade with 6-month grace (PR-gated demotion); rank-floor sanity rule (4★+ cannot land below B without review — **blocks publish** at `gaia validate`). Marco's 10 final decisions captured: GitHub org membership for verifier-cluster; proxy-validation parked as milestone (lenient unverified-flag for now); `gaia dev evidence --cosign-with` flag confirmed for recognized-voice tier; PR-gated demotion at 6-month grace; fork canonicalization opt-out via `links.canonicalRepo`; same-product mothership subdivision; suiteComponents-only for auto-fusion origins; big-bang migration confirmed; stamp report via `gaia-post` skill (type=report, label="Meta-Shift", hero ON, source=`docs/meta/JUN_2026_TRUST_REGRADE.md`); rank-floor blocks publish.
  - **Wave B** (`g7-rfc-chunked-draft`, 9 agents, 303k tokens) chunked the RFC into 7 parallel section-writers + adversarial reviewer + patcher; **patcher stalled twice** on the same socket-close pattern. Recovered: extracted all 7 cached section results + reviewer's structured patch list from workflow journal/transcripts; assembled raw RFC (75k chars); spawned a single dedicated patcher agent with explicit 8-patch instructions (formula canonicalization, calibration reconciliation across §0/§4/§9/§13, migration PR shape one-PR-three-commit-stages, diversity-gate verifier cap, §10.4 wording, §13.5 same-source dedup example, §11 preamble, §6.5 quarterly-batch wording, plus 2 minor patches). Final RFC at `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` — **958 lines, 80kb**, all reviewer findings resolved.
  - **Cost so far this session:** ~1.5M total subagent tokens (Opus xhigh dominates). Logging on master-plan tracking issue when opened.
  - **Op note:** Workflow drafter agents stall on long single-shot writes (>20 page markdown). Pattern that worked: chunked parallel writes (≤3 pages each) + structured review schema + dedicated downstream patcher agent. Avoid single mega-write agents on Bedrock.

- **2026-06-16 (session 4 — Phase 1 closeout reorganization)** — Marco asked for a clean re-org with no chaos. Three parallel audits (handover sweep, GitHub-state audit via gh, repo reality check) caught: (1) memory was 5 minor releases stale (v4.4.2 → actual v4.9.0); (2) **PR-8 from old plan already shipped as #682** on 2026-06-14 (auth honest revoke); (3) **PR-7 (CI fix)** partially landed — `pull_request:` trigger present, but path filter excludes `registry/**` so data-only PRs still skip; (4) **PR-1 (rank gates)** floors exist on legacy `class` field but `_meets_evidence_floor` doesn't read the new `grade` field — so #699 narrows from greenfield to translation patch; (5) milestone #4 had drift items (#637, #647, #654 not Phase-1 acceptance; #650 duplicates #658; #699 had no milestone; #642 had no milestone). Then: archived all 8 obsolete PR-1..PR-8 handovers + old plan to `done/`; wrote **`handovers/PHASE1_MASTER.md`** as the unified plan with G1–G7 numbering, agent-model assignments (Haiku for XS, Sonnet for S/M, Opus for L/research), and parallelization lanes (A=infra+rank-gate sequential, B=share+narrow-tree parallel, C=scanner→verification sequential, D=benchmark RFC any-time); wrote **`handovers/HYGIENE_BATCH_2026-06-16.md`** as a 9-step approve-and-execute draft (fold #650→#658, prune #637/#647/#654 from #4, post #647 git-as-DB 1-pager, set #699/#642 milestone, open new G1 issue, sweep `phase-1` labels, schedule mid-July recalibration RFC). Updated `CLAUDE.md` Key References + Project Facts to point at the new master plan and reflect v4.9.0. Awaiting Marco approval on (a) the master plan including agent assignments + parallel lanes, (b) the hygiene batch.

- **2026-06-16 (session 3, wrap-up)** — Marco requested a final gap analysis. Dispatched an auditing subagent which caught 3 missing code PRs (#642 narrow-tree render, CI trigger fix, #155 revoke patch) and 2 non-code tasks (#647 1-pager, mid-July recalibration RFC). Generated comprehensive handover specs for all 8 Phase 1 completion PRs, numbered them sequentially (PR1–8), and archived all obsolete handovers to `handovers/done/`. The master execution plan (`00_PHASE1_COMPLETION_PLAN.md`) is updated. Session complete; ready to dispatch coding agents next.

- **2026-06-16 (session 3, cont.)** — Spawned an exploring agent to investigate the `gaia-skill-tree` repo for existing logic tying ranking to evidence grades. Findings: `meta.json` and `grading.py` currently implement the **Suite Ultimate Gate** (the pillar rule) and grade thresholds. Additionally, **Issue #658** covers "Enterprise Ready" Verification gating (requiring Grade A + 30-day tenure). However, there is no general gate tying standard skill ranks (e.g., Evolved, Apex) to evidence grades. Drafted an issue to fully set up these general rank gates per Marco's request.

- **2026-06-16 (session 3, final)** — Triage subagent successfully closed duplicates and connected related issues. Filtered out speculative/v2-unrelated ideas into a parking lot. Formulated the prioritized roadmap plan focusing on unfinished Phase 1 tasks (Rank Gates, Security Scanner, Verification Workflow, Benchmark Design, and Share Page) and identified necessary subagent weights for implementation.

- **2026-06-16 (session 3)** — Marco informed me that PR-4 (#694) was merged to main. This resolves #648 and completes the end-to-end trust model implementation described in #646. Drafted tracking operations for Marco's approval: closing #646, updating the project board, and seeding the next sprint issues (Trending / Rising Skills) since Milestone #7 is reaching 100% completion for its first batch of tasks.

- **2026-06-14 (session 2, cont. 3)** — Reviewed + merged **#690** (merge commit `74b2a6ee`) — the consolidated trust-layering PR (superseded closed #687/PR-2.5 + #688/PR-3; **Resolves #689**). Contains: `--index` in-place re-grade CLI + `evidence_graded` schema enum (fixes the live validate regression), 220 generic-node backfill, 173 named-skill backfill, and the **architectural step** — named-skill grade **inheritance** (effective = own ∪ inherited) + suite-gate fix (component lookup keyed by *named* id → kills the universal "0/3 components" artifact) + A3 build-path fix (thread `generic_skills_map`/`gate_config` through `write_index`). **CI gap:** the "Test, Build, and Smoke Test" unit-test workflow **did not run** on the head — compensated by running grading+regrade suites (**55/55**) and **`gaia validate` (all 10 checks, 228 skills)** locally before merging. Board #690→Done, #689→Done/closed, milestone #7. Then: started the trust-methodology meta-report + PR-4 plan expansion (Marco's request). Carryover: effective grade is still a max (recalibration RFC).

- **2026-06-14 (session 2, cont. 2)** — Marco surfaced a **PR-3 blocker** from his pre-PR-3 prep. Verified two gaps in merged PR-2 (#686): (1) `gaia dev evidence` is **append-only** (`evidence.append(...)` in `dev.py`, no source-match/dedup) → re-running over ~220 entries would duplicate them to ~440; (2) `evidence_graded` is fired but **absent from the schema timeline `action` enum** in both `skill.schema.json` + `namedSkill.schema.json` → **live `gaia validate` regression on main**. Resolution (Marco's call, Orchestrator concurs): **fix the CLI first** via two pre-PR-3 patches — Patch A `schema/` (add the enum value; urgent), Patch B `cli/` (in-place re-grade). PR-3 then runs as **pure `review/meta/` data** (resolves the no-CLI-on-review/meta tension). Wrote `handovers/GRADING_CLI_FIXES_HANDOVER.md`; revised `handovers/PR3_BACKFILL_HANDOVER.md` (in-place regrade + patch dependency). **Process note:** my PR-2 review checked that `evidence_graded` fires but not that the schema enum permits it / that `gaia validate` passes — add "grep new timeline actions against the schema enum + run validate" to the review checklist.

- **2026-06-14 (session 2, cont.)** — PR-2 (grading pipeline) landed. Reviewed #686 against the handover — read `grading.py` keystone + `dev.py` evidence wiring + `formatting.py` colors; CI green (full suite ran on head). **Squash-merged** `e6ef540c`, milestone #7; board #686→Done, #646→In progress; review comment 4700932541. Faithful to spec; **one non-blocking semantic flag:** `overall_trust_grade()` = single highest grade (max), not the RFC's accumulation → folded into the recalibration-RFC follow-up. Wrote `handovers/PR4_REPORTS_HANDOVER.md` (#648, design/ branch). Op note: sandbox `/tmp` clears between turns (home/gh persist); relied on CI-green rather than a costly re-clone for the local test re-run.

- **2026-06-14 (session 2)** — Reviewed PR #669 (auth MVP, #155) on Marco's request. Cloned the branch, ran the auth suite (50/50 green, 0.16s). Verdict: usable / merge-ready, faithful to the PRD. Posted a review comment (issue-comment 4700324066, Marco-approved) with three auth findings: (1) `revoke_token` is effectively a no-op against live GitHub — `DELETE /applications/{client_id}/token` needs client_id:client_secret Basic auth, absent by design; the test mocks a 204 and masks it; logout still clears locally and the message stays honest; (2) chmod-600 file write leaves a brief world-readable window (open→chmod); (3) broad env precedence (GH_TOKEN/GITHUB_TOKEN) can silently shadow `gaia login`. Confirmed `load_config` flat-parses a top-level `oauthClientId`, so the config path resolves. Answered Marco: building ahead of the OAuth app is the correct/intended order (client_id env>config>placeholder + fail-fast). His failed attempt was a **GitHub App** (callback required) vs the needed classic **OAuth App** + Enable Device Flow. gstack `/browse` unavailable here (broken symlink → Termux path); Marco chose a manual registration recipe (delivered). OAuth app still unregistered → real end-to-end `gaia login` unverified. gh re-installed in sandbox (apt-get download + dpkg-deb extract to ~/.local/bin; PAT re-provided this session, sandbox-local). Then, on Marco's explicit instruction, ran operations: final review pass (head moved 84900f8→35fa295 via rebase onto newer main; re-verified auth.py + test_auth.py **byte-identical** to review, 50/50 green, CI CLEAN/MERGEABLE) — **flagged 4 bundled non-auth commits** now riding on the branch (infra(badges) registry-date + generateBadges.py; infra(docs) --check fixes in build_docs.py + test_docs_site.py; cli(init) username detection in main.py + treeManager.py); **merged #669** via merge commit `b4d6659d` (REST API, to dodge gh-2.4.0 classic-projects error); set milestone #4; commented #155 + moved board #155→In progress; added #669 to board→Done. Client ID `Ov23litFvQBfMkwbIxfg` live-verified; keychain/file green per Marco.

- **2026-06-10 (session 1, wrap)** — Auth PRD finalized after Marco's inline reviews: persistent tokens (keyring, revised from "none"), offline first-class + remote-repo read selection with worktree-style `.gaia` path, CLI-forever leaning. Badge redesign accepted: generator/registry.json stay (Layer 1 canon), Worker dropped, `gaia badge sign`/`verify` SSH-attestation layer added; docs/badges page design updates added to PRD §6; #494 design comment posted (4675974778). Existing badge infra confirmed in repo: generateBadges.py, docs/badges/_assets/, registry.json v2, dead Worker ?repo= path. NEXT SESSION: PR-2 is critical path; Marco registers OAuth app; #654 brainstorm open.

- **2026-06-10 (session 1)** — Bootstrapped orchestrator workspace. Read roadmaps v1/v2 + GIT.md. Audited GitHub (logged-out web): milestones mapped, #647 label conflict and verification-workflow gap found. Scope/access/autonomy decisions captured. Created CLAUDE.md, MEMORY.md, PHASE1_PLAN.md v1.
- **2026-06-10 (session 1, cont.)** — PAT received (2nd token worked; 1st lacked read:org). gh installed (arm64). Full comment harvest on 9 issues → major finding: Marco is pivoting away from numeric trust scores toward rank/evidence-grade model; #647 deferred; #128/#155 have actionable design notes awaiting his decisions. Board confirmed healthy (not empty). Plan revised to v2: RFC-first sequencing, Batch 1 ops drafted.
- **2026-06-10 (session 1, close)** — Marco approved: all Batch 1 ops, #128 option (a) CLI-first, RFC drafting, weekly review. Executed #647 ops (wontfix removed, milestone → #4, verified via gh). Drafted #155/#128 comments — awaiting his text approval before posting. Wrote TRUST_MODEL_RFC.md + GAIA_SHARE_HANDOVER.md. Created `gaia-weekly-review` scheduled task (Mon 09:01).
- **2026-06-10 (session 1, final)** — Comments posted to #155 + #128 (with Marco's amendments: gaia install exists, #642 relation, backlog PR). Marco resolved all 5 trust-model decisions → RFC v2 accepted. Created #654 (evidence types RFC) + linked as sub-issue of #646 via API. Posted decision summary to #646. Remaining queue: #646/#648 implementation handover draft, verification-workflow issue draft.
