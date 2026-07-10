# Design Entrypoints — plan before you ship

**Every new user-facing page or section MUST plan its entrypoints as part of the design pass, not reactively.** Shipping `/benchmarks/`, `/named/`, `/graph/`, or any new section without a way for a homepage visitor to reach it is a broken feature — the page might as well not exist. This rule is codified after the 2026-07-06 Sprint D W4 review, where `/benchmarks/` shipped with no homepage link, no docs/index.html tile, and no nav-drawer entry, and the gap only surfaced when the operator noticed there was "literally no way to get there."

Before opening a PR that adds a new page (or a substantively new section on an existing page), the design must enumerate:

1. **Main nav (`docs/js/site-nav.js`)** — does the section belong in the top-level nav? If yes, add it to the `MOUNTS` array AND the visible nav link list AND the mobile drawer. If no, justify it in the PR body.
2. **Footer (`docs/js/site-footer.js`)** — is the section a peer of existing footer categories (product, docs, community)? Add it there or justify the exclusion.
3. **Homepage (`docs/index.html`)** — does the section deserve a tile, CTA, or prose mention on the landing page? For anything that concerns Trust Magnitude, evidence, benchmarks, badges, or measurement, the answer is almost always yes.
4. **`docs/js/mounts.js`** — every new `docs/<section>/` subdirectory that uses site-nav must be added to `window.GAIA_MOUNTS`. CI Guard D enforces this, but plan it upfront so you're not scrambling at PR time.
5. **Cross-page references** — if the new content is discovered from a specific existing surface (e.g. skill explorer → benchmark evidence rows), wire the link at both ends in the same PR.
6. **Cache-busting** — every new HTML page must be registered in `build_html_cache_busting()` in `scripts/build_docs.py`. Never manually patch `?v=` strings.

The PR description must include an "Entrypoints" section listing which of the above were touched (or explicitly waived, with justification). Design-review agents check for this section; PRs without it get bounced regardless of code quality.

**Rule of thumb:** if a user landing on `gaiaskilltree.com/` with fresh eyes cannot discover the new feature within 30 seconds of scanning, the entrypoints are broken.
