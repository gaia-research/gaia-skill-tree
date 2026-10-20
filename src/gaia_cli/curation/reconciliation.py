"""Deterministic inventory freeze and reconciliation for discovery-packet-v2.

Lane C API for the chain/orchestrator: ``freezeInventory(candidates)`` freezes
candidate IDs, exact named identities, source revision/hash, and stable task IDs
before any dispatch. ``reconcileInventory(envelope, receipts, ...)`` verifies
receipts against that freeze and returns exactly one disposition per candidate.
This is an outer control envelope only; packet payloads remain discovery-packet-v2
and no alternate ontology or human approval is represented here.

Receipt contract: candidateId, taskId, attempt, inputDigest, outputDigest,
packetPath, packetHash, proposedGeneric, outcome; optionally packet (mapping) or
packetBytes (bytes). The actual packet bytes are independently hashed. A path is
read only beneath packetRoot (default current directory), and its bytes are the
authoritative output. Exact duplicates require explicit source proof matching a
frozen candidate's source URL, cited origin, or source SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

ENVELOPE_VERSION = "curation-inventory-v1"
OUTCOMES = {"review-ready", "deferred", "rejected", "proven-duplicate"}


def canonicalJson(value: Any) -> bytes:
    """Serialize JSON deterministically (UTF-8, sorted keys, compact form)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def freezeInventory(candidates: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Freeze a candidate inventory into deterministic, dispatch-ready rows.

    Each candidate must contain candidateId, namedIdentity, sourceRevision,
    sourceDigest, and packetInput (the immutable worker input). Optional source
    proof fields (canonicalUrl/citedOrigin) are retained. Duplicate candidate
    IDs are rejected rather than collapsed. Identity and source facts are copied
    into the envelope before workers can run.
    """
    rows = []
    seen: set[str] = set()
    for item in candidates:
        if not isinstance(item, Mapping):
            raise ValueError("each inventory candidate must be a mapping")
        candidate_id = _nonempty(item.get("candidateId"), "candidateId")
        if candidate_id in seen:
            raise ValueError(f"duplicate candidateId: {candidate_id}")
        seen.add(candidate_id)
        identity = _nonempty(item.get("namedIdentity"), f"{candidate_id}.namedIdentity")
        revision = item.get("sourceRevision")
        digest = item.get("sourceDigest")
        if not isinstance(revision, str) or not revision.strip():
            raise ValueError(f"{candidate_id}.sourceRevision must be a non-empty string")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
            raise ValueError(f"{candidate_id}.sourceDigest must be a SHA-256 hex digest")
        if "packetInput" not in item:
            raise ValueError(f"{candidate_id}.packetInput is required")
        packet_input = item["packetInput"]
        input_digest = sha256(canonicalJson(packet_input))
        task_id = "task-" + sha256(canonicalJson({
            "candidateId": candidate_id, "namedIdentity": identity,
            "sourceRevision": revision, "sourceDigest": digest.lower(),
            "inputDigest": input_digest,
        }))[:24]
        rows.append({
            "candidateId": candidate_id,
            "namedIdentity": identity,
            "sourceRevision": revision,
            "sourceDigest": digest.lower(),
            "canonicalUrl": item.get("canonicalUrl"),
            "citedOrigin": item.get("citedOrigin"),
            "packetInput": packet_input,
            "inputDigest": input_digest,
            "taskId": task_id,
            "assignedAttempt": 1,
        })
    rows.sort(key=lambda row: row["candidateId"])
    envelope = {"contractVersion": ENVELOPE_VERSION, "candidates": rows}
    envelope["inventoryDigest"] = sha256(canonicalJson(envelope))
    return envelope


def _safe_packet_bytes(receipt: Mapping[str, Any], packet_root: Path) -> bytes:
    if "packetBytes" in receipt:
        data = receipt["packetBytes"]
        if not isinstance(data, bytes):
            raise ValueError("packetBytes must be bytes")
        return data
    if "packet" in receipt:
        packet = receipt["packet"]
        if not isinstance(packet, Mapping) or packet.get("contractVersion") != "discovery-packet-v2":
            raise ValueError("packet must be a discovery-packet-v2 mapping")
        return canonicalJson(packet)
    path_value = receipt.get("packetPath")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("packet output is missing")
    path = Path(path_value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("packetPath must be a safe relative path")
    root = packet_root.resolve()
    resolved = (root / path).resolve(strict=True)
    if os.path.commonpath((str(root), str(resolved))) != str(root) or not resolved.is_file():
        raise ValueError("packetPath escapes packetRoot or is not a file")
    return resolved.read_bytes()


def _proof_matches(row: Mapping[str, Any], proof: Any) -> bool:
    if not isinstance(proof, Mapping):
        return False
    source = proof.get("source") if isinstance(proof.get("source"), Mapping) else proof
    return any((key in row and row.get(key) and source.get(key) == row.get(key)) for key in ("canonicalUrl", "citedOrigin")) or (
        bool(row.get("sourceDigest")) and source.get("contentSha256") == row.get("sourceDigest")
    )


def reconcileInventory(envelope: Mapping[str, Any], receipts: Iterable[Mapping[str, Any]], *, packetRoot: str | os.PathLike[str] = ".", genericDefinitions: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Verify worker receipts and conserve every frozen row exactly once.

    Invalid, absent, stale, or mismatched receipts become deferred rows. If
    multiple NEW_GENERIC definitions share an ID but differ in full definition,
    every proposer for that ID is rejected deterministically (never first-wins).
    ``review-ready`` means ready for L4 presentation only, never approved.
    """
    if not isinstance(envelope, Mapping) or envelope.get("contractVersion") != ENVELOPE_VERSION:
        raise ValueError("unsupported inventory envelope")
    frozen_rows = envelope.get("candidates")
    if not isinstance(frozen_rows, list):
        raise ValueError("inventory candidates must be a list")
    unsigned = {k: v for k, v in envelope.items() if k != "inventoryDigest"}
    if envelope.get("inventoryDigest") != sha256(canonicalJson(unsigned)):
        raise ValueError("inventory digest mismatch")
    rows = {row["candidateId"]: row for row in frozen_rows}
    if len(rows) != len(frozen_rows):
        raise ValueError("duplicate candidate in frozen inventory")
    accepted: dict[str, tuple[Mapping[str, Any], bytes]] = {}
    failures: dict[str, str] = {}
    for receipt in receipts:
        cid = receipt.get("candidateId") if isinstance(receipt, Mapping) else None
        row = rows.get(cid)
        if row is None:
            continue
        try:
            if cid in accepted:
                raise ValueError("multiple accepted receipts for candidate")
            if receipt.get("taskId") != row["taskId"]:
                raise ValueError("task binding mismatch")
            attempt = receipt.get("attempt")
            if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < row.get("assignedAttempt", 1):
                raise ValueError("invalid attempt")
            if receipt.get("inputDigest") != row["inputDigest"]:
                raise ValueError("input digest mismatch")
            data = _safe_packet_bytes(receipt, Path(packetRoot))
            actual_hash = sha256(data)
            if receipt.get("outputDigest") != actual_hash or receipt.get("packetHash") != actual_hash:
                raise ValueError("actual packet output hash mismatch")
            packet = json.loads(data.decode("utf-8"))
            if not isinstance(packet, dict) or packet.get("contractVersion") != "discovery-packet-v2":
                raise ValueError("output is not discovery-packet-v2")
            if packet.get("candidateId") != cid:
                raise ValueError("packet candidate identity mismatch")
            if receipt.get("outcome") not in OUTCOMES:
                raise ValueError("invalid outcome")
            if receipt["outcome"] == "proven-duplicate" and not _proof_matches(row, receipt.get("duplicateProof")):
                raise ValueError("exact duplicate lacks matching source proof")
            accepted[cid] = (receipt, data)
        except (ValueError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            failures[cid] = str(exc)
    proposals: dict[str, list[tuple[str, Any]]] = {}
    rejected: dict[str, str] = {}
    for cid, (receipt, _) in accepted.items():
        proposal = receipt.get("proposedGeneric")
        if isinstance(proposal, Mapping) and proposal.get("decision") == "NEW_GENERIC":
            generic_id = proposal.get("genericId")
            definition = proposal.get("definition")
            if isinstance(generic_id, str) and isinstance(definition, Mapping):
                definition_digest = sha256(canonicalJson(definition))
                canonical = (genericDefinitions or {}).get(generic_id)
                if canonical is not None and canonicalJson(canonical) != canonicalJson(definition):
                    rejected[cid] = "generic definition conflicts with supplied canonical definition"
                proposals.setdefault(generic_id, []).append((cid, definition_digest))
    conflicts = {gid for gid, items in proposals.items() if len({digest for _, digest in items}) > 1}
    for gid in conflicts:
        for cid, _ in proposals[gid]:
            rejected[cid] = f"conflicting full definitions for genericId {gid}"
    decisions = []
    for cid, row in sorted(rows.items()):
        pair = accepted.get(cid)
        if cid in rejected:
            outcome, reason = "rejected", rejected[cid]
        elif cid in failures:
            outcome, reason = "deferred", failures[cid]
        elif pair is None:
            outcome, reason = "deferred", "missing worker receipt"
        else:
            receipt = pair[0]
            outcome, reason = receipt["outcome"], receipt.get("reason")
        decisions.append({
            "candidateId": cid, "namedIdentity": row["namedIdentity"],
            "taskId": row["taskId"], "inputDigest": row["inputDigest"],
            "outcome": outcome, "reason": reason,
            "proposedGeneric": pair[0].get("proposedGeneric") if pair and outcome == "review-ready" else None,
            "packetPath": pair[0].get("packetPath") if pair and outcome in ("review-ready", "deferred", "rejected", "proven-duplicate") else None,
        })
    counts = {outcome: sum(1 for item in decisions if item["outcome"] == outcome) for outcome in sorted(OUTCOMES)}
    return {
        "contractVersion": "curation-reconciliation-report-v1",
        "inventoryDigest": envelope["inventoryDigest"],
        "humanApproved": False,
        "accounted": len(decisions) == len(rows),
        "candidateCount": len(rows), "counts": counts, "decisions": decisions,
    }
