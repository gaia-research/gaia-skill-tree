# Yggdrasil II — Pre-merge Design Review · MASTER CHECKLIST

**Date:** 2026-07-20 · **Reviewer:** orchestrator (design-review pass) + 3 browser scouts
**Branch reviewed:** `dev/design-review-staging-8515fa` (byte-identical to `origin/dev/yggdrasil-ii-staging` tip `ac634b9d9`, the PR #1185 aggregate → main)
**Authority:** `founder/handovers/YGGDRASIL_II_TAXONOMY_AUTHORITY.md` (build-time cut, 2026-07-18) > `DESIGN.md` (2026-07-17) > design ledger.
**Method:** Playwright 1.61.1 vs local `http://localhost:8090/` (docs/), desktop 1280×900 + mobile 390×844. Every ship-blocker below was re-verified by the orchestrator looking at the screenshot directly.
**Out of scope (per founder):** homepage Ascension section, `docs/en`, ascension-overdrive-v2/v3 CSS, low-traffic pages, and pure token-vs-hex bookkeeping. Lens = **design intention** (layout, overlap, hierarchy, wrong-looking color in context), not lint.

**Per-scout source docs (evidence detail):** [scout-a-homepage.md](scout-a-homepage.md) · [scout-b-discovery.md](scout-b-discovery.md) · [scout-c-prestige.md](scout-c-prestige.md) · [scout-d-outer.md](scout-d-outer.md) (about/meta/codex/starless/api/benchmarks/evidence/trending/trust). Screenshots live in the session scratchpad `scoutA/ scoutB/ scoutC/` (not committed — a Haiku collector copies the checklist-referenced ones into a viewable folder). The complete set of verified screenshots is available in the [screenshots/](screenshots/) folder.


> **How to read the "Where" column:** each row points at the real source. Where a surface is **generated**, the fix MUST go at the generator/template — editing the emitted HTML gets reverted on the next `gaia dev docs` / content-engine run. Generated surfaces are tagged ⚙.

---

## The one structural insight

Several *visible* defects share one root cause: the **6★ Apex reading cyan on `/trust/ledger/`** (P18 — a genuine rank-prestige inversion), the stray **gold underline / lost accents** on named cards (P9), and part of the duplicate **"SHOW ULTIMATE PATH"** button collapse (SB3). The Yggdrasil II token regen dropped the `--tier-extra` and `--tier-ultimate` families, leaving ~90 live consumers resolving to nothing and falling to the default/glow ramp. So the token migration (Overhaul **O1**) is not cosmetic bookkeeping — it restores several rank/type accents (including the highest rank on a live ranked table) to their intended reading. Marco's ruling is captured in O1: **extra → fusion family; ultimate → rank-driven (5★-suite gold today)**.

> **Note (Marco, 2026-07-20):** the trust-leaderboard bars (P2) are **not** part of this — they color by **evidence grade** (S = platinum), not by rank, so the "cyan 5★ bar" is likely the S/platinum reading, not a dead-token inversion. P2 is descoped as a fix; retained only as a cross-surface *consistency* flag (grade-coloring may look inconsistent against rank elsewhere — worth an eyeball, not a change here).

---

## PART 1 — SHIP-BLOCKERS (resolve before the staging→main merge)

| ID | Surface | Where (source) | What's wrong (design intent broken) | Screenshot | Effort |
|----|---------|----------------|--------------------------------------|-----------|--------|
| **SB1** | Skill Explorer overlay, **mobile** | `docs/js/skill-explorer.js` (overlay build) + explorer CSS in `docs/css/styles.css` (`.se-body` 2-col layout) | On a phone the overlay shows **only Hero + Installation**. The "Upgrade Path & Adjacent Skills" flow panel is a desktop 2nd column that never stacks into the single-column flow, and the overlay itself doesn't scroll (wheel dismisses it). Result: 3 of the 5 required sections are unreachable on mobile. | `scoutB/explorer2-mobile-1.png` | **overhaul → O2** |
| **SB2** | `/reports/2026-28/` detail (all report detail pages) | ⚙ generator `scripts/contentEngine/templates/report.html.j2`; emitted `docs/reports/2026-28/index.html` L351 pins `site-nav.js?v=6.0.1` while 72 other pages run `?v=6.8.8` | The report's utility bar (← Previous week / Archive / Canonical JSON) renders **on top of the site nav** — the Gaia logo and Home/About/Skills/Docs links are fully hidden; only a gold caret and a clipped "Star on GitHub" pill poke out. The `.report-shell` declares 5rem/8rem clearance but the mounted nav (stale v6.0.1 script) overlays it. | `scoutC/reportDetail-top-crop.png` | **easy-win** (bump the template's `site-nav.js` to 6.8.8 / add report pages to `build_html_cache_busting()` in `scripts/build_docs.py`, re-verify clearance) |
| **SB3** | Skill Explorer overlay, **desktop** | `docs/js/skill-explorer.js` (path-toggle button labels, rank-word resolution) | Two adjacent path-toggle buttons both read **"SHOW ULTIMATE PATH"** — reads as a duplicate/broken control. One was meant to be a different path. Likely both buttons resolve their rank word to the same 5★ "Ultimate" via a branch-blind/dead-token fallback. | `scoutB/explorer2-desktop-1.png` | medium |
| **SB4** | `/named/` catalog grouping | `docs/js/named-skills.js:577` `groupHeader()` — deliberately uses `SUITE_LADDER` for the representative label | A 4★ section is headed **"◆ EXTRA · 4★"** but every card under it is `data-branch="unique"` (obra, pbakaus, safishamsi, openai, stanfordnlp…). Per DESIGN.md **E2**, a 4★ unique must read "Unique", never the suite word "Extra". The code comment shows this is an intentional "group by rank integer, label with suite ladder" choice. **RULING (Marco, 2026-07-20): DEFERRED to after this merge** (grouping-label rework, tracked via O5). Not a merge blocker. | `scoutB/named-unique-cards.png` | **deferred post-merge (O5)** |

