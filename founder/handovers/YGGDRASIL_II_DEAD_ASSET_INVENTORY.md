# Yggdrasil II — Dead Asset Inventory (`docs/assets/`)

**Status:** Inventory only. **Nothing is deleted by this document or the PR that carries it.**
**Date:** 2026-07-24 · **Branch:** `dev/yggdrasil-ii-staging` @ `052fb6c`
**Decision:** Founder elected *inventory-only* for the Yggdrasil II sprint. Deletion is a
separate, deliberate design-side call — see "Before deleting anything" below.

---

## Headline

| Bucket | Size | Files |
|---|---|---|
| **Referenced web assets** (live — do not touch) | 18.9 MB | — |
| **Unreferenced web assets** | **45.90 MB** | 68 |
| Design tooling checked into `docs/assets/` (scripts/READMEs/manifests) | 0.01 MB | 9 |
| **`docs/assets/` total** | 64.8 MB | — |

**71% of `docs/assets/` is referenced by no HTML, CSS, or JS in the repo.**

### One important caveat, stated up front

**This is not a page-speed problem.** Unreferenced means never fetched — a browser
loading gaiaskilltree.com does not download any of these bytes. This is **repository and
GitHub Pages hygiene**, not site latency. The real latency defects are tracked separately
(RAF gating, JSON double-fetch, render-blocking scripts, the `live.js` injector) and are
fixed in the accompanying PR.

Deleting these files from `HEAD` also does **not** shrink clone size, because the blobs
remain in history. A history rewrite (as was done in PR #1185 for PNGs and the Asset E
MP4s) would be required for that, and is explicitly **out of scope**.

---

## Method

1. Enumerated every blob under `docs/assets/` on `origin/dev/yggdrasil-ii-staging`.
2. Extracted every asset filename referenced from `docs/**/*.{html,js,css}`.
3. Matched by basename; treated anything unmatched as a candidate.
4. **Manually audited the candidate list for false positives** (see below) — the raw
   automated result was wrong in one place and is corrected here.

### Known false positive, corrected

The first automated pass flagged `docs/assets/fonts/DepartureMono-Regular.woff2` as dead.
**It is not** — it is referenced at `docs/css/styles.css:19` via `@font-face`. The
extension filter omitted `.woff2`. The font, its `LICENSE.txt`, and the `.gitkeep`
have been removed from the inventory below. No other font/webmanifest assets exist.

### Dynamic references were checked

Three call sites build asset URLs at runtime rather than as literals:

- `docs/js/plaque.js:127` → `assets/ascension-overdrive/aov4-<stem>-<tier>.webp`
- `docs/js/named-skills.js:265` and `:708` → `assets/ascension-overdrive/aov4-<stem>-badge.webp`

All are confined to the `aov4-` prefix. **Zero `aov4-*` assets appear in the dead list** —
the live Ascension Overdrive V4 set is fully intact. Everything below is V2/V3-era residue.

---

## Breakdown

| Group | Size | Files | Notes |
|---|---|---|---|
| V3 motion loops (`.mp4`) | 24.82 MB | 3 | `unique-5-loop.mp4` alone is **18.96 MB** |
| `rimuru.gif` | 5.10 MB | 1 | |
| `f-rank-*-hero.webp` | 4.48 MB | 6 | V2 rank plates |
| `Asset F/` | 4.48 MB | 6 | **byte-identical duplicates** of the row above (same blob SHAs) |
| `aov3-*` | 3.81 MB | 32 | superseded V3 generation |
| V2/V3 loose scene art | 3.16 MB | 17 | `apex-*`, `rank-*`, `ledger-*`, `unique-*` |
| other | 0.06 MB | 3 | incl. 2 unreferenced `marks/*.svg` |

### Largest single items

```
18.96 MB  docs/assets/ascension-overdrive/unique-5-loop.mp4
 5.10 MB  docs/assets/rimuru.gif
 3.67 MB  docs/assets/ascension-overdrive/unique-4-loop.mp4
 2.19 MB  docs/assets/ascension-overdrive/unique-6-loop.mp4
 1.04 MB  docs/assets/ascension-overdrive/apex-arch.webp
 0.86 MB  docs/assets/ascension-overdrive/f-rank-5-hero.webp
 0.86 MB  docs/assets/Asset F/webp/asset-f-rank-5-transcendent-plate-4k.webp
```

The `f-rank-*-hero.webp` / `Asset F/webp/asset-f-rank-*-plate-4k.webp` pairs are the same
six blobs stored twice under two paths — 4.48 MB of pure duplication independent of
whether the art is still wanted.

---

## Related: dead frontend code

`docs/js/ascension-overdrive-v2.js` (22 KB) and `docs/css/ascension-overdrive-v2.css` are
loaded by **no HTML file in the repo** — superseded by the V4 runtime. The "Asset F"
references that survive in the tree are *comments inside these two dead files*, which is
why the `f-rank-*` art scans as orphaned.

Two consequences worth noting:

- Any future grep for "is Asset F still used?" will get misleading hits from dead code.
- Deleting the V2 art without deleting the V2 JS/CSS leaves broken references in files
  that nothing loads — harmless, but confusing to the next reader. Treat them as one unit.

---

## Path hazard: `docs/assets/Asset F/` and `Asset G/`

Both directory names contain a **space**. Nothing currently builds a URL to either, so
there is no live 404. But if a future build script or CSS rule references them without
percent-encoding (`Asset%20F`), it will silently 404 on GitHub Pages. If these directories
are kept rather than deleted, **rename them without spaces**.

---

## Before deleting anything

These are design work product, not build output. Recommended sequence when the design
side is ready:

1. Confirm with the design owner that the V2/V3 generations are genuinely superseded and
   no longer needed as source material for future regeneration.
2. Delete the V2 runtime (`ascension-overdrive-v2.js` / `.css`) **together with** the V2/V3
   art, so no dangling references remain.
3. Resolve the `Asset F/` duplication either way — if the art is kept, keep exactly one
   copy and drop the space from the directory name.
4. Re-run the reference scan afterward to confirm no live asset was caught in the sweep,
   paying particular attention to the three dynamic `aov4-` call sites listed above.

Do **not** fold this into a history rewrite without a separate, explicit decision — the
last rewrite (PR #1185) required every collaborator to re-clone.
