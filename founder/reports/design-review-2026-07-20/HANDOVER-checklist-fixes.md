# Yggdrasil II — Design Fixes HANDOVER (full CHECKLIST completion)

> **Active Branch:** `design/ygg2-checklist-fixes-t6` (targeting T6 onwards)
> **For:** the coding agent (Sonnet) running `/design-iteration`.
> **Goal:** complete the **entire** `founder/reports/design-review-2026-07-20/CHECKLIST.md` in **one PR** — every ship-blocker, every easy-win, and the overhauls folded in — on a branch off `dev/yggdrasil-ii-staging`.
> **Method:** `/design-iteration` — one fix at a time, present diff, wait for Marco's **APPROVE / REJECT / NO CHANGES**, then commit that single fix and move on. **Never batch. Never self-merge.**
> **Author:** orchestrator, 2026-07-20 session 3. Source-of-truth: `CHECKLIST.md` (scouted, verified) + `INSIGHTS.md` (cherry-pick record — Bucket-1 already DONE, see below).

---

## READ THIS FIRST — the three things that will bite you

1. **Cherry-picking is DONE.** Everything in `INSIGHTS.md` Bucket-1 (the 8 marooned design commits) already landed on staging via **PR #1241** (Fix 1/1b/2 prior session; Fix 3/4/5 this session). **Do NOT re-recover any Bucket-1 item. Do NOT touch any Bucket-2/Bucket-3 commit** — several would *silently regress* the shipped §8 sampler order or the named-grid architecture with no conflict marker. Your job is the **CHECKLIST**, not INSIGHTS. INSIGHTS is context only.
2. **The CHECKLIST line anchors have drifted.** Files were rewritten by #1235/#1241. Line numbers like `named-skills.js:577` or `plaque.js:663` are *approximate*. **Always re-grep / re-read to locate the real anchor before editing** — this is step 1 of every `/design-iteration` loop. If a fix looks already-present, call **NO CHANGES** and move on.
3. **This is a `design/` branch.** CI branch-scope allows `docs/` (HTML/CSS/JS) + `*.md` only. Some fixes touch **generated surfaces** (⚙) whose real source is a `scripts/*.py` / `*.j2` generator — editing emitted HTML gets reverted on the next `gaia dev docs`. Where a fix is ⚙ and its generator lives outside `docs/`, it crosses branch-scope: **surface the conflict and ask Marco** (split to a `design/`-adjacent branch, or `[skip-scope-check]` in the commit body per his call — the pattern already used for Fix 4 last session).

---

## Branch + PR setup

