# `docs/assets/` — Unreferenced File List

**Status:** List only. Nothing deleted. Founder reviews and decides what stays.
**Date:** 2026-07-25 · **Branch:** `dev/yggdrasil-ii-staging`

## How this was produced

Every blob under `docs/assets/` was matched by **basename** against every asset
filename referenced in `docs/**/*.{html,js,css}`. Anything unmatched is listed below.

## Read this before acting on the list

The match is a heuristic and **will contain false positives.** Known limits:

- Only these extensions were scanned for references: `webp png jpg jpeg gif mp4 svg avif`.
  A confirmed miss from this: `DepartureMono-Regular.woff2` is referenced at
  `docs/css/styles.css:19` via `@font-face` but was absent from the reference set.
  It has been removed from the list; other non-scanned types may be similarly wrong.
- Files referenced only from dead code scan as unreferenced. `docs/js/ascension-overdrive-v2.js`
  and its CSS are loaded by no HTML file, so anything only they mention appears here.
- Assets whose URLs are built at runtime are matched only where the literal filename
  appears. Three dynamic call sites exist, all on the `aov4-` prefix
  (`plaque.js:127`, `named-skills.js:265`, `named-skills.js:708`). No `aov4-` file
  appears below.
- `.py`, `.md`, `.json`, `.txt` entries are design tooling, not web assets.

Some entries are certainly worth keeping. Treat this as a starting inventory, not a delete list.

## Note on impact

Unreferenced assets are never fetched by a browser, so removing them does not affect
page speed. This is repository and Pages-storage weight. Deleting from `HEAD` also
does not reduce clone size — the blobs remain in history.

## List

**80 files · 45.93 MB**

