"""Compact current-state checkpoint and claim status for resumed curation (#2052).

Pure, offline helpers. Nothing here reads the registry, calls a model, or
writes a file. Callers pass in already-loaded dictionaries.

Two contracts (canonical text: ``docs/agents/curation-authority-map.md`` §5–§6):

1. **Claim status.** Every reported metric or draft assertion carries one of
   ``verified`` / ``reported`` / ``inferred`` / ``unknown``. A claim may be
   exported as ``verified`` only with ``repro`` provenance. Without it,
   ``exportClaims`` downgrades the claim and records why.
2. **Resumed blockers.** A resumed run reads the checkpoint's blockers, not
   raw history. A resolved blocker that has resolution evidence stays
   resolved, unless a *fresh* failing check with the same ``checkId``
   re-raises it. A resolved blocker without evidence is not trusted.
"""

from __future__ import annotations

from typing import Any, Iterable

CLAIM_STATUSES = ("verified", "reported", "inferred", "unknown")


def claimStatus(claim: dict[str, Any]) -> str:
    """Return the claim's declared status, normalising unknown values to ``unknown``."""
    status = claim.get("status")
    return status if status in CLAIM_STATUSES else "unknown"


def exportClaims(claims: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return export-safe copies of ``claims``.

    - ``verified`` needs ``repro``. Without it the claim becomes ``reported``
      (when it names a ``source``) or ``unknown``, with
      ``downgradedFrom: "verified"``.
    - ``inferred`` needs a ``method`` naming the derivation. Without one it
      becomes ``unknown``.
    - An unrecognised status becomes ``unknown``.
    """
    out: list[dict[str, Any]] = []
    for claim in claims:
        exported = dict(claim)
        declared = claim.get("status")
        status = claimStatus(claim)
        if status == "verified" and not claim.get("repro"):
            status = "reported" if claim.get("source") else "unknown"
            exported["downgradedFrom"] = "verified"
            exported["downgradeReason"] = "no repro provenance"
        elif status == "inferred" and not claim.get("method"):
            status = "unknown"
            exported["downgradedFrom"] = "inferred"
            exported["downgradeReason"] = "no derivation method"
        elif declared not in CLAIM_STATUSES:
            exported["downgradeReason"] = f"unrecognised status {declared!r}"
        exported["status"] = status
        out.append(exported)
    return out


def activeBlockers(
    checkpoint: dict[str, Any],
    freshFailingChecks: Iterable[dict[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Return the blockers a resumed run must treat as current.

    ``checkpoint["blockers"]`` entries carry ``checkId``, ``status``
    (``open`` / ``resolved``), optional ``resolutionEvidence``, and an optional
    ``summary``. ``freshFailingChecks`` lists checks that failed in *this*
    resume run, each with a ``checkId`` and ``evidence``.

    Result entries copy the blocker and set ``currentStatus``:

    - ``open``: still open in the checkpoint.
    - ``unproven-resolution``: marked resolved, but with no evidence to show it.
    - ``regressed``: resolved earlier, re-raised by a fresh failing check.
    - ``new``: a fresh failing check that no blocker in the checkpoint covers.
    """
    fresh = {}
    for check in freshFailingChecks:
        checkId = check.get("checkId")
        if checkId:
            fresh[checkId] = check

    current: list[dict[str, Any]] = []
    seen: set[str] = set()
    for blocker in checkpoint.get("blockers") or []:
        checkId = blocker.get("checkId")
        if checkId:
            seen.add(checkId)
        status = blocker.get("status")
        entry = dict(blocker)
        if status == "resolved":
            if checkId in fresh:
                entry["currentStatus"] = "regressed"
                entry["freshEvidence"] = fresh[checkId].get("evidence")
                current.append(entry)
            elif not blocker.get("resolutionEvidence"):
                entry["currentStatus"] = "unproven-resolution"
                current.append(entry)
            continue
        entry["currentStatus"] = "open"
        if checkId in fresh:
            entry["freshEvidence"] = fresh[checkId].get("evidence")
        current.append(entry)

    for checkId, check in fresh.items():
        if checkId not in seen:
            current.append({
                "checkId": checkId,
                "currentStatus": "new",
                "freshEvidence": check.get("evidence"),
            })
    return current


def compactCheckpoint(
    checkpoint: dict[str, Any],
    freshFailingChecks: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Return the compact current state a resumed run should read first."""
    fresh = list(freshFailingChecks)
    active = activeBlockers(checkpoint, fresh)
    activeIds = {b.get("checkId") for b in active}
    resolved = [
        {"checkId": b.get("checkId"), "resolutionEvidence": b.get("resolutionEvidence")}
        for b in checkpoint.get("blockers") or []
        if b.get("status") == "resolved"
        and b.get("resolutionEvidence")
        and b.get("checkId") not in activeIds
    ]
    return {
        "activeBlockers": active,
        "resolvedBlockers": resolved,
        "sourceRevisions": dict(checkpoint.get("sourceRevisions") or {}),
    }
