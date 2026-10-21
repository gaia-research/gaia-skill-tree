"""Semantic identity for issue hygiene (contract section 3.2).

``classify`` names one census row: what it is, the key that stays stable across reruns,
its suite, version, candidate slug, evidence URL and parent. ``buildGraph`` links the
rows: parent to children, orphan children, duplicate candidate keys and per-suite
umbrella ordering. Both are pure and never raise on odd data; problems are recorded as
reasons on the identity or the graph.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from functools import cmp_to_key
from typing import Any

BOT_LOGIN = "github-actions[bot]"
GH_AW_PREFIX = "[aw]"
GH_AW_FAMILY = "gh-aw"
PAYLOAD_OPEN = "<!-- gaia-upstream-payload"
PAYLOAD_RE = re.compile(r"<!-- gaia-upstream-payload\s*\n(.*?)\n\s*-->", re.DOTALL)
UMBRELLA_TITLE_RE = re.compile(r"^\[upstream\]\s+(\S+)\s+→\s+(\S+)\s*$")
BOOTSTRAP_TITLE_RE = re.compile(r"^\[upstream:bootstrap\]\s+(\S+)\s+→\s+(?:baseline at\s+)?(\S+)\s*$")
CHILD_TITLE_RE = re.compile(r"^\[intake\]\s+(\S+)\s*$")
SUGGESTED_RE = re.compile(r"\*\*Suggested ID:\*\*\s*`([^`]+)`")
EVIDENCE_URL_RE = re.compile(r"\*\*url:\*\*\s*(\S+)")
GITHUB_REPO_RE = re.compile(r"github\.com/([^/\s]+)/([^/\s#?]+)")
UMBRELLA_REF_RE = re.compile(r"Umbrella:\s*#(\d+)")
CHILD_LINE_RE = re.compile(r"child intake", re.IGNORECASE)
HASH_REF_RE = re.compile(r"#(\d+)")

KINDS = ("child", "umbrella", "bootstrap", "botreport", "untracked")


@dataclass(frozen=True)
class Identity:
    """What one census row is, in terms the reconciler can compare."""

    number: int
    kind: str
    key: str
    suite: str | None = None
    version: str | None = None
    slug: str | None = None
    candidateId: str | None = None
    evidenceUrl: str | None = None
    evidenceRepo: str | None = None
    parent: int | None = None
    childRefs: tuple[int, ...] = ()
    payload: dict | None = None
    payloadReason: str | None = None
    family: str | None = None
    titleHash: str | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Graph:
    """Linked view over classified rows."""

    items: dict[int, Identity]
    children: dict[int, tuple[int, ...]]
    orphans: tuple[int, ...]
    duplicates: dict[str, tuple[int, ...]]
    suites: dict[str, tuple[int, ...]]
    conflicts: tuple[str, ...] = ()


def labelNames(row: dict) -> set[str]:
    """Label names from a census row; accepts plain strings or GitHub label objects."""
    names = set()
    for label in row.get("labels") or []:
        if isinstance(label, str):
            names.add(label)
        elif isinstance(label, dict) and isinstance(label.get("name"), str):
            names.add(label["name"])
    return names


def bodyText(row: dict) -> str:
    value = row.get("body")
    return value if isinstance(value, str) else ""


def parsePayload(body: str) -> tuple[dict | None, str | None]:
    """Return ``(payload, reason)``.

    No block gives ``(None, None)``. A block that parses to a JSON object gives
    ``(dict, None)``. A block that does not close, does not decode, or is not an object
    gives ``(None, "malformed:...")``.
    """
    match = PAYLOAD_RE.search(body)
    if match is None:
        if PAYLOAD_OPEN in body:
            return None, "malformed:unterminated-block"
        return None, None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return None, f"malformed:{exc.msg}"
    if not isinstance(data, dict):
        return None, "malformed:not-an-object"
    return data, None


def versionKey(text: Any) -> tuple | None:
    """Semver-tolerant sort key: ``v0.60.340.0``, ``0.6.13``, ``v7.0.0``, ``1.0.0-rc1``."""
    if not isinstance(text, str) or not text.strip():
        return None
    core = text.strip()
    if core[:1] in ("v", "V"):
        core = core[1:]
    pre = ""
    if "-" in core:
        core, pre = core.split("-", 1)
    try:
        numbers = tuple(int(part) for part in core.split("."))
    except ValueError:
        return None
    return (numbers, 0 if pre else 1, pre)


def compareVersions(left: Any, right: Any) -> int:
    """-1, 0 or 1. Unparsable versions sort before parsable ones, ties by raw text."""
    a = versionKey(left)
    b = versionKey(right)
    if a is None or b is None:
        ka = (a is not None, str(left))
        kb = (b is not None, str(right))
        return (ka > kb) - (ka < kb)
    na = a[0] + (0,) * max(0, len(b[0]) - len(a[0]))
    nb = b[0] + (0,) * max(0, len(a[0]) - len(b[0]))
    ka = (na, a[1], a[2])
    kb = (nb, b[1], b[2])
    return (ka > kb) - (ka < kb)


def normalizedTitle(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip().lower()


def childLines(body: str) -> tuple[int, ...]:
    """Issue numbers named on checklist or 'child intake' lines of an umbrella body."""
    found = []
    for line in body.splitlines():
        if CHILD_LINE_RE.search(line) or re.match(r"^\s*-\s*\[[ xX]\]", line):
            found.extend(int(number) for number in HASH_REF_RE.findall(line))
    return tuple(dict.fromkeys(found))


def classifyChild(number: int, title: str, body: str, reasons: list[str]) -> Identity:
    suggested = SUGGESTED_RE.search(body)
    candidate = suggested.group(1) if suggested else None
    if candidate is None:
        titled = CHILD_TITLE_RE.match(title)
        candidate = titled.group(1) if titled else None
        if candidate is None:
            reasons.append("candidate-id-unknown")
    slug = candidate.rsplit("/", 1)[-1] if candidate else None
    evidence = EVIDENCE_URL_RE.search(body)
    evidenceUrl = evidence.group(1) if evidence and evidence.group(1) != "_unknown" else None
    repo = GITHUB_REPO_RE.search(evidenceUrl or "")
    evidenceRepo = f"{repo.group(1)}/{repo.group(2)}" if repo else None
    if evidenceRepo is None:
        reasons.append("evidence-repo-unknown")
    parentMatch = UMBRELLA_REF_RE.search(body)
    parent = int(parentMatch.group(1)) if parentMatch else None
    owner = evidenceRepo or "unknown"
    key = f"upstream-candidate:{owner}:{slug}" if slug else f"upstream-candidate:{owner}:#{number}"
    return Identity(
        number=number, kind="child", key=key, slug=slug, candidateId=candidate,
        evidenceUrl=evidenceUrl, evidenceRepo=evidenceRepo, parent=parent,
    )


def classifyUpstream(number: int, kind: str, title: str, body: str, reasons: list[str]) -> Identity:
    titled = BOOTSTRAP_TITLE_RE.match(title) if kind == "bootstrap" else UMBRELLA_TITLE_RE.match(title)
    titleRepo = titled.group(1) if titled else None
    titleVersion = titled.group(2) if titled else None
    if titled is None:
        reasons.append("title-unrecognized")
    payload, payloadReason = parsePayload(body)
    if payloadReason:
        reasons.append(payloadReason)
    elif payload is None:
        reasons.append("payload-absent")
    payloadRepo = payload.get("skillId") if payload else None
    payloadVersion = payload.get("newVersion") if payload else None
    repo = payloadRepo or titleRepo
    if payloadRepo and titleRepo and payloadRepo != titleRepo:
        reasons.append(f"title-payload-suite-mismatch:{titleRepo}!={payloadRepo}")
    version = payloadVersion or titleVersion
    if repo is None:
        reasons.append("suite-unknown")
    if version is None:
        reasons.append("version-unknown")
    suiteRepo = repo or "unknown"
    suite = f"upstream-suite:{suiteRepo}"
    if kind == "bootstrap":
        key = f"upstream-bootstrap:{suiteRepo}"
    else:
        key = f"upstream-release:{suiteRepo}@{version or '?'}"
    return Identity(
        number=number, kind=kind, key=key, suite=suite, version=version,
        childRefs=childLines(body) if kind == "umbrella" else (),
        payload=payload, payloadReason=payloadReason,
    )


def classifyBot(number: int, title: str, body: str, reasons: list[str]) -> Identity:
    normal = normalizedTitle(title[len(GH_AW_PREFIX):]) if title.startswith(GH_AW_PREFIX) else normalizedTitle(title)
    titleHash = hashlib.sha256(normal.encode("utf-8")).hexdigest()[:12]
    return Identity(
        number=number, kind="botreport", key=f"bot-report:{GH_AW_FAMILY}:{titleHash}",
        family=GH_AW_FAMILY, titleHash=titleHash,
    )


def classify(row: dict) -> Identity:
    """Name one census row. Never raises; anything odd is recorded in ``reasons``."""
    number = row.get("number") if isinstance(row.get("number"), int) else -1
    title = row.get("title") if isinstance(row.get("title"), str) else ""
    body = bodyText(row)
    labels = labelNames(row)
    author = row.get("author") or ""
    reasons: list[str] = []
    if "upstream:child" in labels:
        identity = classifyChild(number, title, body, reasons)
    elif "upstream:bootstrap" in labels or title.startswith("[upstream:bootstrap]"):
        identity = classifyUpstream(number, "bootstrap", title, body, reasons)
    elif "upstream:release" in labels or title.startswith("[upstream]"):
        identity = classifyUpstream(number, "umbrella", title, body, reasons)
    elif author == BOT_LOGIN and title.startswith(GH_AW_PREFIX) and not any(name.startswith("upstream:") for name in labels):
        identity = classifyBot(number, title, body, reasons)
    else:
        identity = Identity(number=number, kind="untracked", key=f"issue:{number}")
    return replace(identity, reasons=tuple(reasons))


def buildGraph(rows: Any, closedRows: Any = ()) -> Graph:
    """Classify open rows and link them. ``closedRows`` lets a child report a closed parent."""
    openRows = [row for row in rows if isinstance(row, dict) and not row.get("isPullRequest")]
    items = {}
    for row in openRows:
        identity = classify(row)
        items[identity.number] = identity
    openNumbers = set(items)
    closedNumbers = {row.get("number") for row in closedRows if isinstance(row, dict)}
    conflicts: list[str] = []

    children: dict[int, list[int]] = {}
    orphans: list[int] = []
    for number in sorted(items):
        identity = items[number]
        if identity.kind != "child":
            continue
        parent = identity.parent
        if parent is None:
            orphans.append(number)
            items[number] = replace(identity, reasons=identity.reasons + ("no-parent-reference",))
            continue
        parentItem = items.get(parent)
        if parentItem is None:
            orphans.append(number)
            cause = "parent-closed" if parent in closedNumbers else "parent-not-open"
            items[number] = replace(identity, reasons=identity.reasons + (cause,))
            continue
        if parentItem.kind not in ("umbrella", "bootstrap"):
            orphans.append(number)
            items[number] = replace(identity, reasons=identity.reasons + ("parent-not-umbrella",))
            continue
        children.setdefault(parent, []).append(number)
        items[number] = replace(identity, suite=parentItem.suite)

    for number in sorted(items):
        identity = items[number]
        if identity.kind != "umbrella":
            continue
        for ref in identity.childRefs:
            child = items.get(ref)
            if child is None or child.kind != "child":
                continue
            if child.parent is not None and child.parent != number:
                conflicts.append(f"child-ref-parent-mismatch:{number}->{ref}")
                continue
            if ref not in children.get(number, []):
                children.setdefault(number, []).append(ref)

    groups: dict[str, list[int]] = {}
    for number, identity in items.items():
        if identity.kind != "untracked":
            groups.setdefault(identity.key, []).append(number)
    duplicates = {key: tuple(sorted(numbers)) for key, numbers in groups.items() if len(numbers) > 1}

    suites: dict[str, list[int]] = {}
    for number, identity in items.items():
        if identity.kind == "umbrella" and identity.suite:
            suites.setdefault(identity.suite, []).append(number)
    def byVersion(left: int, right: int) -> int:
        return compareVersions(items[left].version, items[right].version) or (left > right) - (left < right)

    ordered = {suite: tuple(sorted(numbers, key=cmp_to_key(byVersion))) for suite, numbers in suites.items()}

    return Graph(
        items=items,
        children={parent: tuple(sorted(numbers)) for parent, numbers in children.items()},
        orphans=tuple(sorted(set(orphans))),
        duplicates=duplicates,
        suites=ordered,
        conflicts=tuple(conflicts),
    )


__all__ = [
    "BOT_LOGIN",
    "GH_AW_FAMILY",
    "KINDS",
    "Graph",
    "Identity",
    "buildGraph",
    "classify",
    "compareVersions",
    "parsePayload",
    "versionKey",
]
