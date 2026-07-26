# Why the Gaia API Exists — Product Story

**Authored:** 2026-06-26
**Origin:** Founder scratchpad session, orchestrator pass for EPIC #855 (Sprint B)
**Status:** Canonical — update as the product evolves

---

## The One-Line Version

The Gaia API converts the registry from a website you visit into **infrastructure you call**.

---

## The Problem It Solves

The AI agent ecosystem has a trust vacuum. Every agent framework claims it can "do X". Capabilities are scattered across repos, undocumented, and unverified. There is no canonical record. No evidence standard. No way to compare "mattpocock's TypeScript skill" vs "some random repo's TypeScript skill" without reading them both manually.

Gaia's registry fills that gap. But right now, accessing it requires either scraping the website or cloning the git repo. Neither is infrastructure. The API makes the registry **queryable by machines** — meaning an AI agent (Claude Code, Cursor, Continue, Codex) can look up trust data *while it's helping a developer*, without the developer leaving their IDE.

---

## What the API Returns

For any named skill, the API returns:

| Signal | What it means | Why devs care |
|---|---|---|
| **Trust Magnitude (TM)** | Composite score across all evidence types | "Is this real or vaporware?" |
| **Trust Grade (S/A/B/C)** | Bucketed from TM thresholds | "Can I rely on this in production?" |
| **Evidence items** | Peer reviews, GitHub stars, social signal, benchmarks | "Show your work" |
| **Origin flag** | This is the canonical first implementation | "Who invented it?" |
| **Level (★ rank)** | How far this skill has progressed through the Ascension Cycle | "Is this named and proven, or provisional?" |
| **Suite components** | What sub-skills a suite contains | "What am I actually getting?" |
| **`links.github`** | Where the SKILL.md lives | "Where do I install from?" |
| **Timeline** | Promotion history | "How long has this been proven?" |

---

## The Claude Code Story (Primary Use Case)

A developer is in Claude Code, building an agent pipeline. They ask:

> *"Find me the best web search skill to add to my agent."*

**Without the Gaia API**, Claude Code either guesses, searches GitHub broadly, or asks the developer to do the research.

**With the Gaia API**, Claude Code can:

1. Hit `/api/v1/search-index.json` → search by keyword, ranked by Trust Magnitude
2. Pull `/api/v1/skills/<top_result>.json` → check TM, grade, evidence, origin
3. See `"links.github": "https://github.com/garrytan/gstack/blob/main/skills/browse/SKILL.md"` → install it directly
4. Surface to the dev: *"Found 3 candidates. garrytan/browse is Grade S, TM=489, origin contributor, 47 evidence items. Want me to install it?"*

That's the killer workflow — **evidence-backed skill discovery inside an agentic IDE session**. No scraping, no repo-cloning, no manual research.

---

## The Two-Phase Interaction Model

The API is **read-only**. Interaction is a two-phase flow:

### Phase 1 — Via API (discover / evaluate)
- Search skills by keyword
- Browse by contributor, type, or trust grade
- Evaluate a specific skill before integrating it
- Check the leaderboard to find top-ranked implementations

### Phase 2 — Via CLI or direct (act / install / contribute)
- `gaia skills install <contributor>/<skill>` — follow `links.github`, wire the skill into your project
- `gaia push` — submit your own skills for review
- `gaia scan` — detect which Gaia skills your project already demonstrates

The API is the **discovery and trust layer**. The CLI is the **action layer**. They are complementary — the API tells you what exists and how trustworthy it is; the CLI does something about it.

---

## How It Fits Alongside the MCP Server

`@gaia-registry/mcp-server` already exposes `gaia_lookup`, `gaia_suggest`, `gaia_scan_context`, `gaia_my_tree` as MCP tools. Claude Code can call those today.

The API serves a different population:

| Who | Uses | Because |
|---|---|---|
| Developers running Claude Code / Cursor with MCP configured | MCP server | Richer tool surface, local context, my-tree support |
| SDK authors, CI pipelines, third-party tools | REST API | Zero setup — just a URL, no daemon |
| Browser-based tools | REST API | MCP requires local process; API is just `fetch()` |
| Any language / any runtime | REST API | `curl` works. No SDK required. |

The API is the **floor** — universally accessible, zero friction. MCP is the **ceiling** — richer, more context-aware, for configured environments.

---

## Why Static JSON (No Backend)

The API is a build-time projection: `gaia dev docs` regenerates `docs/api/v1/` from the registry, and GitHub Pages/Cloudflare serves it as static JSON. No server, no database, no hidden fees.

- **Cost**: $0 (already hosting the static site)
- **Reliability**: same uptime as the website (Cloudflare CDN)
- **Freshness**: as current as the last `gaia dev docs` run + merge to main
- **Rate limits**: Cloudflare edge handles ~100k requests/day per IP on free tier — should never be hit by legitimate use

The tradeoff is staleness: the API reflects the registry at the time of the last build. Real-time queries aren't possible. For trust data — which changes on evidence additions and promotions, not by the minute — this is acceptable.

---

## Success Criterion (Sprint B Kill Criterion)

```bash
curl https://gaiaskilltree.com/api/v1/skills/garrytan/gstack.json
# Returns valid JSON with trustMagnitude and overallTrustGrade
```

That single curl working is the proof that Gaia is infrastructure, not just a website.

---

## What This Is Not

- Not a write API (no submissions, no auth, no rate-limit enforcement)
- Not a real-time feed (static JSON, updated on deploy)
- Not a replacement for `gaia skills install` (API tells you where; CLI does the install)
- Not a GitHub package registry (no npm/pip semantics)

---

## References

- EPIC #855: Sprint B — Public API + Trending Engine + Hall of Heroes
- Implementation spec: `founder/handovers/B1_IMPL_SPEC.md`
- API platform design: `founder/handovers/API_PLATFORM_DESIGN_2026-06-20.md`
- Product audience and voice: `PRODUCT.md`
