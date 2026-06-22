# Epic #780 — Close-out Handover

**Drafted:** 2026-06-22, session 18 (review of PR #787 against `main`).
**Reviewer:** Two-axis `/review #787` (Standards + Spec sub-agents) then `/grill-me` with Marco.
**State at draft time:** PR #787 (`dev/improve-codebase-architecture` → `main`) is open, draft, 53 commits, 557 files, +21,488 / −119,556. CI green at last check. **Not yet merged.**

This handover is the playbook for the next orchestrator session. It splits into two halves:

1. **BEFORE the merge of #787** — what must land in PR #787 itself before Marco merges it.
2. **AFTER the merge** — five tracked follow-up issues that close Epic #780.

Both halves matter. The epic does not close while any of the five follow-ups is open.

---

## Context snapshot (carry into the next session)

- **Branch:** `dev/improve-codebase-architecture` @ `358e16171`
- **PR:** #787, draft, base = `main` @ `e41b8cc2`
- **Epic:** #780 (Architectural Modernization & Technical Debt Reduction) — OPEN
- **Sub-Issues:** #781 (CLOSED), #782 (CLOSED), #783 (OPEN), #784 (CLOSED), #785 (OPEN), #786 (OPEN, added during the epic)
- **Tests:** 1,191/1,191 green per MEMORY.md session 17 snapshot. CI green per PR runs.
- **Active key documents:**
  - this file (close-out playbook, BEFORE + AFTER merge)
  - `EPIC780_REVERT.md` — rollback playbook, kept live in `handovers/` until ~7 days of post-merge stability
  - `EPIC780_DEPRECATION_CLEANUP.md` — forward-looking v7.0.0 shim removal playbook (referenced by #792 docs drift). Kept live until v7.0.0 ships.
  - Mid-epic handovers (`AGENT_TESTING.md`, `MIDPOINT_HANDOVER.md`) archived to `done/epic-780/`.

### Five close-out blocker issues (filed 2026-06-22)

| # | Title | Sub-Issue link | Severity |
|---|---|---|---|
| **#789** | CLI Pre-Flight gaps in decomposed dev/ modules: calibrate (Star Bar) + evidence (benchmark percentile) | Sub-Issue 2c (#786) | medium — pre-existing gaps now codified in new structure |
| **#790** | Drop deprecated `--class` flag from `gaia dev evidence` | Sub-Issue 2b | low — small mechanical cleanup |
| **#791** | Backfill unit tests for `commands/dev/*` subcommand modules | Sub-Issue 2c (#786) | medium — TDD bypass acknowledged in midpoint handover |
| **#792** | Docs drift: update CLI Shape + agent docs for `gaia dev <verb>` namespace move | Sub-Issue 2b | low — text-only |
| **#793** | Sub-Issue 1 regression: `gaia pull`/`fetch` 404 + bundled snapshot stuck at v3.1.0 | Sub-Issue 1 (#781) | **HIGH — real CLI regression on merge** |

Epic #780 closes only when **all five** close. #793 is the only one that genuinely breaks user-facing behavior; the other four are hygiene/discoverability.

---

## BEFORE the merge of PR #787

These are blockers Marco should resolve in this PR's branch (or accept the risk and merge anyway). The grill conversation explicitly authorized #789, #790, #791, #792 as **separate-PR follow-ups** (so PR #787 stays scope-pure). The only items that must land **inside PR #787 before merge** are:

### B1. Revert fabricated timeline rows in skill-trees

**File 1:** `skill-trees/mattpocock/skill-tree.json` — lines 240-248 in the diff
**File 2:** `skill-trees/ruvnet/skill-tree.json` — lines 563-571 in the diff

Both contain hand-fabricated `levelHistory` entries with hardcoded `achievedAt: "2026-06-18T12:54:50Z"` and the literal note `"backfilled from trunk timeline (CLI gap)"`. `founder/CLAUDE.md` § "Timeline events — NEVER fabricate by hand" forbids this absolutely: *"A missing entry is auditable. A synthetic entry is not."*

**Origin:** these rows came in via commit `54bfc0956` (*"design: Trust Ledger — May/June stars (#779)"*) — not introduced by any Epic #780 sub-issue. PR #787 is the carrier, not the author. Marco's call (2026-06-22): revert with this PR; investigate via separate ticket whether the new CI generates these timelines and whether tests rely on them.

**How to revert:**

```bash
git checkout main -- skill-trees/mattpocock/skill-tree.json skill-trees/ruvnet/skill-tree.json
# Confirm with `git diff main -- skill-trees/{mattpocock,ruvnet}/skill-tree.json` returning empty
# Then re-apply ONLY the lines that are legitimate trust-ledger updates (level 6★→5★ on the
# top-level `levelHistory` entry, plus the `previousValue: "6★"` add on the timeline event).
# Do NOT re-apply the fabricated "demote" rows.
```

Marco's followup: check if PR #779's CI generated these and treat as a separate bug.

### B2. (Optional) Add staleness warning before merge

#793 documents the bundled-snapshot regression. The full fix is post-merge. If Marco wants to soften the blast radius **inside PR #787**, the minimum viable in-PR change is:

- A `print(file=sys.stderr)` line in `src/gaia_cli/registry.py:bundled_registry_path()` warning users when they're reading the bundled v3.1.0 snapshot.

This is not required; #793 covers it fully post-merge. Mention as optional in the merge conversation with Marco.

### B3. PR description update

Before marking PR #787 ready-for-review:
- Add a "Known close-out items (post-merge)" section linking #789, #790, #791, #792, #793.
- Explicitly note that #793 is a real regression Marco accepted to merge as-is.
- Note the timeline-revert (B1) was applied in this PR.
- Token-spend comment per project root `CLAUDE.md` is the next orchestrator's call (Marco said drop the requirement for this session).

### B4. Skill-trees `.md` drift

39 `skill-trees/*/skill-tree.md` files have a single-line `generated 2026-06-20 → 2026-06-22` timestamp diff. Marco (2026-06-22): this drift is an architectural side-effect that the new CI will eventually update on its own. **Do not revert in PR #787** — let it ride. Future PR will retire the pattern.

### B5. Generated-artifact drift in `docs/css/tokens.css`, `docs/badges/registry.json`, `docs/experiments/ml-graph-viz/layouts_3d.json`, `registry/layouts_3d.json`

Same disposition as B4. Architectural cleanup, not a PR #787 ask.

---

## AFTER the merge of PR #787

Once PR #787 is merged, the next orchestrator inherits the five close-out blockers. **Recommended sequence:**

### Wave 1 — Stop the bleeding (#793)

**Priority: HIGHEST. Do this first.**

#793 documents a literal CLI regression: `gaia pull` and `gaia fetch` return 404s after merge, and every fresh `pip install gaia-cli` silently reads a v3.1.0 snapshot (current version is v5.0.7). Six-part fix:

1. **CI step** in `.github/workflows/sync-artifacts.yml` (or `python-package.yml`): on `vX.Y.0` tag pushes, copy `registry/{gaia.json,named-skills.json,named/}` into `src/gaia_cli/data/registry/` ahead of `python -m build`. Skip on patch tags.
2. **Git-untrack** `src/gaia_cli/data/registry/{gaia.json,named-skills.json,named/}` (keep `data/registry/schema/` tracked). Append to `.gitignore`.
3. **Retarget `fetch_command`** in `src/gaia_cli/impl.py:2719-2739` to GitHub Releases API → download `gaia-artifacts.tar.gz` → unpack to `.gaia/registry/`.
4. **Staleness warning** in `src/gaia_cli/registry.py:bundled_registry_path()` — print yellow `⚠️ Using bundled registry snapshot from <DATE>. Run \`gaia pull\` for the latest.` once per CLI invocation when bundled fallback fires.
5. **Update CLAUDE.md files** — project root `CLAUDE.md` § "Current Layout" + § "Versioning"; `src/gaia_cli/CLAUDE.md` (new section on registry-path resolution); `founder/CLAUDE.md` (release-runbook note).
6. **Update `CONTRIBUTING.md`** — new section "Consuming the registry without a clone."

Acceptance criteria are spelled out in #793. Verify wheel size lands at ~2.6 MB.

Dispatch shape: single coding-agent worktree, Sonnet. ~80k tokens budget. Commits split per file area (CI step → untrack → fetch_command → staleness warning → CLAUDE.md → CONTRIBUTING.md). Pre-PR test: `pip install -e . && rm -rf .gaia && gaia tree` should warn about staleness; `gaia pull` should succeed and re-run silent.

### Wave 2 — CLI hygiene (#789 + #790, group into one PR)

Both are CLI tech-debt cleanup, both small, both safe to group.

- **#790** (drop `--class`): mechanical edit across `commands/dev/__init__.py`, `commands/dev/evidence.py`, `impl.py`, plus three test files (`test_grading.py`, `test_meta_ops.py`, `test_evidence_regrade.py`). Add CHANGELOG entry.
- **#789** (calibrate Star Bar + evidence percentile pre-flight): add `_preflight_starbar(meta, level)` to `commands/dev/calibrate.py` reading `links.github` from frontmatter; add `_preflight_benchmark_percentile(args)` to `commands/dev/evidence.py` requiring/validating `--percentile` on `--type benchmark-result`. Unit tests under `tests/test_dev_calibrate.py` + `tests/test_dev_evidence.py` (these also seed #791's required files).

Dispatch shape: one Sonnet agent, ~60k tokens. Two commits (one per issue). Single PR resolving both.

### Wave 3 — Test backfill (#791)

The big one in line count. 8 new test files (`test_dev_calibrate.py`, `test_dev_evidence.py`, `test_dev_merge.py`, `test_dev_rename.py`, `test_dev_timeline.py`, `test_dev_named.py`, `test_dev_audit.py`, `test_dev_build.py`) covering all mutating verbs. Acceptance bar: 70% branch coverage on `src/gaia_cli/commands/dev/*.py`.

Convention: use `tmp_path` + monkeypatched registry root, mirror `tests/test_meta_ops.py` style. Cover happy path + at least one rejection path per verb. Each test asserts stdout/stderr surface AND registry/timeline state mutation.

If #789 (Wave 2) landed first, two of these files (`test_dev_calibrate.py`, `test_dev_evidence.py`) already exist as seeds — extend rather than replace.

Dispatch shape: Opus 4.8 likely (more reasoning needed per verb), ~120k tokens, worktree-isolated. Commit-per-file pattern. Mandate the warmup boilerplate from `founder/CLAUDE.md` § "Worktree warmup boilerplate."

### Wave 4 — Docs (#792)

Audit pass across `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, `DEV.md`, `CHANGELOG.md`, `docs/agents/issue-tracker.md`, `docs/agents/domain.md`, `docs/agents/triage-labels.md`. Replace stale top-level mutating-verb examples with `gaia dev <verb>` and note the deprecation timeline (warn now → remove in v7.0.0). CHANGELOG entry.

**Source of truth for the shim list:** `founder/handovers/EPIC780_DEPRECATION_CLEANUP.md`. That file enumerates every shim (`gaia release`, `gaia validate`, `gaia test`, `gaia docs build`, `gaia mcp`), where each lives, what each prints, the v7.0.0 removal steps, and the grep command to find lingering references. The #792 docs audit should use that table verbatim rather than re-deriving it.

Dispatch shape: Sonnet, ~40k tokens, no code changes, single PR.

### Wave 5 — Sub-Issues #783 + #785 final state

Both Sub-Issues are still OPEN despite PR #787 shipping their nominal deliverables. The grill conversation established:

- **#783**: Changesets approach was rejected in favor of `verify_lockstep.py` lockstep validation. The midpoint handover said *"Close the Changesets portion of #783 by posting a comment on issue #783 explaining that the Changesets approach was rejected"* — that comment was never posted. Either (a) post the explanatory comment and close #783, or (b) reopen the Changesets work as a separate issue for a future cycle and close #783 as superseded.
- **#785**: Marco's explicit framing was *"Minimal abstraction… invest minimal effort here."* What shipped (50-line `merger.ts` + PID-file `daemon.ts`, raw `@modelcontextprotocol/sdk` still in place) matches that scope. Either (a) close #785 with a comment scoping it down to delivered minimum + filing a future-cycle issue for full MCPorter adoption, or (b) reopen as a future-cycle issue.

Dispatch shape: orchestrator-only. Draft comments, route for Marco's approval, post via `gh issue comment` then `gh issue close`.

### Wave 6 — Close Epic #780

After Waves 1–5 close, post a summary comment on #780 itself referencing all five close-out PRs and the resolution of #783/#785. Then `gh issue close 780`.

### Archive `EPIC780_REVERT.md`

After ~7 days of post-merge stability with no rollback needed, `git mv founder/handovers/EPIC780_REVERT.md founder/handovers/done/epic-780/`. Until then it stays in the active handover dir per Marco's instruction (2026-06-22) — if the merge fails, the revert plan must be findable, not buried.

---

## Risks the next orchestrator should weigh

1. **#793 is HIGH severity.** Until it's fixed, `pip install gaia-cli` from PyPI immediately after PR #787 merges will silently serve a v3.1.0 snapshot. If a new contributor pip-installs and tries `gaia tree` they will see ~13 skills instead of ~700. This is a release-quality problem — handle in Wave 1, not later.

2. **Mid-epic tests bypassed TDD.** PR #787 marks 1,191/1,191 green, but the green isn't from the new code — it's from end-to-end smoke tests that don't exercise the new dev/ verbs at unit level. Real regressions in a refactored verb may not surface until the test backfill (#791) lands.

3. **`impl.py` is still 4,157 lines.** Sub-Issue 2 was reported as "main.py shrunk from 4,078 → 130 lines." Reality (per midpoint handover): the 4,078 lines were renamed to `impl.py` and re-exported via `globals()[_name] = getattr(_impl, _name)`. The "fat module" pattern was not eliminated. A future Sub-Issue 2d (not yet filed) should actually decompose `impl.py` into the per-command modules in `commands/`. Out of scope for this epic close-out.

4. **`registry/gaia.json` lives in two timelines.** Untracked from git (Sub-Issue 1), but regenerated locally by `gaia docs build` and bundled by CI on minor releases. Three places it can exist: contributor working tree (transient), `.gaia/registry/` after `gaia pull` (cache), `src/gaia_cli/data/registry/` (bundled per-wheel). Each has different freshness. Document this clearly in #793's CLAUDE.md updates.

5. **Token spend logging.** Project root `CLAUDE.md` § "Token Spend Logging (Critical)" requires per-PR comments. Marco (2026-06-22): drop for this session, he's doing estimates separately. Don't carry this rule into the post-merge dispatches blindly; ask before adding it back.

---

## Pre-merge checklist for Marco

- [ ] B1 timeline revert applied (or explicit decision to leave the fabricated rows)
- [ ] PR description updated with the five close-out issue links
- [ ] CI green on PR #787 head
- [ ] No further commits expected on the branch
- [ ] Decision recorded on whether B2 staleness warning lands in PR #787 or post-merge in #793

## Post-merge checklist for the orchestrator

- [ ] Tag `pre-epic-780` on the pre-merge `main` commit (`e41b8cc2`) — already done if revert script ran; verify with `git tag --list pre-epic-780`
- [ ] Tag `vX.Y.0` or whatever the merge release is per `EPIC780_REVERT.md`
- [ ] Trigger Cloudflare Pages deploy verification
- [ ] Start Wave 1 (#793) within the same session if possible — the regression is live as soon as the merge lands

## Reference

- PR #787: https://github.com/mbtiongson1/gaia-skill-tree/pull/787
- Epic #780: https://github.com/mbtiongson1/gaia-skill-tree/issues/780
- Sub-Issues: #781 (CLOSED), #782 (CLOSED), #783 (OPEN — see Wave 5), #784 (CLOSED), #785 (OPEN — see Wave 5), #786 (OPEN — closes via #791)
- Close-out blockers: #789, #790, #791, #792, #793
- Revert playbook (kept live): `founder/handovers/EPIC780_REVERT.md`
- Deprecation-shim removal playbook (kept live until v7.0.0): `founder/handovers/EPIC780_DEPRECATION_CLEANUP.md`
- Archived mid-epic handovers: `founder/handovers/done/epic-780/`
