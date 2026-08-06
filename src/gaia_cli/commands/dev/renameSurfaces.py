"""Reference-surface updates for `gaia dev rename` (#1456).

Before this module, `gaia dev rename` moved the registry node / named `.md`
file and repointed a short frontmatter list, leaving suite manifests, user
trees, and prose to be patched by hand (PR #1452). Structural JSON edits
below are exact whole-string matches; prose edits are whole-token matches
that skip changelog/history sections; anything left over is printed as a
checklist rather than silently rewritten.
"""

import json
import re
from pathlib import Path

from gaia_cli.timeline import append_skill_tree_event

# Regenerated wholesale by `gaia dev docs` — reported as out of scope, not
# rewritten, since the next docs build overwrites any edit made here.
GENERATEDREFPREFIXES = (
    "docs/graph/", "docs/api/", "docs/og/", "docs/badges/", "docs/u/",
    "docs/tree.md", "registry/gaia.json", "registry/named-skills.json",
)

SCANROOTS = ("registry", "docs", "skill-trees")
SCANEXTRAFILES = ("README.md",)
SCANSKIPDIRS = frozenset(
    {".git", ".gaia", ".venv", "venv", "node_modules", "__pycache__", "generated-output", "graphify-out"}
)

CHANGELOGHEADING = re.compile(r"^#{1,6}\s+.*(changelog|history)", re.IGNORECASE)
MARKDOWNHEADING = re.compile(r"^(#{1,6})\s")

# (globRoot, glob, skipKeys, proseKeys, namedOnly)
JSONSURFACES = (
    ("registry/suites", "**/*.json", frozenset(), (), True),
    ("skill-trees", "*/skill-tree.json", frozenset({"unlockedIn"}), ("details",), False),
)


def idPattern(skillId: str) -> re.Pattern:
    """Whole-token matcher: `skill-old` must not match `skill-older`."""
    return re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(skillId) + r"(?![A-Za-z0-9_-])")


def replaceRefsDeep(node, oldId: str, newId: str, *, skipKeys=frozenset(), proseKeys=()):
    """Walk a JSON tree replacing references to `oldId`. Exact whole-string
    equality everywhere, except dict values under a key in `proseKeys` (a
    token-bounded substring replace instead — absorbs the old
    `rewriteTimelineDetails` helper) and keys in `skipKeys` (left untouched,
    e.g. `unlockedIn`, an owner/repo string that could equal a named id).
    Returns `(node, changed)`.
    """
    if isinstance(node, str):
        return (newId, True) if node == oldId else (node, False)
    if isinstance(node, list):
        changed = False
        out = []
        for item in node:
            value, itemChanged = replaceRefsDeep(item, oldId, newId, skipKeys=skipKeys, proseKeys=proseKeys)
            out.append(value)
            changed = changed or itemChanged
        return out, changed
    if isinstance(node, dict):
        changed = False
        out = {}
        pattern = None
        for key, value in node.items():
            if key in skipKeys:
                out[key] = value
            elif key in proseKeys and isinstance(value, str):
                pattern = pattern or idPattern(oldId)
                rewritten = pattern.sub(newId, value)
                out[key] = rewritten
                changed = changed or (rewritten != value)
            else:
                out[key], valueChanged = replaceRefsDeep(value, oldId, newId, skipKeys=skipKeys, proseKeys=proseKeys)
                changed = changed or valueChanged
        return out, changed
    return node, False


def rewriteProseRefs(text: str, oldId: str, newId: str):
    """Rewrite whole-token `oldId` references in markdown prose. Returns
    `(text, rewritten, changelogHits)` — changelog/history sections are left
    alone (they record what the skill was called at the time) and their hit
    count is disclosed rather than hidden.
    """
    pattern = idPattern(oldId)
    out, rewritten, changelogHits = [], 0, 0
    inChangelog, changelogDepth = False, 0

    for line in text.split("\n"):
        heading = MARKDOWNHEADING.match(line)
        if heading:
            depth = len(heading.group(1))
            if CHANGELOGHEADING.match(line):
                inChangelog, changelogDepth = True, depth
            elif inChangelog and depth <= changelogDepth:
                inChangelog = False
        hits = len(pattern.findall(line))
        if hits and inChangelog:
            changelogHits += hits
            out.append(line)
        elif hits:
            out.append(pattern.sub(newId, line))
            rewritten += hits
        else:
            out.append(line)

    return "\n".join(out), rewritten, changelogHits


