# gaia_cli — Developer Reference

This file documents the data flow for `gaia scan` and the Local-First Naming
system. Read this before touching `scanner.py`, `localContext.py`,
`treeManager.py`, or `formatting.py`.

---

## `gaia scan` — end-to-end data flow

```
gaia scan
    │
    ├─ Phase 1: Token scan  (scanner.scan_repo_detailed)
    │   • Reads scanPaths from .gaia/config.toml
    │   • Walks every file in each path, skips excluded dirs/extensions
    │   • Regex: /[a-z][a-z0-9]*(-[a-z0-9]+)* → raw tokens {"/gaia-curate", ...}
    │   • Returns {tokens, files_scanned, paths_found, paths_missing}
    │
    ├─ Phase 2: Resolve tokens → canonical IDs  (resolver.resolve_skills)
    │   • Strips leading "/" from each token
    │   • Fuzzy-matches against registry/nodes/**/*.json skill IDs
    │   • Returns set of canonical IDs that are "detected"
    │
    ├─ Phase 3: Build LocalContext  (localContext.LocalContext.load)
    │   │   include_scan=False so it reads the registry fresh, not paths.json
    │   │
    │   ├─ load_tree(username) → owned_ids  (skill-trees/<user>/skill-tree.json)
    │   │
    │   ├─ registry/nodes/**/*.json → skill_map  (canonical skills)
    │   │   Fallback: gaia.json if nodes dir missing
    │   │
    │   └─ _build_local_first_map() → named_map  (see § Local-First Naming)
    │
    ├─ Phase 4: Display resolved skills
    │   • For each canonical ID: ctx.display_name(sid) → colored line
    │   • Own nickname → green /nickname
    │   • Other contributor → red contributor/name
    │   • Canon only → rank-colored /skill-id
    │
    ├─ Phase 5: Semantic scan  (scanner.scan_skill_mds)
    │   • Scans all known skill directories (see § Skill Search Dirs)
    │   • For each dir not already resolved: match_skill_to_canonical
    │     (Jaccard word overlap ≥ 0.20 threshold)
    │   • Prints "Installed custom skills" section with match arrows
    │
    ├─ Phase 6: Fusion detection  (combinator.get_combinations)
    │   • Finds fusion recipes where owned + detected → new extra/unique skill
    │   • Prints `gaia fuse <skill>` prompts
    │
    ├─ Phase 7: Path engine  (pathEngine.compute_paths / save_paths)
    │   • Recomputes skill unlock paths from owned + detected
    │   • diff_paths detects new near-unlocks → render_unlock_card
    │   • Writes generated-output/paths.json (used by LocalContext later)
    │
    └─ Phase 8: Tree render  (treeManager.show_tree)
        • Writes generated-output/tree.md and tree.html
```

---

## Local-First Naming — `_build_local_first_map`

`named_map` is `{canonical_skill_id → "contributor/nickname"}`.
Priority (highest wins):

```
1. Install manifest  (.gaia/install-manifest.json)
   └─ _build_install_map → _iter_manifest_refs
       Resolution chain per entry:
         a. entry.localPath (modern) → find skill.md/README.md → read genericSkillRef
         b. registry/named/<contrib>/<name>.md (if id has /)
         c. entry.sourceRef (legacy, rarely set)

2. Agent dirs  (not already covered by manifest)
   └─ _build_agent_dir_map → scan_skill_mds + match_skill_to_canonical
       • Each unmanifested dir_name → word-overlap match → canonical_id
       • Stored as "username/dirname"

3. Registry named-skills.json  (lowest priority)
   └─ _build_named_map → registry/named/**/*.md → genericSkillRef frontmatter
```

**Why this order matters:** Your installed `/gaia-curate` is a symlink to
`~/.gaia/skills/marco/gaia-skill-tree/...`. The manifest entry has
`localPath → .agents/skills/gaia-curate`. `_iter_manifest_refs` finds
`skill.md` there, reads `genericSkillRef: research`, and maps
`research → marco/gaia-curate`. So `ctx.display_name("research")` returns
`/gaia-curate` (green), not `/research`.

Without the manifest step (old bug), `_load_local_lookup` read `sourceRef`
which was never written by `install_skill()` → always empty → no nicknames.

---

## Skill Search Dirs — `_skill_search_dirs(root)`

Ordered, deduplicated by `os.path.realpath()`. Symlinks are followed
transparently (`os.path.isdir` dereferences).

```
Project-local (under root=):
  .agents/skills          ← primary (gaia, agent-agnostic)
  .claude/skills          ← Claude Code
  .antigravity/skills     ← Antigravity
  .cursor/rules           ← Cursor IDE
  .windsurf/rules         ← Windsurf IDE
  .copilot/skills         ← GitHub Copilot (speculative)
  .zed/skills             ← Zed editor (speculative)

Global user dirs:
  ~/.agents/skills
  ~/.claude/skills
  $XDG_DATA_HOME/gaia/skills  (default: ~/.local/share/gaia/skills)

Config-driven (from .gaia/config.toml):
  skillDirs = ["~/my-custom-skills", "relative/path"]
```

**Note:** `~/.gaia/skills/` is the git clone cache
(`owner/repo/` nesting) — it is intentionally NOT in this list.
The symlinks created by `install_skill()` in `.agents/skills/` already
expose those skills under the project-local dir.

**Dedup logic:** Two dirs that resolve to the same `os.path.realpath()` are
collapsed to whichever appears first (higher priority). This prevents a
symlinked `.claude/skills → .agents/skills` from producing duplicate results.

---

## Key files

| File | Role |
|---|---|
| `scanner.py` | Token scan, skill dir scan, semantic matching |
| `localContext.py` | Unified user view — named_map, owned, detected |
| `treeManager.py` | Tree I/O, `_iter_manifest_refs` for install lookup |
| `formatting.py` | Display strings — `format_skill_plain/colored`, `named_ref` param |
| `install.py` | `install_skill()` — writes `localPath` to manifest |
| `main.py` | `scan_command`, wires all phases together |
| `pathEngine.py` | Unlock-path graph compute; produces `paths.json` |
| `resolver.py` | Token → canonical ID matching |
| `combinator.py` | Fusion recipe detection |

---

## `format_skill_plain` / `format_skill_colored`

Always pass `named_ref=ctx.named_ref(sid)`, not `named_contributor=`.

```python
# CORRECT
format_skill_plain(sid, named_ref=ctx.named_ref(sid), local_user=username)
# → "/gaia-curate"  (own), or "marco/gaia-curate"  (other)

# WRONG (legacy — passes canonical ID as the nickname slug)
format_skill_plain(sid, named_contributor="marco")
# → "marco/research"  (canonical ID leaked as nickname)
```

`named_contributor` is kept as a backward-compat fallback for callers that
haven't been updated yet. Do not introduce new uses of it.

---

## `--global` flag for `gaia skills install`

**Currently a stub.** `install_skill()` always calls `get_repo_skills_dir()`
which returns `.agents/skills` (or `.claude/skills`). The `--global` argparse
flag is parsed but ignored. There is no wired global install destination yet.

When wiring it up, the natural target would be `~/.agents/skills/<name>` (with
`~/.gaia/skills/<owner>/<repo>` continuing as the clone cache).