| MB | Path |
|---:|---|
| 18.96 | `docs/assets/ascension-overdrive/unique-5-loop.mp4` |
| 5.10 | `docs/assets/rimuru.gif` |
| 3.67 | `docs/assets/ascension-overdrive/unique-4-loop.mp4` |
| 2.19 | `docs/assets/ascension-overdrive/unique-6-loop.mp4` |
| 1.04 | `docs/assets/ascension-overdrive/apex-arch.webp` |
| 0.86 | `docs/assets/ascension-overdrive/f-rank-5-hero.webp` |
| 0.86 | `docs/assets/Asset F/webp/asset-f-rank-5-transcendent-plate-4k.webp` |
| 0.82 | `docs/assets/ascension-overdrive/f-rank-2-hero.webp` |
| 0.82 | `docs/assets/Asset F/webp/asset-f-rank-2-named-plate-4k.webp` |
| 0.79 | `docs/assets/ascension-overdrive/f-rank-3-hero.webp` |
| 0.79 | `docs/assets/Asset F/webp/asset-f-rank-3-evolved-plate-4k.webp` |
| 0.73 | `docs/assets/ascension-overdrive/f-rank-4-hero.webp` |
| 0.73 | `docs/assets/Asset F/webp/asset-f-rank-4-hardened-plate-4k.webp` |
| 0.72 | `docs/assets/ascension-overdrive/f-rank-1-hero.webp` |
| 0.72 | `docs/assets/Asset F/webp/asset-f-rank-1-awakened-plate-4k.webp` |
| 0.55 | `docs/assets/ascension-overdrive/f-rank-6-hero.webp` |
| 0.55 | `docs/assets/Asset F/webp/asset-f-rank-6-apex-plate-4k.webp` |
| 0.28 | `docs/assets/ascension-overdrive/aov3-unique-impossible-terminal-mobile.webp` |
| 0.28 | `docs/assets/ascension-overdrive/aov3-unique-impossible-terminal.webp` |
| 0.24 | `docs/assets/ascension-overdrive/unique-6-impossible.webp` |
| 0.24 | `docs/assets/ascension-overdrive/aov3-astrolabe-substrate.webp` |
| 0.24 | `docs/assets/ascension-overdrive/unique-5-ultimate.webp` |
| 0.21 | `docs/assets/ascension-overdrive/rank-4-hardened.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-3-evolved-card.webp` |
| 0.17 | `docs/assets/ascension-overdrive/unique-4.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-2-named.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-5-ultimate.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-1-awakened.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-4-extra-card.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-5-ultimate-card.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-1-awakened-card.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-6-apex-card.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-2-named-card.webp` |
| 0.17 | `docs/assets/ascension-overdrive/aov3-suite-stamp-6-apex.webp` |
| 0.16 | `docs/assets/ascension-overdrive/aov3-astrolabe-substrate-mobile.webp` |
| 0.16 | `docs/assets/ascension-overdrive/apex-component-classical-stele.webp` |
| 0.16 | `docs/assets/ascension-overdrive/apex-component-grand-arch.webp` |
| 0.15 | `docs/assets/ascension-overdrive/aov3-suite-plate-6-apex.webp` |
| 0.15 | `docs/assets/ascension-overdrive/aov3-suite-stamp-4-extra.webp` |
| 0.15 | `docs/assets/ascension-overdrive/aov3-suite-stamp-3-evolved.webp` |
| 0.14 | `docs/assets/ascension-overdrive/rank-3-evolved.webp` |
| 0.12 | `docs/assets/ascension-overdrive/rank-5-ultimate.webp` |
| 0.12 | `docs/assets/ascension-overdrive/rank-2-named.webp` |
| 0.11 | `docs/assets/ascension-overdrive/aov3-y-fork.webp` |
| 0.11 | `docs/assets/ascension-overdrive/apex-component-column-crowned.webp` |
| 0.11 | `docs/assets/ascension-overdrive/apex-component-column-finial.webp` |
| 0.09 | `docs/assets/ascension-overdrive/aov3-unique-stamp-6-impossible.webp` |
| 0.09 | `docs/assets/ascension-overdrive/aov3-unique-stamp-4.webp` |
| 0.09 | `docs/assets/ascension-overdrive/aov3-suite-plate-6-apex-mobile.webp` |
| 0.09 | `docs/assets/ascension-overdrive/apex-component-pillar-with-plant.webp` |
| 0.08 | `docs/assets/ascension-overdrive/aov3-y-fork-mobile.webp` |
| 0.08 | `docs/assets/ascension-overdrive/apex-component-stele-with-foliage.webp` |
| 0.08 | `docs/assets/ascension-overdrive/ledger-texture.webp` |
| 0.07 | `docs/assets/ascension-overdrive/aov3-unique-stamp-5-ultimate.webp` |
| 0.06 | `docs/assets/Asset G/outputs/asset-g-haze.webp` |
| 0.05 | `docs/assets/ascension-overdrive/rank-1-awakened.webp` |
| 0.05 | `docs/assets/ascension-overdrive/ledger-texture-variant.webp` |
| 0.03 | `docs/assets/ascension-overdrive/aov3-unique-stamp-4-mobile.webp` |
| 0.02 | `docs/assets/ascension-overdrive/aov3-unique-stamp-6-impossible-mobile.webp` |
| 0.02 | `docs/assets/ascension-overdrive/aov3-unique-stamp-5-ultimate-mobile.webp` |
| 0.02 | `docs/assets/ascension-overdrive/aov3-suite-stamp-4-extra-badge.webp` |
| 0.02 | `docs/assets/fonts/DepartureMono-Regular.woff2` |
| 0.02 | `docs/assets/ascension-overdrive/aov3-suite-stamp-3-evolved-badge.webp` |
| 0.02 | `docs/assets/ascension-overdrive/aov3-suite-stamp-6-apex-badge.webp` |
| 0.02 | `docs/assets/ascension-overdrive/aov3-suite-stamp-5-ultimate-badge.webp` |
| 0.01 | `docs/assets/ascension-overdrive/aov3-suite-stamp-2-named-badge.webp` |
| 0.01 | `docs/assets/ascension-overdrive/aov3-suite-stamp-1-awakened-badge.webp` |
| 0.00 | `docs/assets/Asset G/scripts/make_asset_g_haze.py` |
| 0.00 | `docs/assets/Asset D/remove_white_borders_helper.py` |
| 0.00 | `docs/assets/Asset F/manifest.json` |
| 0.00 | `docs/assets/Asset G/scripts/audit_asset_g.py` |
| 0.00 | `docs/assets/Asset G/README.md` |
| 0.00 | `docs/assets/fonts/DepartureMono-LICENSE.txt` |
| 0.00 | `docs/assets/fonts/.gitkeep` |
| 0.00 | `docs/assets/marks/diamond-seal-preview.svg` |
| 0.00 | `docs/assets/Asset G/manifest.json` |
| 0.00 | `docs/assets/Asset F/README.md` |
| 0.00 | `docs/assets/Asset G/scripts/asset_g_css_snippet.css` |
| 0.00 | `docs/assets/marks/diamond-seal-favicon.svg` |
| 0.00 | `docs/assets/Asset G/scripts/asset_g_parallax_snippet.js` |