---

## PART 2 — EASY-WIN POLISH (mechanical; safe to batch into one PR)

| ID | Surface | Where (source) | What's wrong | Screenshot | Root-cause note |
|----|---------|----------------|--------------|-----------|-----------------|
| **P1** | Site nav links | `docs/js/site-nav.js` mount + nav link color rule in `docs/css/styles.css` | Right-hand nav links render as a **rainbow** (About gold, GitHub Badges violet, Skills red, Docs blue). Gold=Apex-only and red=contributor-handles-only per §Hunter's Atlas — nav breaches both. Should be one neutral link color. | `scoutA/desktop-site-nav.png` | reserved-color rule not applied to nav |
| ~~**P2**~~ | Homepage trust-leaderboard preview + `/trust/leaderboard/` | `docs/trust/leaderboard/leaderboard.js` + `leaderboard.css` | ~~5★ bars filled cyan not gold~~ **DESCOPED (Marco): bars color by evidence GRADE (S=platinum), not rank — the cyan is the S/platinum reading, working as intended.** Kept only as a cross-surface consistency note (grade-vs-rank color may read inconsistent elsewhere). | `scoutA/desktop-trust-preview.png` | **descoped — no change** |
| **P3** | `/named/` 1★ cards | `docs/js/named-skills.js` (contributor slot render) | 1★ (Awakened) cards show a literal **`@[anonymous]`** token in muted gray instead of a designed "no contributor" empty state. Reads as broken across the whole 1★ band. | `scoutB/named-desktop-bottom.png` | raw fallback token |
| **P4** | `/named/` catalog, desktop | `docs/named/index.html` / `named-skills.js` grid | **16px horizontal overflow** at 1280 (0 at 390) — stray horizontal scrollbar. | `scoutB` probe | grid exceeds container by ~scrollbar width |
| **P5** | Homepage — Path B agent-prompt preview | `docs/index.html` `section.agent-prompt textarea` | Read-only prompt **clips its own text** — desktop cuts leading/trailing chars at the right edge ("he Gaia CLI…" for "The"), mobile cuts mid-line at the bottom, no scroll cue. Sample prompt is unreadable. | `scoutA/desktop-paths.png`, `scoutA/mobile-paths.png` | fixed-size box, `overflow:hidden`, no wrap |
| **P6** | Homepage — review-showcase | `docs/index.html` `#review-showcase .terminal` | Two empty "Awaiting simulation trigger…" terminals are very tall/barren and the centered text **wraps mid-word** ("Awai/ting", "trigg/er"). Reads as a layout accident, not an intentional empty state. | `scoutA/desktop-review-showcase.png` | min-height sized for populated output; centered mono on narrow column |
| **P7** | `/badges/` | `docs/badges/index.html` (graph fetch path) | Page fetches `graph/gaia.json` **relative to `/badges/`** → `/badges/graph/…` → **404** (should be `../graph/…`). Badge still renders from fallback (not blank), but graph hydration silently fails. | `scoutB/b404` log | relative-path bug |
| **P8** | `/badges/` hero | `docs/badges/index.html` "HONESTY ON" status pill | Pill **overlaps the H1 "Github Badges"** on mobile and floats at an awkward mid-title position on desktop — reads as a stray tag, not a deliberate chip. | `scoutB/badges-390.png` | absolute-positioned pill, no reflow |
| **P9** | `/named/` cards | `docs/js/named-skills.js` / `docs/css/plaque.css` | Stray thin **gold/amber underline** appears under the tag-pill row on *some* cards but not others — inconsistent decorative accent. Also `plaque__install-cmd` text overflows the pill 160–250px before the ellipsis on long slugs. | `scoutB/named-desktop-mid.png` | dead `--tier-extra` token (O1) + tight ellipsis box |
| **P10** | Skill Explorer, desktop | `docs/js/skill-explorer.js` | **"Fuse skills on Gaia Research"** CTA appears **twice** in one view — cyan box under the hero card AND the right-column flow header. Redundant. | `scoutB/explorer2-desktop-1.png` | bridge CTA rendered in both slots |
| **P11** | Skill Explorer, mobile | explorer CSS | Scroll-to-top FAB **overlaps the "MAG 482.3" evidence bar** at the hero card's bottom-right. | `scoutB/explorer2-mobile-1.png` | FAB ignores evidence bar z-space |
| **P12** | Hall of Heroes band, mobile | `docs/index.html` `#scrollToTop` vs `.hoh-plate .share` | Floating scroll-to-top chevron **overlaps a plaque's share button** at the addy-osmani card. Two round controls stacked. | `scoutA/mobile-hall-of-heroes.png` | no collision margin |
| **P13** | Profile `/u/<handle>/`, mobile | ⚙ `scripts/generateProfilePages.py` (filter control) | **Two FILTER controls** on screen at once — an inline button beside "Progression Timeline" AND a floating pill bottom-right overlapping the panel. | `scoutC/profile-mattpocock-mobile.png` | sticky trigger not gated on inline scroll-out |
| **P15** | `/api/` — whole page (nav + footer) | `docs/api/index.html` — **missing mount elements**: add `<nav id="site-nav"></nav>` (before content) and `<div id="site-footer-mount"></div>` (before scripts) | Page ships with **no site nav and no footer** — no wordmark, no destination links, no way back to the site. Scripts + injection *comments* are present (L305/L535) but the actual mount elements `site-nav.js` targets (`getElementById('site-nav')`) are absent → nothing renders. **Guard D misses this** (it checks GAIA_MOUNTS + script load, not element presence). | `scoutA/outer-api-desktop-full.png` | **easy-win** (2-element add; copy from `docs/named/index.html` L52 + L139) |
| **P16** | `/api/` — Endpoint Reference table, mobile | `docs/api/index.html` `.api-endpoints table` | Table doesn't reflow at 390: PATH clipped mid-string, DESCRIPTION + TAG columns pushed off-screen — reference unusable on a phone. | `scoutA/outer-api-mobile-full.png` | medium |
| **P17** | `/api/` — Example links, desktop | `docs/api/index.html` `.api-endpoints .example a` | Long example URLs clip at the cell's right edge, cutting link text mid-URL. | `scoutA/outer-api-desktop-full.png` | easy-win |
| **P18** | `/trust/ledger/` rank columns | `docs/trust/ledger/` rank cells `.tl-rank[data-level="6"]` | **6★ Apex renders cyan** while 5★ above it is gold — the single highest rank looks *below* 5★, inverting prestige on a live ranked table. Also 3★/4★ near-indistinguishable violets. **This is a genuine rank-color inversion (unlike P2's grade-colored bars)** — the 6★ label lost its gold via the dead `--tier-ultimate` and fell to the cyan `--glow-VI` halo. | `scoutA/scr-ledger2-d-y560.png` | **fixed by O1** (rank→gold restore) |
| **P19** | `/about.html` pull-quotes | `docs/about.html` `.about-quote blockquote::after` | Stray gold closing-quote glyph dangles on its own line **below** each byline — reads as an orphaned floating character, not a paired quote mark. | `scoutA/scr-about-d-y2300.png` | easy-win |
| **P20** | `/trending/` "Recently Awarded" cards | `docs/trending/` `.trending-awarded .award-card` | Every award card (incl. ordinary 2★→3★ B-grade) carries a full **Apex-gold border** — a wall of gold frames dilutes the "gold = Apex-only" reservation. Low confidence — may be an intentional ceremonial award frame; Marco's call. | `scoutA/scr-trending-d-y6600.png` | easy-win (if changed) |
| **P14** | 3D explorer status line | data: `docs/graph/gaia.json` (not a JS bug) | Status reads **"10 Unique"** (prior sessions said 6). **VERIFIED (orchestrator, 2026-07-20):** the served `gaia.json` genuinely carries `branch:'unique'` on **10** starless nodes — the HUD is accurate to the data, NOT a render defect. Distribution now: 10 unique / 15 suite / 54 standard / 164 no-branch (of 243). The 6→10 delta traces to the 4★ origin-gate **restoration** commits on staging (`8ea5b64c4`, `796158a13` — graphify/using-git-worktrees/writing-plans/dspy 3★→4★, each flipping to unique-branch). **This is a CURATION question, not a design fix:** confirm all ten are intended 4★+ unique. The ten: `few-shot-learning, knowledge-graph-build, performance-tuning, prompt-optimization, subagent-driven-development, using-git-worktrees, ux-audit, web-scrape, web-search, writing-plans`. Marco to eyeball + verify registry. | `scoutB/threed-desktop-1.png` | **data/curation — verify registry, no code change** |

---

## PART 3 — OVERHAUL PROPOSALS (pattern-level; need Marco's guidance before build)

These are too large or too design-load-bearing for a mechanical fix. Each is a *pattern* decision, not a one-line edit.

### O1 — `--tier-extra` / `--tier-ultimate` token migration  *(Marco's ruling logged)*
- **Problem:** Ygg II regen left `tokens.css` with only `--tier-basic`, `--tier-fusion`, `--tier-unique(-5/-6)`. ~60 `--tier-extra*` + ~29 `--tier-ultimate*` consumers now resolve to nothing (only 9 carry fallbacks). Visible cost: P2 (5★ bars cyan), P9 (stray/lost underlines), part of SB3. Also case-bug siblings: `styles.css` consumes lowercase `--grade-s/a/b/c` (defined only uppercase) → evidence-grade A renders `#fbbf24` amber instead of the real `#d4af37`.
- **Marco's migration direction (2026-07-20):**
  - `--tier-extra*` consumers → **fusion family** (fusion purple).
  - `--tier-ultimate*` consumers → **rank-driven color**, read from rank. Today that collapses to **5★-suite gold** because there are no 5★-unique / 6★-suite / 6★-unique instances yet. The rank-aware branch (5★ unique, 6★ suite/unique) is future logic — add the read-rank switch but the current data makes it a straight "5★ suite → gold" map.
- **Scope:** primarily `docs/css/styles.css` (~90 call sites) + `docs/css/plaque.css` remainder + `scripts/generateCssTokens.py` (emit any retained aliases). Where it lands: a dedicated migration PR, **not** pre-merge-blocking unless Marco wants P2's gold restored before the merge (recommend: yes, restore 5★ gold — it's the most visible one).
- **Decision for Marco:** confirm whether P2 (trust bars gold) rides this overhaul post-merge, or gets a targeted pre-merge patch.

