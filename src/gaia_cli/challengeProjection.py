"""Public challenge artifacts, each mirrored byte-identically from ``docs/graph/challenges`` to
``docs/api/v1/challenges``.

``index.json`` is ``gaia-challenge-projection/v1``. ``sourceStatus``:

* ``unavailable`` no challenge has been admitted through the production resolver (or anything
                  below failed): ``subjects`` is empty and the UI renders nothing;
* ``verified``    at least one challenge was admitted, receipt verified and bound to its bundle.

``verified-empty`` is reserved by the contract but never produced: a tooling probe is not proof
that the set of challenges is empty. The file is fail-closed as a whole: any inconsistency
yields the ``unavailable`` document. Consequence is only ``current-baseline`` |
``approved-decision`` (``unavailable`` while no canonical consequence source exists). No
proposed value is ever published, and there is no ``pendingProposal`` field until an
adjudication ledger exists to point into.

``reviews.json`` is the separate ``gaia-challenge-review/v1`` artifact: held admissions and leads rejected at triage,
never part of the index, never labelled as a dispute.
"""
from __future__ import annotations

import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any

from . import challengeAdmission as admission
from .challengeAdmission import REASONS
from .committedChallenges import REVIEWCONTRACT, DEFERREDSTATUS, TRIAGESTATUS, Collected, collect, lifecyclePorts
from .lifecycleProjection import produce_lifecycle

CONTRACT = "gaia-challenge-projection/v1"
STATUSES = ("unavailable", "verified")
RESERVED = ("verified-empty",)
CONSEQUENCES = ("current-baseline", "approved-decision", "unavailable")
FILES = {"index": ("docs/graph/challenges/index.json", "docs/api/v1/challenges/index.json"),
         "reviews": ("docs/graph/challenges/reviews.json", "docs/api/v1/challenges/reviews.json")}
CONTESTED = re.compile(r"contested", re.IGNORECASE)
SYSTEMFIELDS = ("contract", "status", "held", "triage", "disclosure")  # experiment/assessment hold challenger-authored strings
FORBIDDENKEYS = re.compile(r"contested|propos|^(tm|stars?|grade|origin|level|trustmagnitude|rank)$", re.IGNORECASE)


def emptyIndex() -> dict[str, Any]:
    return {"contract": CONTRACT, "sourceStatus": "unavailable", "subjects": []}


def emptyReviews() -> dict[str, Any]:
    return {"contract": REVIEWCONTRACT, "reviews": []}


def strings(value: Any):
    if isinstance(value, dict):
        for child in value.values():
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


def validateReview(record: Any) -> list[str]:
    """One held-review record. The word guard covers only fields the system generates;
    challenger-authored text (claim, comparator, challenger) is data, not a label."""
    if not isinstance(record, dict):
        return ["review must be an object"]
    errors = []
    status = record.get("status")
    if record.get("contract") != REVIEWCONTRACT or status not in ("admission-held", TRIAGESTATUS, DEFERREDSTATUS):
        errors.append("review must be a held or rejected-at-triage gaia-challenge-review/v1 record")
    held = record.get("held")
    if status in (TRIAGESTATUS, DEFERREDSTATUS):
        if "held" in record or not isinstance(record.get("triage"), dict) or "experiment" in record:
            errors.append("a triage review carries a triage note and no held reason or experiment")
    elif not isinstance(held, dict) or held.get("reason") not in REASONS:
        errors.append("held.reason must be a known hold reason")
    system = {name: record.get(name) for name in SYSTEMFIELDS}
    if any(CONTESTED.search(text) for text in strings(system)):
        errors.append("a held review must never be labelled contested")
    if any(FORBIDDENKEYS.search(name) for name in keys(record)):
        errors.append("review carries a forbidden key (dispute label, proposal or Gaia number)")
    return errors


def validateReviews(document: Any) -> list[str]:
    if not isinstance(document, dict) or set(document) != {"contract", "reviews"} or document["contract"] != REVIEWCONTRACT:
        return ["reviews document must carry exactly contract and reviews"]
    if not isinstance(document["reviews"], list):
        return ["reviews must be a list"]
    return [error for record in document["reviews"] for error in validateReview(record)]


