# GAIA Roadmap v3 — BUILD plan (post-Phase-1.5, 2026-06-20)

**Status:** active. Supersedes `GAIA_ROADMAP v2 (BUILD).md`.
**Audience:** Marco (founder), Codex/Claude/Orchestrator agents, future maintainers.
**Authored:** 2026-06-20, end of Phase 1.5 consolidation.

---

## What changed from v2

The v2 roadmap was an 8-phase build list ordered by topical area (Trust → Reputation → Discovery → Benchmark → SEO → Content → API → Enterprise). Two months of execution proved several of its assumptions wrong:

| v2 assumption | v3 correction |
|---|---|
| Phase 7 (API) is M6–10. | **Phase 7 moves to front (Sprint B).** Reading Gaia data over scraped HTML is what blocks agent platforms (Claude Code, Cursor, Windsurf) from embedding the trust layer. Cheap to build, large leverage. |
| Trending (Phase 3) is M3–6. | **Trending moves to Sprint B alongside the API.** Marco's call 2026-06-20: *"a good repo is only as good as its community using it... biggest impact holders would be new trending skills."* The trending engine is the demand-side flywheel; the API is the supply-side enabler. They ship together. |
| Reputation (Phase 2) Hall of Fame is M2–5 deliverable. | **Hall of Heroes already exists.** Drop from the build list. Surface the existing artifact, don't rebuild. |
| Phase ordering is sequential. | **Phases overlap explicitly via Sprints A–E.** Each Sprint is 2–4 weeks with a kill criterion; Phases (the v2 vocabulary) are kept as topical groupings inside Sprints. |
| 10,000 skills in 12 months is a Phase-1 success criterion. | **Removed.** It's downstream of Reputation + Discovery + automated curation; chasing it would erode the trust invariant. Replaced with quality/usage metrics (see §Success Criteria below). |
| Phases are unbounded — work expands until "done". | **Every Sprint has a task budget + kill criteria.** When the budget runs out, scope cuts; the Sprint ends regardless. |

The v2 moat statement at the bottom (*"trust, prestige, naming, attribution become infrastructure"*) is preserved verbatim. That part was right.

---

## Mission (unchanged)

GAIA becomes the canonical source of truth for AI agent skills, skill discovery, skill verification, contributor reputation, repository trust, and ecosystem intelligence. The long-term goal is to become **infrastructure rather than a website.**

---

## Revised Success Criteria (12 months)

**Honest, measurable, not vanity.**

| Metric | 12-month target | Why |
|---|---|---|
| Named skills with Trust Magnitude > 0 | 500 (was: 10k) | 249 today; doubling is realistic and matches the curation pipeline cadence. 10k requires loosening the trust bar. |
| Embedded API consumers | 5 distinct platforms | An agent platform reading Gaia trust data over the API. Claude Code, Cursor, Windsurf, Continue, etc. |
| S-grade skills | 12 (S=4 today) | A capped tier — overshooting means we got the bar wrong. |
| Trending engine impressions / week | 5,000 | Programmatic SEO + RSS + meta-post output. |
| Public trust API requests / day | 50,000 | Read-only, anonymous tier. |
| Contributors with Trust Score > B | 30 (≈10 today) | The reputation flywheel needs visible winners. |
| Monthly Active Curators | 10 | Humans + bots merging registry PRs / month. |

**Removed from v2:**
- ~~10,000+ indexed skills~~ — vanity, erodes trust if pursued directly.
- ~~1,000+ repositories~~ — same.
- ~~500+ contributors~~ — same.

---

## Sprint plan — 6 month horizon

### Sprint A — Phase 1.5 close-out (now → end of June 2026, ~10 days)

**Goal:** ship Phase 1.5 to main, publish 5.0.0, close the trust foundation.

