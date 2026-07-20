# Scout B — Discovery Family Design Review (2026-07-20)

Reviewer lens: designer's eye (layout/overlap/color/readability), not a linter. Surfaces: /named/ catalog, Skill Explorer overlay, /badges/, 3D explorer.
Viewports: 1280×900 (desktop), 390×844 (mobile). Screenshots in scratchpad/scoutB/.

## Findings

| Surface | Viewport | What looks wrong | Evidence | Suspected cause | Severity | Effort |
|---|---|---|---|---|---|---|
| /named/ catalog | desktop | **Section header "◆Extra · 4★" groups UNIQUE-branch cards.** All 4★ cards under it are `data-branch="unique"` (obra/writing-plans, subagent-driven-development, using-git-worktrees, pbakaus/impeccable, safishamsi/graphify, addy-osmani/performance-optimization, openai/few-shot-learning, stanfordnlp/dspy). Per DESIGN E2, a 4★ unique must read "Unique", never the suite word "Extra". No separate "Unique · 4★" group exists — the grouping uses suite vocabulary only, ignoring branch. | named-unique-cards.png; header `◆Extra · 4★`; cards `data-branch=unique level=4` | Section grouping keys the rank word off level alone (`rankWord(level)` w/o branch), a flat rank→word swap | ship-blocker | medium |
| /named/ catalog | desktop | Horizontal overflow of 16px at 1280 (documentElement.scrollWidth − clientWidth = 16). Not present at 390. Minor but produces a stray horizontal scroll on desktop. | probe hOverflow=16 (desktop), 0 (mobile) | Likely a full-bleed row/grid exceeding container by scrollbar width or a card gutter miscalc | polish | easy-win |
| /named/ catalog | desktop | 1★ (Awakened) cards show literal **`@[anonymous]`** in the contributor slot (muted gray) instead of an Honor-Red handle or a clean "no contributor" treatment. Reads as a broken placeholder/empty state across the whole 1★ band. | named-desktop-bottom.png (/zoom-out, /gaia-bot-curate, /implement-with-discernment, /agentdb-learning all `@[anonymous]`) | Missing contributor handle falls back to a raw `[anonymous]` token rather than a designed empty state | polish | easy-win |
| /named/ catalog | desktop | `plaque__install-cmd` text is clipped/truncated inside its box on many cards (e.g. `gaia install obra/subagent-driven-develo…`, `addy-osmani/performance-opt…`). Truncation is expected for long slugs, but several overflow the pill by 160–250px before the ellipsis, and the copy affordance sits tight against clipped text. | probe `clipped[]` (ow up to 253px); named-desktop-mid.png install rows | Fixed-width install pill with `text-overflow: ellipsis` but the underlying text overflow is large; ellipsis clips mid-word | nit | easy-win |
| /named/ catalog | desktop | Thin **stray gold/amber hairline underline** appears beneath the tag-pill row on some cards (planning, subagent/orchestration, git-worktrees/isolation, design/audit/frontend, self-learning) but not others — inconsistent decorative accent. | named-desktop-mid/bottom.png (under tag rows) | Likely a dead `--tier-extra`/`--tier-ultimate` token or an underline accent rendering only where a class resolves | nit | easy-win |

### Surface 2 — Skill Explorer overlay (opened on /ruflo, 5★ Ultimate suite)

