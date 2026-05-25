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

### Step 1: Prepare the Report

Ensure your report is written in Markdown and saved as `METASHIFT.md` in the project root. It should include:
- Executive Summary
- Key Actions Taken (e.g., rank adjustments, reclassifications)
- Affected Skill IDs and rationale
- Verification status (schema, tests)

### Step 2: Run the Meta-Post

Execute the publication process. Provide a title and a short summary for the landing page.

```bash
# Example usage (Agent logic):
# 1. Move report to docs/meta/reports/YYYY-MM-DD-title.md
# 2. Update docs/meta.html with a new <article> card
# 3. Update docs/index.html hero version/stat if needed
```

### Step 3: Format the Card

When adding the report to `docs/meta.html`, use the following HTML template:

```html
<article class="meta-report-card">
  <div class="meta-report-date">Month DD, YYYY</div>
  <h3 class="meta-report-title">REPORT_TITLE</h3>
  <p class="meta-report-summary">
    REPORT_SUMMARY_OR_ASSESSMENT
  </p>
  <a href="meta/reports/YYYY-MM-DD-filename.md" class="btn btn-ghost meta-report-link">Read Full Report →</a>
</article>
```

### Step 4: Verify and Commit

Check the new page and the link:
1. Open `docs/meta.html` locally.
2. Verify the hero link in `docs/index.html` works.
3. Commit with prefix `docs(meta): publish [TITLE] report`.

## Constraints

- **Language**: Avoid banned terms (apex tier, Atomic Basics, card, etc.) as defined in `CONTEXT.md`.
- **Design**: Maintain compliance with `DESIGN.md` (EB Garamond for titles, Bricolage for body).
- **Icons**: Use the `info` icon for report-related affordances.

## Example

```bash
/meta-post "Programmatic Registry Audit" "Enforced hardened prestige rules and star bar requirements across 211 skills."
```
