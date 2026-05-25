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
- Floating "View Changelog" button (upper right).
- Embedded Chart.js for timeline plots.
- A "Back to Hunter's Atlas" footer link.

### Step 3: Update Path B Queue

Add the report to the `door-meta-queue` in `docs/index.html` using this template:

```html
<a href="meta/reports/YYYY-MM-DD-filename.html" class="dmq-post" target="_blank">
  <span class="dmq-label">Latest Audit</span>
  <h4 class="dmq-title">REPORT_TITLE</h4>
  <p class="dmq-summary">Short summary.</p>
</a>
```

### Step 4: Update the Hero Notification Peek

Update the `hero-meta-peek` anchor in `docs/index.html` to point to the latest report. Ensure it looks like a push notification.

## Constraints

- **Language**: Avoid banned terms (apex tier, Atomic Basics, card, etc.). Rename "Timeline" to "Changelog".
- **Design**: Strictly follow `DESIGN.md`. Boxy borders for all meta components.
- **Plots**: Prefer data-driven Chart.js line plots.

## Example

```bash
/meta-post "Programmatic Registry Audit" "Enforced hardened prestige rules and star bar requirements across 211 skills."
```