def validate(document: Any) -> list[str]:
    """Whole-file checks for ``index.json``, used by the builder (to fail closed) and by tests."""
    if not isinstance(document, dict) or set(document) != {"contract", "sourceStatus", "subjects"}:
        return ["document must carry exactly contract, sourceStatus and subjects"]
    errors = []
    if document["contract"] != CONTRACT:
        errors.append("contract mismatch")
    status = document["sourceStatus"]
    if status not in STATUSES:
        errors.append("sourceStatus is not a produced state")
    if not isinstance(document["subjects"], list):
        return errors + ["subjects must be a list"]
    if status == "unavailable" and document["subjects"]:
        errors.append("unavailable must have empty collections")
    if status == "verified" and not document["subjects"]:
        errors.append("verified requires at least one admitted subject")
    seen = set()
    for subject in document["subjects"]:
        if not isinstance(subject, dict) or set(subject) != {
                "subjectId", "genericSkillRef", "materialOriginContested", "consequence", "challenges"}:
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
    for name in keys(document["subjects"]):
        if "propos" in name.lower():
            errors.append(f"proposed values are never published: {name}")
    return errors


def buildIndex(root: str | Path, *, collected: Collected | None = None) -> dict[str, Any]:
    """Build ``index.json``; any failure is logged and returns the ``unavailable`` document."""
    try:
        found = collected if collected is not None else collect(root)
        if found.sourceStatus == "unavailable":
            return emptyIndex()
        ports = lifecyclePorts(found)
        if ports is None:
            raise ValueError("admitted challenges but no usable lifecycle ports")
        subjects = []
        for subject in sorted(found.admitted):
            dto = produce_lifecycle({"id": subject, "genericSkillRef": found.genericRefs[subject]}, ports)
            if dto is None:
                raise ValueError(f"lifecycle projection refused subject {subject}")
            subjects.append({
                "subjectId": subject, "genericSkillRef": dto["genericSkillRef"],
                "materialOriginContested": dto["materialOriginContested"], "consequence": dto["consequence"],
                "challenges": dto["challenges"]})
        document = {"contract": CONTRACT, "sourceStatus": "verified", "subjects": subjects}
        errors = validate(document)
        if errors:
            raise ValueError("; ".join(errors))
        return document
    except Exception as exc:
        print(f"  warning: challenge projection failed closed ({type(exc).__name__}: {exc}); publishing 'unavailable'",
              file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return emptyIndex()


def buildReviews(root: str | Path, *, collected: Collected | None = None) -> dict[str, Any]:
    try:
        found = collected if collected is not None else collect(root)
        if found.disabled:
            return emptyReviews()
        kept = []
        for record in found.reviews:  # drop only the offending record, as the named-index channel does
            errors = validateReview(record)
            if errors:
                print(f"  warning: dropping review {record.get('caseId')}: {'; '.join(errors)}", file=sys.stderr)
            else:
                kept.append(record)
        return {"contract": REVIEWCONTRACT, "reviews": kept}
    except Exception as exc:
        print(f"  warning: challenge reviews failed closed ({type(exc).__name__}: {exc}); publishing none",
              file=sys.stderr)
        return emptyReviews()


def render(document: Any) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sync(root: str | Path, *, check: bool) -> bool:
    """Write (or, with ``check``, only compare) all mirrors. Returns True when they drift/changed."""
    base = Path(root)
    found = collect(base)
    for item in found.rejected:  # never silent: every refused bundle is named with its reason
        print(f"  warning: challenge bundle {admission.clean(item['caseId'])} rejected: {admission.clean(item['reason'])}", file=sys.stderr)
    outputs = {"index": render(buildIndex(base, collected=found)), "reviews": render(buildReviews(base, collected=found))}
    changed = False
    for name, data in outputs.items():
        for relative in FILES[name]:
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