| Surface | Viewport | What looks wrong | Evidence | Suspected cause | Severity | Effort |
|---|---|---|---|---|---|---|
| Skill Explorer | mobile (390) | **Mobile overlay is truncated to the Hero + Installation only.** The desktop right-hand "Upgrade Path & Adjacent Skills" flow-graph panel is a 2-column sibling of `.se-body`; on mobile it is not stacked below the hero. `.se-body` scrollHeight == clientHeight == 539px (hero card only) and the overlay does not scroll (wheel gesture dismisses it rather than scrolling). Result: on a phone you can see Hero + install but cannot reach the Upgrade Path/flow, and (if they live in the same panel) Documentation / Evolution Changelog. The primer requires all five sections to render. | explorer2-mobile-1/2/3.png (identical — no scroll); estruct.js `.se-body` h=539 == scrollH; efinal.js bodyScrollH==bodyClientH mobile | Flow/upgrade panel is a desktop-only second column; not reflowed into the mobile single-column stack | ship-blocker | medium |
| Skill Explorer | desktop | **Two adjacent path-toggle buttons carry the IDENTICAL label "SHOW ULTIMATE PATH".** Reads as a duplicate/broken control — one was almost certainly meant to be a different path (e.g. "Full Path" / the suite's "Extra Path"). | explorer2-desktop-1.png, explorer2-desktop-3.png (right column, under "UPGRADE PATH & ADJACENT SKILLS") | Both buttons resolve their rank word to the same 5★ "Ultimate"; likely a dead `--tier-extra`/rank-word fallback collapsing two labels into one | ship-blocker | medium |
| Skill Explorer | desktop | **"Fuse skills on Gaia Research" appears twice** — once as a cyan box under the hero card (left) and again as the right-column flow header box. Redundant duplicate CTA in one view. | explorer2-desktop-1.png (both boxes visible) | Bridge CTA rendered in both hero footer and flow header | polish | easy-win |
| Skill Explorer | desktop | Lower half of the flow graph is a **dense tangle of long crossing edges** spanning the full panel width; the "ruvnet/ruflo" node pill is repeated (top fan-out node + bottom tree node) making the two clusters read as duplicates rather than distinct path/adjacency views. | explorer2-desktop-1.png (bottom tree) | Force/tree layout not de-cluttering long edges; same node labeled in both sub-graphs | polish | medium |
| Skill Explorer | mobile (390) | Scroll-to-top FAB overlaps the "MAG 482.3" evidence bar at the bottom-right of the hero card. | explorer2-mobile-1.png | Fixed FAB not accounting for the evidence bar's z-space | nit | easy-win |

## Verified looks right (Surface 2 Skill Explorer)
- Overlay opens on card click; topbar (Back / @handle / Repo / Share / Report / close X) is clean and consistent.
- Hero card composes well: aov4 medallion + gold-wreath avatar (ruvnet face renders inside the wreath — no empty hole once loaded), rank-colored `/ruflo` title, Honor-Red handle, correct 5★ star fill (5 gold + 1 outline), install command, "ADD TO README", and the "PLATINUM (S) · MAG 482.3" evidence bar.
- Mobile hero card is well-composed and does not overflow horizontally (hOverflow 0 at 390).
- Cross-brand "Fuse skills on Gaia Research →" bridge uses the correct Rimuru-Blue affordance (E5).

### Surface 3 — /badges/?u=mattpocock&s=grill-me

| Surface | Viewport | What looks wrong | Evidence | Suspected cause | Severity | Effort |
|---|---|---|---|---|---|---|
| /badges/ | desktop | Two **404s on live data**: `/badges/graph/gaia.json?v=6.8.8` and `/badges/graph/named/index.json?v=6.8.8`. Page fetches `graph/…` relative to `/badges/` → resolves to `/badges/graph/…` which doesn't exist (should be `/graph/…` or `../graph/…`). Badge still renders from fallback, so not blank — but the graph-data hydration silently fails. | b404.js FAILED REQUESTS list; badge-url-full.png (preview still renders) | Relative-path fetch not accounting for `/badges/` base path | polish | easy-win |
| /badges/ | mobile (390) | **"◇ HONESTY ON" status pill overlaps the H1 "Github Badges"** — the pill sits on the title's right edge instead of clearing it. Cramped collision in the hero. | badges-390.png (pill on top of "Badges" wordmark) | Absolutely/float-positioned pill with no mobile reflow below the H1 | polish | easy-win |
| /badges/ | desktop | "HONESTY ON" pill floats at an awkward mid-title vertical position (aligned to the middle of the H1's right, not the baseline or a header row) — reads as a stray tag rather than a deliberate status chip. | badges-1280.png | Same absolute-position pill; no desktop anchor | nit | easy-win |

## Verified looks right (Surface 3 /badges/)
- **Badge is NOT blank** — the required `?u=mattpocock&s=grill-me` URL renders the full builder + README preview (body 5527 chars). No ship-blocker.
- README preview composes three coherent badges (handle `@mattpocock/grill-me · 3★`, `Ultimate · 5★`, `34 named skills`) with gold-outline pills, Honor-Red handle, star ratings.
- Variants section (handle/rank/skills/powered-by), the rank-system table (1★→6★ with evidence floors), and "What your badge means" table all render cleanly and read as one system.
- Footer + nav consistent with the rest of the site.

### Surface 4 — 3D explorer (homepage "Explore in 3D")

| Surface | Viewport | What looks wrong | Evidence | Suspected cause | Severity | Effort |
|---|---|---|---|---|---|---|
| 3D explorer | desktop | **HUD status line reads "243 skills · 406 links · 10 Unique" — primer expects 6 Unique.** The Unique count is 10, not 6. Either the branch-derivation over-counts unique nodes in the 3D layout or the registry now has 10 unique-branch skills; either way it contradicts the stated design target. | threed-desktop-1/2.png status pill; probe status "243 skills · 406 links · 10 Unique" | `computeBranch` count in the 3D layout diverges from the expected 6, or intended count changed and copy is stale | polish | medium |
| 3D explorer | desktop | **Labels-on state is illegible in the central canopy** — dozens of node labels (/full-stack-developer, code-review, design-generation, subagent-driven-development, request…memory, dispatch…debugging, etc.) overprint into an unreadable mush. No collision avoidance / level-of-detail culling; only peripheral labels (/web-quality-audit, /performance-tuning, /code-explain, /fine-tune, /rank) are readable. | threed-labels.png | No label declutter/LOD; all labels drawn at once regardless of density | polish | medium |
| 3D explorer | desktop | Per-skill detail fetches 404 in bulk — `/api/v1/skills/<handle>/<slug>.json?v=6.8.8` returns 404 for ~20+ skills (deepmind bio suite, pexp13/sentiment-analysis, etc.), so tooltip/detail hydration fails. **Low confidence it's a ship issue** — likely the per-skill API JSON isn't generated by a plain static serve of `docs/` locally; verify on a full `gaia dev docs` build before treating as a defect. | t404.js 404 list | `docs/api/v1/skills/*.json` not present in local serve (Class S per-skill artifacts) | nit | (verify) |
| 3D explorer | desktop | The Yggdrasil raster backdrop reads as a **spooky face/skull** — two violet ringed nodes land exactly over the artwork's dark "eye sockets," producing unintended pareidolia (two glowing eyes + dark socket). Subjective, but it undercuts the "living brand mark" intent. | threed-desktop-1/2.png (center-lower) | Ringed special nodes overlap the raster's dark ovals by coincidence of layout | nit | medium |

## Verified looks right (Surface 4 3D explorer)
- Canvas renders reliably (1280×900, no fatal JS/page errors — only resource 404s).
- **Unique/apex cluster placement is correct**: the bright gold/amber (copper-ember-leaning) cluster sits tucked at the center-top under the branch canopy — NOT violet, NOT a far-right satellite, matching the design intent.
- Node color system reads: teal (2★ named) low/outer, violet (4★) mid, gold (5–6★) at the canopy focal point.
- HUD/control layout is clean: top-left status pill + COLLECTION panel, top-right Labels/Orbit/GEXF/close, right-edge FILTERS tab + "/skill · @handle" search, bottom playback (pause/reset/speed) strip. No control overlaps.
- Homepage "Explore in 3D" control launches the overlay correctly.

## Verified looks right (Surface 1 /named/)
- Card grid reads as one coherent system across 1★–5★; consistent medallion + level-pill + avatar layout.
- Suite 5★ plaques (ruflo/skills/gstack/superpowers): gold-ring dark orb medallion (aov4 suite) + gold-wreath avatar; contributor handles in Honor Red.
- Unique 4★ plaques: darker violet-ring medallion register — visually distinct from gold suite plaques (E3 distinction reads).
- No broken avatar/medallion holes: 119 wreaths, 153 medallions, 392 imgs, none broken (the one "broken" src was the page URL itself, a false positive).
- No horizontal overflow at 390px; mobile hero + filter chips stack cleanly.
- Origin marks render gold (wreath), not red — no red origin laurels observed.