def rewriteJsonSurfaces(registryPath, oldId: str, newId: str) -> list[str]:
    """Repoint suite manifests and user trees, driven by `JSONSURFACES`.

    `registry/suites` only runs for named-skill renames (`"/" in oldId`) —
    a bare generic slug can collide with a suite manifest's own bare `id`.
    `skill-trees` logs a `rename` timeline event on every tree it touches —
    the point of the sibling schema PR that legalizes the action.
    """
    messages: list[str] = []
    rootPath = Path(registryPath)

    for globRoot, glob, skipKeys, proseKeys, namedOnly in JSONSURFACES:
        if namedOnly and "/" not in oldId:
            continue
        base = rootPath / globRoot
        if not base.exists():
            continue

        for path in sorted(base.glob(glob)):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            updated, changed = replaceRefsDeep(data, oldId, newId, skipKeys=skipKeys, proseKeys=proseKeys)
            if not changed:
                continue

            path.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            messages.append(f"Updated references in {path}")

            if globRoot == "skill-trees":
                username = path.parent.name
                append_skill_tree_event(
                    username, newId, "rename", f"Renamed from {oldId} to {newId}", registry_path=registryPath,
                )
                messages.append(f"Logged rename timeline event for {username}")

    return messages


def isGeneratedRefPath(relPath: str) -> bool:
    """True when a path is regenerated by `gaia dev docs`, not hand-edited."""
    normalized = relPath.replace("\\", "/")
    return normalized.endswith("skill-tree.md") or any(
        normalized.startswith(prefix) for prefix in GENERATEDREFPREFIXES
    )


def reportStaleRefs(registryPath, oldId: str, newId: str, *, limit: int = 40) -> int:
    """Print the post-rename stale-reference checklist. Never fatal; returns
    the hit count so callers/tests can assert on it.
    """
    rootPath = Path(registryPath)
    pattern = idPattern(oldId)
    hits: list[tuple[str, int, str]] = []
    generatedSkipped = 0

    candidates: list[Path] = []
    for name in SCANROOTS:
        root = rootPath / name
        if root.exists():
            candidates.extend(p for p in sorted(root.rglob("*")) if p.is_file())
    for name in SCANEXTRAFILES:
        extra = rootPath / name
        if extra.is_file():
            candidates.append(extra)

    for path in candidates:
        if any(part in SCANSKIPDIRS for part in path.parts):
            continue
        rel = str(path.relative_to(rootPath)).replace("\\", "/")
        if isGeneratedRefPath(rel):
            generatedSkipped += 1
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if oldId not in text:
            continue
        for lineNumber, line in enumerate(text.split("\n"), 1):
            if pattern.search(line):
                hits.append((rel, lineNumber, line.strip()))

    print(f"\nStale-reference report for '{oldId}' (now '{newId}'):")
    if not hits:
        print("  clean — no remaining references in registry/, docs/, skill-trees/, README.md")
    else:
        byFile = len({rel for rel, _lineNumber, _line in hits})
        print(f"  {len(hits)} remaining reference(s) in {byFile} file(s) — review each; the rename did not rewrite these:")
        for rel, lineNumber, line in hits[:limit]:
            snippet = line if len(line) <= 110 else line[:107] + "..."
            print(f"  [ ] {rel}:{lineNumber}: {snippet}")
        if len(hits) > limit:
            print(f"  ... and {len(hits) - limit} more (showing first {limit})")
    if generatedSkipped:
        print(
            f"  Out of scope (regenerated, not hand-edited): {generatedSkipped} generated artifact(s) under "
            + ", ".join(GENERATEDREFPREFIXES[:4])
            + ", ... — run `gaia dev docs` to refresh them."
        )
    return len(hits)