**In scope:**
- Merge PR #742 (consolidation) to main, no squash.
- Execute `founder/handovers/RELEASE_5.0.0_RUNBOOK.md` (PyPI, npm, GitHub release).
- Close #746 (A-graded origin curation for top-4 S skills).
- Close #755 (✅ done 2026-06-20 — index thresholds aligned).
- Close #759 (CLI pre-flight rule — partial; full suite follows in Sprint B).
- Close #761 (per-evidence Grade follow-up — schema + migration).
- Document the Phase 1 → Phase 2 transition in `founder/MEMORY.md`.

**Task budget:** ~80k tokens / ~$6 / 1 orchestrator + 2 dispatched agents.

**Kill criterion:** all CI green on `main`, `gaia --version` prints `5.0.0`, leaderboard at `gaiaskilltree.com/trust/leaderboard/` reads correctly.

**Out of scope:** anything API-shaped, anything trending-shaped. Sprint A is just landing what's already done.

---

### Sprint B — API Platform + Trending Engine + Hall of Heroes wiring (July 2026, ~3 weeks)

**Goal:** open Gaia to embed and discovery. The supply side (API) and demand side (trending) ship together because each amplifies the other.

**In scope:**

#### B1. Public Trust API (Phase 7 brought forward)

- Read-only endpoints for skills, contributors, evidence, leaderboard.
- Hosted on the existing static site (`gaiaskilltree.com/api/v1/...`) — see `founder/handovers/API_PLATFORM_DESIGN_2026-06-20.md` for the full design (build mode: snapshot from `registry/named-skills.json` → static JSON, served via Cloudflare Pages — no DB, no server, free).
- Auth: anonymous (no key), rate-limited at the edge (Cloudflare Pages default).
- Versioned (`/api/v1/`), schema documented (OpenAPI 3.1), response schema stable.

#### B2. Trending Engine (Phase 3 brought forward)

- Three views: 24h / 7d / 30d.
- Metrics: TM delta, evidence-row delta, rank-up events, new-evidence-added events.
- Surface as `/trending/` (HTML page) + `/api/v1/trending/<window>` (JSON) + RSS feed.
- "Recently Ascended" — rank changes in the last 7d, sorted by ascension date.
- "Most Contested" — buckets with ≥2 named implementations, sorted by recent activity.
- Marco-as-first-mover: each Monday a meta-post drafts "Trending This Week" using the engine's output (auto-publish via `scripts/add_post.py`).

#### B3. Hall of Heroes wiring

- Marco confirmed Hall of Heroes already exists. **Surface it from the homepage + nav, don't rebuild.**
- Add it as an explicit `/heroes/` route if not already; cross-link from the leaderboard.
- Tag the existing artifact with v3-canonical metadata so the API can serve it.

**Task budget:** ~250k tokens / ~$25 / 1 orchestrator + 4 dispatched agents (B1 design + impl, B2 design + impl, B3 wiring).

**Kill criterion:**
- A third-party agent platform can `curl https://gaiaskilltree.com/api/v1/skills/garrytan/gstack` and parse it.
- `/trending/7d` shows real movement (not zero) on Monday morning.
- A Tweet-length pitch — *"Gaia tracks which AI agent skills are trending"* — has a clickable URL to land on.

**Out of scope:**
- Authenticated API tier (defer to Sprint E).
- Skill-graph types beyond what's already shipped (defer to Sprint C).
- Benchmark integration (defer to Sprint D).

---

### Sprint C — Reputation deepening + Discovery extras (August 2026, ~3 weeks)

**Goal:** turn the trending flywheel into a sustainable contributor incentive loop.

**In scope:**
- **Prestige Score** — formalize the formula (`Contribution + Discovery + Verification + Longevity`). Compute it for every contributor, surface on profiles.
- **Badges** — implement the named badge set (Pioneer, Skill Sage, Apex Contributor, etc.) as derivable from prestige + history. Don't gate them, just compute and award.
- **Rank History per contributor** — chart the contributor's prestige over time on their profile.
- **Skill Graph types** — Dependency + Evolution graphs (the two highest-utility of the v2-named four). Defer Category and Contributor graphs (low marginal value).
- **Per-category SEO pages** (Phase 5 partial) — one page per generic skill ref showing all named children, evidence summary, top contributor.

