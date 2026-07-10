# Fixed-nav clearance — every top-level page container must clear ~58px

**Every page-level container that sits directly under `<body>` MUST provide its own top clearance to sit below the fixed nav.** The site nav (`<nav>` in `docs/js/site-nav.js`, rule at `docs/css/styles.css` L299–315) is `position: fixed` with `padding: .9rem 2rem` + a 1px border, giving it an effective height of ~58px. Nothing in the layout compensates for that automatically. Every page-level container fixes this on its own, and every design pass on a new surface must apply the pattern from the start. Codified after the v6.1.1 review, where the `.wip-banner` on the per-report page and the `.trending-main` on `/trending/` both shipped with insufficient top padding and got cut off by the nav.

## The pattern (use this exact value ladder)

```css
.some-page-shell {
  padding: 5rem 1.5rem 6rem;   /* top: 5rem (80px) clears the ~58px nav with 22px breathing room */
  max-width: 62rem;
  margin: 0 auto;
}
@media (min-width: 768px) {
  .some-page-shell { padding: 8rem 2rem 7rem; }   /* or padding-top: 6rem for compact strips */
}
```

Base clearance is **5rem (80px)**. Desktop clearance is **6rem (96px) for thin strips** (banners, notices) or **8rem (128px) for full page shells** (hero-carrying containers where a bit more breathing room is warranted). Do not invent other values; consistency across surfaces is the point.

## Existing reference implementations

Every current site surface uses this ladder. When adding a new page, copy one of these:

- `.bench-shell` (`docs/benchmarks/index.html` inline `<style>`) — canonical full-page shell, `5rem`/`8rem`
- `.reports-shell` (`scripts/contentEngine/templates/archive.html.j2` inline `<style>`) — full-page shell, `5rem`/`8rem`
- `.trending-main` (`docs/trending/trending.css` L7–16) — full-page shell, `5rem`/`6rem` (added in PR #972 after cutoff regression)
- `.wip-banner` (`scripts/contentEngine/templates/report.html.j2` inline `<style>`) — thin strip, `5rem`/`6rem`

## Anti-patterns (refuse and rewrite)

- **`padding-top: 0` on a body-child container.** The default. Will cut off content. Every page-level container needs an explicit top pad; there is no global `body { padding-top: ... }` and there won't be one (the fixed nav is a scroll-persistent surface, not a document flow element, and a global body offset would break the hero which is intentionally full-bleed under the nav).
- **The `margin-top: -Npx` + `padding-top: calc(... + Npx)` trick** (as seen on `.profile-back-row` at `docs/css/styles.css` L1109–1122). Pulls the element into negative layout space to "pretend" the nav isn't there. Fragile: any preceding sibling with margin breaks the offset math, and the descendants inherit the compressed vertical origin. Legacy; do not extend to new surfaces.
- **Inline `style="margin: 2rem auto"` or similar on `<main>`.** Was the pattern on the pre-Sprint-D bridge-state per-report page. `2rem` (32px) < nav height (58px), so the top of `<main>` sits under the nav. Same failure mode as the `.wip-banner` regression.
- **Adding padding-top only to a nested child** (e.g. the hero inside a page shell). Works for that hero but breaks any subsequent design change that swaps or removes the hero. Put the clearance on the outermost body-child container so it's a property of the surface, not of one section.

## Verification during design pass

Before closing any PR that adds a new page or moves a top-level container:

1. Load the page in a browser, scroll to absolute top (Ctrl+Home).
2. The first content pixel below the nav should have visible breathing room, not touch the nav border.
3. Confirm at both breakpoints (<768px and ≥768px).
4. If a WIP-banner sits above the main content, verify the banner clears the nav AND the main content clears the banner.
