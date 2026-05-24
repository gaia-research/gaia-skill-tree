## 2024-05-19 - Layout thrashing in canvas interaction
**Learning:** The interactive skill graph canvas (`docs/js/skill-graph.js`) suffered from a severe layout thrashing bottleneck. The `mousemove` event handler was calling `canvas.getBoundingClientRect()` on every single trigger to calculate normalized mouse coordinates. Because `getBoundingClientRect()` is a synchronous layout operation, it forced the browser to recalculate style and layout constantly while the user moved the mouse over the graph, drastically reducing framerate. This is especially impactful in this codebase because the graph relies on a highly fluid 3D visualization.
**Action:** Always cache bounding rects for interactive canvases and invalidate the cache only when necessary (e.g., on `window` `resize` and `scroll` events, or just before a drag interaction via `mousedown`), instead of querying it continuously during high-frequency events like `mousemove`.

## 2024-05-21 - Layout thrashing in graph render loops
**Learning:** During the rendering of flowcharts/DAGs in `docs/js/named-skills.js` and `docs/js/skill-explorer.js`, the code was calling `getBoundingClientRect()` for the source and target nodes inside an `.forEach` loop over all edges, then subsequently mutating the DOM by writing generated SVG strings or appending paths. Interleaving DOM reads (`getBoundingClientRect`) with DOM writes (or style recalculations) within a loop causes "layout thrashing" as the browser is forced to synchronously recalculate layout on each iteration. For complex graphs, this heavily blocks the main thread.
**Action:** Always batch DOM reads and writes. Pre-calculate all node bounding rects in a single, separate pass before entering loops that construct paths or mutate the DOM. Use `DocumentFragment` to batch insertions.

## 2024-05-25 - Layout thrashing in CLI Python graph render
**Learning:** The generated HTML graph in `src/gaia_cli/graph.py` also contained a layout thrashing issue in its interactive script. Inside `handlePointerMove`, it was executing `canvas.getBoundingClientRect()` on every `mousemove`. Similar to the issue found in `docs/js/skill-graph.js`, calling layout-triggering methods on high-frequency events tanks performance.
**Action:** Consistently apply layout thrashing mitigations across all generated and static assets. Always cache the bounding rect on initial fetch and only invalidate it during window resizing, scrolling, or specific user interactions (e.g., `mousedown`).

## 2026-05-24 - Optimize _build_named_map using pre-compiled index
**Learning:** File system metadata reading inside a loop `sorted(named_dir.glob("*/*.md"))` when repeatedly called causes I/O bottlenecks and O(N^2) overheads in tightly executed command paths.
**Action:** Caching these files into a pre-compiled JSON index and executing the lookup logic significantly improves baseline speed (3x+ improvement).

## 2025-03-09 - Optimize `meta_merge_command` Named Skill Ref Update
**Performance Insight:** In Python, avoiding nested loops (O(N*M)) over files and expensive operations like parsing JSON/Markdown from disk is crucial. `meta_merge_command` checked every possible merge source `source_id` against every named skill file independently, resulting in redundant disk reads (`_parse_md`) equal to the number of source IDs for each file.
**Action:** Replaced the nested loop with a single pass over the files. By loading the source IDs into a set `sources_set`, each file is parsed exactly once. Its `genericSkillRef` is then checked against the `sources_set` (an O(1) operation). This improved local benchmarking for merging 100 sources into 1000 files from ~22s down to ~0.4s (a 50x speedup). Always load match targets into sets and perform parsing once per file.

## 2026-05-24 - Optimize load_canonical_skills with lru_cache
**Learning:** The `load_canonical_skills` method was being called from `resolve_skills`, which in turn gets called repeatedly by tools relying on path resolution and graph parsing. Because `resolve_skills` gets called potentially 100+ times during these processes, `load_canonical_skills` incurred an O(N) execution that repeated every call causing an O(N^2) file I/O pattern. Wrapping it in `@functools.lru_cache(maxsize=1)` reduced the time by 98.6%.
**Action:** Use memoization decorators like `@functools.lru_cache` for static configuration parsing or repeated file I/O access in loops.

