"""Reference-surface updates for `gaia dev rename` (#1456).

Before this module, `gaia dev rename` moved the registry node / named `.md`
file and repointed a short list of frontmatter fields.  Every other surface
that embeds a skill id had to be patched by hand afterwards (PR #1452):

* `registry/suites/**/*.json` — nested `suites[].members[]` / `suites[].fusion`
  kept pointing at the old id.
* Markdown prose inside the affected registry files (install commands, badge
  and explorer URLs, cross-references).
* `skill-trees/**/skill-tree.json` — `unlockedSkills[]`, `combinedFrom[]`,
  `pendingCombinations[]`, and `timeline[]` entries.

Everything here is deliberately conservative: structural JSON edits are exact
whole-string matches, prose edits are whole-token matches that leave changelog
/ history sections alone, and anything still holding the old id afterwards is
printed as a visible checklist rather than silently rewritten.
"""

import json
import re
from pathlib import Path

from gaia_cli.registry import registry_dir, skill_trees_dir

# Surfaces that legitimately keep the old id until the next generation pass.
# They are regenerated wholesale by `gaia dev docs`, so rewriting them here
# would just be overwritten; the report names them instead of pretending the
# tree is clean.
GENERATEDREFPREFIXES = (
    "docs/graph/",
    "docs/api/",
    "docs/og/",
    "docs/badges/",
    "docs/u/",
    "docs/experiments/",
    "docs/okf/",
    "docs/tree.md",
    "registry/gaia.json",
    "registry/gaia.gexf",
    "registry/gaia.svg",
    "registry/named-skills.json",
    "registry/registry.md",
    "registry/real-skills.",
    "registry/combinations.md",
    "registry/skill-sources.md",
    "registry/layouts_3d.json",
)

SCANROOTS = ("registry", "docs", "skill-trees")
SCANEXTRAFILES = ("README.md",)
SCANSKIPDIRS = frozenset(
    {
        ".git",
        ".gaia",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "generated-output",
        "graphify-out",
    }
)
SCANSKIPSUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".woff",
    ".woff2",
    ".ttf",
    ".svg",
    ".gexf",
)
SCANMAXBYTES = 2_000_000

CHANGELOGHEADING = re.compile(r"^#{1,6}\s+.*(changelog|history)", re.IGNORECASE)
MARKDOWNHEADING = re.compile(r"^(#{1,6})\s")


def idPattern(skillId: str) -> re.Pattern:
    """Whole-token matcher for a skill id.

    `skill-old` must not match `skill-older`, and `ruvnet/hive-mind` must not
    match `other-ruvnet/hive-mind`.  A leading `/` is allowed to precede the
    match so slash-naming (`/gaia-curate`) and paths both hit.
    """
    return re.compile(
        r"(?<![A-Za-z0-9_-])" + re.escape(skillId) + r"(?![A-Za-z0-9_-])"
    )


def replaceExactDeep(node, oldId: str, newId: str):
    """Replace every string equal to `oldId` anywhere in a JSON document.

    Returns `(node, changed)`.  Exact whole-string equality only — a prose
    field never equals a bare skill id, so this cannot corrupt descriptions
    while still catching arbitrarily nested id arrays (`suites[].members[]`).
    """
    if isinstance(node, str):
        return (newId, True) if node == oldId else (node, False)
    if isinstance(node, list):
        changed = False
        out = []
        for item in node:
            value, itemChanged = replaceExactDeep(item, oldId, newId)
            out.append(value)
            changed = changed or itemChanged
        return out, changed
    if isinstance(node, dict):
        changed = False
        out = {}
        for key, value in node.items():
            newValue, valueChanged = replaceExactDeep(value, oldId, newId)
            out[key] = newValue
            changed = changed or valueChanged
        return out, changed
    return node, False


