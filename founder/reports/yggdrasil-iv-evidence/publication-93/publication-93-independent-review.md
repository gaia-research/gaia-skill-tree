## Files Reviewed
- `scripts/build_docs.py` (lines 1716–1765)
- `tests/test_publication_og_coverage.py` (lines 1–78)

## Critical (must fix)
*None.* The repair correctly addresses the 19 orphan PNG coverage failure in strict rehearsal mode while preserving ordinary builder behavior.

## Warnings (should fix)
- `tests/test_publication_context.py:354` - Parent acceptance blocker: `test_real_bounded_builders_double_replay_and_surface_corruption` was excluded by the author due to timeout and was intentionally not executed in this bounded review (parent orchestrator owns combined regression and full-corpus two-root replay). Certification must remain blocked until parent replay completes green.

## Suggestions (consider)
- `scripts/build_docs.py:1756` - When `not drifts` is true and orphan PNGs are deleted (`removed_pngs` non-empty), `build_og_cards` returns early at line 1757 without reaching handle directory pruning at lines 1774–1777 (`for handle_dir in committed.iterdir(): ... handle_dir.rmdir()`). While `publication_parity._tree` checks only files (`p.is_file()`) and git ignores empty directories, pruning empty handle subdirectories after unlinking orphan PNGs would prevent leaving empty directories on disk.

---

### Executed Checks
Using the genuine CairoSVG interpreter `/data/data/com.termux/files/home/gaia-skill-tree/.gaia/yggdrasil-iv/runtime/publication-venv/bin/python` (unresolved symlink, Python 3.14.6, pytest 9.1.1):
1. `tests/test_publication_og_coverage.py`: **3 passed in 3.80s**
   - `test_rehearsal_removes_orphan_png_and_refreshes_real_render`: Verified genuine CairoSVG PNG rendering (`\x89PNG\r\n\x1a\n`), orphan PNG removal, stale raster overwrite (`b"stale"` refreshed), ordinary builder non-destructive retention, and parity oracle failure on semantic/coverage mismatch.
   - `test_rehearsal_rejects_missing_raster[False]` & `[True]`: Verified strict rehearsal raises `RuntimeError("rehearsal cannot certify incomplete OG PNG coverage...")` when rasterization fails, refusing to accept missing or stale rasters.
2. `tests/test_og_medallion_raster.py`: **1 passed in 0.64s** (verified OG medallion WebP to PNG data URI transcoding).

### Code Audit Verification
- **Strict 1-to-1 Raster Coverage (`scripts/build_docs.py:1721–1727`)**: Before touching committed files, strict rehearsal asserts `candidate_pngs == expected_pngs` where `expected_pngs` is every generated SVG with `.png` suffix. Incomplete rasterization fails closed with `RuntimeError`.
- **Orphan PNG Removal & Stale-Byte Refresh (`scripts/build_docs.py:1738–1746`)**: Strict rehearsal computes `removed_pngs = committed_pngs - candidate_pngs` and unlinks all orphan PNGs (including those with no current SVG). Every raster in `candidate_pngs` is unconditionally overwritten via `destination.write_bytes()`, guaranteeing no stale bytes survive.
- **Nested Path Safety (`scripts/build_docs.py:1722, 1739, 1744`)**: `p.relative_to(out_dir)` and `destination.parent.mkdir(parents=True, exist_ok=True)` properly preserve and construct nested directories (e.g. `handle/slug.png`).
- **Ordinary Builder Behavior Preserved (`scripts/build_docs.py:1720, 1736, 1756`)**: When `_STRICT_REHEARSAL` is false, strict checks and raster deletions are skipped; non-rasterizing environments continue to run without error; return value is `False` when no SVGs drift.
- **Check / No-Check Return Consistency (`scripts/build_docs.py:1756–1766`)**: Both check and write modes return identical booleans (`bool(removed_pngs)` on no drift; `True` on drift). In strict rehearsal, `args.check` is disallowed by `main()` CLI validation.
- **Parity Oracle Unchanged (`scripts/publication_parity.py:164–167`)**: The oracle was untouched; strict `_tree(root / "docs/og", target / "og", ".png")` remains the source-of-truth gate.
- **Outer Runtime Gate Reachability**: Confirmed via `publication-368-runtime-gate-counterprobe.json` that the actual outer gate bootstrap in `publication_parity.check_semantic_parity` invokes `activate_rehearsal_context(..., inherit_runtime_check=False)`, properly rejecting runtime mismatches.

### Unverified Requirements
- Full-corpus two-root replay and combined regression suite (active under parent).
- Bounded double-replay fixture `test_real_bounded_builders_double_replay_and_surface_corruption` (unverified; pending parent run).
- Publication certification, founder visual evaluation, live issuer attestations, and release sign-off (out of scope).

## Summary
**Verdict: SCOPED PASS** for commit range `36883266812824dc49de48ffe1bda757d22d45ce..93fb731ea8842ef07fd703bb0b58dea944a83a0d`. The repair correctly enforces strict 1:1 SVG-to-PNG raster coverage, removes orphan rasters, refreshes stale PNG bytes, and preserves ordinary builder workflows without modifying the parity oracle. Full publication acceptance remains conditioned on completion of parent orchestrator regression and two-root replay.

🌱 graft saved ~300,655 tokens this turn (5 calls).