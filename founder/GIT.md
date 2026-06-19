# GAIA Project Operations (GIT.md)

This document is the source of truth for how Marco's project hierarchy maps onto GitHub. Every agent and contributor follows it so that the GAIA V2 Roadmap, milestones, and Project Board #2 stay coherent with the work actually shipping.

*Last Updated: 2026-06-20 (Session 15 — Phase 1.5 consolidation)*

---

## 1. The Hierarchy

GAIA uses a four-tier system. The first three are durable; the fourth is the staging surface for ephemeral work.

1. **Roadmap** (`founder/GAIA_ROADMAP.md` + `founder/GAIA_ROADMAP v2 (BUILD).md`) — strategy and long-term vision. Edits require Marco's approval.
2. **Milestones** (the finish line) — phase-level goals. Every issue **must** be assigned to a milestone so the roadmap dashboard renders correctly. Currently active:
   | # | Title | State |
   |---|---|---|
   | 8 | Phase 1.5 — G7 Implementation | active (12 open / 15 closed as of 2026-06-20) |
   | 7 | Immediate Next 30 Days | rolling sprint anchor |
   | 5 | Phase 2 — Product Moat | queued |
   | 6 | Phase 3 — Growth Engine | queued |
3. **Project Board** ("GAIA V2 Roadmap", project #2) — daily Kanban for execution tracking. Reading requires the `read:project` PAT scope, which is not always present in the sandbox; ask Marco if missing.
4. **Branches** — ephemeral working surface. See `founder/CLAUDE.md` § Worktree rules + Branch Naming. Long-running branches (`dev/phase-1.5-inspection`) act as **consolidation lanes** — see §3.2.

---

## 2. Issue Management

### 2.1 Creation checklist

Every issue must carry these four fields, applied in this order:

1. **Title** — clear, actionable, imperative. *"Implement Trust Score API"*, not *"Trust Scores"*.
2. **Description** — must include a brief Definition of Done or core deliverable list. Include linked artifacts (handover doc paths, RFC sections, related PRs).
3. **Functional label** — exactly one of these (canonical set as of 2026-06-20):

   | Functional | Status / Phase | Special-purpose |
   |---|---|---|
   | `backend` | `phase-1` | `apex-promotion` |
   | `frontend` | `phase-1.5` | `verifier-signoff` |
   | `infrastructure` | `phase-2` | `evidence` |
   | `CLI` | `RFC` | `taxonomy` |
   | `docs` | `tech-debt` | `transparency` |
   | `schema` | `human-proposal` | `mcp` |
   | `bug` | `bot-proposal` | `skip-scope-check` |
   | `enhancement` | `needs-review` | `auto-merge` |
   | | `needs-triage` | `dependencies` |
   | | `draft-skills` | |

   Use `gh label list` to confirm before adding. Custom labels not in this set must be created via `gh label create` first — agents commonly try to add `trust-model`, `design`, or `phase-1.5-data`, none of which exist.

4. **Milestone** — assign to the active phase milestone (today: **Phase 1.5 — G7 Implementation** = milestone #8). Long-lived strategic threads also tag the rolling sprint milestone (`Immediate Next 30 Days` = milestone #7).

### 2.2 Transition

- When you begin work, move the issue to **In Progress** on the Project board.
- When you submit a PR, link it to the issue using `Resolves #<Issue_Number>` in the PR body. Multiple issues = multiple `Resolves` lines.
- If a coding agent opens a PR with `Closes I10` (no issue number), the orchestrator must `gh pr edit <n> --body` to fix it within the same turn.

---

## 3. Pull Request Standards

### 3.1 The basics

To keep roadmap automation working, every PR must:

1. **Link to an Issue** — use the `Resolves` keyword in the PR description.
2. **Match Milestone** — apply the same milestone as the linked issue.
3. **Atomic Commits** — keep changes surgical and focused on the issue's scope. If a single dispatch produces 100+ lines or touches multiple modules, split into multiple commits at natural breakpoints (see `founder/CLAUDE.md` § Working rules).

### 3.2 Consolidation PRs (large multi-issue lanes)

When a phase produces many interlocking PRs (Phase 1.5 = I1–I12 + I8 + sources), the orchestrator opens **one consolidation PR** from a long-running branch (`dev/<phase>-inspection`) to `main`, kept as a draft, and merges feature branches **into the consolidation branch**, not into main directly.

**Pattern (current example: PR #742, `dev/phase-1.5-inspection` → `main`):**

1. Open the consolidation PR as a **draft** before any feature work lands. Body documents the issues it will absorb.
2. Each feature branch (e.g. `cli/apex-gate-fixes`, `design/trust-leaderboard`) opens its own PR targeting the consolidation branch — these are reviewed and merged into the consolidation branch.
3. Feature PRs are **closed/merged into dev**, not main. Their issues stay open until the consolidation PR merges.
4. Once the consolidation branch is fully baked and inspected, the orchestrator updates the consolidation PR body to reflect final state (all I-numbers, status checkmarks, gate checklist) and removes the draft flag for Marco's review.
5. Marco merges the consolidation PR into main as one giant atomic merge. Issues auto-close via their `Resolves` keywords.

**Why this pattern:** Marco wants to inspect Phase 1.5 holistically before main is touched, not piecemeal. A consolidation lane lets agents ship independent slices without contaminating main, and lets Marco see the entire phase delta in one diff.

**Enforcement rule:** No agent should ever open a PR targeting `main` directly during an active consolidation phase. If an agent does (e.g. PR #745 targeted main during Phase 1.5), the orchestrator closes it with a comment pointing to the consolidation PR.

### 3.3 The `skip-scope-check` label — pre-authorized

**Standing pre-approval (decision 2026-06-18):** the orchestrator may apply `skip-scope-check` to any PR being merged when branch-scope CI blocks an otherwise-clean merge. The merge itself still routes through Marco; only the labelling is pre-authorized. Common cases: long-running consolidation PRs that span all branch prefixes, infra PRs that legitimately mix `docs/` + `scripts/`.

### 3.4 Forbidden: hand-edited timeline entries

**Never write timeline entries via direct frontmatter edit.** This applies even when a CLI gap exists. A fabricated entry with a hardcoded timestamp is a lie in the audit log. Correct path on a CLI gap:

1. Leave the timeline entry out of the PR.
2. Note the CLI gap explicitly in the PR description.
3. Open a follow-up issue for the CLI fix.

A missing entry is auditable. A synthetic entry is not.

---

## 4. Maintenance & Cleanup

### 4.1 Sprint transitions

- When the **Immediate Next 30 Days** milestone (#7) reaches 100%, the orchestrator drafts the next batch of issues from the Roadmap's next Sprint and routes them through Marco for milestone assignment.
- Do not seed issues for Phases 3+ until Phase 1.5 closes — this avoids backlog clutter and keeps the dashboard meaningful.
- After a consolidation PR (§3.2) merges to main, the orchestrator:
  1. Confirms all `Resolves` keywords auto-closed their issues.
  2. Deletes merged feature branches (`git push origin --delete <branch>`) — keep the consolidation branch one cycle longer in case of follow-up.
  3. Updates `founder/MEMORY.md` with the snapshot.

### 4.2 Stale issue triage

- Any issue **In Progress** for more than 7 days without a linked PR is moved back to **Todo** and re-evaluated for blockers.
- Any **draft PR** older than 14 days without forward progress is brought to Marco for a kill-or-resurrect call.
- Stale rogue PRs (targeting `main` during an active consolidation phase, or whose commits are already absorbed by a consolidation branch) are closed with a comment pointing to the active consolidation PR.

### 4.3 Stale local branches (orchestrator hygiene)

- After a merge, run `git fetch --prune origin` to clean tracking refs.
- A worktree session left in `.claude/worktrees/agent-<id>/` should be cleaned up via `ExitWorktree action: "remove"` after its commits are pushed.
- Per `founder/CLAUDE.md` hazard #11: a local branch may carry stale commits at `main` HEAD; check `git log --oneline -3` vs `main` before reusing.

---

## 5. Agent Instructions

If you are an AI agent operating in this repository:

1. **Check the milestone first.** Before proposing work, read the active milestone via `gh api repos/:owner/:repo/milestones`. Assume **Phase 1.5 — G7 Implementation** (#8) unless told otherwise.
2. **Check the Project board.** Look at the *Todo* column before starting a new task: `gh project item-list 2 --owner mbtiongson1 --limit 50` (requires `read:project` scope).
3. **Update your session topic** to reflect which Milestone and Issue you are addressing — this aids handoff if your session is cut short.
4. **Read `founder/CLAUDE.md` § Worktree rules** before touching any file. Worktree-isolated dispatches **always** branch from `origin/<base-branch>`, commit + push after each unit, and target the consolidation branch (today: `dev/phase-1.5-inspection`), not main.
5. **Apply hygiene immediately, not at the end.** Within the same orchestrator turn that opens a PR:
   - `gh issue edit <n> --milestone "Phase 1.5 — G7 Implementation" --add-label "phase-1.5,<functional>"`
   - `gh pr edit <PR> --milestone "Phase 1.5 — G7 Implementation" --add-label "phase-1.5,<functional>"`
   - Verify body has `Resolves #<n>`. Patch if missing.
6. **Never push to main directly.** All work goes through the active consolidation lane (today: `dev/phase-1.5-inspection`) or a feature branch targeting it.
7. **Never skip the milestone or label.** Both are non-optional. The roadmap dashboard Marco reads at end-of-session is rendered from milestone progress; an unassigned issue is invisible.
8. **Never fabricate timeline entries.** See §3.4.

---

## 6. Reference: GitHub commands the orchestrator uses most

```bash
# Milestone state
gh api repos/:owner/:repo/milestones --jq '.[] | {number, title, state, open_issues, closed_issues}'

# Issue create with hygiene
gh issue create --title "..." --body "..." \
  --milestone "Phase 1.5 — G7 Implementation" \
  --label "phase-1.5,backend"

# PR hygiene patch
gh pr edit <n> --milestone "Phase 1.5 — G7 Implementation" --add-label "phase-1.5,<functional>"
gh pr edit <n> --body "$(cat new-body.md)"

# Labels — confirm before adding (custom labels often don't exist)
gh label list --limit 100

# Project board (requires read:project scope)
gh project item-list 2 --owner mbtiongson1 --limit 50

# Stale PR triage
gh pr list --state open --json number,title,updatedAt,isDraft \
  --jq '.[] | select((now - (.updatedAt | fromdateiso8601)) > (14 * 86400))'

# Close a rogue PR superseded by consolidation
gh pr close <n> --comment "Closing — superseded by #<consolidation-PR>. ..."
```
