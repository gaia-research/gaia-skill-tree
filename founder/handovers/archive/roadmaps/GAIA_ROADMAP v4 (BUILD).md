GAIA — Canonical Reputation & Discovery Layer for Agent Skills

Version: 4.0

Status: Founder Roadmap (BUILD)

Supersedes: `GAIA_ROADMAP v3 (BUILD).md` (retained for history)

Author: Orchestrator + Marco Tiongson

Ratified: 2026-07-02 (end of Sprint B)

Audience:

* Codex
* Claude Code
* Orchestrator Agents
* Gaia Research Inc. (planning)
* Human Maintainers

---

## What changed from v3

1. **Sprint order is now D-first, not C-first.** Trend engine shipped in B is a tree falling in an empty forest without the Content Engine. Weekly auto-report + first live benchmark ship before any contributor-side rewards.
2. **Sprint C reframed as "Index Foundations."** Prestige as a naive sum-of-TM is inaccurate for suites. Trust Magnitude has known refinement debt (fusion score math, repo-own halving). Sprint C now formalizes indices as first-class Gaia Research products with versioning, reproducibility, and citation format — not "reputation deepening" ornament.
3. **Sprint E is now "Skill Groups + Benchmarks 2.0."** Starless nodes get renamed to Skill Groups, backed by ML clustering + human-relevant benchmarks (cost/use, time-saved). Named badges move here — they need an audience before they mean anything, and the audience is what Sprint D builds.
4. **New Sprint F — "Migration + Monorepo Move."** Web frontend migrates React/Node, Skill Tree gets packaged as a light dev-first repo, everything else moves to `gaia-research/gaia-research` monorepo. This is where the biggest capital is being placed.
5. **Sprint G is v3's old Sprint E** — Enterprise + Auth API. Deferred by one slot.
6. **Named badges, per-generic SEO pages, skill-graph types** — all deferred out of C. Details in per-sprint notes.
7. **Budgets are cushioned** — sprint budgets grew ~30% vs. v3 estimates for orchestration + review + rework overhead. Total 6-month spend stays under $150.
8. **Migration invariants added** as a cross-cutting section — every non-trivial PR must document how the code survives (or gets rewritten in) the Sprint F migration.

---

## Mission (unchanged from v3)

GAIA becomes the canonical source of truth for:

* AI Agent Skills
* Skill Discovery
* Skill Verification
* Contributor Reputation
* Repository Trust
* Ecosystem Intelligence
* **Indices as research products (new in v4)**

Long-term: infrastructure, not a website. **Gaia Research Inc.** is the entity that publishes indices — Skill Tree is its flagship data source and OSS surface.

---

## Product Thesis (updated for v4)

**People do not care about registries. They care about status, discoverability, trust, and recognition.**

**Institutions and the press care about numbers.** Indices are numbers with methodology. That's the Gaia Research pitch — the same way S&P publishes the S&P 500, Gaia publishes:

- **Trust Magnitude Index** — v1 shipped; v2 refinements in Sprint C
- **Prestige Index** — v1 in Sprint C, non-naive (suites-aware)
- **Skill Group Benchmarks** — v1 in Sprint E (cost/use, time-saved, quality per skill group)
- Further indices TBD as Gaia Research directs research agenda

Each index carries a semver number, a `<index>InputHash` reproducibility fingerprint, a whitepaper (`docs/indices/<name>/`), and a citation format.

---

## Sprint Plan — 9 Month Horizon (v4)

### Sprint B — closing (now → +7 days)

**Goal:** merge PR #895 (`dev/sprint-b-closure` → `main`), cut v6.0.0, close remaining Sprint B sub-issues.

**Remaining tasks:**
- Resolve PR #895 merge conflicts
- Comment + close #697, #698 (Rising Skills / Rising Repos — already resolved by PR #891)
- Update EPIC #855 body to reflect merged state
- Cut v6.0.0 release (major bump: API + Trending are new product surfaces)

**Task budget:** ~$3 (mostly resolve conflicts + release runbook)

**Kill criterion:** PR #895 merged, v6.0.0 tagged, `gaiaskilltree.com/api/v1/trending/7d.json` returns live data.

