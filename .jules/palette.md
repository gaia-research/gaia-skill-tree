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

## 2024-05-25 - Focus Rings for All Interactive Elements
**Learning:** Found several missing focus-visible classes on various buttons and interactive elements (`.nav-search-btn-mobile`, `.pmq-changelog-btn`, `.scroll-to-top`, `.mr-pagination-prev`, `.mr-pagination-next`, `.hero-audit-btn`, `.propose-cta`, `.meta-btn-close`, `.se-close-x`, `.hoh-fs-overlay-restore`, `.hoh-fs-btn`, `.hoh-fs-btn--close`, `.hoh-fs-copy-btn`), impacting keyboard accessibility.
**Action:** Always verify keyboard accessibility on all buttons by checking if they belong to the central grouped selector for `:focus-visible` in `styles.css` or `plaque.css`. Ensure new buttons receive `outline: 2px solid var(--tier-extra); outline-offset: 2px;`.
## 2024-05-18 - Universal Focus Ring Consistency
**Learning:** Many interactive components like inputs and custom buttons across badges and plaques were missing the standard focus ring used for keyboard accessibility. While standard buttons had the `focus-visible` rule, many custom classes did not inherit this.
**Action:** Always verify that newly created custom interactive elements (buttons, inputs, chips) explicitly append their selector to the app-wide `focus-visible` rule using the standard outline: `outline: 2px solid var(--tier-extra); outline-offset: 2px;`.
## 2026-06-09 - App-Wide Focus Ring for Starless and Meta pages
**Learning:** Found that multiple interactive elements (`.meta-report-action`, `.sl-btn`, `.sl-search-clear`) on the Meta and Starless pages were missing keyboard focus indicators. The codebase has an established focus ring pattern using `outline: 2px solid var(--tier-extra); outline-offset: 2px;`, which should be explicitly extended to all interactive generic buttons and controls.
**Action:** Added these missing selectors to the app-wide focus ring block in `docs/css/styles.css` to maintain a consistent and accessible keyboard navigation experience.
## 2026-06-13 - App-Wide Focus Ring for Navigation Toggles and Simulator Button
**Learning:** Found that `.nav-more-toggle`, `.nav-menu-toggle`, and `.review-sim-btn` interactive elements were missing keyboard focus indicators. The codebase has an established focus ring pattern using `outline: 2px solid var(--tier-extra); outline-offset: 2px;`, which should be explicitly extended to all interactive generic buttons and controls. Furthermore, `.nav-menu-toggle:focus-visible` was explicitly removing outline `outline: none`, overriding accessibility.
**Action:** Added these missing selectors to the app-wide focus ring block in `docs/css/styles.css` and removed `outline: none` from `.nav-menu-toggle:focus-visible` to maintain a consistent and accessible keyboard navigation experience.
