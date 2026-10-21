"""Read-only index of the registry for issue hygiene (contract section 3.4, lane B).

``buildRegistryIndex`` walks ``registry/named/<contributor>/<slug>.md`` and
``registry/nodes/**/*.json`` and records what the closure rules need: id, contributor,
status, normalized ``links.github``, the ``upstream`` block and ``installable``
(the freeze marker), plus a sha256 of the file bytes. It never writes.

Tolerance is deliberate. A file that cannot be read or parsed is kept in
``unreadable`` instead of being skipped, and every lookup that could have depended on
it reports that fact, so the reconciler can mark the affected item not-evaluated.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from gaia_cli.frontmatter import split_frontmatter

NAMED_DIR = "registry/named"
NODES_DIR = "registry/nodes"
GITHUB_BLOB_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/(?:blob|tree)/([^/]+)(?:/(.*))?$")


@dataclass(frozen=True)
class GithubRef:
    """A GitHub file reference with the repo lowercased; ``path`` keeps its case."""

    repo: str
    ref: str
    path: str

    def blobUrl(self) -> str:
        return f"https://github.com/{self.repo}/blob/{self.ref}/{self.path}".rstrip("/")


def parseGithubUrl(url: Any) -> GithubRef | None:
    """Parse a github.com ``blob`` or ``tree`` URL. ``tree`` is treated as ``blob``.

    Query strings and fragments are dropped and a trailing slash is stripped.
    Anything that is not a github.com file or tree URL gives None.
    """
    if not isinstance(url, str):
        return None
    text = re.split(r"[?#]", url.strip(), maxsplit=1)[0].rstrip("/")
    match = GITHUB_BLOB_RE.match(text)
    if match is None:
        return None
    return GithubRef(f"{match.group(1)}/{match.group(2)}".lower(), match.group(3), match.group(4) or "")


def normalizeHandle(handle: str) -> str:
    """Contributor handle with case and ``-``/``_`` removed, for alias detection only."""
    return re.sub(r"[-_]", "", handle.lower())


def splitId(identifier: str) -> tuple[str, str] | None:
    """``owner/slug`` to ``(owner, slug)``; None when the id has no single slash."""
    owner, sep, slug = identifier.partition("/")
    if not sep or not owner or not slug or "/" in slug:
        return None
    return owner, slug


@dataclass(frozen=True)
class NamedRecord:
    id: str
    contributor: str
    slug: str
    path: str
    sha256: str
    status: str | None
    installable: bool | None
    github: GithubRef | None
    upstreamRepo: str | None
    upstreamVersion: str | None


@dataclass(frozen=True)
class NodeRecord:
    id: str
    path: str
    sha256: str


@dataclass(frozen=True)
class Unreadable:
    path: str
    reason: str
    pathId: str | None
    slug: str | None


@dataclass
class RegistryIndex:
    named: dict[str, NamedRecord] = field(default_factory=dict)
    nodes: dict[str, NodeRecord] = field(default_factory=dict)
    unreadable: tuple[Unreadable, ...] = ()
    slugIndex: dict[str, list[NamedRecord]] = field(default_factory=dict, repr=False)
    githubIndex: dict[tuple[str, str], list[NamedRecord]] = field(default_factory=dict, repr=False)

    def byId(self, identifier: str) -> NamedRecord | None:
        return self.named.get(identifier)

    def byGithub(self, ref: GithubRef) -> list[NamedRecord]:
        """Every named record whose links.github points at this repo and path (any ref)."""
        return list(self.githubIndex.get((ref.repo, ref.path), []))

    def aliasCandidates(self, identifier: str) -> list[NamedRecord]:
        """Records with the same slug under a different contributor handle, sorted by id."""
        parts = splitId(identifier)
        if parts is None:
            return []
        owner, slug = parts
        found = [record for record in self.slugIndex.get(slug, []) if record.contributor != owner]
        return sorted(found, key=lambda record: record.id)

    def unreadableNear(self, identifier: str) -> list[Unreadable]:
        """Unreadable files that could be this id: same path, or same slug under any handle."""
        parts = splitId(identifier)
        slug = parts[1] if parts else None
        return [
            entry for entry in self.unreadable
            if entry.pathId == identifier or (slug is not None and entry.slug == slug)
        ]


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def relParts(relPath: str) -> tuple[str, ...]:
    return tuple(relPath.split("/"))


def readNamed(path: Path, relPath: str) -> tuple[NamedRecord | None, Unreadable | None]:
    below = relPath[len(NAMED_DIR) + 1:] if relPath.startswith(NAMED_DIR + "/") else ""
    parts = below.split("/") if below else []
    if len(parts) != 2 or not parts[0] or not parts[1].endswith(".md"):
        return None, Unreadable(relPath, "unexpected-path", None, None)
    contributor, fileName = parts
    slug = fileName[: -len(".md")]
    pathId = f"{contributor}/{slug}"
    try:
        raw = path.read_bytes()
    except OSError:
        return None, Unreadable(relPath, "read-error", pathId, slug)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, Unreadable(relPath, "utf8-error", pathId, slug)
    fence, frontmatter, body = split_frontmatter(text)
    if not fence:
        return None, Unreadable(relPath, "no-frontmatter", pathId, slug)
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError:
        return None, Unreadable(relPath, "yaml-error", pathId, slug)
    if not isinstance(data, dict):
        return None, Unreadable(relPath, "frontmatter-not-mapping", pathId, slug)
    identifier = data.get("id")
    if not isinstance(identifier, str) or identifier != pathId:
        return None, Unreadable(relPath, "id-path-mismatch", pathId, slug)
    if data.get("contributor") not in (None, contributor):
        return None, Unreadable(relPath, "contributor-path-mismatch", pathId, slug)

    links = data.get("links")
    github = parseGithubUrl(links.get("github")) if isinstance(links, dict) else None
    upstream = data.get("upstream")
    upstreamRepo = None
    upstreamVersion = None
    if upstream is not None:
        if not isinstance(upstream, dict):
            return None, Unreadable(relPath, "upstream-malformed", pathId, slug)
        if isinstance(upstream.get("repo"), str):
            upstreamRepo = upstream["repo"].lower()
        if isinstance(upstream.get("version"), str):
            upstreamVersion = upstream["version"]
    status = data.get("status") if isinstance(data.get("status"), str) else None
    installable = data["installable"] if isinstance(data.get("installable"), bool) else None
    record = NamedRecord(
        id=identifier, contributor=contributor, slug=slug, path=relPath, sha256=sha256(raw),
        status=status, installable=installable, github=github,
        upstreamRepo=upstreamRepo, upstreamVersion=upstreamVersion,
    )
    return record, None


def readNode(path: Path, relPath: str) -> tuple[NodeRecord | None, Unreadable | None]:
    try:
        raw = path.read_bytes()
    except OSError:
        return None, Unreadable(relPath, "read-error", None, None)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, Unreadable(relPath, "json-error", None, None)
    if not isinstance(data, dict) or not isinstance(data.get("id"), str):
        return None, Unreadable(relPath, "node-id-missing", None, None)
    return NodeRecord(id=data["id"], path=relPath, sha256=sha256(raw)), None


def buildRegistryIndex(root: Path) -> RegistryIndex:
    """Index ``registry/named`` and ``registry/nodes`` under ``root``. Read-only."""
    named: dict[str, NamedRecord] = {}
    nodes: dict[str, NodeRecord] = {}
    unreadable: list[Unreadable] = []

    namedRoot = root / NAMED_DIR
    if namedRoot.is_dir():
        for path in sorted(namedRoot.rglob("*.md")):
            if not path.is_file():
                continue
            relPath = path.relative_to(root).as_posix()
            record, problem = readNamed(path, relPath)
            if problem is not None:
                unreadable.append(problem)
                continue
            named[record.id] = record

    nodesRoot = root / NODES_DIR
    if nodesRoot.is_dir():
        for path in sorted(nodesRoot.rglob("*.json")):
            if not path.is_file():
                continue
            relPath = path.relative_to(root).as_posix()
            node, problem = readNode(path, relPath)
            if problem is not None:
                unreadable.append(problem)
                continue
            nodes[node.id] = node

    index = RegistryIndex(named=dict(sorted(named.items())), nodes=nodes, unreadable=tuple(sorted(unreadable, key=lambda item: item.path)))
    for record in index.named.values():
        index.slugIndex.setdefault(record.slug, []).append(record)
        if record.github is not None:
            index.githubIndex.setdefault((record.github.repo, record.github.path), []).append(record)
    return index


__all__ = [
    "GithubRef",
    "NamedRecord",
    "NodeRecord",
    "RegistryIndex",
    "Unreadable",
    "buildRegistryIndex",
    "normalizeHandle",
    "parseGithubUrl",
    "splitId",
]
