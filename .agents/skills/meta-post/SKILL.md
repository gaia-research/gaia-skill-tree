---
name: meta-post
description: Add a new Meta Report to the Gaia documentation and update the landing page. Use when you have completed a registry audit or major meta-shift.
---

# Meta-Post

Publish a dedicated Meta Report to the registry's public assessment list. This skill automates the placement of markdown reports and ensures they are discoverable via the Meta Reports landing page.

## When to Use

- After a major registry audit (e.g., using `gaia-audit` or `gaia-meta-audit`)
- Following a programmatic meta-shift that reclassifies or recalibrates multiple skills
- When structural schema changes or nomenclature shifts occur
- To document written assessments and timelines of registry evolution

## Instructions

### Step 1: Prepare the Report Data

Ensure your audit results are summarized. If a timeline plot is needed, run `scripts/_extract_timeline.py` to update `may-2026-timeline.json`.

### Step 2: Create the Standalone HTML Report

Author your report as a standalone HTML page in `docs/meta/reports/YYYY-MM-DD-title.html`. Use the LaTeX academic template:
- White paper aesthetic (EB Garamond font).
- Abstract, Numbered Sections, References.
- Embedded Chart.js for timeline plots.
- A "Back to Meta Reports" footer link.

### Step 3: Update the Landing Page

Add a new card to `docs/meta.html` using this template:

```html
<article class="meta-report-card">
  <div class="meta-report-date">Month DD, YYYY</div>
  <h3 class="meta-report-title">REPORT_TITLE</h3>
  <p class="meta-report-summary">
    Short 2-3 sentence assessment summary.
  </p>
  <a href="meta/reports/YYYY-MM-DD-filename.html" class="btn btn-ghost meta-report-link">Read Full Report →</a>
</article>
```

### Step 4: Update the Hero Sneak Peek

Update the `hero-meta-peek` anchor in `docs/index.html` to point to the latest report and update the date/title.

## Constraints

- **Language**: Avoid banned terms (apex tier, Atomic Basics, card, etc.).
- **Design**: Strictly follow `DESIGN.md`. Hero peek MUST remain compact and visible on all screen sizes.
- **Plots**: Prefer data-driven Chart.js line plots for timelines.

## Example

```bash
/meta-post "Programmatic Registry Audit" "Enforced hardened prestige rules and star bar requirements across 211 skills."
```
