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
        "generic": {
            "id": generic.get("id"), "name": generic.get("name"),
            "description": generic.get("description"), "type": generic.get("type"),
            "prerequisites": generic.get("prerequisites"),
        },
        "decision": packet.get("decision"),
        "suite": packet.get("suite"),
        "source": {
            "url": source.get("canonicalUrl"), "revision": source.get("commitSha"),
            "sha256": source.get("contentSha256"),
        },
        "packetSha256": _digest(packet),
        "assessmentSha256": _digest(assessment) if isinstance(assessment, dict) else None,
        "genericSnapshot": packet.get("genericSnapshot"),
        "liveContext": _liveContext(registryPath),
    }


def buildReviewPayload(packets, *, registryPath=".", submissionRoute="single-packet",
                       manifestDigest=None, inventory=None, assessments=None) -> dict:
    """Build the canonical review payload; authorization envelope is never input.

    ``manifestDigest`` is SHA-256 of the exact original manifest bytes, not a
    reserialized manifest. ``inventory`` is the complete ordered packet list
    resolved from that manifest. For multi-packet routes callers must supply
    both; leaf-only authorization is rejected.
    """
    rows = list(packets) if isinstance(packets, (list, tuple)) else [packets]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("review inventory must contain packet objects")
    isManifest = submissionRoute in {"manifest", "multi-packet-manifest"}
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
                              envelope=None) -> list[str]:
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
            assessments=assessments,
        )
    except Exception as exc:
        return [f"could not independently build authorization payload: {exc}"]
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
