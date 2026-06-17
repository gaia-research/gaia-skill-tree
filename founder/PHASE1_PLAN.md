# GAIA Phase 1 — Execution Plan

**Status:** Draft v2 — revised after full comment harvest (2026-06-10). Awaiting Marco's approval.
**Scope decision (2026-06-10):** Hybrid. Milestone [#4 "Phase 1 — Trust Infrastructure"](https://github.com/mbtiongson1/gaia-skill-tree/milestone/4) (due Sep 10) is the umbrella; execution follows v2 BUILD sprint order. Benchmarks (#649) and certification tiers (#650) are design-only in Phase 1.
**Owner:** Orchestrator. Implementation hands over to Claude Code / coding agents — the orchestrator never modifies gaia-skill-tree. All GitHub writes require Marco's approval.

---

## Ground Truth (audited 2026-06-10, via gh)

| Milestone | Due | Progress | Open items |
|---|---|---|---|
| #7 Immediate Next 30 Days | Jul 10 | 1/4 (the closed item is PR #653, merged) | #646, #647, #648 |
| #4 Phase 1 — Trust Infrastructure | Sep 10 | 0/6 | #185, #128, #155, #637, #649, #650 |

Project board #2 is healthy: all roadmap issues present, everything in **Todo** (#653 in Done). No board sync needed — earlier logged-out audit was wrong about this.

## What the Comments Changed (the real findings)

**1. Trust scores are under re-evaluation by Marco himself (#646, #648 comments, Jun 10).**
Direction signals: prefer **ranks** over arbitrary 0–100 scores; score **evidence, not skills** — graded tiers à la PSU ratings (80+ Bronze/Silver/Gold/Platinum); possibly **time-based evidence** (how long a skill has held a rank); #648's explanations become **"actionable reports"**; skepticism toward registry-style numeric trust scores as unscientific hype. Token-savings-as-metric noted as future concept (no telemetry yet).
→ **Workstream A cannot hand over to a coding agent yet. The RFC must settle first.**

**2. #647 is dispositioned (comment, Jun 10):** migration **deferred**; not designing for 10,000+ skills; **git-as-database is the strategy** (dolt or Supabase next in line); scaffolding-level ideation only; issue stays open as a beacon for DB-specialist contributors.
→ Label conflict remains (`help wanted` + `wontfix`) — cleanup proposal below.

**3. #128 (gaia push/share) has a full design note awaiting Marco's call:** share-bundle CLI is buildable now; the static copy-link page needs a hosting decision — (a) committed `docs/share/` static file, (b) gist/external, (c) OAuth-bound behind #155.

**4. #155 (GitHub sign-in) has a mini-PRD; blocked on operational setup only:** real GitHub OAuth app, registered callback (gaia.tiongson.co/auth/callback), Cloudflare secrets. Blocks #494 signed badges. Code scaffolding can start once Marco provisions.

**5. #637:** per Marco — #635 covers `gaia tree`/`gaia graph`; everything else except `gaia skills` stays RFC.

**6. #185, #649, #650:** no discussion yet. Verification Workflow still has **no issue at all**.

---

## Workstream A — Trust Model: DECIDED, implementation next (#646 → #648)

RFC accepted 2026-06-10 (`handovers/TRUST_MODEL_RFC.md` v2; summary on #646). Model: ranks are the trust signal; evidence grades S/A/B/C (Platinum/Gold/Silver/Bronze) separate from evidence types (#654 RFC); Overall Trust Grade per skill; tenure display-only; skill-level only.

Remaining steps:

1. **Orchestrator drafts the implementation handover** (RFC §4): schema changes (`schema/` branch), grading pipeline (`cli/`/`infra/`), backfill via `gaia dev` flows, #648 actionable-report rendering (`design/` branch). Marco approves before any coding-agent handover.
2. #654 (evidence types) proceeds as parallel RFC — doesn't block grade-schema work if the type axis ships extensible.

Risk to Jul 10: design risk retired; remaining risk is implementation volume. Mitigation: schema + grading first, reports second; split PRs.

## Workstream B — #647: deferred (resolved)

No Phase 1 implementation. Optional cheap deliverable: orchestrator drafts a 1-page "git-as-database limits" note (what breaks first as the registry grows, dolt/Supabase trigger criteria) to park in the issue. Label cleanup pending approval (below).

## Workstream C — Security Scanner (#185)

Unchanged: orchestrator drafts `handovers/SECURITY_SCANNER_SPEC.md` (scan classes: shell execution, file deletion, network access, prompt-injection patterns, credential harvesting; outputs: warnings, risk level, remediation; hook: `gaia push` intake → `registry-for-review/`). RFC label means Marco reviews spec before handover.

## Workstream D — Verification Workflow (issue still missing)

Hold the issue draft until the Trust Model RFC settles — verification levels (Community/Benchmark/Security/Enterprise) should be defined in terms of whatever evidence-grading model wins, or they'll be rewritten twice.

## Workstream E — Design-only (#649, #650)

Unchanged, low priority. #650 certification tiers now naturally derive from evidence grades — fold into the Trust Model RFC rather than a separate doc.

## Sequencing (revised)

```
Trust Model RFC (A1) ──► #646 impl ──► #648 impl        [milestone 7, Jul 10]
        │
        ├──► D (verification issue)  ├──► E (#650 folded into RFC)
C (#185 spec) ────► scanner handover                     [milestone 4, Sep 10]
B (#647) — deferred; optional limits note
#128 — awaits hosting decision · #155 — awaits OAuth provisioning
```

## Proposed GitHub Ops — BATCH 1 (each needs Marco's approval)

| # | Operation | Rationale |
|---|---|---|
| 1 | #647: remove `wontfix` label | Contradicts the open invitation to DB contributors; `help wanted` + `planning` describe reality |
| 2 | #647: move milestone #7 → #4 | Deferred work shouldn't burn the Next-30 deadline |
| 3 | #646: post Trust Model RFC link/summary as comment (after RFC approved) | Closes the RFC loop where contributors can see it |
| 4 | #155: comment confirming "design/infra task, keep open" + Marco's provisioning checklist | Issue currently dangles between close-as-not-planned and PRD |

## ACTION ITEMS — Marco

1. ~~Provide PAT~~ ✓ done — gh operational in sandbox.
2. **Decide #128 hosting**: (a) docs/ static page, (b) gist, (c) OAuth-bound after #155 — the design note recommends CLI-first then (a).
3. **#155 provisioning** (whenever ready): create GitHub OAuth app, register callback URL, store secrets in Cloudflare — blocks #494 badges.
4. **Approve/amend Batch 1 ops** above.
5. **Trust Model RFC working session** — the highest-leverage hour you can spend this week; everything in milestone 7 sits behind it.