---

### Sprint D — Content Engine + Benchmark MVP (2026-07-02 → 2026-08-01, ~30 days)

**Goal:** build the megaphone. Ship the first live benchmark. Prove the trending flywheel is audible, not just observable.

**In scope (Splurge — the biggest surfaces):**

1. **Content Engine MVP + weekly auto-report**
   - Monday 08:00 UTC cron auto-posts a Trending-This-Week report
   - Templates for: "Trending This Week", "Recently Ascended", "Most Contested"
   - RSS feed picks it up; each post gets a permanent `/reports/YYYY-WW/` URL
   - **Publish gate for first 4 weeks:** generation is auto; publish is a manual flag flip. Prevents first-bad-post trust hit
   - L1→L2→L3-mechanical fallback pattern (per `founder/handovers/WORKFLOW_PATTERNS.md`)
   - **Splurge here.** This is the megaphone that sells all downstream indices.

2. **Benchmark #1 — one skill, end-to-end (HumanEval-derived)**
   - Public dataset, CI-reproducible
   - `gaia push --benchmark <name> --score <pct>` writes benchmark-result evidence
   - Verifier-attestation gate (verifier OR CI reproduction) — required to prevent TM inflation from self-attested benchmark claims
   - One benchmark leaderboard page — reuse Trust Leaderboard SVG bar chart aesthetic
   - **Splurge on schema decisions here** — this echoes into Sprint E's skill-group benchmarks.

**In scope (Satisfice — good-enough + auto-batchable):**

3. **Benchmark #2 — mirrored, not live**
   - Ingests public MMLU-shaped leaderboard scores from published sources
   - No live re-run; treats other benchmarks as citations, not sources of truth
   - Second benchmark surface without doubling infra
   - **Satisfice.** Auto-PR + batch review; modular ingest wrapper.

4. **SEO surface — the parts that survive Sprint F migration**
   - Site-wide meta + Open Graph on all `docs/` pages
   - `docs/sitemap.xml` + `docs/robots.txt` (proper)
   - One human-facing OKF-driven index at `docs/skills/index.html` (aggregated view of all generic skills; no per-generic pages yet — those wait for Sprint E Skill Groups rename)
   - Structured data (JSON-LD) on all live pages
   - **Satisfice.** Auto-PR + batch review.

**In scope (cross-cutting for D):**

5. **Sprint D CONTEXT bundle + agent journal**
   - `founder/handovers/sprint-d/CONTEXT.md` — the ONLY file agents onboard from
   - `founder/handovers/sprint-d/journal.md` — append-only agent notes, 80-100 words per dispatch

