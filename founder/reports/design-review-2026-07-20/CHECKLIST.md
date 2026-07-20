# Yggdrasil II — Pre-merge Design Review · MASTER CHECKLIST

**Date:** 2026-07-20 · **Reviewer:** orchestrator (design-review pass) + 3 browser scouts
**Branch reviewed:** `dev/design-review-staging-8515fa` (byte-identical to `origin/dev/yggdrasil-ii-staging` tip `ac634b9d9`, the PR #1185 aggregate → main)
**Authority:** `founder/handovers/YGGDRASIL_II_TAXONOMY_AUTHORITY.md` (build-time cut, 2026-07-18) > `DESIGN.md` (2026-07-17) > design ledger.
**Method:** Playwright 1.61.1 vs local `http://localhost:8090/` (docs/), desktop 1280×900 + mobile 390×844. Every ship-blocker below was re-verified by the orchestrator looking at the screenshot directly.
**Out of scope (per founder):** homepage Ascension section, `docs/en`, ascension-overdrive-v2/v3 CSS, low-traffic pages, and pure token-vs-hex bookkeeping. Lens = **design intention** (layout, overlap, hierarchy, wrong-looking color in context), not lint.

**Per-scout source docs (evidence detail):** [scout-a-homepage.md](scout-a-homepage.md) · [scout-b-discovery.md](scout-b-discovery.md) · [scout-c-prestige.md](scout-c-prestige.md). Screenshots live in the session scratchpad `scoutA/ scoutB/ scoutC/` (not committed — a Haiku collector copies the checklist-referenced ones into a viewable folder).

> **How to read the "Where" column:** each row points at the real source. Where a surface is **generated**, the fix MUST go at the generator/template — editing the emitted HTML gets reverted on the next `gaia dev docs` / content-engine run. Generated surfaces are tagged ⚙.

---

## The one structural insight

Three separate *visible* defects — the 5★ trust bars rendering **cyan instead of gold** (P2), the stray **gold underline / lost accents** on named cards (P8), and part of the duplicate **"SHOW ULTIMATE PATH"** button collapse (SB3) — are **not** independent. They are downstream of the same root cause: the Yggdrasil II token regen dropped the `--tier-extra` and `--tier-ultimate` families, leaving ~90 live consumers resolving to nothing and falling back to the cyan default ramp. So the token migration (Overhaul **O1**) is not cosmetic bookkeeping — it is the single fix that restores several rank-hierarchy colors to their intended reading. Marco's ruling is captured in O1: **extra → fusion family; ultimate → rank-driven (5★-suite gold today)**.

---

## PART 1 — SHIP-BLOCKERS (resolve before the staging→main merge)

| ID | Surface | Where (source) | What's wrong (design intent broken) | Screenshot | Effort |
|----|---------|----------------|--------------------------------------|-----------|--------|
| **SB1** | Skill Explorer overlay, **mobile** | `docs/js/skill-explorer.js` (overlay build) + explorer CSS in `docs/css/styles.css` (`.se-body` 2-col layout) | On a phone the overlay shows **only Hero + Installation**. The "Upgrade Path & Adjacent Skills" flow panel is a desktop 2nd column that never stacks into the single-column flow, and the overlay itself doesn't scroll (wheel dismisses it). Result: 3 of the 5 required sections are unreachable on mobile. | `scoutB/explorer2-mobile-1.png` | **overhaul → O2** |
| **SB2** | `/reports/2026-28/` detail (all report detail pages) | ⚙ generator `scripts/contentEngine/templates/report.html.j2`; emitted `docs/reports/2026-28/index.html` L351 pins `site-nav.js?v=6.0.1` while 72 other pages run `?v=6.8.8` | The report's utility bar (← Previous week / Archive / Canonical JSON) renders **on top of the site nav** — the Gaia logo and Home/About/Skills/Docs links are fully hidden; only a gold caret and a clipped "Star on GitHub" pill poke out. The `.report-shell` declares 5rem/8rem clearance but the mounted nav (stale v6.0.1 script) overlays it. | `scoutC/reportDetail-top-crop.png` | **easy-win** (bump the template's `site-nav.js` to 6.8.8 / add report pages to `build_html_cache_busting()` in `scripts/build_docs.py`, re-verify clearance) |
| **SB3** | Skill Explorer overlay, **desktop** | `docs/js/skill-explorer.js` (path-toggle button labels, rank-word resolution) | Two adjacent path-toggle buttons both read **"SHOW ULTIMATE PATH"** — reads as a duplicate/broken control. One was meant to be a different path. Likely both buttons resolve their rank word to the same 5★ "Ultimate" via a branch-blind/dead-token fallback. | `scoutB/explorer2-desktop-1.png` | medium |
| **SB4** | `/named/` catalog grouping | `docs/js/named-skills.js:577` `groupHeader()` — deliberately uses `SUITE_LADDER` for the representative label | A 4★ section is headed **"◆ EXTRA · 4★"** but every card under it is `data-branch="unique"` (obra, pbakaus, safishamsi, openai, stanfordnlp…). Per DESIGN.md **E2**, a 4★ unique must read "Unique", never the suite word "Extra". The code comment shows this is an intentional "group by rank integer, label with suite ladder" choice — so this is a **design decision for Marco** (see Overhaul O5), not just a bug. | `scoutB/named-unique-cards.png` | medium → **needs ruling (O5)** |

---

## PART 2 — EASY-WIN POLISH (mechanical; safe to batch into one PR)

| ID | Surface | Where (source) | What's wrong | Screenshot | Root-cause note |
|----|---------|----------------|--------------|-----------|-----------------|
| **P1** | Site nav links | `docs/js/site-nav.js` mount + nav link color rule in `docs/css/styles.css` | Right-hand nav links render as a **rainbow** (About gold, GitHub Badges violet, Skills red, Docs blue). Gold=Apex-only and red=contributor-handles-only per §Hunter's Atlas — nav breaches both. Should be one neutral link color. | `scoutA/desktop-site-nav.png` | reserved-color rule not applied to nav |
| **P2** | Homepage trust-leaderboard preview + `/trust/leaderboard/` | `docs/trust/leaderboard/leaderboard.js` + `leaderboard.css` (bar fill by rank) | The 4 tallest bars are labeled **5★** (gold badge) but filled **cyan**, while shorter 3★ bars are gold — color no longer tracks rank, inverting the hierarchy against the star labels. | `scoutA/desktop-trust-preview.png` | **dead `--tier-ultimate` → cyan fallback; fixed by O1** |
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
| **P14** | 3D explorer status line | `docs/js/world-tree-layout.js` / graph HUD | Status reads **"243 skills · 406 links · 10 Unique"** — the stated design target was 6 Unique. Either the count changed (copy stale) or the 3D layout over-counts unique nodes. **Verify intended count** before treating as a bug. | `scoutB/threed-desktop-1.png` | count vs copy mismatch — confirm with Marco |

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

### O5 — Rank-word-by-branch in `/named/` grouping  *(resolves SB4)*
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

1. **Pre-merge PR (easy wins):** SB2 (report nav — bump site-nav version), P1, P3, P4, P5, P6, P7, P8, P10, P11, P12, P13. All mechanical, one `design/` branch, one Playwright smoke to confirm. CI reds are Marco's to handle per his note.
2. **Pre-merge decisions (no code until Marco rules):** SB4/O5 (grouping label), P2 (restore 5★ gold now or via O1), P14 (unique count intent).
3. **Overhaul PRs (post-merge unless Marco pulls forward):** O1 token migration, O2 explorer mobile reflow, O3 3D label LOD, O4 heroes mobile stage.
