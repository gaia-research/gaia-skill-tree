# Phase 1 Master Plan — Trust Infrastructure Closeout

**Status:** Active. Replaces `done/00_PHASE1_COMPLETION_PLAN.md` (archived 2026-06-16).
**Owner:** Orchestrator agent. Coding agents execute; Marco approves all GitHub writes and merges.
**Goal:** Bring milestone #4 (Phase 1 — Trust Infrastructure) to a clean close before Phase 2 (Sprint 2 — Trending / Rising) begins, with no chaos and no parallel duplicate work.

---

## What changed since `00_PHASE1_COMPLETION_PLAN.md`

The previous plan listed 8 PRs (PR-1 … PR-8). Reality check on 2026-06-16:

| Old PR | Old issue | Reality | Action |
|---|---|---|---|
| ~~PR-1 Rank Gates~~ | #699 | Floors exist on legacy `class`; need translation to new `grade`. **Not greenfield.** | Re-scoped → **G2** (small patch) |
| PR-2 Security Scanner | #185 | Genuinely missing | Carried → **G3** |
| PR-3 Verification Workflow | #658 | Genuinely missing; folds in #650 | Carried → **G4** |
| PR-4 Benchmark Framework RFC | #649 | Design-only; carried | Carried → **G7** |
| PR-5 Share Static Page | #128 | #128 already CLOSED. Static page is fast-follow. | Re-scoped → **G5** |
| PR-6 Narrow-Path Tree Render | #642 | Genuinely missing | Carried → **G6** |
| ~~PR-7 CI Trigger Fix~~ | — | `pull_request:` trigger present. Path filter still excludes `registry/**` (data-only PRs silently skip). **Partial fix landed.** | Re-scoped → **G1** (small patch) |
| ~~PR-8 Auth Logout Revoke~~ | #155 | **Already shipped as PR #682** (merged 2026-06-14). | **DONE** — no action |

Net: 4 real coding PRs, 2 small patches, 1 RFC, plus orchestrator hygiene.

---

## Numbering convention