### O2 — Skill Explorer mobile responsive reflow  *(fixes SB1)*
- The overlay's two-column desktop layout must collapse to a single scrollable column on mobile so all five sections (Hero, Installation, Documentation, Upgrade Path, Evolution Changelog) are reachable, and the overlay body must scroll instead of dismissing on wheel. This is a genuine responsive rebuild of `#skillExplorer` layout, not a padding tweak.
- **Pattern decision:** does the flow-graph (Upgrade Path) render as a full interactive graph on mobile, or degrade to a simpler stacked list? Recommend degrade-to-list on <768px.

### O3 — 3D explorer label declutter / level-of-detail
- With Labels toggled on, the central canopy is an **unreadable mush** of overprinted labels; only peripheral ones are legible. Needs collision-avoidance or zoom-gated LOD (show labels only for focused/nearby/high-rank nodes). Pattern decision: label-on-hover vs label-by-rank-threshold vs label-by-zoom.

### O4 — `/heroes/` mobile full-viewport stage
- Mobile `.hero-stage` is 561px against an 844px viewport (66%), so the "one ceremonial stage per contributor" intent collapses into a cramped stacked list and the next plate bleeds in. Needs `min-height: 100svh` (not `vh`) with a top offset for the ~58px fixed nav. Medium, but touches the gallery's core composition so it's a pattern call, not a nit.