**Task budget:** ~180k tokens / ~$18.

**Kill criterion:**
- Marco can point at a contributor's badge and explain why they earned it without consulting the source.
- The Dependency graph at `/graph/dependency/` is non-trivial (≥30 nodes visible).
- Programmatic-SEO indexability check passes on 50 random per-skill pages.

**Caveat (Marco 2026-06-20):** *"Still on defense on Sprint C if it will go first with Sprint B."* — the call to ship C before B is reserved; default ordering is B → C. If trending hits a content/data wall during B and stalls, swap to C.

---

### Sprint D — Benchmark MVP + Content Engine (September 2026, ~3 weeks)

**Goal:** make trust quantitative, not just curated.

**In scope:**
- **Two real benchmarks** running end-to-end. Coding (e.g., HumanEval-derived) + research (e.g., MMLU-shaped). Pick benchmarks that already have public datasets — do not invent.
- **Benchmark-result evidence flow** — submitted via `gaia push --benchmark <name> --score <pct>`. Routes through CI; produces a `benchmark-result` evidence row with `percentile` populated.
- **Benchmark pages** — one per benchmark, leaderboard view + score history.
- **Content Engine MVP** — the meta-post pipeline from Phase 1.5 generalised. Weekly auto-report via the L3-mechanical fallback pattern (`founder/handovers/WORKFLOW_PATTERNS.md`).

**Task budget:** ~250k tokens / ~$25.

**Kill criterion:**
- A contributor can submit a benchmark run from CLI and have their skill regrade within an hour.
- A weekly auto-report ships every Monday morning without orchestrator intervention.

---

### Sprint E — Enterprise + scale (October–December 2026, ~10 weeks)

**Goal:** monetization-ready surface area.