<<<<<<< HEAD
## 2026-05-24 - Optimize _build_named_map using pre-compiled index
**Learning:** File system metadata reading inside a loop `sorted(named_dir.glob("*/*.md"))` when repeatedly called causes I/O bottlenecks and O(N^2) overheads in tightly executed command paths.
**Action:** Caching these files into a pre-compiled JSON index and executing the lookup logic significantly improves baseline speed (3x+ improvement).

## 2025-03-09 - Optimize `meta_merge_command` Named Skill Ref Update
**Performance Insight:** In Python, avoiding nested loops (O(N*M)) over files and expensive operations like parsing JSON/Markdown from disk is crucial. `meta_merge_command` checked every possible merge source `source_id` against every named skill file independently, resulting in redundant disk reads (`_parse_md`) equal to the number of source IDs for each file.
**Action:** Replaced the nested loop with a single pass over the files. By loading the source IDs into a set `sources_set`, each file is parsed exactly once. Its `genericSkillRef` is then checked against the `sources_set` (an O(1) operation). This improved local benchmarking for merging 100 sources into 1000 files from ~22s down to ~0.4s (a 50x speedup). Always load match targets into sets and perform parsing once per file.

## 2026-05-24 - Optimize load_canonical_skills with lru_cache
**Learning:** The `load_canonical_skills` method was being called from `resolve_skills`, which in turn gets called repeatedly by tools relying on path resolution and graph parsing. Because `resolve_skills` gets called potentially 100+ times during these processes, `load_canonical_skills` incurred an O(N) execution that repeated every call causing an O(N^2) file I/O pattern. Wrapping it in `@functools.lru_cache(maxsize=1)` reduced the time by 98.6%.
**Action:** Use memoization decorators like `@functools.lru_cache` for static configuration parsing or repeated file I/O access in loops.

## 2026-05-24 - CLI stats loading performance
**Learning:** The CLI stats command (`_iter_named_skill_metadata` in `stats.py`) was performing synchronous O(N^2) file I/O and frontmatter parsing using `root.rglob("*.md")` on the `registry/named` directory. This is incredibly slow and forces an expensive file I/O for every single metadata file, leading to significant degradation in response times.
<<<<<<< HEAD
**Action:** When working with registry data in the Python CLI, always use the pre-compiled JSON indices (like `named-skills.json`) instead of querying the filesystem directly via glob and individually parsing frontmatter. Cache mechanisms via existing endpoints (`named_skills_index_path`) drastically improve performance (e.g. from 1.66s to 0.20s for iterations).
<<<<<<< HEAD
=======
## 2026-05-24 - CLI stats loading performance
**Learning:** The CLI stats command (`_iter_named_skill_metadata` in `stats.py`) was performing synchronous O(N^2) file I/O and frontmatter parsing using `root.rglob("*.md")` on the `registry/named` directory. This is incredibly slow and forces an expensive file I/O for every single metadata file, leading to significant degradation in response times.
**Action:** When working with registry data in the Python CLI, always use the pre-compiled JSON indices (like `named-skills.json`) instead of querying the filesystem directly via glob and individually parsing frontmatter. Cache mechanisms via existing endpoints (`named_skills_index_path`) drastically improve performance (e.g. from 1.66s to 0.20s for iterations).
>>>>>>> 3bf7bb05 (⚡ Optimize stats command to use named-skills index (#424))
=======
>>>>>>> origin/main
<<<<<<< HEAD
>>>>>>> 141c3495 (⚡ Optimize load_canonical_skills to reduce file I/O overhead (#431))
=======
>>>>>>> origin/main
>>>>>>> 2ad6c63c (perf: optimize named skill reference updates in meta_merge_command (#432))
=======
**Action:** When working with registry data in the Python CLI, always use the pre-compiled JSON indices (like `named-skills.json`) instead of querying the filesystem directly via glob and individually parsing frontmatter. Cache mechanisms via existing endpoints (`named_skills_index_path`) drastically improve performance (e.g. from 1.66s to 0.20s for iterations).
>>>>>>> 18d94fd5 (⚡ Optimize _build_named_map using pre-compiled index (#426))
