## 2026-05-19 - ARIA labels for icon-only buttons
**Learning:** Found that some buttons with text inside also have `title` tags but no `aria-label`. Adding `aria-label` provides a stronger guarantee that screen readers announce the intent correctly when visually there is an icon and a short text.
**Action:** Added `aria-pressed` to `.ns-view-btn` controls and wrapped them in a `role="group"` with an `aria-label` of "View mode" to improve screen reader announcement of these toggle buttons.

## 2026-05-19 - Tab roles and dynamic aria attributes
**Learning:** Adding WAI-ARIA `role="tablist"`, `role="tab"` along with dynamically updating `aria-selected` and `aria-pressed` based on the `active` class is a recurring necessity for component-level tabs/toggles that aren't using a framework.
**Action:** Used JS to toggle `aria-selected`/`aria-pressed` in tandem with `active` class in `docs/js/named-skills.js` and `docs/js/page-ia.js`.
