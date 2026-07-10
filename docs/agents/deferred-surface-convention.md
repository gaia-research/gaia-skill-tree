# Deferred-surface convention — ship the bridge state, disclose the bridge state

**When a surface ships to satisfy a kill criterion but its design register is explicitly slated for a later sprint, the interim state MUST be disclosed on the surface itself with a WIP banner linking to the tracking issue.** Codified after the v6.0.1 review, where the archive landing at `/reports/` was correctly redesigned but the per-report page at `/reports/YYYY-WW/` shipped as the L3-mechanical `<pre>{{ markdownBody }}</pre>` fallback and confused a reviewer into thinking the leaderboard rendering was missing (it wasn't; it was Sprint F scope).

## When this applies

Apply the pattern when **all three** conditions hold:

1. The surface is user-visible and reachable from the homepage or main nav.
2. Its current rendering satisfies its ratified kill criterion (URL exists, JSON contract shipped, cron produces output, etc.) but is visibly below the design bar of adjacent surfaces.
3. `founder/GAIA_ROADMAP v*.md` explicitly slates the rendering-layer work for a named later sprint, OR a tracking issue exists with that sprint tag.

Do **not** apply the pattern to hide unfinished work that has no sprint home. That's not a bridge state, that's a defect. File it and fix it.

## What ships

1. **A `.wip-banner` element** at the top of the surface (inside `<main>`, before content). Uses the shared class from the content-engine template pass, or an equivalent local styled element that matches:
   - `--font-mono`, `0.78rem`, subtle `--evidence-gold` tint background + border
   - Two spans: `<span class="wip-tag">◇ Interim rendering</span>` (or an equivalent short label) + `<span class="wip-body">` with one sentence of what's provisional, one sentence of what's frozen, and a link to the tracking issue.
   - `role="note"` + `aria-label` describing the notice.
2. **A tracking issue** with the target sprint label (e.g. `sprint-f`) and an explicit `## Non-goals` section noting the WIP banner is removed by the port. Reference sprint scope from `founder/GAIA_ROADMAP v*.md` by line number.
3. **A note in the shipping PR body** under a `## Deferred surfaces` section listing which surfaces carry the banner and their tracking issues.

## What NOT to do

- Do not silently ship the bridge state and hope reviewers infer the sprint schedule. That was the v6.0.1 failure mode; the fix is disclosure.
- Do not add a WIP banner without a tracking issue. The banner exists to point somewhere; without a link, it's decoration.
- Do not use the banner to defer trivial polish (missing padding, wrong color, one label). Polish gets fixed in the same PR. The banner is for cross-sprint rendering-layer or infrastructure boundaries.
- Do not stack multiple WIP banners on one surface. If a surface has more than one deferred concern, consolidate them into one tracking issue and one banner.

## Reference implementation

See `scripts/contentEngine/templates/report.html.j2` (added in PR #972, tracking issue #973 for Sprint F rendering-layer rewrite). The banner CSS is inline in the template `<style>` block; the markup sits between the `<nav>` and `<main>` elements.
