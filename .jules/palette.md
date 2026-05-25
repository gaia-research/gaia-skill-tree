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

## 2024-06-25 - App-Wide Focus Ring Convention
**Learning:** Found that multiple interactive elements (.btn, .mr-tab, .ns-tab, .os-tab, .se-tab-btn, .se-flow-btn) were missing keyboard focus indicators. The codebase has an established focus ring pattern for some components using `outline: 2px solid var(--tier-extra); outline-offset: 2px;`, which should be explicitly extended to generic buttons and tabs.
**Action:** Always check for missing `:focus-visible` styles on interactive components and apply the `var(--tier-extra)` focus ring to maintain a consistent keyboard navigation experience across the app.

## 2026-05-23 - App-Wide Focus Ring Convention
**Learning:** Found that multiple interactive elements (.tree-act-btn, .tree-close-x, .graph-legend-drawer-toggle, .graph-action-btn, .ult-claim, .footer-link-btn) were missing keyboard focus indicators. The codebase has an established focus ring pattern for some components using `outline: 2px solid var(--tier-extra); outline-offset: 2px;`, which should be explicitly extended to all interactive generic buttons and tabs.
**Action:** Always check for missing `:focus-visible` styles on interactive components and apply the app-wide focus ring to maintain a consistent and accessible keyboard navigation experience.

## 2026-05-24 - App-Wide Focus Ring for Graph Collection
**Learning:** Found that multiple interactive elements (.graph-collection-copy-all, .graph-collection-clear-all, .graph-collection-minimize, .graph-collection-share, .graph-collection-remove, .graph-skill-panel-close) in the newly added graph collection panel were missing keyboard focus indicators. The codebase has an established focus ring pattern using `outline: 2px solid var(--tier-extra); outline-offset: 2px;`, which should be explicitly extended to all interactive generic buttons and tabs.
**Action:** Added these missing selectors to the app-wide focus ring block in `docs/css/styles.css` to maintain a consistent and accessible keyboard navigation experience.
