"""Human L4 authorization boundary for discovery-packet intake.

The payload is independently reconstructed from the packet(s), live generic
catalog, assessment receipts, rubric and submission context. No fields inside
that payload (including reviewedBy, approvalRef, comments, flags or environment
variables) authenticate a reviewer. The production verifier intentionally
refuses all requests until a protected-default-branch Actions workflow and its
independently authenticated, immutable review artifact are configured here.

Tests may replace the private verifier with a clearly unit-only stub; callers
must not pass a verifier or trust policy through user-controlled input.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


AUTHORIZATION_CONTRACT = "gaia-l4-authorization-v1"


def canonicalJson(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def sha256Hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return sha256Hex(canonicalJson(value))


def _liveContext(registryPath: str) -> dict[str, Any]:
    # Import lazily: authorization is a security boundary and curation modules
    # have optional dependencies that should not affect unrelated CLI commands.
    from gaia_cli.curation.assessment import loadGenericSemantics, loadPrinciples

    catalog = loadGenericSemantics(registryPath)
    rubric = loadPrinciples()
    return {
        "genericCatalog": catalog,
        "genericCatalogSha256": _digest(catalog),
        "rubric": rubric,
        "rubricSha256": _digest(rubric),
    }


def _proposalPacket(packet: dict) -> dict:
    """Exclude authorization carriers from the independently hashed proposal.

    Local humanReview prose is display metadata, not an input that can grant or
    alter authority. Selected identity/definition/decision/source remain bound.
    """
    proposal = copy.deepcopy(packet)
    for key in ("authorization", "authorizationEnvelope"):
        proposal.pop(key, None)
    resolution = proposal.get("l4Resolution")
    if isinstance(resolution, dict):
        for key in ("authorization", "authorizationEnvelope", "humanReview"):
            resolution.pop(key, None)
    return proposal


def _reviewRow(packet: dict, registryPath: str, assessment: dict | None) -> dict:
    resolution = packet.get("l4Resolution")
    resolution = resolution if isinstance(resolution, dict) else {}
    generic = resolution.get("generic")
    named = resolution.get("named")
    source = packet.get("source")
    generic = generic if isinstance(generic, dict) else {}
    named = named if isinstance(named, dict) else {}
    source = source if isinstance(source, dict) else {}
    # Bind the complete source identity, topology and exact names rather than
    # retrieval rank/top-K position. Human choice outside top-K remains valid.
    return {
        "candidateId": packet.get("candidateId"),
        "namedIdentity": {
            "contributor": named.get("contributor"),
            "skillName": named.get("skillName"),
        },
        "generic": copy.deepcopy(generic),
        "decision": packet.get("decision"),
        "suite": packet.get("suite"),
        "source": {
            "url": source.get("canonicalUrl"),
            "revision": source.get("commitSha") or source.get("revision") or source.get("resolvedCommit"),
            "sha256": source.get("contentSha256"),
        },
        "packetSha256": _digest(_proposalPacket(packet)),
        "assessmentSha256": _digest(assessment) if isinstance(assessment, dict) else None,
        "genericSnapshot": packet.get("genericSnapshot"),
        "liveContext": _liveContext(registryPath),
    }


def buildReviewPayload(packets, *, registryPath=".", submissionRoute="single-packet",
                       manifestDigest=None, inventory=None, assessments=None,
                       reviewInventory=None, continuation=None) -> dict:
    """Build the canonical review payload; authorization envelope is never input.

    ``manifestDigest`` is SHA-256 of the exact original manifest bytes, not a
    reserialized manifest. ``inventory`` is the complete ordered packet list
    resolved from that manifest. For multi-packet routes callers must supply
    both; leaf-only authorization is rejected.
    """
    rows = list(packets) if isinstance(packets, (list, tuple)) else [packets]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("review inventory must contain packet objects")
    if submissionRoute not in {"single-packet", "manifest", "multi-packet-manifest", "existing-intake", "existing-intake-manifest"}:
        raise ValueError("unsupported submission route")
    isManifest = submissionRoute in {"manifest", "multi-packet-manifest", "existing-intake-manifest"}
    if isManifest and (not isinstance(inventory, (list, tuple)) or not inventory
                       or not isinstance(manifestDigest, str)):
        raise ValueError("manifest authorization requires the full inventory and exact manifest byte digest")
    inventoryRows = list(inventory) if inventory is not None else rows
    if not inventoryRows or any(not isinstance(row, dict) for row in inventoryRows):
        raise ValueError("full review inventory must contain packet objects")
    if rows != inventoryRows:
        raise ValueError("authorized packets must equal the complete manifest inventory")
    if manifestDigest is not None and (len(manifestDigest) != 64 or any(c not in "0123456789abcdef" for c in manifestDigest)):
        raise ValueError("manifestDigest must be a lowercase SHA-256 of exact original manifest bytes")
    assessments = assessments or {}
    if not isinstance(assessments, dict):
        raise ValueError("assessments must map candidate IDs to validated receipt objects")
    identities = [packet.get("candidateId") for packet in inventoryRows]
    if any(not isinstance(cid, str) or not cid for cid in identities) or len(identities) != len(set(identities)):
        raise ValueError("review inventory requires unique exact candidate IDs")
    if reviewInventory is not None:
        frozen = reviewInventory.get("inventory", {})
        report = reviewInventory.get("reconciliation", {})
        receipts = reviewInventory.get("receipts")
        expected = frozen.get("candidates", [])
        outcomes = report.get("decisions", [])
        expectedIds = [row["candidateId"] for row in expected]
        outcomeIds = [row["candidateId"] for row in outcomes]
        if len(set(expectedIds)) != len(expectedIds) or sorted(expectedIds) != sorted(outcomeIds) or len(set(outcomeIds)) != len(outcomeIds):
            raise ValueError("review accounting must contain every expected candidate exactly once")
        from gaia_cli.curation.reconciliation import canonicalJson as inventoryJson, sha256 as inventoryHash, OUTCOMES
        unsigned = {key: value for key, value in frozen.items() if key != "inventoryDigest"}
        if frozen.get("inventoryDigest") != inventoryHash(inventoryJson(unsigned)) or report.get("inventoryDigest") != frozen.get("inventoryDigest"):
            raise ValueError("review inventory/reconciliation digest mismatch")
        if any(row.get("outcome") not in OUTCOMES for row in outcomes):
            raise ValueError("unaccounted review outcome")
        # The report must be a genuine reconciliation of the frozen inventory:
        # every candidate accounted for, no receipt left invalid, and no claim
        # of human approval (approval is exactly what is still missing here).
        if report.get("accounted") is not True:
            raise ValueError("review accounting must be a fully accounted reconciliation")
        if report.get("humanApproved") is not False:
            raise ValueError("review accounting must not claim human approval")
        # A report is a CLAIM. It is only evidence when it can be recomputed
        # from the receipts it says it came from. Recompute the reconciliation
        # here and require the claimed report to agree with it, so a
        # hand-forged "review-ready" row cannot be bound into a payload.
        if not isinstance(receipts, list) or not receipts:
            raise ValueError("review accounting must carry the receipts that produced it")
        from gaia_cli.curation.reconciliation import reconcileInventory

        recomputed = reconcileInventory(frozen, receipts, packetRoot=registryPath)
        if recomputed.get("accounted") is not True:
            raise ValueError("review accounting receipts do not reconcile the frozen inventory")
        if recomputed.get("humanApproved") is not False:
            raise ValueError("review accounting must not claim human approval")
        claimedById = {row["candidateId"]: row for row in outcomes}
        for row in recomputed.get("decisions", []):
            claimed = claimedById.get(row["candidateId"])
            if claimed is None:
                raise ValueError(f"review accounting omits reconciled candidate {row['candidateId']}")
            if claimed.get("outcome") != row.get("outcome"):
                raise ValueError(f"review accounting outcome disagrees with the receipts for {row['candidateId']}")
            if claimed.get("receiptValid") is not True or row.get("receiptValid") is not True:
                raise ValueError(f"review accounting has an invalid receipt for {row['candidateId']}")
        packetsById = {packet["candidateId"]: packet for packet in inventoryRows}
        frozenById = {row["candidateId"]: row for row in expected}
        outcomesById = {row["candidateId"]: row for row in outcomes}
        outcomeForDecision = {
            "MAP": "review-ready", "NEW_GENERIC": "review-ready",
            "DEFER": "deferred", "NOT_A_SKILL": "rejected",
            "DUPLICATE": "proven-duplicate",
        }
        for candidateId, frozenRow in frozenById.items():
            packet = packetsById.get(candidateId)
            if packet is None:
                continue
            source = packet.get("source") if isinstance(packet.get("source"), dict) else {}
            # Use the SAME identity resolution rule as reconciliation, so a
            # legitimate packet is never rejected for binding its identity in a
            # different (but equivalent) place.
            from gaia_cli.curation.reconciliation import packetNamedIdentity

            identity = packetNamedIdentity(packet)
            if identity != frozenRow.get("namedIdentity"):
                raise ValueError(f"review inventory named identity mismatch for {candidateId}")
            packetRevision = source.get("commitSha") or source.get("revision") or source.get("resolvedCommit")
            if (source.get("canonicalUrl") != frozenRow.get("canonicalUrl")
                    or packetRevision != frozenRow.get("sourceRevision")
                    or source.get("contentSha256") != frozenRow.get("sourceDigest")):
                raise ValueError(f"review inventory source provenance mismatch for {candidateId}")
            reportRow = outcomesById[candidateId]
            decision = packet.get("decision") if isinstance(packet.get("decision"), dict) else {}
            proposed = {"decision": decision.get("value")}
            if decision.get("value") == "MAP":
                proposed["genericId"] = decision.get("genericId")
            elif decision.get("value") == "NEW_GENERIC" and isinstance(decision.get("proposal"), dict):
                proposed["proposal"] = decision["proposal"]
            if (reportRow.get("outcome") != outcomeForDecision.get(decision.get("value"))
                    or reportRow.get("proposedGeneric") != proposed):
                raise ValueError(f"reconciliation decision disagrees with packet for {candidateId}")
            assessment = assessments.get(candidateId)
            expectedPacketDigest = inventoryHash(inventoryJson(packet))
            expectedProposalDigest = inventoryHash(inventoryJson(_proposalPacket(packet)))
            if reportRow.get("receiptValid") is not True:
                raise ValueError(f"review accounting has an invalid receipt for {candidateId}")
            if reportRow.get("packetDigest") != expectedPacketDigest:
                raise ValueError(f"reconciliation packet digest mismatch for {candidateId}")
            if reportRow.get("packetProposalSha256") != expectedProposalDigest:
                raise ValueError(f"reconciliation packet proposal digest mismatch for {candidateId}")
            if not isinstance(assessment, dict):
                raise ValueError(f"review accounting requires a real assessment for {candidateId}")
            if reportRow.get("assessmentSha256") != _digest(assessment):
                raise ValueError(f"reconciliation assessment digest mismatch for {candidateId}")
        ready = [row["candidateId"] for row in outcomes if row.get("outcome") == "review-ready"]
        if sorted(ready) != sorted(identities):
            raise ValueError("submitted packets must equal all review-ready accounted candidates")
    reviewRows = []
    for packet in inventoryRows:
        candidateId = packet.get("candidateId")
        assessment = assessments.get(candidateId)
        reviewRows.append(_reviewRow(packet, registryPath, assessment))
    return {
        "contractVersion": AUTHORIZATION_CONTRACT,
        "submissionRoute": submissionRoute,
        "manifestSha256": manifestDigest,
        "inventory": reviewRows,
        "inventorySha256": _digest(reviewRows),
        "completeAccounting": copy.deepcopy(reviewInventory),
        "continuation": copy.deepcopy(continuation),
    }


def _verifyTrustedEnvelope(payload: dict, envelope: dict | None, *, registryPath=".") -> list[str]:
    """Production trust hook. Disabled until a real protected workflow is wired.

    A future implementation must verify through the GitHub Actions API the
    canonical workflow path/ref and protected environment approval; verify the
    successful run, attempt, actors and permissions independently; prove the
    reviewer differs from the submitting/calling agent; download the unique
    immutable artifact bytes; compare the artifact's complete payload digest;
    and check revocation/current policy. The existing topology-approval
    workflow is NOT sufficient: it does not review this payload and has no
    protected environment gate. Never replace this refusal with local flags,
    comments, JSON claims or environment-variable bypasses.
    """
    return ["independent protected human authorization is not configured; L4 remains pending"]


def verifyPacketAuthorization(packet, *, registryPath=".", submissionRoute="single-packet",
                              manifestDigest=None, inventory=None, assessments=None,
                              envelope=None, reviewInventory=None, continuation=None) -> list[str]:
    """Recompute review bindings and authenticate an external authorization.

    ``envelope`` is only a pointer/data carrier; its contents are not trusted.
    The production verifier is fail-closed until a trusted workflow policy is
    implemented. Returns errors, matching the lane-B freshness API convention.
    """
    try:
        payload = buildReviewPayload(
            packet if isinstance(packet, (list, tuple)) else [packet],
            registryPath=registryPath, submissionRoute=submissionRoute,
            manifestDigest=manifestDigest, inventory=inventory,
            assessments=assessments, reviewInventory=reviewInventory,
            continuation=continuation,
        )
    except Exception as exc:
        return [f"could not independently build authorization payload: {exc}"]
    if submissionRoute in {"manifest", "multi-packet-manifest", "existing-intake-manifest"} and reviewInventory is None:
        return ["trusted manifest authorization requires complete frozen inventory and reconciliation accounting"]
    if submissionRoute.startswith("existing-intake") and not isinstance(continuation, dict):
        return ["existing-intake authorization requires exact original batch and issue references"]
    if not isinstance(envelope, dict):
        return _verifyTrustedEnvelope(payload, None, registryPath=registryPath)
    claimedDigest = envelope.get("reviewPayloadSha256")
    if claimedDigest != _digest(payload):
        return ["authorization envelope does not bind the independently computed review payload"]
    return _verifyTrustedEnvelope(payload, envelope, registryPath=registryPath)


def verifyFreshness(packet, *, registryPath=".") -> list[str]:
    """Invoke lane B's independent source/catalog/dedupe freshness check lazily."""
    try:
        from gaia_cli.curation.freshness import verifyPacketFreshness
    except ImportError:
        return ["independent packet freshness verifier is unavailable; intake remains pending"]
    try:
        return list(verifyPacketFreshness(packet, registryPath=registryPath))
    except Exception as exc:
        return [f"packet freshness verification failed closed: {exc}"]


def exactManifestDigest(manifestPath: str | Path) -> str:
    """Hash the exact bytes read from a manifest file."""
    return sha256Hex(Path(manifestPath).read_bytes())