### O5 — Rank-word-by-branch in `/named/` grouping  *(resolves SB4)*  — **DEFERRED post-merge (Marco, 2026-07-20)**
- Current `named-skills.js:577` intentionally groups by rank integer and labels the group with the **suite** ladder word, relying on per-card `data-branch` for suite-vs-unique differentiation. DESIGN.md E2 says a 4★ unique must never read "Extra". **Two options for Marco:**
  1. **Split the 4★/5★/6★ buckets by branch** — separate "Extra · 4★" (suite) and "Unique · 4★" (unique) group headers. Truest to E2, more headers.
  2. **Neutralize the group label** — head mixed rank buckets with a branch-agnostic label (e.g. "4★" or "Tier 4") and let the per-card medallion/plaque carry the branch word. Fewer headers, still E2-safe (no wrong branch word shown).
- Recommend option 2 if the grid is meant to stay dense; option 1 if branch identity should be a primary sort axis.

---

## PART 4 — VERIFIED CLEAN (looks right — do not touch)

- **Homepage hero** (desktop + mobile): monochrome tonal-gold World Tree, `Skill Tree` in Apex Gold EB Garamond, no gradient text, copy legible over the tree, correct mobile full-bleed backdrop. Nav chrome is the correct plain hairline, no glassmorphism.
- **Hall of Heroes band:** ceremonial two-column ledger, avatars in **gold** wreaths, handles in Honor Red, **zero red origin marks** (E4 clean).
- **/named/ card system:** coherent 1★–5★, suite = gold-ring plaque, unique = darker violet-ring plaque (E3 distinction reads), 119 wreaths / 153 medallions / no broken avatar holes.
- **/badges/:** the `?u=mattpocock&s=grill-me` badge **renders** (not blank) — three coherent badges, correct star ratings; rank table + variants read as one system.
- **3D explorer:** the **copper/ember unique cluster is correctly tucked under the canopy** — not violet, not a far-right satellite (matches the recent ratified placement). Node color ramp reads teal→violet→gold outward-to-canopy. HUD controls don't overlap.
- **/heroes/ desktop:** stages compose cleanly, ledger rail (192px) clears the crest, 5★ Apex Gold / 4★ fuchsia accents correct. Share modal fits at 390px, ORIGIN gold (E4), "Ultimate · 5★" correct (E2).
- **Profiles desktop:** medallion + gold wreath sized right, Honor Red on handle only, Back-row clears the fixed nav.
- **/reports/ index** and **/named/report.html** empty state: clean, intentional, well-cleared.
- **No horizontal overflow at 390px** on any surface except P4's 16px desktop case; **no console errors** beyond graceful-degrade data 404s (per-skill `/api/v1/skills/*.json` are Class-S artifacts absent from a plain local serve — verify on a full `gaia dev docs` build, not a defect).