**Task budget (cushioned):** ~$27 total
- Splurge domains: ~$15 (Content Engine ~$6, Benchmark #1 pipeline ~$5, benchmark schema ~$4)
- Satisfice domains: ~$6 (Benchmark #2 mirror ~$2, benchmark leaderboard page ~$2, SEO surface ~$2)
- Orchestration + review + rework overhead: ~$6

**Kill criteria (all must pass):**
- KC1: First Monday auto-report ships without orchestrator intervention (behind manual-publish gate)
- KC2: `gaia push --benchmark humaneval --score X` writes a valid benchmark-result evidence row; verifier gate or CI check enforces trust
- KC3: `gaiaskilltree.com/reports/YYYY-WW/` returns a permanent, indexed, tweetable URL
- KC4: One skill has a live benchmark score visible on its explorer page

**Splurge/satisfice rationale:** biggest strategic surface is the megaphone (KC1 + KC3) and the schema that ripples into Sprint E benchmarks. Everything else can be modularly rebuilt in the React/Node migration; the auto-report content pipeline and evidence schema are portable Python that survives migration.

---

### Sprint C — Index Foundations (2026-08 → 2026-09, ~21 days)

**Goal:** Trust Magnitude v2 (fixes fusion + repo halving); Prestige Index v1 (non-naive, suites-aware); versioning framework for all indices; rank-history chart on contributor profiles.

**In scope:**

1. **Trust Magnitude v2 refinement (~$5)**
   - Fix fusion-recipe scoring (currently over-credits suites)
   - Fix repo-own halving edge case
   - TM v2.0 diff report vs v1 published as a whitepaper (`docs/indices/tm/v2.0-changelog.md`)
   - Backfill run; publish `trustMagnitudeInputHash_v2` alongside v1 for a deprecation window

2. **Prestige Index v1 (~$5)**
   - Non-naive formula that discounts suite-membership (probably weighted-average with per-suite cap)
   - Marco's call on formula shape; Orchestrator drafts 2-3 candidate formulas for review before dispatch
   - **NOT longevity** (Marco's call in v4 planning session — longevity is deferred to potential v2 of Prestige Index)
   - Published as `/api/v1/indices/prestige/v1.0.json`, methodology page `docs/indices/prestige/`

3. **Index Versioning framework (~$5)**
   - `/api/v1/indices/<name>/<semver>.json` schema
   - Each index has `inputHash`, `methodology_url`, `version`, `computed_at`
   - Landing page `docs/indices/` lists all indices with current version + whitepaper + citation snippet
   - Citation format: BibTeX + APA + plaintext

4. **Rank History per contributor chart (~$2)**
   - Per-contributor prestige-over-time line chart on `docs/u/<handle>/`
   - Backfilled from timeline events already in `skill-trees/<handle>/skill-tree.json`
   - Reuse `docs/js/profile-timeline.js` — new render fn, same file

5. **Sprint C CONTEXT bundle + agent journal**

**Task budget (cushioned):** ~$21 total
- Splurge: index versioning framework (~$5) + TM v2 refinement (~$5) — these are load-bearing for Gaia Research thesis
- Balanced: Prestige Index v1 (~$5)
- Satisfice: Rank history chart (~$2)
- Orchestration + review: ~$4

**Kill criteria:**
- KC1: `gaiaskilltree.com/indices/` lists TM v2 + Prestige v1 with whitepapers and citations
- KC2: A press/paper citing "Gaia TM v2.0, 2026-08" gets a permanent reproducible fingerprint
- KC3: Prestige Index v1 does NOT rank contributors purely by sum-of-skills (suites-aware)
- KC4: Contributor profile page renders a prestige-over-time chart

---

### Sprint E — Skill Groups + Benchmarks 2.0 + Named Badges (2026-09 → 2026-10, ~28 days)

**Goal:** rename Starless → Skill Groups; ML-driven clustering to auto-group similar skills; human-relevant benchmarks (cost/use, time-saved); named badges as reward layer for contributors now that there's an audience.

**In scope:**

1. **Skill Groups infrastructure (~$8)**
   - Rename Starless → Skill Groups across code + docs + copy (banned-synonym list update in `CONTEXT.md`)
   - ML clustering pipeline that dynamically groups skills of same caliber
   - Skill Group directory + per-group landing page
   - Migration: existing Starless URLs redirect to new Skill Group URLs (SEO invariant)

2. **Benchmarks 2.0 — human-relevant scores (~$8)**
   - Cost/use benchmark (compute cost per invocation, benchmarked across N runs)
   - Time-saved benchmark (human-hours displaced, sourced from case studies or verifier attestations)
   - One additional quality benchmark per Skill Group
   - Group leaderboards: which skill in this group performs best?

3. **Named Badges (~$5)**
   - Pioneer / Skill Sage / Apex Contributor / Archivist / Pathfinder / Grand Curator derivation from prestige + history
   - Display on Hall of Heroes + contributor profiles
   - Don't gate; compute and award

4. **Per-Skill-Group SEO pages (~$4)**
   - Now that groups are meaningful, generate one human-facing HTML page per group
   - Includes: named children, evidence summary, top contributor, group benchmark leaderboard
   - This is v3's "per-generic-skill SEO pages" done properly

5. **Sprint E CONTEXT bundle + agent journal**

**Task budget (cushioned):** ~$32 total (biggest sprint after F)

**Kill criteria:**
- KC1: "Starless" no longer appears in user-facing surfaces (grep verifies)
- KC2: Every skill belongs to exactly one Skill Group; grouping is ML-derived + auditable
- KC3: Cost/use benchmark returns real numbers for at least 20 skills across ≥5 groups
- KC4: At least 5 contributors carry a named badge on their profile
- KC5: `/skills/<group>/` renders a full SEO-optimized page with group benchmark leaderboard

---

### Sprint F — Migration + Monorepo Move (2026-10 → 2027-01, ~10 weeks)

**Goal:** migrate frontend to React/Node; package Skill Tree as a light dev-first OSS repo; move website + Gaia Research surfaces to `gaia-research/gaia-research` monorepo.

**In scope:**

1. **`gaia-research/gaia-research` monorepo scaffold (~$8)**
   - New Turborepo (or nx) with packages: `@gaia-research/web`, `@gaia-research/indices`, `@gaia-research/skill-tree` (data), `@gaia-research/api-client`
   - CI/CD pipeline
   - Migration invariants doc

2. **React/Node frontend rewrite (~$25)**
   - Next.js 15+ (Node 22 LTS); reuse Cloudflare Pages/Workers
   - All URLs preserved (SEO invariant)
   - All Sprint D content-engine templates ported (Python content pipeline stays; just the rendering layer moves)
   - All Sprint C indices surfaces reimplemented; API contracts unchanged (SDK compatibility)
   - All Sprint E group pages ported
   - Modern design system

3. **Skill Tree as light dev-first repo (~$5)**
   - Strip website surfaces from `gaia-skill-tree`
   - Repo becomes: CLI + Python SDK + registry data + schema + MCP server + minimal reference docs
   - Website moves out
   - PyPI/npm continues shipping from `gaia-skill-tree` unchanged (users don't feel this)

4. **Cutover + DNS (~$3)**
   - `gaiaskilltree.com` DNS switches to `gaia-research/gaia-research` deployment
   - 30-day grace period where old site still runs (fallback)
   - Post-cutover monitoring

5. **Documentation + migration retrospective (~$3)**

**Task budget (cushioned):** ~$60 total — biggest single sprint. Marco's call: "putting most of my funds here."

**Kill criteria:**
- KC1: `gaiaskilltree.com` serves React/Node stack; all v4-shipped URLs return 200
- KC2: `gaia-skill-tree` repo passes CI with website removed
- KC3: `gaia dev docs` still generates all data artifacts (Class P + Class S — the S artifacts now live in the new repo)
- KC4: No SEO regression 14 days post-cutover (search console diff acceptable)

**Migration invariants (mandatory for every PR from Sprint D onwards):**
- Every non-trivial PR includes `## Migration notes` in body: "This code ports to new stack as: X" OR "Rewrite required in Sprint F, tracked in issue #YYY"
- Data files (JSON, MD, YAML) survive as-is
- Python CLI + registry survive as-is
- API contracts survive as-is (SDK compatibility)
- URL structure survives as-is (SEO)
- HTML/CSS/JS in `docs/` is throwaway — do NOT splurge on styling refinements that will be rebuilt

---

### Sprint G — Enterprise + Auth API (2027-Q1+, ~10 weeks)

**Goal:** monetization-ready surface area. Formerly v3's Sprint E.

**In scope (unchanged from v3):**
- Authenticated API — keys, per-user rate limits, billing scaffolding
- Private registries — orgs maintain internal skills
- Enterprise Trust — compliance reports, security review summaries
- Enterprise Analytics — trend monitoring, capability mapping, contributor intelligence
- API rate limits — actually enforced (anonymous 100/day, authenticated 5000/day, enterprise custom)
- Per-ascension SEO pages — long-tail traffic

**Task budget:** ~$65 (unchanged)

**Kill criterion:** A paying customer could be onboarded if one walked up.

---

## Cross-Cutting Concerns

### Migration Invariants (starting Sprint D)

Every non-trivial PR must include this block in its body:

```markdown
## Migration notes

- **Portable:** [list files/modules that survive as-is in Sprint F]
- **Rewrites:** [list files that will be rewritten in Sprint F; link tracking issue if known]
- **Invariants:** [URL preservation, API contract, data schema — call out anything load-bearing]
```

Orchestrator applies `migration-notes-missing` label on PRs that lack this section for non-trivial changes. Trivial: docs typos, single-file refactors under 50 LoC, dependency bumps.

### Splurge vs Satisfice Discipline

Splurge (careful spec, high review effort) applies to:
- Schema decisions (evidence types, index versioning contracts)
- URL structure
- Load-bearing algorithms (TM, Prestige, ML clustering)
- Anything shipped as Gaia Research index or API contract

Satisfice (auto-PR, batch review, "good enough") applies to:
- Docs updates
- Test coverage improvements
- CI YAML tweaks
- Non-critical UI iterations
- Anything explicitly slated for Sprint F rewrite

Orchestrator applies `auto-merge-eligible` label on PRs that are: <100 LoC, CI green, non-schema, non-registry, non-URL-affecting. Auto-merge action closes without per-PR review turn.

### Batch Review Windows

- **Non-blocking dispatches:** Tue / Wed / Fri / Sat
- **Marco reviews:** Mon evenings + Thu evenings
- **Orchestrator drafting:** Sundays

Reduces context switching and lets deep-work happen mid-week.

### Sprint CONTEXT bundles

Each sprint gets `founder/handovers/sprint-<x>/CONTEXT.md` — the ONLY file agents onboard from. Consolidates: kill criteria, files-that-matter, invariants, other agents' state. Replaces 8-10 per-agent reads with 1.

### Append-only agent journal

Each dispatched agent writes 80-100 words to `founder/handovers/sprint-<x>/journal.md` at close: what they did, SHAs pushed, gotchas the next agent needs. Cheap knowledge transfer, zero orchestrator re-derivation.

### Model routing

Default per workstream (Sprint D EPIC will override where needed):
- **Splurge domains:** Opus (max effort) — Content Engine core, benchmark schema, TM v2 formula
- **Balanced domains:** Opus (high) — Prestige formula, index versioning framework, ML clustering
- **Satisfice domains:** Sonnet — mirror ingest, docs updates, satisfice UI, port-and-adapt work
- **Auto-batchable:** Haiku with schema — test additions, dependency bumps, CI YAML edits

---

## Task Budget Summary (9-month horizon, v4)

| Sprint | Token budget | Cost estimate | Days |
|---|---|---|---|
| B — closing | ~30k | ~$3 | 7 |
| D — Content Engine + Benchmark MVP | ~270k | ~$27 | 30 |
| C — Index Foundations | ~210k | ~$21 | 21 |
| E — Skill Groups + Benchmarks 2.0 + Named Badges | ~320k | ~$32 | 28 |
| F — Migration + Monorepo Move | ~600k | ~$60 | 70 |
| G — Enterprise + Auth API | ~650k | ~$65 | 70 |
| **Total (9 months)** | **~2.08M** | **~$208** | **~226** |

**Vs. v3:** v3 total was ~$134 for 6 months; v4 is ~$208 for 9 months. Higher absolute spend, ~7% higher per-day rate — the delta is the migration + monorepo capital (F). Marco's explicit call: "putting most of my funds in migration to make sure we are in the clear."

**Cushions:** every sprint budget has ~25-35% orchestration/review/rework overhead baked in. If a sprint runs under budget, unspent tokens roll into the next sprint's cushion, not a scope expansion.

---

## What's NOT on v4

- Discord / community feature — deferred until after Sprint E
- Skill marketplace / monetization for contributors — out of scope per `README.md`
- Selling raw index data — Sprint G+ conversation, Gaia Research call
- Multi-tenancy / SaaS — implied by G private registries, not committed
- **Longevity dimension in Prestige** — deferred; Marco prefers Prestige v1 handles suites first
- **Category graph / Contributor graph** views — permanently deferred; low marginal value
- **Evolution graph as a distinct view** — Upgrade Path in skill-explorer.js is sufficient
- **Per-generic-skill SEO pages** — replaced by per-Skill-Group SEO pages in Sprint E

---

## Decision Log (v4 ratification)

| Date | Decision | Recorder |
|---|---|---|
| 2026-07-02 | Sprint D promoted to Sprint C's slot; Sprint C reframed as Index Foundations. | Marco |
| 2026-07-02 | Prestige Index v1 will be non-naive (suites-aware), NOT include longevity. | Marco |
| 2026-07-02 | Named badges moved from Sprint C to Sprint E. Reasoning: rewards need audience; audience is Sprint D output. | Marco |
| 2026-07-02 | Skill graph types (dependency + evolution) deferred out of C. Not on v4 explicitly. | Marco |
| 2026-07-02 | Per-generic-skill SEO pages replaced by per-Skill-Group SEO pages in Sprint E. | Marco |
| 2026-07-02 | Starless → Skill Groups rename in Sprint E, not before (ML clustering + benchmarks make the name meaningful). | Marco |
| 2026-07-02 | Sprint F (React/Node migration + monorepo move) is the largest capital placement. | Marco |
| 2026-07-02 | Migration invariants become mandatory PR body section starting Sprint D. | Orchestrator + Marco |
| 2026-07-02 | Splurge/satisfice discipline codified; auto-merge label for <100 LoC + non-schema + CI-green PRs. | Marco |
| 2026-07-02 | Batch review windows: Mon + Thu evenings only. | Marco |
| 2026-07-02 | Model routing defaults set per workstream tier. | Orchestrator |
| 2026-07-02 | Gaia Research Inc. is the parent org; Skill Tree is the flagship OSS repo; indices are the research products. | Marco |
| 2026-07-02 | Content Engine's first 4 weeks run behind a manual-publish gate. | Orchestrator + Marco |
| 2026-07-02 | Benchmark evidence requires verifier attestation OR CI reproduction — never self-attested only. | Orchestrator + Marco |

---

## Status of Phase 1 / Sprint B — final at v4 ratification

| Deliverable | State |
|---|---|
| Trust Magnitude (v1) | ✅ Live |
| Public Trust API v1 | ✅ Live (Sprint B, PR #857) |
| Trending engine pipeline | ✅ Live (Sprint B, PR #891 → #895 pending) |
| RSS feed + Ascended/Contested | ✅ Live (Sprint B, PR #894 → #895 pending) |
| Hall of Heroes | ✅ Live (Sprint B, PR #892 on dev/sprint-b-closure → #895 pending) |
| Python + TS SDK | ✅ Live (Sprint B, PR #893 → #895 pending) |
| OKF (agent-readable skill bundle) | ✅ Live (merged main 2026-06-29) |
| Trust Leaderboard (AA-style) | ✅ Live (PR #867) |
| Content Engine | ⏳ Sprint D |
| Live benchmark #1 | ⏳ Sprint D |
| Trust Magnitude v2 (fusion + repo fixes) | ⏳ Sprint C |
| Prestige Index v1 | ⏳ Sprint C |
| Index versioning framework | ⏳ Sprint C |
| Rank history chart on profile | ⏳ Sprint C |
| Skill Groups (Starless rename + ML clustering) | ⏳ Sprint E |
| Benchmarks 2.0 (cost/use, time-saved) | ⏳ Sprint E |
| Named badges | ⏳ Sprint E |
| Per-Skill-Group SEO pages | ⏳ Sprint E |
| React/Node monorepo migration | ⏳ Sprint F |
| Enterprise + Auth API | ⏳ Sprint G |

---

## Marco's North Star (v4 framing)

*"Biggest impact holders would be new trending skills. I would love to be the first (reliable) one talking about it or sending the trend."*

Sprint D delivers exactly that: a Monday-morning weekly report shipped automatically, RSS-syndicated, tweetable-permalink, backed by a real benchmark. First to talk about the trend, reliably.

Sprint C then indexes the trend so paper/press citations point at Gaia. Sprint E adds the benchmark diversity so the trend has *content* to report. Sprint F scales the megaphone. Sprint G monetizes.

The path is coherent. The order matters. **Megaphone before medals. Numbers before rewards. Products before ornament.**

---

*Authored: 2026-07-02, end of Sprint B. Next ratification: end of Sprint D (2026-08-01), or upon Marco's revision.*
