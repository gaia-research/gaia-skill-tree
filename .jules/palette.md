## 2026-05-19 - ARIA labels for icon-only buttons
**Learning:** Found that some buttons with text inside also have `title` tags but no `aria-label`. Adding `aria-label` provides a stronger guarantee that screen readers announce the intent correctly when visually there is an icon and a short text.
**Action:** Added `aria-pressed` to `.ns-view-btn` controls and wrapped them in a `role="group"` with an `aria-label` of "View mode" to improve screen reader announcement of these toggle buttons.

## 2026-05-19 - Tab roles and dynamic aria attributes
**Learning:** Adding WAI-ARIA `role="tablist"`, `role="tab"` along with dynamically updating `aria-selected` and `aria-pressed` based on the `active` class is a recurring necessity for component-level tabs/toggles that aren't using a framework.
**Action:** Used JS to toggle `aria-selected`/`aria-pressed` in tandem with `active` class in `docs/js/named-skills.js` and `docs/js/page-ia.js`.

## 2024-05-20 - Adding ARIA labels to dynamically generated HTML elements
**Learning:** Found multiple instances where UI JS logic (e.g. `plaque.js`, `skill-explorer.js`, `skill-graph.js`) generated icon-only buttons via template strings without ARIA labels, creating accessibility issues.
**Action:** When working on UI enhancements, check dynamically constructed DOM elements inside JS files for accessibility attributes, especially `aria-label` for icon-only buttons, as these are often overlooked compared to static HTML files.

## 2024-05-24 - Accessible icon-only copy buttons
**Learning:** Icon-only copy buttons (like the `ns-install-copy` button) were relying solely on the `title` attribute for screen readers. While `title` gives hover tooltips, `aria-label` provides a much more robust and universally supported experience for assistive technologies on icon-only actions.
**Action:** Always complement or replace visual `title` attributes with explicit `aria-label`s on icon-only buttons (`.ico` wrappers) to guarantee correct semantic parsing by screen readers.