---

## Recommended sequencing

1. **Pre-merge PR (easy wins):** SB2 (report nav — bump site-nav version), P1, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, **P15 (/api/ nav+footer mounts), P17, P19**. All mechanical, one `design/` branch, one Playwright smoke to confirm. CI reds are Marco's to handle per his note. (P16 /api mobile table + P20 trending gold frames are also easy-ish but carry a judgment call — group with the batch if Marco greenlights.)
2. **Still open (SB3):** duplicate "SHOW ULTIMATE PATH" button — medium, likely rides the O1/rank-word work; not deferred, but not a mechanical one-liner.
3. **Deferred post-merge (Marco ruled 2026-07-20):** SB4/O5 (grouping label rework); O1 token migration; O2 explorer mobile reflow; O3 3D label LOD; O4 heroes mobile stage.
4. **Descoped / no-change (Marco ruled 2026-07-20):** P2 (trust bars are grade-colored, not rank — working as intended; consistency note only). P14 (10 Unique is accurate to data — a **curation** verify on the registry, not a design edit).

---

## Unmerged Design Polish Commits (For Review)

During our cherry-picking, we discovered a pattern of "load-bearing" design commits that seem to have been lost (likely during a fast-forward or squashed PR merge) across various `origin/design/*` and `origin/dev/*` branches. 

