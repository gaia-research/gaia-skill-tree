# Artificial Analysis Intelligence Index — Design Reference

> Reverse-engineered 2026-06-29. Source: https://artificialanalysis.ai/models and https://artificialanalysis.ai/#intelligence
> Purpose: design peg for Gaia Trust Leaderboard (docs/trust/leaderboard/).

---

## 1. Bar Chart Orientation

**Vertical bars** (columns), NOT horizontal. Each model = one vertical bar. Bars are sorted descending left-to-right (highest score on the left). The x-axis is the model list; the y-axis is the score.

Score values are rendered as a numeric strip **below the chart area** — a row of numbers like `60 56 55 51 50 47 46 46 44 43 43 42...` aligned to each bar's x-position. These are not axis tick labels in a traditional sense; they float beneath the bar as inline text per column.

Bar height is proportional to score. Bars are relatively narrow (~28–32px wide) with small gaps between them. There is no y-axis gridline overlay in the primary chart; the score strip below serves as the only numeric reference.

---

## 2. Row / Column Structure (per bar)

Each bar column contains (top to bottom):

1. **Score value** — appears at the top of or just above the bar (for the main index chart, score floats below as a strip; in sub-charts it may appear above the bar)
2. **Bar body** — filled rectangle, color varies (see §5)
3. **Model name** — rotated 45° or vertical text below the bar, truncated
4. **Provider logo** — small SVG icon (~20px) below or beside the model name
5. **Badge pill** — "Reasoning model" tag with a lightbulb icon (💡), shown for reasoning models only

For stacked bar charts (latency, end-to-end response time, model size), segments are stacked vertically within the bar with a color per segment and a legend below.

---

## 3. Tab System (per chart section)

Every major chart section has its own inline tab row that switches the chart view. Tabs are plain text links styled as pills/underline-active. Examples:

- **Intelligence section:** `Artificial Analysis Intelligence Index` | `Coding Index` | `Agentic Index`
- **Intelligence Breakdown section:** `Open Weights / Proprietary` | `Reasoning / Non-Reasoning` | `Text Only / Multimodal Inputs`
- **Latency section:** `Time To First Answer Token` | `Time To First Token` | `Latency by Input Token Count` | `Latency Variance` | `Latency Over Time`
- **End-to-End Response Time:** `End-to-End Response Time` | `End-to-End Response Time by Input Token Count` | `End-to-End Response Time Over Time`
- **Model Size:** `Total & Active Parameters` | `Intelligence vs. Active Parameters` | `Intelligence vs. Total Parameters`

Active tab = underlined or bolded. Tab switching re-renders the chart in-place (no page navigation).

---

## 4. Model Selector / Search

Each chart section shows:
- **`X of N models`** counter (e.g., "27 of 543 models") — X is the number currently displayed
- **"Add model from specific provider"** dropdown — lets you add a specific provider's model to the current chart view
- Some rows carry status badges: `Not currently available` (gray pill) or `Estimate (independent evaluation forthcoming)` (italic gray text) — overlaid on the bar or in the row

There is **no free-text search box** visible on the main leaderboard page. Model selection is done via the "Add model from specific provider" dropdown. The LLM Leaderboard page (https://artificialanalysis.ai/leaderboards/models) may have additional search.

---

## 5. Color Coding

Color is by **segment type / category**, NOT by score or ranking position.

- **Main Intelligence Index chart:** Single-color bars per model. The color appears to be provider-based (e.g., all Anthropic models same blue, all OpenAI models same green) — NOT grade-based.
- **Stacked charts (latency, end-to-end, model size):** Each segment has its own color with a legend below the chart. Examples:
  - Latency bars: blue = "Thinking (reasoning models)" / orange = "Input processing"
  - End-to-end bars: teal = "Outputting time" / blue = "'Thinking' time (reasoning models)" / orange = "Input processing time"
  - Model size bars: dark = "Passive Parameters" / bright = "Active Parameters"
- **Color legend** appears as labeled color swatches below or beside each stacked chart.

No grade-based (S/A/B/C) coloring visible. No score-range color ramping visible in the primary chart.

---

## 6. Action Buttons (per chart section)

Three action buttons appear in the top-right corner of each chart section (not always visible in scrape but confirmed from page structure and AA's known UI):

| Button | Behavior |
|--------|----------|
| **Copy link** | Copies a URL with an anchor hash to that specific chart section (`#intelligence`, `#speed`, etc.) to clipboard |
| **Copy image** | Copies the chart rendered as a PNG image to clipboard |
| **Download data** | Downloads the underlying chart data as a CSV or JSON file |

These buttons are lightweight icon-buttons (no text label in compact mode, tooltip on hover).

---

## 7. Section Navigation

A sticky horizontal nav strip appears at the top of the page (below the main site nav) listing all chart sections as anchor links:

```
Intelligence | Intelligence Breakdown | AA-Briefcase | AA-Omniscience | Openness | ... | Speed | Latency | End-to-End Response Time | Model Size
```

Some entries carry update badges: `Updated`, `New`. Clicking scrolls to that section.

---

## 8. "Show More" / Pagination

**There is no "Show more" button.** The chart always shows the currently selected set of models (default = 27). Users add/remove models via the "Add model from specific provider" dropdown. This keeps the chart readable without infinite scroll.

---

## 9. Hover / Click Behavior

- **Click a bar / model row** → navigates to that model's dedicated page (e.g., `/models/claude-opus-4-8`)
- **Hover** → likely a highlight/tooltip state (not captured in static scrape, but standard for AA charts)
- Model name text in the column is also a direct hyperlink

---

## 10. Stacked Bar Detail (Latency / End-to-End)

Some charts use **segmented stacked bars** where multiple components are stacked vertically within one bar:

- Each segment has a distinct color matching the legend
- Segment heights are proportional to their component value
- Legend appears below the chart as colored squares + labels
- For reasoning models, a "Thinking time" segment is added (absent for non-reasoning models)

---

## 11. Gaia Adaptation Notes

Decisions made when adapting this design to the Gaia Trust Leaderboard:

| AA Feature | Gaia Adaptation |
|------------|-----------------|
| Provider SVG logos | **Colored circle avatars** — deterministic color per contributor handle (no GitHub fetch, no external requests). Same color for every occurrence of the same handle on the page. |
| Model name + provider logo per bar | Skill name + contributor handle + rank pill (e.g., `3★`) |
| "Reasoning model" badge | Skill type badge (`ultimate`, `basic`, `research`, etc.) |
| Provider-based bar color | **Grade-based gradient** (S = platinum shimmer, A = gold, B = steel, C = copper) + rank luminosity modifier |
| Score strip below chart | TM (Trust Magnitude) value label above or at bar top |
| Tab system per section | Grade filter tabs (`All` / `S` / `A` / `B` / `C`) + sort tabs (`By TM` / `By Grade`) — existing pill buttons satisfy this |
| "Add model from specific provider" dropdown | **Contributor search/filter input** — type to filter to one contributor's skills |
| Copy link | Anchor-hash copy to section |
| Copy image | SVG serialization → `data:image/svg+xml` → open in new tab (no html2canvas, no CDN) |
| Download data | Download visible rows as CSV |
| Sticky section nav | Existing section anchors; sticky nav is a future enhancement |
| No "show more" button | Keep existing "Show more (N remaining)" — Gaia has 249 skills vs AA's curated 27, so pagination is still needed |
