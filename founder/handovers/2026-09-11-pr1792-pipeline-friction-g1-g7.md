# PR #1792 — pipeline-friction findings (G1–G7) — settings decisions + ground-truth corrections

**Status:** implementation log for a landed/landing PR, not a design proposal. Recorded so the next
agent touching squash-merge policy, `dev/*` branch lifecycle, or the pipeline docs below doesn't
re-litigate what was already decided here.

Source: trailhq/graft full-pipeline curation run (intake #1776, 2026-09-10), run deliberately with
Haiku + Sonnet worker agents to stress-test small-model friendliness against the documented pipeline.
Issues filed: #1784–#1790 (G1–G7). PR: `fix/pipeline-friction-findings-graft-intake` (#1792).

## Settings decisions (founder-confirmed 2026-09-11)

Two of G7's (#1790) asks were GitHub repo/org settings, not code — verified live via `gh api
repos/gaia-research/gaia-skill-tree`:

| Setting | Live value | Decision |
|---|---|---|
| `allow_squash_merge` | `false` | **Keep disabled.** CLAUDE.md § Squash Merges rewritten to say "merge commit everywhere" instead of the previous (already-false) claim that squash was allowed on integration/stacked PRs. |
| `delete_branch_on_merge` | `true` | **Keep enabled.** GitHub has no per-branch or ruleset exemption for this — it's repo-wide, all-or-nothing. CLAUDE.md § Multi-PR work documents the recreate-`dev/*`-from-`main` workaround instead. |

Do not reopen either question without a new founder ruling — a future sprint wanting squash on
integration PRs needs an explicit settings change first, not a docs edit assuming it's already true.

## Ground-truth corrections found during HEAVIER's planning pass

Three of the original issue bodies turned out to be stale or partially wrong once the actual code was
read — noted here so nobody "fixes" something that's already fine:

- **G3 (#1785):** `scripts/validate_intake.py`'s `VALID_TYPES` already includes `"fusion"` — the
  reported rejection was real at the time it was hit, but the code has since been corrected elsewhere.
  Only a regression test was added to pin it against regressing back to the pre-Yggdrasil-II set.
- **G6 (#1788):** `.claude/skills/ev-discovery/SKILL.md` was not a skill with a wrong preflight — it was
  a 43-line stub with **zero** code blocks, no concrete Firecrawl commands, and no retry-rule section at
  all. The fix authored those sections from scratch rather than editing existing (nonexistent) ones.
- **G2 (#1789):** the reported `PYTHONPATH` failure in `build_docs.py --check` was misdiagnosed as "no
  bootstrap" — `build_docs.py` already bootstraps its own `sys.path`. The real bug: that in-process
  `sys.path` mutation never reaches a `subprocess.run` child (sys.path edits aren't environment
  variables), and two of the scripts it shells out to (`generateBenchmarkProjection.py`,
  `validate.py`) had no bootstrap of their own to fall back on. Fixed via a `_child_env()` helper on the
  parent side plus adding bootstraps to the child scripts that lacked one.

## Reference

- Issues: #1784 (G1), #1789 (G2), #1785 (G3), #1786 (G4), #1787 (G5), #1788 (G6), #1790 (G7).
- PR: #1792, branch `fix/pipeline-friction-findings-graft-intake`.
