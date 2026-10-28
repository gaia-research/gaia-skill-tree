"""Public challenge projection ``gaia-challenge-projection/v1`` (one artifact, two mirrors).

``docs/graph/challenges/index.json`` is mirrored byte-identically to
``docs/api/v1/challenges/index.json``. ``sourceStatus``:

* ``unavailable``   no admission path is verifiable (no committed case ledger, or the issuer
                    pins/tooling do not verify in this build, or anything below failed):
                    every collection is empty and the UI renders nothing;
* ``verified-empty`` the issuer path verifies, the case ledger was read, nothing is admitted;
* ``verified``      at least one challenge was admitted through the production resolver.

The file is fail-closed as a whole: any inconsistency yields the ``unavailable`` document.
Consequence is only ``current-baseline`` | ``approved-decision`` (or ``unavailable`` when no
canonical consequence source exists). A proposal appears only as ``pendingProposal``, a
pointer into the adjudication ledger; no proposed number is ever published. Held admissions
appear only as labelled ``reviews[]`` (``gaia-challenge-review/v1``), never as disputes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .committedChallenges import REVIEWCONTRACT, Collected, collect, lifecyclePorts
from .lifecycleProjection import produce_lifecycle

CONTRACT = "gaia-challenge-projection/v1"
STATUSES = ("unavailable", "verified-empty", "verified")
CONSEQUENCES = ("current-baseline", "approved-decision", "unavailable")
GRAPHPATH = "docs/graph/challenges/index.json"
APIPATH = "docs/api/v1/challenges/index.json"
CONTESTED = re.compile(r"contested", re.IGNORECASE)


def emptyDocument(status: str = "unavailable") -> dict[str, Any]:
    return {"contract": CONTRACT, "sourceStatus": status, "subjects": [], "reviews": []}


def pointerOf(value: Any) -> dict[str, str] | None:
    """A pending proposal is only an id/path pointer into the adjudication ledger."""
    if value is None:
        return None
    if (not isinstance(value, Mapping) or set(value) != {"id", "path"}
            or not all(isinstance(value[key], str) and value[key].strip() for key in ("id", "path"))
            or value["path"].startswith("/") or ".." in Path(value["path"]).parts):
        raise ValueError("pendingProposal must be exactly an id and a repo-relative path")
    return {"id": value["id"], "path": value["path"]}


def strings(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
    elif isinstance(value, str):
        yield value


def keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys(child)


def validate(document: Any) -> list[str]:
    """Whole-file checks used by the builder (to fail closed) and by tests."""
    if not isinstance(document, dict) or set(document) != {"contract", "sourceStatus", "subjects", "reviews"}:
        return ["document must carry exactly contract, sourceStatus, subjects and reviews"]
    errors = []
    if document["contract"] != CONTRACT:
        errors.append("contract mismatch")
    status = document["sourceStatus"]
    if status not in STATUSES:
        errors.append("sourceStatus is not recognised")
    if not isinstance(document["subjects"], list) or not isinstance(document["reviews"], list):
        return errors + ["subjects and reviews must be lists"]
    if status == "unavailable" and (document["subjects"] or document["reviews"]):
        errors.append("unavailable must have empty collections")
    if status == "verified-empty" and document["subjects"]:
        errors.append("verified-empty cannot carry subjects")
    if status == "verified" and not document["subjects"]:
        errors.append("verified requires at least one admitted subject")
    seen = set()
    for subject in document["subjects"]:
        if not isinstance(subject, dict) or set(subject) != {
                "subjectId", "genericSkillRef", "materialOriginContested", "consequence", "pendingProposal", "challenges"}:
            errors.append("subject has the wrong shape")
            continue
        if subject["subjectId"] in seen:
            errors.append("duplicate subject")
        seen.add(subject["subjectId"])
        consequence = subject["consequence"]
        if not isinstance(consequence, dict) or consequence.get("kind") not in CONSEQUENCES:
            errors.append("consequence must be current-baseline, approved-decision or unavailable")
        if type(subject["materialOriginContested"]) is not bool or not subject["challenges"]:
            errors.append("subject needs a boolean origin flag and at least one challenge")
        try:
            pointerOf(subject["pendingProposal"])
        except ValueError as exc:
            errors.append(str(exc))
    for review in document["reviews"]:
        if not isinstance(review, dict) or review.get("contract") != REVIEWCONTRACT or review.get("status") != "admission-held":
            errors.append("review must be a held gaia-challenge-review/v1 record")
        elif any(CONTESTED.search(text) for text in strings(review)):
            errors.append("a held review must never be labelled contested")
    for name in keys({"subjects": [{key: value for key, value in subject.items() if key != "pendingProposal"}
                                   for subject in document["subjects"] if isinstance(subject, dict)],
                      "reviews": document["reviews"]}):
        if "propos" in name.lower():
            errors.append(f"proposed values are never published: {name}")
    return errors


def build(root: str | Path, *, collected: Collected | None = None,
          pending: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build the projection; any failure returns the ``unavailable`` document."""
    try:
        found = collected if collected is not None else collect(root)
        status = found.sourceStatus
        if status == "unavailable":
            return emptyDocument()
        subjects = []
        if found.admitted:
            ports = lifecyclePorts(found)
            if ports is None:
                return emptyDocument()
            for subject in sorted(found.admitted):
                dto = produce_lifecycle({"id": subject, "genericSkillRef": found.genericRefs[subject]}, ports)
                if dto is None:
                    return emptyDocument()
                subjects.append({
                    "subjectId": subject, "genericSkillRef": dto["genericSkillRef"],
                    "materialOriginContested": dto["materialOriginContested"], "consequence": dto["consequence"],
                    "pendingProposal": pointerOf((pending or {}).get(subject)), "challenges": dto["challenges"]})
        document = {"contract": CONTRACT, "sourceStatus": status, "subjects": subjects,
                    "reviews": list(found.reviews)}
        return document if not validate(document) else emptyDocument()
    except Exception:
        return emptyDocument()


def render(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sync(root: str | Path, *, check: bool) -> bool:
    """Write (or, with ``check``, only compare) both mirrors. Returns True when they drift/changed."""
    base = Path(root)
    data = render(build(base))
    changed = False
    for relative in (GRAPHPATH, APIPATH):
        path = base / relative
        if path.is_file() and path.read_bytes() == data:
            continue
        changed = True
        if check:
            print(f"diff {relative}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return changed
