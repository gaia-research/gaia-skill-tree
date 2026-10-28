"""
scripts.upstream_watcher.prechecks — deterministic prechecks for batch candidates (#2131).

Every candidate row in an umbrella's batch record is checked BEFORE any write:

registry    absent | present | alias-suspect
              present        = registry id equals the suggested id AND the
                               registry links.github equals the candidate evidence
                               URL after blob normalization. The ref segment is
                               ignored: registry records pin release tags while
                               evidence URLs point at main.
              alias-suspect  = registry id differs but the slug matches another
                               record, or the id matches while the links differ.
                               Never reported as identical; a human decides.
tracked     none | child:#N
              an open ``upstream:child`` issue already carries the suggested id.
priorDisposition   none | rejected:#N
              a closed ``upstream:child`` issue labelled ``upstream:rejected``
              carries the suggested id.

Suppression: a row whose status is present, tracked or rejected is suppressed
(not proposed as new work) but is RETAINED in the umbrella payload. Nothing is
ever dropped to make a count go down.

All inputs are plain data (registry frontmatter list, live issue dicts), so
the module is pure and testable without GitHub.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

from scripts.lib.named_iterator import iter_named_skills
from scripts.upstream_watcher.live import GhError

SUPPRESSED_STATUSES = frozenset({"present", "tracked", "rejected"})

_SUGGESTED_ID_RE = re.compile(r"\*\*Suggested ID:\*\*\s*`([^`]+)`")
_EVIDENCE_URL_RE = re.compile(r"(?mi)^\s*-\s*\*\*url:\*\*\s*(\S+)\s*$")
_UMBRELLA_RE = re.compile(r"Umbrella:\s*#(\d+)")
_SIMPLE_REF_NAMES = frozenset({"HEAD", "main", "master"})
_SEMVER_REF_RE = re.compile(r"v?[0-9]+(?:\.[0-9]+){0,3}(?:[-+][0-9A-Za-z.-]+)?")
_SHA_REF_RE = re.compile(r"[0-9a-f]{7,40}")


def _simple_ref(ref: str) -> bool:
    """Whether a URL's single-segment ref/path split is safe to ignore."""
    return (
        ref in _SIMPLE_REF_NAMES
        or _SEMVER_REF_RE.fullmatch(ref) is not None
        or _SHA_REF_RE.fullmatch(ref) is not None
    )


class AmbiguousChildIdentity(GhError):
    """A legacy child cannot be safely associated with a candidate source."""


class _ChildIndex(dict):
    """Compatibility view of child indexes with source-qualified identity lookup."""

    def __init__(self):
        super().__init__()
        self.by_identity: dict[tuple[str, str], int] = {}
        self.ambiguous_ids: set[str] = set()

    def get(self, key, default=None):
        if isinstance(key, tuple):
            if key[0] in self.ambiguous_ids:
                raise AmbiguousChildIdentity(f"child for {key[0]} has an ambiguous source")
            return self.by_identity.get(key, default)
        if isinstance(key, str):
            raise AmbiguousChildIdentity(
                "child lookup by suggested ID alone is unsafe; candidate source identity is required"
            )
        return super().get(key, default)


def child_source_identity(body: str, suggested_id: str) -> tuple[str, str]:
    """Return the suggested ID and normalized GitHub blob path, rejecting unknown sources."""
    urls = _EVIDENCE_URL_RE.findall(body or "")
    if len(urls) != 1:
        raise AmbiguousChildIdentity(f"child for {suggested_id} has no unique evidence URL")
    url = urls[0]
    parts = urlsplit(url)
    segments = [segment for segment in parts.path.split("/") if segment]
    if (
        parts.scheme.lower() != "https"
        or parts.netloc.lower() not in {"github.com", "www.github.com"}
        or len(segments) < 5
        or segments[2] not in {"blob", "tree"}
        or not segments[4:]
    ):
        raise AmbiguousChildIdentity(f"child for {suggested_id} has an unsupported evidence URL")
    normalized = normalize_blob(url, ignore_ref=True)
    if not normalized:
        raise AmbiguousChildIdentity(f"child for {suggested_id} has an unsupported evidence URL")
    return suggested_id, normalized


def candidate_identity(row: dict) -> tuple[str, str]:
    """Identity shared by a candidate and its child across equivalent Git refs."""
    return child_source_identity(f"- **url:** {row.get('evidenceUrl', '')}", row["suggestedId"])


class RegistryUnreadable(RuntimeError):
    """The named-skill registry could not be read or is empty (fail closed)."""


def normalize_blob(url: str | None, ignore_ref: bool = False) -> str:
    """Return a comparable form of a GitHub URL.

    ``tree/`` is rewritten to ``blob/``, ``.git`` and trailing slashes are
    dropped, and host/owner/repo are lowercased. The path is kept case-sensitive.
    With ``ignore_ref`` a trusted simple ``blob/<ref>/`` segment is dropped, so
    a registry record pinned to a release tag matches the same file on ``main``.
    Ambiguous refs (which may contain slashes) are retained in the path. Returns ""
    for anything that is not a GitHub owner/repo URL.
    """
    if not url:
        return ""
    parts = urlsplit(url.strip())
    segments = [seg for seg in parts.path.split("/") if seg]
    if len(segments) < 2:
        return ""
    owner = segments[0].lower()
    repo = segments[1].lower()
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]
    rest = segments[2:]
    if rest and rest[0] == "tree":
        rest[0] = "blob"
    if ignore_ref and len(rest) >= 3 and rest[0] == "blob" and _simple_ref(rest[1]):
        rest = rest[2:]
    tail = "/".join(rest).rstrip("/")
    host = parts.netloc.lower()
    if host == "www.github.com":
        host = "github.com"
    base = f"{host}/{owner}/{repo}"
    return f"{base}/{tail}" if tail else base