**In scope:**
- **Authenticated API** — keys, per-user rate limits, billing scaffolding (don't actually charge yet).
- **Private registries** — orgs maintain internal skills, internal rankings, internal trust scores.
- **Enterprise Trust** — compliance reports, security review summaries.
- **Enterprise Analytics** — trend monitoring, capability mapping, contributor intelligence.
- **API rate limits** — actually enforced (anonymous 100/day, authenticated 5000/day, enterprise custom — match v2 numbers).
- **Per-ascension SEO pages** — auto-generated for every rank-up event, drives long-tail traffic.

**Task budget:** ~600k tokens / ~$60. (E is the biggest because it adds infra surface area.)

**Kill criterion:**
- A paying customer could be onboarded if one walked up. (Not actually onboarding; just being ready.)
- The first month's API request log shows real outside use.

---

## Cross-cutting concerns (running throughout all Sprints)

- **Programmatic-First Policy** + **CLI pre-flight rule** (CLAUDE.md §Programmatic-First) — every mutation goes through CLI; CLI rejects invalid states before write. Issue #759.
- **Source curation automation** (#762) — graduates `/ev-pipeline` to a scheduled crawl. Lands during Sprint B–C; reduces P3 effort to zero by Sprint D.
- **Stargazer + monthly TM heartbeat** (#760) — defensive maintenance. Lands during Sprint C.
- **Per-evidence Grade calibration** (#761) — explicit row-grade thresholds distinct from skill-level. Lands during Sprint A close-out.
- **Liveness Heartbeat** — META.md §2.2; weekly URL checks; demerit emit on death. Bundled into #760.

---

## What's still NOT on the roadmap

These are Marco's calls to make later, not now:

- **A1 Discord / community feature** — "community" is downstream of reputation; revisit after Sprint C.
- **Skill marketplace / monetization for contributors** — explicitly out of scope per `README.md` ("This is not a skill marketplace").
- **AI-skill ranking-as-a-service** — the API is read-only in v3; selling the rankings is a Phase-9 conversation.
- **Multi-tenancy / SaaS** — implied by Sprint E private registries but not committed.

---

## Task budget summary (6-month horizon)

| Sprint | Token budget | Cost estimate | Days |
|---|---|---|---|
| A — Phase 1.5 close-out | ~80k | ~$6 | 10 |
| B — API + Trending | ~250k | ~$25 | 21 |
| C — Reputation + Discovery | ~180k | ~$18 | 21 |
| D — Benchmark + Content | ~250k | ~$25 | 21 |
| E — Enterprise | ~600k | ~$60 | 70 |
| **Total** | **~1.36M** | **~$134** | **~143** |

These are **dispatch budgets, not orchestrator costs.** Orchestrator overhead (planning, GitHub hygiene, memory, dispatch authoring) typically runs 30% on top — total program cost over 6 months is **~$175** for ~1.8M tokens.

That's a fraction of one developer-week. **The constraint is not money, it's serialised review bandwidth (Marco's time).** Sprint budgets are sized for Marco-can-review-on-Saturday cadence.

---

## How this maps to GitHub

Each Sprint becomes one **Milestone** (the "Phase 1.5 — G7 Implementation" pattern works; reuse it).

Each Issue gets:
- Sprint milestone + functional label (per `founder/GIT.md` §2)
- Sized estimate in the body (`size: S/M/L/XL` corresponding to ~10k/30k/100k/300k tokens)
- Kill criterion in the description

The roadmap dashboard Marco reads at end-of-session is the milestone progress page, exactly as today.

---

## Status of Phase 1 (v2) — final

| v2 deliverable | State |
|---|---|
| Trust score MVP | ✅ Trust Magnitude in code |
| Database migration | ✅ Atomic, signed by `trustMagnitudeInputHash` |
| Score explanations | ✅ `gaia-tm-inspect` skill + leaderboard tooltip |
| Trending engine | ⏳ Sprint B |
| Rising skills | ⏳ Sprint B |
| Rising repositories | ⏳ Sprint B (depends on stargazer pull #760) |
| Contributor prestige | ⏳ Sprint C |
| Badge framework | ⏳ Sprint C (basics shipped via Phase-1; named badges in C) |
| Hall of Fame | ✅ Hall of Heroes (Marco confirms exists; Sprint B wires it) |
| Security scanner MVP | ✅ G3 / `securityScanner.py` |
| Verification workflow | ✅ G4 / `verification.py` |
| Benchmark architecture | ✅ Designed (`docs/architecture/benchmark-framework.md`); ⏳ live runs Sprint D |
| Weekly ecosystem reports | ⏳ Sprint D (content engine) |

**Phase 1 of v2 is closed at end of Sprint A.** Anything not done by then moves explicitly into the new Sprint plan.

---

## Decision log (v3 ratification)

| Date | Decision | Recorder |
|---|---|---|
| 2026-06-20 | Move Phase 7 (API) to Sprint B; defer Phase 8 enterprise to Sprint E. | Marco |
| 2026-06-20 | Trending engine elevated to Sprint B alongside API. | Marco |
| 2026-06-20 | Hall of Heroes is shipping; surface, don't rebuild. | Marco |
| 2026-06-20 | Drop "10k skills in 12 months" — replace with quality/embed metrics. | Marco + Orchestrator analysis |
| 2026-06-20 | Sprint A–E sequence with kill criteria + budgets. | Marco |
| 2026-06-20 | Sprint C-before-B contingency reserved. | Marco |

---

*Authored: 2026-06-20, end of Phase 1.5 consolidation. Next ratification: end of Sprint A (post-merge of PR #742).*

*Marco's framing for v3: "biggest impact holders would be new trending skills... I would love to be the first (reliable) one talking about it or sending the trend." That's the north star — be first in the trending conversation. Everything else serves that.*
