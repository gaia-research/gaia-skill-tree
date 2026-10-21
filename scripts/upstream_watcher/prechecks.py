"""
scripts.upstream_watcher.prechecks — deterministic prechecks for batch candidates (#2131).

Every candidate row in an umbrella's batch record is checked BEFORE any write:

registry    absent | present | alias-suspect
              present        = registry id equals the suggested id AND the
                               registry links.github (blob-normalized) equals the
                               candidate evidence URL (blob-normalized).
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

SUPPRESSED_STATUSES = frozenset({"present", "tracked", "rejected"})

_SUGGESTED_ID_RE = re.compile(r"\*\*Suggested ID:\*\*\s*`([^`]+)`")
_UMBRELLA_RE = re.compile(r"Umbrella:\s*#(\d+)")


class RegistryUnreadable(RuntimeError):
    """The named-skill registry could not be read or is empty (fail closed)."""


def normalize_blob(url: str | None) -> str:
    """Return a comparable form of a GitHub URL.

    ``tree/`` is rewritten to ``blob/``, ``.git`` and trailing slashes are
    dropped, and host/owner/repo are lowercased. The path is kept case-sensitive.
    Returns "" for anything that is not a GitHub owner/repo URL.
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
    tail = "/".join(rest).rstrip("/")
    base = f"{parts.netloc.lower()}/{owner}/{repo}"
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
            "links": normalize_blob(links.get("github")),
            "status": fm.get("status"),
        }
        by_slug.setdefault(slug_key(rid.split("/")[-1]), []).append(rid)
    return {"byId": by_id, "bySlug": by_slug}


def registry_state(row: dict, index: dict) -> str:
    """Return ``present``, ``alias-suspect`` or ``absent`` for a candidate row."""
    suggested = row["suggestedId"]
    entry = index["byId"].get(suggested)
    if entry is not None:
        if entry["links"] and entry["links"] == normalize_blob(row.get("evidenceUrl")):
            return "present"
        return "alias-suspect"
    for other in index["bySlug"].get(slug_key(row["slug"]), []):
        if other != suggested:
            return "alias-suspect"
    return "absent"


def tracked_state(row: dict, open_children: dict[str, int]) -> str:
    """Return ``child:#N`` when an open intake child already tracks the candidate."""
    number = open_children.get(row["suggestedId"])
    return f"child:#{number}" if number is not None else "none"


def prior_disposition(row: dict, rejected: dict[str, int]) -> str:
    """Return ``rejected:#N`` when a closed, rejected intake child covers the candidate."""
    number = rejected.get(row["suggestedId"])
    return f"rejected:#{number}" if number is not None else "none"


def index_children(issues: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    """Map suggested ids to issue numbers for open and rejected intake children.

    ``issues`` are raw REST issue dicts from a LIST call (open and closed).
    Only ``upstream:child`` issues count. Returns (open_children, rejected).
    """
    open_children: dict[str, int] = {}
    rejected: dict[str, int] = {}
    for issue in issues:
        if issue.get("pull_request"):
            continue
        labels = {label["name"] if isinstance(label, dict) else label for label in issue.get("labels", [])}
        if "upstream:child" not in labels:
            continue
        suggested = suggested_id_of(issue.get("body") or "")
        if not suggested:
            continue
        if issue.get("state") == "open":
            open_children.setdefault(suggested, issue["number"])
        elif "upstream:rejected" in labels:
            rejected.setdefault(suggested, issue["number"])
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
