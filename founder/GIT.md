# GAIA Project Operations (GIT.md)

This document outlines how to maintain the project hierarchy and workflow using GitHub's built-in tools. Every agent and contributor must follow these guidelines to ensure the GAIA V2 Roadmap stays on track with minimal operational overhead.

---

## 1. The Hierarchy

GAIA uses a three-tier system for project management:

1.  **Roadmap (@founder/GAIA_ROADMAP.md)**: The ultimate source of truth for strategy and long-term vision.
2.  **Milestones (The Finish Line)**: Phase-level goals (e.g., "Phase 1 — Trust Infrastructure"). Every issue **must** be assigned to a milestone to track roadmap progress.
3.  **Project Board (The Workbench)**: The "GAIA V2 Roadmap" GitHub Project. Used for daily task prioritization and execution tracking.

---

## 2. Issue Management

### Creation
- **Title**: Clear and actionable (e.g., "Implement Trust Score API" not "Trust Scores").
- **Description**: Must include a brief "Definition of Done" or core deliverables.
- **Labels**: Always apply at least one functional label (e.g., `backend`, `frontend`, `infrastructure`).
- **Milestone**: Assign the issue to the relevant Phase milestone and/or the "Immediate Next 30 Days" milestone.

### Transition
- When you begin work, move the issue to **In Progress** on the Project board.
- When you submit a PR, link it to the issue using `Resolves #<Issue_Number>`.

---

## 3. Pull Request Standards

To keep the roadmap automation working, every PR must:
1.  **Link to an Issue**: Use the `Resolves` keyword in the PR description.
2.  **Match Milestone**: The PR should ideally be tagged with the same Milestone as its linked issue.
3.  **Atomic Commits**: Keep changes surgical and focused on the issue's scope.

---

## 4. Maintenance & Cleanup

### Sprint Transitions
- When the **"Immediate Next 30 Days"** milestone reaches 100%, agents should seed the next batch of issues from the next Sprint in the Roadmap.
- Do not seed issues for Phases 3+ until Phase 1 is nearing completion to avoid backlog clutter.

### Stale Issue Triage
- Any issue in **In Progress** for more than 7 days without a linked PR should be moved back to **Todo** and re-evaluated for blockers.

---

## 5. Agent Instructions

If you are an AI agent operating in this repository:
1.  **Check Milestones**: Before proposing work, check the current milestone progress via `gh api repos/:owner/:repo/milestones`.
2.  **Check the Board**: Look at the "Todo" column in the GitHub Project before starting a new task.
3.  **Update Topic**: Always update your session topic to reflect which Milestone and Issue you are currently addressing.

---

*Last Updated: June 10, 2026*