def rewriteProseRefs(text: str, oldId: str, newId: str):
    """Rewrite whole-token references to `oldId` in markdown prose.

    Returns `(text, rewritten, changelogHits)`.  Changelog / history sections
    are left untouched — those entries describe what the skill was called at
    the time and rewriting them would falsify the record.  Their hit count is
    returned so the caller can disclose it instead of hiding it.
    """
    pattern = idPattern(oldId)
    lines = text.split("\n")
    out = []
    rewritten = 0
    changelogHits = 0
    inChangelog = False
    changelogDepth = 0

    for line in lines:
        heading = MARKDOWNHEADING.match(line)
        if heading:
            depth = len(heading.group(1))
            if CHANGELOGHEADING.match(line):
                inChangelog = True
                changelogDepth = depth
            elif inChangelog and depth <= changelogDepth:
                inChangelog = False
        hits = len(pattern.findall(line))
        if hits and inChangelog:
            changelogHits += hits
            out.append(line)
            continue
        if hits:
            out.append(pattern.sub(newId, line))
            rewritten += hits
            continue
        out.append(line)

    return "\n".join(out), rewritten, changelogHits


def updateSuiteManifests(registryPath, oldId: str, newId: str) -> list[str]:
    """Repoint every reference to `oldId` inside `registry/suites/**/*.json`.

    Covers top-level `capstone` / `standalones` / `components` AND the nested
    `suites[].fusion` / `suites[].members[]` arrays that the pre-#1456 command
    walked straight past.  A manifest whose own `id` was the renamed skill is
    moved so its path keeps matching its id.
    """
    messages: list[str] = []
    suitesDir = Path(registry_dir(registryPath)) / "suites"
    if not suitesDir.exists():
        return messages

    for path in sorted(suitesDir.glob("**/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        updated, changed = replaceExactDeep(data, oldId, newId)
        if not changed:
            continue

        writePath = path
        if isinstance(updated, dict) and updated.get("id") == newId and "/" in newId:
            newContributor, newSlug = newId.split("/", 1)
            candidate = suitesDir / newContributor / f"{newSlug}.json"
            if candidate != path and not candidate.exists():
                candidate.parent.mkdir(parents=True, exist_ok=True)
                writePath = candidate

        writePath.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if writePath != path:
            path.unlink()
            messages.append(f"Moved suite manifest {path} to {writePath}")
        messages.append(f"Updated suite manifest references in {writePath}")

    return messages


def rewriteTimelineDetails(tree: dict, oldId: str, newId: str) -> bool:
    """Rewrite whole-token id references inside user-tree timeline `details`."""
    pattern = idPattern(oldId)
    changed = False
    for event in tree.get("timeline") or []:
        if not isinstance(event, dict):
            continue
        details = event.get("details")
        if not isinstance(details, str):
            continue
        rewritten = pattern.sub(newId, details)
        if rewritten != details:
            event["details"] = rewritten
            changed = True
    return changed


def updateSkillTrees(registryPath, oldId: str, newId: str) -> list[str]:
    """Repoint `skill-trees/*/skill-tree.json` references to the renamed skill.

    Covers `unlockedSkills[].skillId`, `unlockedSkills[].combinedFrom[]`,
    `pendingCombinations[]`, and `timeline[].skillId` (structural, exact
    match) plus `timeline[].details` prose (whole-token match).

    No timeline event is appended.  `skillTree.schema.json`'s `timelineEvent`
    action enum has no `rename` member, so writing one would land a state the
    schema rejects — and fabricating a different action, or backfilling a
    synthetic timestamp, is worse than saying nothing.  The rename is already
    audited on the registry side by `append_skill_event`.
    """
    messages: list[str] = []
    treesDir = Path(skill_trees_dir(registryPath))
    if not treesDir.exists():
        return messages

    for treePath in sorted(treesDir.glob("*/skill-tree.json")):
        try:
            data = json.loads(treePath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        updated, changed = replaceExactDeep(data, oldId, newId)
        detailsChanged = (
            rewriteTimelineDetails(updated, oldId, newId)
            if isinstance(updated, dict)
            else False
        )
        if not (changed or detailsChanged):
            continue
        treePath.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        messages.append(f"Updated user-tree references in {treePath}")

    return messages


def isGeneratedRefPath(relPath: str) -> bool:
    """True when a path is regenerated by `gaia dev docs` rather than edited."""
    normalized = relPath.replace("\\", "/")
    if normalized.endswith("skill-tree.md"):
        return True
    return any(normalized.startswith(prefix) for prefix in GENERATEDREFPREFIXES)


def _iterScanFiles(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SCANSKIPDIRS for part in path.parts):
            continue
        if path.name.lower().endswith(SCANSKIPSUFFIXES):
            continue
        yield path


def scanStaleReferences(registryPath, oldId: str) -> dict:
    """Find remaining `oldId` references across the known reference surfaces.

    Returns `{"hits": [(relPath, lineNumber, line)], "skippedLarge": [relPath],
    "generatedSkipped": [relPath]}`.  Purely a read — the caller decides what
    to do with it, and nothing here is fatal.
    """
    rootPath = Path(registryPath)
    pattern = idPattern(oldId)
    hits: list[tuple[str, int, str]] = []
    skippedLarge: list[str] = []
    generatedSkipped: list[str] = []

    candidates: list[Path] = []
    for name in SCANROOTS:
        root = rootPath / name
        if root.exists():
            candidates.extend(_iterScanFiles(root))
    for name in SCANEXTRAFILES:
        extra = rootPath / name
        if extra.is_file():
            candidates.append(extra)

    for path in candidates:
        try:
            rel = str(path.relative_to(rootPath)).replace("\\", "/")
        except ValueError:
            rel = str(path)
        if isGeneratedRefPath(rel):
            generatedSkipped.append(rel)
            continue
        try:
            if path.stat().st_size > SCANMAXBYTES:
                skippedLarge.append(rel)
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if oldId not in text:
            continue
        for lineNumber, line in enumerate(text.split("\n"), 1):
            if pattern.search(line):
                hits.append((rel, lineNumber, line.strip()))

    return {
        "hits": hits,
        "skippedLarge": skippedLarge,
        "generatedSkipped": generatedSkipped,
    }


def reportStaleReferences(registryPath, oldId: str, newId: str, *, limit: int = 40) -> int:
    """Print the post-rename stale-reference checklist.  Never fatal.

    Returns the number of hits found so callers/tests can assert on it.
    """
    result = scanStaleReferences(registryPath, oldId)
    hits = result["hits"]

    print("")
    print(f"Stale-reference report for '{oldId}' (now '{newId}'):")
    if not hits:
        print("  clean — no remaining references in registry/, docs/, skill-trees/, README.md")
    else:
        byFile: dict[str, int] = {}
        for rel, _lineNumber, _line in hits:
            byFile[rel] = byFile.get(rel, 0) + 1
        print(
            f"  {len(hits)} remaining reference(s) in {len(byFile)} file(s) — "
            "review each; the rename did not rewrite these:"
        )
        for rel, lineNumber, line in hits[:limit]:
            snippet = line if len(line) <= 110 else line[:107] + "..."
            print(f"  [ ] {rel}:{lineNumber}: {snippet}")
        if len(hits) > limit:
            print(f"  ... and {len(hits) - limit} more (showing first {limit})")

    if result["generatedSkipped"]:
        print(
            f"  Out of scope (regenerated, not hand-edited): "
            f"{len(result['generatedSkipped'])} generated artifact(s) under "
            + ", ".join(GENERATEDREFPREFIXES[:4])
            + ", ... — run `gaia dev docs` to refresh them."
        )
    if result["skippedLarge"]:
        print(
            f"  Not scanned (over {SCANMAXBYTES // 1000}kB): "
            + ", ".join(result["skippedLarge"][:5])
            + ("" if len(result["skippedLarge"]) <= 5 else ", ...")
        )
    print(
        "  Surfaces scanned: registry/, docs/ (non-generated), skill-trees/, README.md. "
        "Anything outside this repo (published wheels, external mirrors) is out of scope."
    )
    return len(hits)