`G` = Gate (anything that closes a milestone-#4 acceptance criterion).
Numbers are execution priority: G1 → G7 = lowest → highest cost.

---

## Master sequence

| G# | Title | Issue | Branch prefix | Effort | Agent model | Lane | Blocked by | Acceptance |
|---|---|---|---|---|---|---|---|---|
| **G1** | CI path filter: cover `registry/**` | (open new) | `infra/ci-data-paths` | XS — 1 file, 5 lines | **Haiku 4.5** | A | — | Empty registry-only PR triggers `python-package.yml`; existing matrix still passes |
| **G2** | Rank gate translation: `class` → `grade` | #699 | `cli/rank-gate-grade` | S — 1 file, ~30 lines + tests | **Sonnet 4.6** | A | — | `_meets_evidence_floor()` reads `grade` first, falls back to `class`; test for both paths; floors transcoded so S satisfies any A floor |
| **G3** | Security Scanner | #185 | `cli/security-scanner` | L — new module, integrated into `gaia push` + `gaia dev verify` | **Opus 4.8** | B | — | Detects shell exec, destructive ops, network exfiltration, prompt-injection markers, credential harvesting; blocks `gaia push` with structured warnings; ≥10 unit cases covering each detector; integration test on a poisoned skill fixture |
| **G4** | Verification Workflow | #658 (folds #650) | `cli/verification-workflow` | L — schema + grading + CLI surface | **Opus 4.8** | C | **G2, G3** | 4 tiers (Community Verified / Benchmark Verified / Security Reviewed / Enterprise Ready); tenure baseline = `firstEvidenceAt`, measured in completed UTC days; `verification_status` field added to schema; `gaia skills info <id>` shows tier; predicate logic unit-tested per tier |
| **G5** | Share static page (`docs/share/`) | new fast-follow of closed #128 | `design/share-page` | M — frontend only | **Sonnet 4.6** | B | — | Page at `gaia.tiongson.co/share/?b=<url>` renders bundle JSON; copy-link button; matches site visual language; renders empty + malformed bundle gracefully; Lighthouse Perf ≥ 90 on a sample bundle |
| **G6** | Narrow-path tree render | #642 | `cli/narrow-tree-render` | S — 1 module, ~50 lines | **Sonnet 4.6** | B | — | When called from share-bundle export, `treeManager.show_tree()` (or sibling) emits only the path slice for the bundle's skills; full-tree mode unchanged; test fixture covers a 3-deep narrow path |
| **G7** | Benchmark Framework RFC | #649 | `design/benchmark-rfc` | M — research + writing | **Opus 4.8** (xhigh) | D | — | 6–10 page RFC at `docs/architecture/benchmark-framework.md`; covers reproducibility model, category taxonomy (Coding / Research / Automation / Agent Orch / Tool Use / MCP / Multi-Agent), one worked percentile→grade example, list of open questions deferred to Phase 2; **no code** |

**Lanes** describe parallelism: items in the same lane run sequentially in one Claude session; different lanes can run in parallel sessions/worktrees.

- **Lane A** (Haiku → Sonnet): G1 → G2 — same area (registry-touching infra/CLI), low risk, ~1 hour total.
- **Lane B** (Sonnet trio): G5, G6, G3-handover-prep can run in parallel; G3 itself needs Opus and goes solo.
- **Lane C** (Opus, sequential): G3 → G4. G4 hard-depends on G3 schema and on G2 grade reads.
- **Lane D** (research): G7 can start anytime; only blocks the milestone close on its own.

### Visual flow

```
Day 1 (parallel):
  Lane A:  [G1: Haiku] → [G2: Sonnet]
  Lane B:  [G5: Sonnet]
  Lane B:  [G6: Sonnet]
  Lane D:  [G7: Opus xhigh]   (research mode)

Day 2 (Lane C only):
  Lane C:  [G3: Opus]

Day 3 (Lane C cont):
  Lane C:  [G4: Opus]   ← needs G2 + G3 merged

Day 4: orchestrator hygiene (H1–H6 below) + milestone close
```

---

## Orchestrator hygiene tasks (H-series)

These are not coding PRs; they are GitHub state changes the orchestrator drafts and Marco approves before posting.

| H# | Action | Target | Why |
|---|---|---|---|
| **H1** | Comment + close as duplicate | #650 → folded into #658 | "Define Certification Tiers" and "Implement Verification Workflow levels" are the same artifact. G4 ships both. |
| **H2** | Remove from milestone #4; keep open | #647 | Per Marco's earlier decision: stays open for DB-specialist contributors. The 1-pager goes here as a comment, not a closing note. |
| **H3** | Post 1-pager comment | #647 | Git-as-DB strategy, when to migrate (rough triggers: registry > 5k named skills, or query latency > 200ms p95), and Supabase / Dolt evaluation criteria. |
| **H4** | Remove from milestone #4 | #637 | RFC-only per Marco's 2026-06-10 disposition; not Phase 1 acceptance. |
| **H5** | Move to Phase 2 milestone or new "RFC backlog" | #654 | Evidence types expansion is Phase 2 scope; doesn't gate trust-infrastructure closeout. |
| **H6** | Set milestone #4 + label `phase-1` on #699 | #699 | Currently has no milestone — must live on #4 to count toward closure. |
| **H7** | Open **G1** issue + add to #4 | new | "CI: include `registry/**` in pull_request path filter so data-only PRs don't silently skip" |
| **H8** | Schedule recalibration RFC | mid-July, ~2026-07-10 | Folds in (a) pillar-rule threshold review, (b) `overall_trust_grade()` MAX-vs-accumulation finding from PR-2 review. |

After H1–H7 land, milestone #4 contents become exactly: `#185, #658, #642, #649, #699, +G1-issue` — 6 items, all addressed by G1–G7 above.

---

## Acceptance criteria for "Phase 1 Complete"

All of the following must be true:

1. Milestone #4 shows 100% closed (after H1, H2, H4, H5 prune; after G1–G7 land).
2. `gaia validate` green on main; full pytest suite green; `python-package.yml` runs on every PR (including registry-only).
3. CONTEXT.md vocabulary unchanged from current state (no new "rarity"/"class" creep).
4. Trust methodology page (already shipped, PR #694) updated only if G2/G3/G4 surface user-visible behavior shifts; otherwise untouched.
5. `founder/MEMORY.md` reflects this plan + final state.
6. Phase 2 milestone (#5) populated with #654, #697, #698, plus whatever G7 surfaces as deferred.

---

## Per-task handover specs

### G1 — CI path filter (Haiku 4.5)

**File:** `.github/workflows/python-package.yml`
**Change:** Add `registry/**` (and `registry/schema/**` for clarity) to BOTH the `push.paths` and `pull_request.paths` lists.
**Verify:** Open a draft PR that touches only `registry/named-skills.json` whitespace; confirm the workflow runs. Close the PR.
**Token spend log:** Comment on the new G1 issue with model + tokens.

### G2 — Rank gate `class`→`grade` translation (Sonnet 4.6)

**File:** `src/gaia_cli/promotion.py` (`_meets_evidence_floor`).
**Spec:**
- Read `evidence[].grade` first; fall back to `evidence[].class` if `grade` absent.
- Floor list `["C","B","A"]` semantically means "any grade ≥ C". Treat `S` as satisfying any `A` floor (S > A).
- Add tests: legacy-only-class entry passes; new-only-grade entry passes; mixed dataset passes; ungraded entry below-floor blocks.
**Files to add tests in:** `tests/test_promotion.py`.
**Acceptance:** existing 32 promotion tests still pass; ≥4 new tests; `gaia validate` green.
**Issue:** #699 — comment links to PR; close on merge.

### G3 — Security Scanner (Opus 4.8)

**Files:** new `src/gaia_cli/securityScanner.py`; integrate into `src/gaia_cli/push.py` and `src/gaia_cli/commands/dev.py::verify`.
**Detector classes (each its own function returning a list of findings):**
1. Shell execution (`subprocess`, `os.system`, backticks, `eval`/`exec`).
2. Destructive filesystem ops (`rm -rf`, `shutil.rmtree`, `os.remove` on absolute or `~` paths).
3. Outbound network calls (`requests`, `urllib`, `httpx`, `socket.connect`) outside an allowlist.
4. Prompt-injection markers in skill text ("ignore previous instructions", role-override patterns, hidden Unicode tag chars).
5. Credential harvesting (regex for tokens, env-var reads of `GH_TOKEN`/`OPENAI_API_KEY`/`AWS_*`).
**Output:** structured warnings with `(severity, category, file, line, snippet)`; `gaia push` blocks on `severity=high` unless `--allow-unsafe` is set with explicit reason.
**Tests:** `tests/test_security_scanner.py` with one fixture per detector + a known-clean baseline.
**Issue:** #185 — comment, close on merge.
**Note:** This intersects with the `defensive-security` framing in the system prompt. All work is in-tree, defensive, and auditable.

### G4 — Verification Workflow (Opus 4.8)

**Schema:** add `verification` object to `registry/schema/skill.schema.json` and `namedSkill.schema.json`:
```json
"verification": {
  "tier": "community-verified | benchmark-verified | security-reviewed | enterprise-ready",
  "tierEvaluatedAt": "ISO timestamp",
  "firstEvidenceAt": "ISO timestamp"
}
```
**Predicate logic** (in `src/gaia_cli/verification.py` new module):
- `community-verified`: ≥1 evidence entry, any grade.
- `benchmark-verified`: ≥1 evidence with `type` in benchmark-types-allowlist (e.g., `benchmark-result`); placeholder for now since G7 RFC is design-only.
- `security-reviewed`: G3 scan ran clean within the last 90 days (recorded in timeline).
- `enterprise-ready`: overall trust grade ≥ A AND tenure ≥ 30 completed UTC days from `firstEvidenceAt`.
**Tenure rule:** completed UTC days only. `firstEvidenceAt` is the timestamp of the first `evidence_added` event. If absent, set on next `evidence_added`.
**CLI:** `gaia skills info <id>` prints tier + reason; `gaia dev verify <id>` recomputes and writes.
**Tests:** unit-tested per tier; one regression test for tenure boundary (29 days fails, 30 days passes).
**Issues:** #658 closes on merge; comment on #650 marking it folded.

### G5 — Share static page (Sonnet 4.6)

**Files:** `docs/share/index.html`, `docs/share/styles.css`, `docs/share/share.js`.
**Behavior:** read `?b=<https-url-to-bundle.json>` query param; fetch bundle; render sharer name + tree preview + per-skill rows with install commands; "Copy install" button per row; "Copy all" button for the whole bundle.
**Visual language:** match `gaia.tiongson.co` palette/typography; reuse existing components if any in `docs/`.
**Edge cases:** empty bundle ("Nothing to share yet"), malformed JSON ("Invalid bundle, ask the sharer to regenerate"), 404 ("Bundle not reachable").
**Acceptance:** Lighthouse Performance ≥ 90 on a 20-skill bundle; works at viewport 320px wide; WCAG 2.1 AA color contrast.
**Issue:** open new fast-follow of closed #128; reference closed #128 in the body.

### G6 — Narrow-path tree render (Sonnet 4.6)

**File:** `src/gaia_cli/treeManager.py` (or sibling module that owns `show_tree`).
**Spec:** add a `path_subset: set[str] | None` parameter (or equivalent); when set, the renderer prunes any subtree whose descendants don't intersect the subset. Used by `gaia share` to render only the path slice for bundled skills.
**Test fixture:** a 3-level tree with 8 skills; pass a 3-skill subset; assert the rendered markdown contains only those 3 skills + their direct ancestor path; siblings are absent.
**Issue:** #642.

### G7 — Benchmark Framework RFC (Opus 4.8 xhigh)

**File:** `docs/architecture/benchmark-framework.md`.
**Sections:** Motivation; Reproducibility model (deterministic seeds, pinned model versions, dockerized harness); Category taxonomy (Coding / Research / Automation / Agent Orchestration / Tool Use / MCP / Multi-Agent); Score → Evidence Grade mapping (worked percentile example: top 10% → S, top 25% → A, top 50% → B, else C; numbers are illustrative, not normative); Open questions deferred to Phase 2 (≥6).
**Length target:** 6–10 pages including a small example mapping table.
**No code.** The output is a markdown RFC.
**Issue:** #649 closes on merge.

---

## Token spend logging

Per the workspace rule (`PR #695`), each agent logs spend at the end of its session as a comment on the PR or issue:
> `<date> <model> <effort>: <X>k in, <Y>k out. ~$<Z>`

Orchestrator collects totals at end of Phase 1 and posts summary on the milestone-close issue.

---

## Stop conditions

If during execution any of the following are discovered, **pause and surface to Marco**:
- A G-task touches `STEWARDSHIP_PLAN.md` or any Hermes-owned file (CLAUDE.md §"Agent-Managed Files").
- The pillar rule or `derive_grade` thresholds need adjusting mid-PR (recalibration is H8 territory, not in-PR).
- A G-task discovers a security issue not covered by the in-flight scanner; document and re-route.

---

## Done definition

Phase 1 is complete when:
- Milestone #4 shows 6/6 closed (or 0 open).
- All G1–G7 PRs merged on `main`.
- H1–H7 GitHub-state changes posted.
- H8 recalibration RFC scheduled.
- `MEMORY.md` updated with closing snapshot.
- Phase 2 (Sprint 2) issues #697 + #698 are unblocked and labeled `phase-2`.
