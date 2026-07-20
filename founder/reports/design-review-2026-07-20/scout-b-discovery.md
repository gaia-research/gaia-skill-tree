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

## Verified looks right (Surface 1 /named/)
- Card grid reads as one coherent system across 1★–5★; consistent medallion + level-pill + avatar layout.
- Suite 5★ plaques (ruflo/skills/gstack/superpowers): gold-ring dark orb medallion (aov4 suite) + gold-wreath avatar; contributor handles in Honor Red.
- Unique 4★ plaques: darker violet-ring medallion register — visually distinct from gold suite plaques (E3 distinction reads).
- No broken avatar/medallion holes: 119 wreaths, 153 medallions, 392 imgs, none broken (the one "broken" src was the page URL itself, a false positive).
- No horizontal overflow at 390px; mobile hero + filter chips stack cleanly.
- Origin marks render gold (wreath), not red — no red origin laurels observed.