- **Base branch:** `dev/yggdrasil-ii-staging` (tip `1c0a0a291` at handover time; the head of open **draft PR #1185** → main).
- **Work branch:** create `design/ygg2-checklist-fixes` off `origin/dev/yggdrasil-ii-staging` (branch from origin, not a stale local ref).
- **One PR** from `design/ygg2-checklist-fixes` → `dev/yggdrasil-ii-staging`, titled **`fix(design): Yggdrasil II CHECKLIST — ship-blockers + easy-wins + overhauls`**. Draft PR already teed up below; open it after the branch is pushed with the first commit (or immediately as a draft).
- **One commit per fix.** Message form: `fix(design): <ID> — <one-line summary>`. Push after each approved commit (durable-progress rule; a pushed commit survives cutoff, a local one dies).
- **Never push to main. Never merge — Marco merges.**

---

## What's IN scope vs OUT (read before you start — do not re-litigate)

| Bucket | Items | Action |
|---|---|---|
| **Ship-blockers** | SB1, SB2, SB3 | **FIX** (SB1 = overhaul O2, SB3 rides O1's rank-word work) |
| **Easy-wins** | P1, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, P15, P16, P17, P19, P20 | **FIX** |
| **Overhauls** | O1, O2, O3, O4 | **FIX** (folded into their page clusters below) |
| **Deferred (Marco ruled)** | SB4 / O5 (named grouping-label rework) | **DO NOT TOUCH.** Marco deferred post-merge. Note in PR body as deliberately skipped. |
| **Descoped (Marco ruled)** | P2 (trust bars = grade-colored, working as intended) | **DO NOT TOUCH.** Consistency note only. |
| **Curation, not design** | P14 (10 Unique is accurate to registry data) | **DO NOT TOUCH.** Marco verifies the registry separately; no code change. |
| **Verified clean** | Part 4 list | **DO NOT TOUCH.** Homepage hero, HoH band, /named card system base, badge render, 3D cluster placement, /heroes desktop, profiles desktop, reports index. |

> Marco's original CHECKLIST §"Recommended sequencing" put O1/O2/O3/O4 as *deferred post-merge*. **This handover overrides that per Marco's instruction in this session: finish the WHOLE checklist in one PR, overhauls included.** SB4/O5, P2, P14 remain out (those are ruling-level descopes, not sequencing).

---

## The plan — organized per page (fix cluster order)

Work the clusters top-to-bottom; within a cluster, work items in listed order. Each item is one `/design-iteration` loop (verify → port → read-back → present → decide → commit). The **⚙** tag = generated surface (fix the generator, not the emitted HTML; may cross branch-scope → ask Marco).

### Cluster A — Homepage (`docs/index.html`, `docs/js/site-nav.js`, `docs/css/styles.css`)
| ID | Fix | Anchor to re-locate | Intent |
|---|---|---|---|
| **P1** | Nav links render rainbow (About gold / Badges violet / Skills red / Docs blue). | `site-nav.js` mount + nav link color rule in `styles.css`. | One neutral link color for all nav links. Gold = Apex-only, red = contributor-handles-only (Hunter's Atlas reserved-color rule); nav must not breach either. |
| **P5** | Path-B agent-prompt preview clips its own text (desktop cuts edge chars, mobile cuts mid-line, no scroll cue). | `section.agent-prompt textarea`. | Make the sample prompt fully readable: allow wrap / scroll, remove `overflow:hidden` fixed-box clipping. |
| **P6** | Review-showcase: two "Awaiting simulation trigger…" terminals too tall/barren; centered text wraps mid-word ("Awai/ting"). | `#review-showcase .terminal`. | Intentional empty state — right-size min-height, stop mid-word wrap (break-word/normal wrap, left-align or wider column). |
| **P12** | (mobile) Floating scroll-to-top chevron overlaps a plaque's share button at the addy-osmani HoH card. | `#scrollToTop` vs `.hoh-plate .share`. | Collision margin / z-space so the FAB never sits on the share control. |

### Cluster B — Skill Explorer (`docs/js/skill-explorer.js`, explorer CSS in `docs/css/styles.css`)
> ⚠ `skill-explorer.js` is **two IIFEs** (L1–~1862, ~L1864–end) that do NOT share scope — anything shared must be re-declared per IIFE or hung off `window`. Render fns in `openExplorer` stay wrapped in `_safeRender`. **After ANY edit, re-verify the five sections render** (Hero, Installation, Documentation, Upgrade Path, Evolution Changelog) per the frontend-known-issues invariant.
| ID | Fix | Intent |
|---|---|---|
| **SB3** | Two adjacent path-toggle buttons both read "SHOW ULTIMATE PATH" — reads as duplicate/broken. | Resolve each button's rank word from its actual branch/rank (not a branch-blind/dead-token fallback that collapses both to 5★ "Ultimate"). Rides the O1 rank-word logic — do O1 first if the rank-word switch is shared. |
| **P10** | "Fuse skills on Gaia Research" CTA appears twice in one view (cyan box under hero card + right-column flow header). | Render the bridge CTA in one slot only. |
| **P11** | (mobile) Scroll-to-top FAB overlaps the "MAG 482.3" evidence bar at the hero card's bottom-right. | FAB respects the evidence bar's z-space / offset. |
| **SB1 = O2** | (mobile) Overlay shows only Hero + Installation; the 2-col "Upgrade Path & Adjacent Skills" panel never stacks, and the body doesn't scroll (wheel dismisses). 3 of 5 sections unreachable. | **Overhaul O2:** genuine responsive rebuild — collapse the 2-col layout to a single scrollable column <768px; make the overlay body scroll instead of dismiss on wheel. **Pattern decision (ask Marco / recommend):** the Upgrade-Path flow-graph degrades to a stacked list on <768px (recommended) vs full interactive graph. |

### Cluster C — /named/ catalog (`docs/js/named-skills.js`, `docs/named/index.html`, `docs/css/plaque.css`)
> Do NOT touch SB4/O5 (grouping-label rework — deferred). These are the card-render / overflow polish items only.
| ID | Fix | Intent |
|---|---|---|
| **P3** | 1★ (Awakened) cards show literal `@[anonymous]` muted token instead of a designed "no contributor" empty state. Reads broken across the whole 1★ band. | Replace raw fallback token with a designed empty state (e.g. subtle "unclaimed" chip / omit the handle row). |
| **P4** | (desktop) 16px horizontal overflow at 1280 (0 at 390) — stray horizontal scrollbar. | Grid exceeds container by ~scrollbar width; contain it (box-sizing / max-width / gap fix). |
| **P9** | Stray thin gold/amber underline under the tag-pill row on *some* cards (dead `--tier-extra` token → O1). Plus `plaque__install-cmd` text overflows the pill 160–250px before ellipsis on long slugs. | Underline resolves via O1 token migration (do O1 first). Tighten the install-cmd ellipsis box so it clips at the pill edge. |

### Cluster D — Token migration OVERHAUL O1 (`docs/css/styles.css`, `docs/css/plaque.css`, ⚙ `scripts/generateCssTokens.py`)
> **Do O1 EARLY** — SB3, P9, P18 all resolve through it. This is the "one structural insight" from the CHECKLIST: Ygg II regen dropped `--tier-extra*` (~60 consumers) and `--tier-ultimate*` (~29 consumers), leaving ~90 live consumers resolving to nothing.
- **Marco's ratified migration direction (2026-07-20):**
  - `--tier-extra*` consumers → **fusion family** (fusion purple).
  - `--tier-ultimate*` consumers → **rank-driven color**, read from rank. Add the read-rank switch, but today the data collapses it to a straight **5★-suite → gold** map (no 5★-unique / 6★ instances exist yet; that branch is future logic).
- **Also fix the case-bug sibling:** `styles.css` consumes lowercase `--grade-s/a/b/c` but they're defined only uppercase → evidence-grade A renders `#fbbf24` amber instead of `#d4af37`. Align the case.
- **⚙ scope note:** `scripts/generateCssTokens.py` emits any retained aliases and lives outside `docs/` → **crosses branch-scope. Ask Marco** (skip-scope-check vs split). If tokens can be fully migrated at the *consumer* call-sites in `docs/css/*` without regenerating, prefer that to stay in-scope.
- **Guardrails:** NO raw hex (CI guard rejects). Use design tokens / `var(--token, fallback)` only. No gradient text.

### Cluster E — /trust/ledger/ (`docs/trust/ledger/`)
| ID | Fix | Intent |
|---|---|---|
| **P18** | **6★ Apex renders cyan** while 5★ above it is gold — inverts prestige on a live ranked table (single highest rank looks below 5★). 3★/4★ near-indistinguishable violets. | **Resolved by O1** — the 6★ label lost its gold via the dead `--tier-ultimate` and fell to the cyan `--glow-VI` halo; the rank→gold restore fixes it. Verify after O1 lands; if the ledger reads its own tokens, apply the rank-driven color there too. **This is a genuine inversion — unlike P2, which is grade-colored and OUT of scope.** |

### Cluster F — /badges/ (`docs/badges/index.html`)
> ⚠ `badges/index.html` is a **core** page. Any new field used in `renderRows()` MUST be added to its `currentState` destructuring or blank-outs all badge output. After edits, verify `https://gaiaskilltree.com/badges/?u=mattpocock&s=grill-me` renders. Auto-sync never touches `docs/badges/` — fine here since this is human-reviewed.
| ID | Fix | Intent |
|---|---|---|
| **P7** | Page fetches `graph/gaia.json` relative to `/badges/` → `/badges/graph/…` → 404. Badge still renders from fallback; graph hydration silently fails. | Fix the relative path to `../graph/…`. |
| **P8** | "HONESTY ON" status pill overlaps the H1 "Github Badges" on mobile; floats awkwardly mid-title on desktop. | Reflow the pill as a deliberate chip (not absolute-positioned over the title). |

### Cluster G — /api/ (`docs/api/index.html`)
| ID | Fix | Intent |
|---|---|---|
| **P15** | **No site nav, no footer** — mount *elements* absent. Scripts + injection comments present (~L305) but `site-nav.js` targets `getElementById('site-nav')` which doesn't exist → nothing renders. Guard D misses this (checks GAIA_MOUNTS + script load, not element presence). | **Easy-win:** add `<nav id="site-nav"></nav>` before content and `<div id="site-footer-mount"></div>` before scripts. Copy the exact pattern from `docs/named/index.html` (~L52 + L139). Verify nav + footer render. |
| **P17** | (desktop) Long example URLs clip at the cell's right edge, cutting link text mid-URL. | `.api-endpoints .example a` — allow wrap/break or scroll so full URLs read. |
| **P16** | (mobile) Endpoint Reference table doesn't reflow at 390: PATH clipped, DESCRIPTION + TAG columns off-screen. | `.api-endpoints table` — responsive reflow (stacked/card layout or horizontal scroll with sticky first col). Medium; judgment call — present options. |

### Cluster H — /about.html
| ID | Fix | Intent |
|---|---|---|
| **P19** | Stray gold closing-quote glyph dangles on its own line **below** each byline — orphaned floating character. | `.about-quote blockquote::after` — pair/position the closing quote correctly (inline with the quote, not a floated orphan). |

### Cluster I — /trending/
| ID | Fix | Intent |
|---|---|---|
| **P20** | Every "Recently Awarded" card (incl. ordinary 2★→3★ B-grade) carries a full **Apex-gold border** — a wall of gold dilutes the "gold = Apex-only" reservation. | **Low confidence — may be an intentional ceremonial award frame; ASK Marco first.** If changed: reserve gold for Apex; use a neutral/ceremonial-but-non-gold frame for ordinary awards. |

### Cluster J — /u/<handle>/ profiles (⚙ `scripts/generateProfilePages.py`)
| ID | Fix | Intent |
|---|---|---|
| **P13** | (mobile) **Two FILTER controls** at once — inline button beside "Progression Timeline" AND a floating pill bottom-right overlapping the panel. | Gate the sticky/floating trigger on the inline one scrolling out of view (show only one at a time). **⚙ generated by `generateProfilePages.py` — crosses branch-scope. Ask Marco.** |

### Cluster K — /reports/ detail (⚙ `scripts/contentEngine/templates/report.html.j2`, `scripts/build_docs.py`)
| ID | Fix | Intent |
|---|---|---|
| **SB2** | Report utility bar renders **on top of the site nav** — Gaia logo + Home/About/Skills/Docs fully hidden; only a gold caret + clipped "Star on GitHub" pill poke out. Root: the template pins a **stale `site-nav.js` version** (`{{ report.generatorVersion }}` resolves to an old `v6.0.1`) while 72 other pages run `v6.8.8`; the stale nav script overlays the `.report-shell`'s declared 5rem/8rem clearance. | **Easy-win (but ⚙ + cross-scope):** bump the template's `site-nav.js` to the current version AND add report detail pages to `build_html_cache_busting()` in `scripts/build_docs.py` (~L316) so cache-busting auto-versions them. Re-verify the nav renders above the utility bar and clearance holds. **Both files are outside `docs/` → crosses branch-scope. Ask Marco** (this is exactly the Fix-4 situation from last session — `[skip-scope-check]` in the commit body was the sanctioned resolution). |

### Cluster L — 3D explorer OVERHAUL O3 (`docs/js/skill-graph.js` + 3D layer)
| ID | Fix | Intent |
|---|---|---|
| **O3** | With Labels toggled on, the central canopy is an unreadable mush of overprinted labels; only peripheral ones legible. | Collision-avoidance or zoom-gated level-of-detail. **Pattern decision — ASK Marco / recommend:** label-on-hover vs label-by-rank-threshold vs label-by-zoom. Recommend label-by-rank-threshold + focus/hover reveal so high-rank nodes always read. |
> ⚠ `skill-graph.js`: null-check overlay button selectors before wiring events — a null `querySelector(...).addEventListener` at bootstrap silently aborts the IIFE → FALLBACK_SKILLS. Verify the graph still hydrates from real data after edits.

### Cluster M — /heroes/ OVERHAUL O4 (`docs/heroes/` CSS / `docs/js/heroes.js`)
| ID | Fix | Intent |
|---|---|---|
| **O4** | (mobile) `.hero-stage` is 561px against an 844px viewport (66%) — the "one ceremonial stage per contributor" intent collapses to a cramped list; the next plate bleeds in. | `min-height: 100svh` (not `vh`) with a top offset for the ~58px fixed nav, so each stage fills the mobile viewport. Medium; touches the gallery's core composition → present the diff carefully. |
> ⚠ Fixed-nav clearance invariant: any top-level container under `<body>` must clear ~58px (base 5rem/80px; desktop 6rem thin or 8rem full-shell). Use `100svh` minus the nav offset — do not invent other values.

---

## Suggested execution order (dependency-aware)

1. **O1 token migration first** (Cluster D) — unblocks SB3, P9, P18. Ask Marco on the ⚙ `generateCssTokens.py` scope up front.
2. **Cluster-by-cluster easy-wins:** A (homepage) → C (named) → F (badges) → G (api) → H (about) → E (ledger, verify post-O1).
3. **⚙ / cross-scope items grouped** so Marco makes one scope call: SB2 (reports), P13 (profiles), and the O1 generator. Ask before the first one.
4. **Overhauls:** O2/SB1 (explorer mobile) → O3 (3D labels) → O4 (heroes mobile). Each is a pattern decision — present the approach with the diff.
5. **Judgment-call items:** P20 (trending gold frames), P16 (api mobile table) — present options, let Marco rule.

You do NOT have to follow this order rigidly — but do O1 before SB3/P9/P18, and cluster the ⚙ scope questions so Marco isn't pinged repeatedly.

---

## Per-fix loop (the `/design-iteration` contract — non-negotiable)

For **every** item above:

1. **Verify it's still broken.** Re-grep / re-read the real anchor (the CHECKLIST line numbers drifted). If already fixed → **NO CHANGES**, note it, next.
2. **Port the intent by hand** onto the current code shape. Do not paste stale patches — files were rewritten by #1235/#1241.
3. **Read the edited file(s) back.** Confirm: no duplicated/merged lines, no raw hex (tokens only), no gradient text, no dead-enum reads, IIFE-scope respected on `skill-explorer.js`/`skill-graph.js`, `renderRows()` `currentState` destructuring intact on badges.
4. **STOP. Present:** Fix ID + description, files changed, `git diff` (or key hunks), one-line "why this is safe," then ask **APPROVE / REJECT / NO CHANGES?**
5. On decision: APPROVE → `git add <only those files>` → `commit fix(design): <ID> — <summary>` → `git push` → report SHA → next. REJECT → `git restore` → next. NO CHANGES → touch nothing → next.
6. **Never proceed before a decision.** Never batch. Never merge.

**Verification after visual fixes:** use Playwright (the `/browse` skill is BANNED — Playwright only) against `http://localhost:8090/` desktop 1280×900 + mobile 390×844 to confirm the fix reads right, per the CHECKLIST's own method. Screenshot the before/after for the ship-blockers and overhauls.

---

## PR body must include (when you open it)

- **Resolves:** the CHECKLIST completion (link `founder/reports/design-review-2026-07-20/CHECKLIST.md`).
- **Entrypoints section** (load-bearing invariant): P15 adds nav+footer mounts to `/api/` — list it; every other fix touches existing surfaces (waive with a note). Design-review agents bounce PRs missing this.
- **Per-fix outcome table:** each ID + approved/rejected/no-change + commit SHA.
- **Deliberately skipped (Marco ruled):** SB4/O5 (grouping-label rework, deferred post-merge), P2 (grade-colored bars, working as intended), P14 (10 Unique accurate to data — curation, not design). State these were verified out-of-scope so a future reviewer doesn't re-open them.
- **Any `[skip-scope-check]` commits** and why (⚙ generators outside `docs/`).
- **Token spend log** per CLAUDE.md (`<date> <model> <effort>: Xk in, Yk out. ~$Z`) as a PR comment at session close.

---

## Token / cutoff discipline (from founder/CLAUDE.md)

- Commit + push after EACH approved fix — never batch. A pushed commit survives cutoff.
- For any bulk edit (like a multi-file token sweep), use a single shell command, then confirm with a follow-up grep count, rather than N individual edits.
- If you hit ~80k tokens mid-pass, commit what's approved, push, report status — don't try to finish in one shot.

*Handover authored 2026-07-20 (orchestrator, session 3). Supersedes the CHECKLIST's own "deferred post-merge" sequencing for O1–O4 per Marco's "finish the whole checklist in one PR" instruction. SB4/O5, P2, P14 remain out per Marco's rulings.*
