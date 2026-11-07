"""The canonical producer registry for PR maintenance (``founder/steward/pr-producers.json``).

A pull request is routine work only when a registered producer *proves* it: a verified
automation identity, the producer's branch convention, a same-repository head, and the
producer's required labels. An author name or a title proves nothing. The registry also
carries explicit holds and the repositories whose coverage is deferred, so an absent
repository is reported as unknown rather than healthy.
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "steward-pr-producers-v1"
REGISTRY_PATH = Path("founder/steward/pr-producers.json")
# Squash is disabled repo-wide and is never representable here (CLAUDE.md § Squash Merges).
MERGE_METHODS = ("merge", "rebase")
DRAFT_POLICIES = ("ineligible", "hold")
REVIEW_POLICIES = ("informational", "required")
CLOSURE_REASONS = ("superseded-by-merged-replacement", "label-already-published", "duplicate-of-open-sibling")
SURFACES = ("template-instance", "docs-edit")
PRODUCER_KEYS = {
    "id", "family", "repo", "workflow", "commitMarker", "identity", "commitAuthors", "branchPattern", "requiredLabels", "holdLabels", "cadence",
    "allowedFiles", "protectedGlobs", "requiredChecks", "requiredApprovals", "reviewRequestPolicy", "approvalBasis",
    "allowedMergeCommitters", "draftPolicy", "destination", "mergeMethod", "closureEligibility", "validator",
    "reconciler", "renderedSurface", "renderedSurfaceBasis", "enabled",
}
TOP_KEYS = {"schemaVersion", "revision", "provenance", "scope", "producers", "holds"}


class RegistryError(ValueError):
    """The producer registry is malformed. Every consumer fails closed on this."""


@dataclass(frozen=True)
class Identity:
    login: str
    accountId: int | None
    accountType: str


@dataclass(frozen=True)
class Producer:
    id: str
    family: str
    repo: str
    workflow: str
    commitMarker: str | None
    identity: Identity
    commitAuthors: tuple[Identity, ...]
    branchPattern: re.Pattern
    requiredLabels: tuple[str, ...]
    holdLabels: tuple[str, ...]
    cadence: str
    allowedFiles: tuple[str, ...]
    protectedGlobs: tuple[str, ...]
    requiredChecks: tuple[str, ...]
    requiredApprovals: int
    reviewRequestPolicy: str
    approvalBasis: str
    allowedMergeCommitters: tuple[str, ...]
    draftPolicy: str
    destination: str
    mergeMethod: str
    closureEligibility: tuple[str, ...]
    validator: str
    reconciler: str | None
    renderedSurface: str
    renderedSurfaceBasis: str
    enabled: bool

    def labelOf(self, branch: str) -> str | None:
        found = self.branchPattern.match(branch or "")
        return found.group("label") if found and "label" in found.groupdict() else (branch if found else None)

    def allowedPathsFor(self, label: str | None) -> tuple[str, ...]:
        return tuple(pattern.replace("{label}", label or "{label}") for pattern in self.allowedFiles)

    def pathAllowed(self, path: str, label: str | None) -> bool:
        return any(fnmatch.fnmatchcase(path, pattern) for pattern in self.allowedPathsFor(label))

    def pathProtected(self, path: str) -> bool:
        return any(fnmatch.fnmatchcase(path, pattern) for pattern in self.protectedGlobs)


@dataclass(frozen=True)
class DeferredRepo:
    repo: str
    reason: str
    coverage: str


@dataclass(frozen=True)
class Registry:
    revision: int
    enabledRepos: tuple[str, ...]
    deferred: tuple[DeferredRepo, ...]
    producers: tuple[Producer, ...]
    holds: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    sha256: str = ""

    def producer(self, producerId: str) -> Producer | None:
        return next((p for p in self.producers if p.id == producerId), None)

    def deferredFor(self, repo: str) -> DeferredRepo | None:
        return next((d for d in self.deferred if d.repo == repo), None)


@dataclass(frozen=True)
class Match:
    """Outcome of matching one PR to a producer. ``status`` is never inferred from the title."""

    status: str  # verified | forged-identity | unknown-producer | deferred | not-enabled | ambiguous
    producer: Producer | None
    label: str | None
    reasons: tuple[str, ...]

    @property
    def verified(self) -> bool:
        return self.status == "verified"


def _need(mapping: Mapping[str, Any], key: str, kind: type, where: str) -> Any:
    value = mapping.get(key)
    if isinstance(value, bool) and kind is not bool:
        raise RegistryError(f"{where}.{key} has the wrong type")
    if not isinstance(value, kind):
        raise RegistryError(f"{where}.{key} must be {kind.__name__}")
    return value


def _strings(mapping: Mapping[str, Any], key: str, where: str) -> tuple[str, ...]:
    value = _need(mapping, key, list, where)
    if not all(isinstance(item, str) and item for item in value):
        raise RegistryError(f"{where}.{key} must be a list of non-empty strings")
    return tuple(value)


def parseIdentity(raw: Any, where: str) -> Identity:
    if not isinstance(raw, dict) or set(raw) != {"login", "accountId", "accountType"}:
        raise RegistryError(f"{where} keys invalid")
    accountId = raw["accountId"]
    if accountId is not None and (isinstance(accountId, bool) or not isinstance(accountId, int) or accountId <= 0):
        raise RegistryError(f"{where}.accountId must be a positive integer or null")
    if raw["accountType"] not in ("Bot", "User"):
        raise RegistryError(f"{where}.accountType must be Bot or User")
    if not isinstance(raw["login"], str) or not raw["login"]:
        raise RegistryError(f"{where}.login must be a non-empty string")
    return Identity(raw["login"], accountId, raw["accountType"])


def parseProducer(raw: Any, index: int) -> Producer:
    where = f"producers[{index}]"
    if not isinstance(raw, dict):
        raise RegistryError(f"{where} must be an object")
    unknown, missing = set(raw) - PRODUCER_KEYS, PRODUCER_KEYS - set(raw)
    if unknown or missing:
        raise RegistryError(f"{where} keys invalid; missing={sorted(missing)}, unknown={sorted(unknown)}")
    identity = parseIdentity(raw["identity"], f"{where}.identity")
    authors = tuple(parseIdentity(item, f"{where}.commitAuthors[{n}]") for n, item in enumerate(_need(raw, "commitAuthors", list, where)))
    if not authors:
        raise RegistryError(f"{where}.commitAuthors must name at least one verified commit identity")
    try:
        pattern = re.compile(_need(raw, "branchPattern", str, where))
    except re.error as exc:
        raise RegistryError(f"{where}.branchPattern is not a regular expression: {exc}") from exc
    if raw["mergeMethod"] not in MERGE_METHODS:
        raise RegistryError(f"{where}.mergeMethod must be one of {MERGE_METHODS}; squash is never allowed")
    if raw["draftPolicy"] not in DRAFT_POLICIES:
        raise RegistryError(f"{where}.draftPolicy must be one of {DRAFT_POLICIES}")
    if raw["reviewRequestPolicy"] not in REVIEW_POLICIES:
        raise RegistryError(f"{where}.reviewRequestPolicy must be one of {REVIEW_POLICIES}")
    if raw["renderedSurface"] not in SURFACES:
        raise RegistryError(f"{where}.renderedSurface must be one of {SURFACES}")
    approvals = raw["requiredApprovals"]
    if isinstance(approvals, bool) or not isinstance(approvals, int) or not 0 <= approvals <= 5:
        raise RegistryError(f"{where}.requiredApprovals must be an integer from 0 to 5")
    closure = _strings(raw, "closureEligibility", where)
    if set(closure) - set(CLOSURE_REASONS):
        raise RegistryError(f"{where}.closureEligibility names unknown reasons")
    marker = raw["commitMarker"]
    if marker is not None and (not isinstance(marker, str) or len(marker) < 8):
        raise RegistryError(f"{where}.commitMarker must be null or a string of at least 8 characters")
    reconciler = raw["reconciler"]
    if reconciler is not None and not isinstance(reconciler, str):
        raise RegistryError(f"{where}.reconciler must be a string or null")
    destination = _need(raw, "destination", str, where)
    if not destination or destination.startswith("-") or ".." in destination:
        raise RegistryError(f"{where}.destination is not a plain branch name")
    return Producer(
        id=_need(raw, "id", str, where), family=_need(raw, "family", str, where), repo=_need(raw, "repo", str, where),
        workflow=_need(raw, "workflow", str, where), commitMarker=marker,
        identity=identity, commitAuthors=authors, branchPattern=pattern, requiredLabels=_strings(raw, "requiredLabels", where),
        holdLabels=_strings(raw, "holdLabels", where), cadence=_need(raw, "cadence", str, where),
        allowedFiles=_strings(raw, "allowedFiles", where), protectedGlobs=_strings(raw, "protectedGlobs", where),
        requiredChecks=_strings(raw, "requiredChecks", where), requiredApprovals=approvals,
        reviewRequestPolicy=raw["reviewRequestPolicy"], approvalBasis=_need(raw, "approvalBasis", str, where),
        allowedMergeCommitters=_strings(raw, "allowedMergeCommitters", where), draftPolicy=raw["draftPolicy"],
        destination=destination, mergeMethod=raw["mergeMethod"], closureEligibility=closure,
        validator=_need(raw, "validator", str, where), reconciler=reconciler,
        renderedSurface=raw["renderedSurface"], renderedSurfaceBasis=_need(raw, "renderedSurfaceBasis", str, where),
        enabled=_need(raw, "enabled", bool, where),
    )


def parseRegistry(raw: Any, digest: str = "") -> Registry:
    if not isinstance(raw, dict):
        raise RegistryError("producer registry must be an object")
    unknown, missing = set(raw) - TOP_KEYS, TOP_KEYS - set(raw)
    if unknown or missing:
        raise RegistryError(f"producer registry keys invalid; missing={sorted(missing)}, unknown={sorted(unknown)}")
    if raw["schemaVersion"] != SCHEMA:
        raise RegistryError(f"producer registry must declare {SCHEMA}")
    revision = raw["revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise RegistryError("revision must be a positive integer")
    scope = _need(raw, "scope", dict, "scope")
    enabled = _strings(scope, "enabledRepos", "scope")
    deferred = []
    for index, row in enumerate(_need(scope, "deferredRepos", list, "scope")):
        if not isinstance(row, dict) or set(row) != {"repo", "reason", "coverage"} or row["coverage"] != "unknown":
            raise RegistryError(f"scope.deferredRepos[{index}] must carry repo, reason and coverage 'unknown'")
        deferred.append(DeferredRepo(row["repo"], row["reason"], row["coverage"]))
    if set(enabled) & {d.repo for d in deferred}:
        raise RegistryError("a repository cannot be both enabled and deferred")
    producers = tuple(parseProducer(row, i) for i, row in enumerate(_need(raw, "producers", list, "registry")))
    ids = [p.id for p in producers]
    if len(set(ids)) != len(ids):
        raise RegistryError("producer ids must be unique")
    for producer in producers:
        if producer.enabled and producer.repo not in enabled:
            raise RegistryError(f"producer {producer.id} is enabled outside scope.enabledRepos")
    holds = tuple(row for row in _need(raw, "holds", list, "registry") if isinstance(row, dict))
    return Registry(revision, enabled, tuple(deferred), producers, holds, digest)


def loadRegistry(root: Path) -> Registry:
    """Read the registry, or raise ``RegistryError``. A missing or symlinked file fails closed."""

    import hashlib

    path = root / REGISTRY_PATH
    if path.is_symlink() or not path.is_file():
        raise RegistryError("producer registry is missing or a symlink")
    data = path.read_bytes()
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise RegistryError(f"producer registry is not valid JSON: {exc}") from exc
    return parseRegistry(raw, hashlib.sha256(data).hexdigest())


def matchProducer(registry: Registry, repo: str, row: Mapping[str, Any]) -> Match:
    """Match one census pull row to a producer by proven evidence only.

    ``forged-identity`` is reported when the branch convention matches a producer but the author
    is not that producer's verified identity: an impostor is distinguished from an unknown PR.
    """

    deferred = registry.deferredFor(repo)
    if deferred is not None:
        return Match("deferred", None, None, (f"repository deferred: {deferred.reason}",))
    if repo not in registry.enabledRepos:
        return Match("not-enabled", None, None, (f"repository {repo} is not in scope",))
    branch = str(row.get("headRef") or "")
    candidates = [p for p in registry.producers if p.enabled and p.repo == repo and p.branchPattern.match(branch)]
    if not candidates:
        return Match("unknown-producer", None, None, ("no registered producer owns this branch convention",))
    if len(candidates) > 1:
        return Match("ambiguous", None, None, ("more than one producer claims this branch",))
    producer = candidates[0]
    label = producer.labelOf(branch)
    author = row.get("author") if isinstance(row.get("author"), Mapping) else {}
    reasons: list[str] = []
    if author.get("login") != producer.identity.login:
        reasons.append(f"author {author.get('login')!r} is not {producer.identity.login!r}")
    if author.get("type") != producer.identity.accountType:
        reasons.append(f"account type {author.get('type')!r} is not {producer.identity.accountType!r}")
    if producer.identity.accountId is not None and author.get("id") != producer.identity.accountId:
        reasons.append(f"account id {author.get('id')!r} is not {producer.identity.accountId}")
    if row.get("headRepo") != repo:
        reasons.append("head lives in another repository (fork)")
    labels = {str(item) for item in row.get("labels") or []}
    missing = [name for name in producer.requiredLabels if name not in labels]
    if missing:
        reasons.append(f"missing required label(s): {', '.join(missing)}")
    if row.get("baseRef") != producer.destination:
        reasons.append(f"base {row.get('baseRef')!r} is not the producer destination {producer.destination!r}")
    if reasons:
        return Match("forged-identity", producer, label, tuple(reasons))
    return Match("verified", producer, label, ())
