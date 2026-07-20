# Scout D — Outer public pages design-intent review (2026-07-20)

Surfaces: Priority 1 — `/about.html`, `/meta.html`, `/codex.html`, `/codex/trust-methodology.html`, `/starless.html`. Priority 2 — `/api/`, `/benchmarks/`, `/evidence/`, `/trending/`, `/trust/` + `/trust/ledger/`.
Viewports: 1280x900 (desktop) and 390x844 (mobile). Playwright 1.61.1 against `http://localhost:8090/`.
Screenshots (not committed): scoutA/ — `outer-*` full-page, `scr-*` scrolled section shots.

Lens: designer's eye — layout/overlap/hierarchy/color-in-context/readability/empty-broken states. Token-vs-hex bookkeeping out of scope. Watching for dead `--tier-extra`(purple)/`--tier-ultimate`(amber) symptoms (accents rendering cyan/unstyled), rank-vocab defects (4★ reading "Extra"), and red origin marks (should be gold).

Global: **no horizontal overflow at 390px on any page** (scrollWidth == innerWidth everywhere). Nav renders at ~60px on every page except `/api/` (see finding). Only console noise is one `net::ERR_CONNECTION_REFUSED` (dev `localhost:8400/live.js` reload script) plus a few `/api/**.json` 404 data fetches — none produce a visible defect except where noted.

## Findings

| Surface | Viewport | What looks wrong | Evidence (screenshot + selector) | Suspected cause | Severity | Effort |
|---|---|---|---|---|---|---|
| /about.html — contributor quote blocks | desktop + mobile | Each pull-quote has a stray gold closing-quote glyph `"` dangling on its own line **below** the byline (under "— PAUL BAKAUS", "— MATT POCOCK", "— GARRY TAN"), reading as an orphaned floating character rather than a paired quotation mark. | `scr-about-d-y2300.png`, `outer-about-mobile-full.png`; `.about-quote / blockquote::after` | Decorative closing-quote pseudo-element positioned absolutely/after the cite with wrong offset, so it drops to a new line. | nit | easy-win |
