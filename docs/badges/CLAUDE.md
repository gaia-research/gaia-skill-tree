# docs/badges — agent notes

## Architecture (the part that bites)

Real badge SVGs live at **`docs/badges/_assets/<handle>/<file>.svg`** (3-segment path,
served as static assets). The public README badge URL is
**`/badges/<handle>/<file>.svg`** (2-segment path) — that route has *no* static asset, so
the Cloudflare Worker at `worker/index.js` handles it, validates `?repo=` against
`registry.json`, then internally fetches the real SVG from `_assets/`.

This split is intentional and load-bearing — see the long doc-comment at the top of
`worker/index.js` for the full reasoning. **Do not** create files at the 2-segment public
path; that would shadow the worker and bypass `?repo=` validation.

### `docs/.nojekyll` is load-bearing

Production traffic for `gaia.tiongson.co` is served by **GitHub Pages** (Cloudflare is
a CDN/proxy in front; the worker config in `wrangler.toml` is a separate deploy lane
that isn't currently in the request path — confirm with `curl -sI https://gaia.tiongson.co/`
and look for the `X-Github-Request-Id` / `Via: 1.1 varnish` headers).

GitHub Pages runs Jekyll by default, and **Jekyll silently strips any path segment that
starts with `_`**. Without `docs/.nojekyll`, the entire `_assets/` directory is dropped
from the deploy and every Honesty-Mode-ON URL 404s. That cascades into:

- `exists()` HEAD probes return false → page says "No badges yet for @<handle>".
- `<img src="./_assets/...">` 404s → live strip + variant cards + README simulator
  show broken images.
- `chkSeal` flip swaps to `*-seal.svg` URLs that also 404 → "Hide Gaia breaks rank.svg".

**Do not delete `docs/.nojekyll`.** If `_assets/` ever stops resolving in production,
that's the first thing to check (`curl -sI https://gaia.tiongson.co/badges/_assets/<handle>/handle.svg`
should return 200, not 404 with a GitHub-Pages 404 body).

## Honesty Mode toggle (the page-visible switch)

Without the Worker (local dev, any preview deploy that doesn't run the worker, or any
caller hitting the static `_assets/` route directly), the validated 2-segment URL 404s.
That's why the page once said **"no badges yet"** for handles that clearly had badges:
the JS was HEAD-checking the worker route.

The fix has two parts and both ship in `index.html`:

1. **Detection always probes `_assets/`** — `generate()` HEAD-checks
   `./_assets/<handle>/<file>.svg`, the real static path, so detection works without
   the worker. Local previews (live strip, variant cards, README simulator, per-row
   thumbnails) also read from `_assets/` for the same reason.

2. **Honesty Mode** is a **build-time** toggle — a single `HONESTY_MODE` constant
   inside `index.html`'s script block. There is intentionally no runtime UI to
   change it; the pill at the top of the hero is a **read-only indicator** so any
   viewer can see which mode the page is in. **Flip via PR.**

   | Mode | URL emitted into copied markdown | Where it works |
   |---|---|---|
   | **`HONESTY_MODE = true`** *(current default)* | `https://gaia.tiongson.co/badges/_assets/<handle>/<file>.svg?repo=<repo>` | Anywhere — bypasses worker, `?repo=` still included for camo caching |
   | **`HONESTY_MODE = false`** | `https://gaia.tiongson.co/badges/<handle>/<file>.svg?repo=<repo>` | Only when worker is deployed; enforces `?repo=` validation |

   The pill renders green with state `ON` when `HONESTY_MODE === true` and slate
   with `OFF` otherwise. Both the `data-state` attribute on the chip and the
   inner `.bd-honesty-state` text are painted from the constant on page load —
   keep those two lines in sync if you rename the indicator.

### Why no runtime/localStorage toggle?

Earlier iteration shipped a click-to-toggle pill backed by `localStorage`. That
let one viewer flip the page into a state nobody else could see, which made it
impossible to tell from a screenshot whether a copied URL was actually going
through the worker. A build-time constant means: *the URL you see copied is the
URL everyone else gets*. No surprises across browsers, sessions, or PR previews.

### When to flip Honesty Mode OFF

Flip `HONESTY_MODE` to `false` in `index.html` (and ship the PR) when **all** of:
- The Cloudflare Worker is deployed and `run_worker_first = true` is set.
- You actually want `?repo=` binding to gate badges (i.e., a stale README in a
  non-approved repo should render the "validating…" SVG instead of the real badge).
- You're rolling out the registered-repo flow (Path A).

Until then, leave it `true`. Worker-validated URLs in unhandled environments produce
broken images; the static `_assets/` path doesn't.

### Removing the toggle later

This is a *temporary* mitigation — the long-term answer is to keep the worker route
as the canonical embed URL once the worker deploy is rock-solid. To rip out the
toggle:
1. Delete the `bd-honesty-pill` block in `index.html` (and its CSS).
2. Delete the `HONESTY_MODE` constant, the indicator-paint lines, and
   `badgeMarkdownUrl()` helper.
3. Restore `renderRows()` to emit `${BASE}/badges/${handle}/${sealed}${q}` directly.
4. Keep the `_assets/` detection paths and local previews — those should stay
   regardless, because the page still needs to render before the worker runs.

## Files in this directory

| Path | What |
|---|---|
| `index.html` | The badge generator page. Hand-maintained. |
| `registry.json` | Generated. Approved repos + named-skill list per contributor. |
| `_assets/<handle>/*.svg` | Generated. The real badge SVGs (each has `*.svg` and `*-seal.svg`). |
| `samples/rank-N{,-seal}.svg` | Generated. Empty-state rank sampler. |
| `not-found.svg` | Hand-maintained. The "validating…" SVG returned on `?repo=` mismatch. |
| `powered-by-gaia.svg` | Hand-maintained. The generic, no-handle-required badge. |

`registry.json`, `_assets/`, and `samples/` are regenerated by `gaia docs build`. Don't
hand-edit them.