**Recovered Examples:**
- `f55282253`: `design(ygg2): rebalance plaque layout — avatar↔handle, medallion↔slug` (Cherry-picked)
- `e31f58077`: `fix(design): D6/D8 — detail plaque avatar→medallion order + kill orb tint behind loaded stamp` (Cherry-picked)
- `6ed132955`: `fix(design): D6/D8 plaque avatar→medallion order + D3/D18 graph gold-star mark` (Cherry-picked)

**Additional Marooned Commits for Review:**
These commits carry similar `design(ygg2)` or `fix(design)` signatures and address specific visual/layout intent. They are currently stranded on `origin/design/*` branches and are NOT reachable from the current `dev/design-review-staging-8515fa` branch:

- **`e15c7bfae`** `design(ygg2): contributor-card header groups handle + rank (surface 3)`
  - *Context*: Further refines the plaque/card header groupings to match the intended Yggdrasil II layout.
- **`93a187916`** `fix(ygg2): sampler ascends 1★→6★ (extra-before-unique); mixed grid header names both branches (Unique/Extra)`
  - *Context*: Adjusts the ordering of the skill sampler and handles branch headers. 
- **`18c0dc1a1`** `fix(ygg2): badge claim/README pins to 1★, decoupled from sampler cycle (no rank leak)`
  - *Context*: Fixes a UI bug where the badge claim snippet might leak higher rank states incorrectly.
- **`8aa300702`** `fix(ygg2): DAG node dot color reads emitted branch, not dead type enum`
  - *Context*: A graph visualization fix bridging the gap between old `type` and new `branch` data.
- **`ecd4f7186`** `fix(ygg2): named grid group header/segregation reads emitted branch, not hard-wired suite ladder`
  - *Context*: Aligns the `/named/` directory grouping logic with the `branch` taxonomy.
- **`3555c40da`** `fix(design): D74 — homepage '0 ultimates' dead-type read (D9-class)`
  - *Context*: Fixes a broken stat on the homepage hero reading from a deprecated data field.
- **`55a62ac13`** `fix(ygg2): D15 — reports grey out '← Previous week' when no prior report exists`
  - *Context*: UX polish for the `/reports/` navigation controls.
- **`332736ab0`** `fix(ygg2): D12 — badges page drops banned rank words Hardened/Transcendent`
  - *Context*: Aligns badge generation language with the finalized rank word vocabulary.
- **`04d6114d6`** `fix(ygg2): D14 — tree.md renders suites biggest-fusion-first via topological branch resolver`
  - *Context*: Fixes the topological rendering of suites in the markdown tree.
- **`c0def6d62`** `fix(design): D9 — derive branch at read-time in 3D graph (suites no longer render as unique)`
  - *Context*: A critical visualization fix for the 3D graph ensuring suites are styled properly.
- **`0213d073b`** `design(heroes): fix wreath geometry — size 100% fills crest square, not phantom 200px box`
  - *Context*: Fixes scaling issues with the gold hero wreaths.
- **`1006e5d75`** `fix(badges): kill Hardened/Transcendent vocab + regenerate all badge SVGs`
  - *Context*: Final visual regeneration of the badges to remove deprecated rank terminology.

*Recommendation*: These should be reviewed as a batch, as they represent the finalized polish layer for Yggdrasil II that was accidentally orphaned during branch synchronization.