def slug_key(text: str) -> str:
    """Loose slug comparison key: lowercase with hyphens and underscores removed."""
    return re.sub(r"[-_]", "", (text or "").lower())


def suggested_id_of(body: str) -> str | None:
    """Extract the ``**Suggested ID:**`` value from an intake child body."""
    match = _SUGGESTED_ID_RE.search(body or "")
    return match.group(1).strip() if match else None


def umbrella_number_of(body: str) -> int | None:
    """Extract ``Umbrella: #N`` from a child intake body."""
    match = _UMBRELLA_RE.search(body or "")
    return int(match.group(1)) if match else None


def load_registry_index(root: Path | None = None) -> dict:
    """Read ``registry/named/**`` into a lookup index.

    Raises RegistryUnreadable when the directory cannot be read or yields no
    records at all. An empty registry is treated as unreadable: an absent
    registry must never make every candidate look "absent".
    """
    try:
        rows = list(iter_named_skills(root=root))
    except Exception as exc:  # noqa: BLE001 — any read failure fails closed
        raise RegistryUnreadable(f"registry read failed: {exc}") from exc
    if not rows:
        raise RegistryUnreadable("registry/named yielded no records")

    by_id: dict[str, dict] = {}
    by_slug: dict[str, list[str]] = {}
    for _path, fm in rows:
        rid = fm.get("id")
        if not rid:
            continue
        links = fm.get("links") or {}
        by_id[rid] = {
            "links": normalize_blob(links.get("github"), ignore_ref=True),
            "status": fm.get("status"),
        }
        by_slug.setdefault(slug_key(rid.split("/")[-1]), []).append(rid)
    return {"byId": by_id, "bySlug": by_slug}


def registry_state(row: dict, index: dict) -> str:
    """Return ``present``, ``alias-suspect`` or ``absent`` for a candidate row."""
    suggested = row["suggestedId"]
    entry = index["byId"].get(suggested)
    if entry is not None:
        if entry["links"] and entry["links"] == normalize_blob(row.get("evidenceUrl"), ignore_ref=True):
            return "present"
        return "alias-suspect"
    for other in index["bySlug"].get(slug_key(row["slug"]), []):
        if other != suggested:
            return "alias-suspect"
    return "absent"


def tracked_state(row: dict, open_children: dict) -> str:
    """Return ``child:#N`` only for an open child with the same source-qualified identity."""
    number = (
        open_children.get(candidate_identity(row))
        if isinstance(open_children, _ChildIndex)
        else open_children.get(row["suggestedId"])
    )
    return f"child:#{number}" if number is not None else "none"


def prior_disposition(row: dict, rejected: dict) -> str:
    """Return a rejection only for a child with the same source-qualified identity."""
    number = (
        rejected.get(candidate_identity(row))
        if isinstance(rejected, _ChildIndex)
        else rejected.get(row["suggestedId"])
    )
    return f"rejected:#{number}" if number is not None else "none"


def index_children(issues: list[dict]) -> tuple[dict, dict]:
    """Index children by suggested ID and normalized source blob path.

    ``issues`` are raw REST issue dicts from a LIST call (open and closed).
    Only ``upstream:child`` issues count. A child with a suggested ID but no
    uniquely supported source URL makes the snapshot ambiguous and fails closed.
    """
    open_children = _ChildIndex()
    rejected = _ChildIndex()
    for issue in issues:
        if issue.get("pull_request"):
            continue
        labels = {label["name"] if isinstance(label, dict) else label for label in issue.get("labels", [])}
        if "upstream:child" not in labels:
            continue
        body = issue.get("body") or ""
        suggested = suggested_id_of(body)
        if not suggested:
            continue
        target = open_children if issue.get("state") == "open" else rejected
        if issue.get("state") == "open" or "upstream:rejected" in labels:
            target.setdefault(suggested, issue["number"])
            try:
                identity = child_source_identity(body, suggested)
            except AmbiguousChildIdentity:
                target.ambiguous_ids.add(suggested)
            else:
                target.by_identity.setdefault(identity, issue["number"])
    return open_children, rejected


def precheck_row(row: dict, index: dict, open_children: dict[str, int], rejected: dict[str, int]) -> dict:
    """Return the precheck record and the derived status for one candidate row."""
    precheck = {
        "registry": registry_state(row, index),
        "tracked": tracked_state(row, open_children),
        "priorDisposition": prior_disposition(row, rejected),
    }
    if precheck["priorDisposition"] != "none":
        status = "rejected"
    elif precheck["registry"] == "present":
        status = "present"
    elif precheck["tracked"] != "none":
        status = "tracked"
    else:
        status = "new"
    return {"precheck": precheck, "status": status}
