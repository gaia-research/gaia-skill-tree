"""Deterministic inventory freeze and reconciliation for discovery-packet-v2.

The frozen inventory binds candidate and exact named identity independently,
source URL/revision/digest, and a detached packet input. ``sourceRevision`` may
be null only when ``freshnessRequired`` is true; no branch or commit is inferred.
Receipts are untrusted claims: actual packet bytes are validated and bound to
all frozen facts before a row can be review-ready. Review-ready means L4
presentation only, never human approval.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from gaia_cli.namedIdentity import NAMED_SLUG_RE, validateContributor

ENVELOPE_VERSION = "curation-inventory-v1"
OUTCOMES = {"review-ready", "deferred", "rejected", "proven-duplicate"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def canonicalJson(value: Any) -> bytes:
    """Serialize JSON deterministically (UTF-8, sorted keys, compact form)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _valid_identity(value: Any, label: str) -> str:
    identity = _nonempty(value, label)
    if identity.count("/") != 1:
        raise ValueError(f"{label} must be exact contributor/slug identity")
    contributor, slug = identity.split("/")
    problem = validateContributor(contributor)
    if problem or not NAMED_SLUG_RE.fullmatch(slug):
        raise ValueError(f"{label} is not a valid lowercase named identity" + (f": {problem}" if problem else ""))
    return identity


def freezeInventory(candidates: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Freeze validated candidate rows before dispatch; detach all JSON inputs."""
    rows = []
    seen: set[str] = set()
    for item in candidates:
        if not isinstance(item, Mapping):
            raise ValueError("each inventory candidate must be a mapping")
        cid = _nonempty(item.get("candidateId"), "candidateId")
        if cid in seen:
            raise ValueError(f"duplicate candidateId: {cid}")
        seen.add(cid)
        identity = _valid_identity(item.get("namedIdentity"), f"{cid}.namedIdentity")
        revision = item.get("sourceRevision")
        freshness_required = item.get("freshnessRequired", False)
        if not isinstance(freshness_required, bool):
            raise ValueError(f"{cid}.freshnessRequired must be boolean")
        if revision is None:
            if not freshness_required:
                raise ValueError(f"{cid}.sourceRevision may be null only with freshnessRequired")
        elif not isinstance(revision, str) or not revision.strip():
            raise ValueError(f"{cid}.sourceRevision must be a non-empty string or null")
        digest = item.get("sourceDigest")
        if digest is None and freshness_required:
            pass  # Explicitly unresolved source; cannot become review-ready.
        elif not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise ValueError(f"{cid}.sourceDigest must be a lowercase SHA-256 digest")
        source_url = _nonempty(item.get("canonicalUrl"), f"{cid}.canonicalUrl")
        if "packetInput" not in item:
            raise ValueError(f"{cid}.packetInput is required")
        try:
            packet_input = copy.deepcopy(item["packetInput"])
            input_bytes = canonicalJson(packet_input)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{cid}.packetInput must be JSON-compatible") from exc
        input_digest = sha256(input_bytes)
        task_id = "task-" + sha256(canonicalJson({
            "candidateId": cid, "namedIdentity": identity,
            "sourceRevision": revision, "sourceDigest": digest,
            "canonicalUrl": source_url, "inputDigest": input_digest,
        }))[:24]
        rows.append({
            "candidateId": cid, "namedIdentity": identity,
            "sourceRevision": revision, "freshnessRequired": freshness_required,
            "sourceDigest": digest, "canonicalUrl": source_url,
            "citedOrigin": copy.deepcopy(item.get("citedOrigin")),
            "packetInput": packet_input, "inputDigest": input_digest,
            "taskId": task_id, "assignedAttempt": 1,
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
        if not isinstance(packet, Mapping):
            raise ValueError("packet must be a mapping")
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


def _proof_matches(row: Mapping[str, Any], proof: Any, targets: Mapping[str, Mapping[str, Any]]) -> bool:
    if not isinstance(proof, Mapping):
        return False
    target = proof.get("targetNamedIdentity")
    target_row = targets.get(target) if isinstance(target, str) else None
    if target_row is None or target == row["namedIdentity"]:
        return False
    source = proof.get("source") if isinstance(proof.get("source"), Mapping) else proof
    return any(
        bool(row.get(frozenKey)) and row.get(frozenKey) == target_row.get(frozenKey)
        and source.get(proofKey) == row.get(frozenKey)
        for frozenKey, proofKey in (("canonicalUrl", "canonicalUrl"), ("citedOrigin", "citedOrigin"), ("sourceDigest", "contentSha256"))
    )


def _packet_errors(packet: dict[str, Any], row: Mapping[str, Any]) -> list[str]:
    if packet.get("candidateId") != row["candidateId"]:
        return ["packet candidate identity mismatch"]
    source = packet.get("source")
    named = packet.get("namedIdentity")
    if named is None:
        named = (packet.get("l4Resolution") or {}).get("named") if isinstance(packet.get("l4Resolution"), Mapping) else None
    if not isinstance(named, (Mapping, str)):
        return ["packet is not bound to frozen named identity"]
    packet_identity = f"{named.get('contributor', '')}/{named.get('slug', named.get('skillSlug', ''))}" if isinstance(named, Mapping) else named
    # discovery-packet-v2's l4Resolution uses contributor/skillName for the
    # exact contributor/slug identity; pre-L4 discovery may bind it explicitly.
    if isinstance(named, Mapping) and named.get("namedIdentity") is not None:
        packet_identity = named.get("namedIdentity")
    elif isinstance(named, Mapping) and named.get("skillName") is not None and named.get("slug") is None and named.get("skillSlug") is None:
        packet_identity = f"{named.get('contributor', '')}/{named.get('skillName')}"
    if packet_identity != row["namedIdentity"]:
        return ["packet named identity mismatch"]
    if not isinstance(source, Mapping):
        return ["packet source provenance missing"]
    if source.get("canonicalUrl") != row["canonicalUrl"]:
        return ["packet source URL mismatch"]
    if source.get("contentSha256") != row["sourceDigest"]:
        return ["packet source digest mismatch"]
    revision = source.get("commitSha", source.get("revision"))
    if row["sourceRevision"] is not None and revision != row["sourceRevision"]:
        return ["packet source revision mismatch"]
    if row["sourceRevision"] is None and not row["freshnessRequired"]:
        return ["unresolved source revision lacks freshness requirement"]
    frozen_input = row.get("packetInput")
    input_packet = frozen_input.get("packet") if isinstance(frozen_input, Mapping) else None
    expected_snapshot = input_packet.get("genericSnapshot") if isinstance(input_packet, Mapping) else None
    if not isinstance(expected_snapshot, Mapping):
        return ["frozen input lacks a trusted generic snapshot"]
    actual_snapshot = packet.get("genericSnapshot")
    if not isinstance(actual_snapshot, Mapping) or any(
        actual_snapshot.get(key) != expected_snapshot.get(key)
        for key in ("command", "generics", "contentSha256", "semanticCatalogSha256")
    ):
        return ["packet generic snapshot differs from frozen input"]
    if packet.get("contractVersion") != "discovery-packet-v2":
        return ["output is not discovery-packet-v2"]
    try:
        from gaia_cli.prefill import _importPacketValidator
        validator = _importPacketValidator()
        if validator is None:
            return ["discovery-packet-v2 validator unavailable"]
        snapshot = packet.get("genericSnapshot")
        trusted = snapshot.get("generics") if isinstance(snapshot, Mapping) else None
        errors = validator(packet, trusted_generics=trusted)
    except Exception as exc:
        return [f"packet validator failed: {type(exc).__name__}: {exc}"]
    return [f"invalid discovery packet: {code}" for code in errors]


def reconcileInventory(envelope: Mapping[str, Any], receipts: Iterable[Mapping[str, Any]], *, packetRoot: str | os.PathLike[str] = ".", genericDefinitions: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Reconcile all receipts independent of arrival order; retain one decision per row.

    Every unknown receipt is reported, never accepted. Multiple receipts for a
    candidate are a deterministic conflict and defer that candidate even if one
    receipt is valid. Exact-duplicate proof must identify a different surviving
    frozen named identity and match source proof; shared generic mapping is not
    a duplicate. ``review-ready`` does not mean human-approved.
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
    targets = {row["namedIdentity"]: row for row in frozen_rows}
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    unknown = []
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            unknown.append({"reason": "receipt is not a mapping"})
            continue
        cid = receipt.get("candidateId")
        if cid not in rows:
            unknown.append({"candidateId": cid, "reason": "receipt references unknown candidate"})
            continue
        grouped.setdefault(cid, []).append(receipt)
    validated: dict[str, tuple[Mapping[str, Any], bytes, str]] = {}
    observed_digests: dict[str, str] = {}
    failures: dict[str, str] = {}
    for cid, candidates in grouped.items():
        if len(candidates) != 1:
            failures[cid] = "conflicting receipts: multiple attempts/receipts supplied"
            continue
        receipt = candidates[0]
        row = rows[cid]
        try:
            if receipt.get("taskId") != row["taskId"]:
                raise ValueError("task binding mismatch")
            attempt = receipt.get("attempt")
            if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < row.get("assignedAttempt", 1):
                raise ValueError("invalid attempt")
            if receipt.get("inputDigest") != row["inputDigest"]:
                raise ValueError("input digest mismatch")
            data = _safe_packet_bytes(receipt, Path(packetRoot))
            actual_hash = sha256(data)
            observed_digests[cid] = actual_hash
            if receipt.get("outputDigest") != actual_hash or receipt.get("packetHash") != actual_hash:
                raise ValueError("actual packet output hash mismatch")
            packet = json.loads(data.decode("utf-8"))
            if not isinstance(packet, dict):
                raise ValueError("packet must be a JSON object")
            packet_errors = _packet_errors(packet, row)
            if packet_errors:
                raise ValueError("; ".join(packet_errors))
            if receipt.get("outcome") not in OUTCOMES:
                raise ValueError("invalid outcome")
            if receipt["outcome"] == "proven-duplicate" and not _proof_matches(row, receipt.get("duplicateProof"), targets):
                raise ValueError("exact duplicate proof must match source and a different surviving named identity")
            validated[cid] = (receipt, data, actual_hash)
        except (ValueError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            failures[cid] = str(exc)
    proposals: dict[str, list[tuple[str, str]]] = {}
    rejected: dict[str, str] = {}
    for cid, (receipt, _, _) in validated.items():
        proposal = receipt.get("proposedGeneric")
        # Proposal is bound to the actual packet decision below, not just the receipt.
        data = validated[cid][1]
        actual_packet = json.loads(data.decode("utf-8"))
        decision = actual_packet.get("decision", {})
        proposal_in_packet = decision.get("proposal") if isinstance(decision, Mapping) else None
        expected = {"decision": decision.get("value")} if isinstance(decision, Mapping) else None
        if decision.get("value") == "MAP":
            expected["genericId"] = decision.get("genericId")
        elif decision.get("value") == "NEW_GENERIC" and isinstance(proposal_in_packet, Mapping):
            expected["proposal"] = dict(proposal_in_packet)
        if proposal != expected:
            failures[cid] = "receipt generic proposal does not match packet decision"
            continue
        if expected and expected.get("decision") == "NEW_GENERIC":
            definition = expected.get("proposal")
            if isinstance(definition, Mapping):
                proposed_id = definition.get("genericId")
                conflict_key = proposed_id if isinstance(proposed_id, str) else str(definition.get("name", "")).casefold()
                digest = sha256(canonicalJson(definition))
                canonical = (genericDefinitions or {}).get(conflict_key)
                if canonical is not None and canonicalJson(canonical) != canonicalJson(definition):
                    rejected[cid] = "generic definition conflicts with supplied canonical definition"
                proposals.setdefault(conflict_key, []).append((cid, digest))
    conflicts = {gid for gid, values in proposals.items() if len({digest for _, digest in values}) > 1}
    for gid in conflicts:
        for cid, _digest in proposals[gid]:
            rejected[cid] = f"conflicting full definitions for genericId {gid}"
    decisions = []
    for cid, row in sorted(rows.items()):
        item = validated.get(cid)
        raw = grouped.get(cid, [None])[0] if len(grouped.get(cid, [])) == 1 else None
        if cid in rejected:
            outcome, reason = "rejected", rejected[cid]
        elif cid in failures:
            outcome, reason = "deferred", failures[cid]
        elif item is None:
            outcome, reason = "deferred", "missing worker receipt"
        else:
            raw = item[0]
            outcome = raw["outcome"]
            packet_value = json.loads(item[1].decode("utf-8"))
            reason = raw.get("reason") or (packet_value.get("decision", {}).get("reasonCode") if isinstance(packet_value.get("decision"), Mapping) else None)
        decisions.append({
            "candidateId": cid, "namedIdentity": row["namedIdentity"],
            "sourceUrl": row["canonicalUrl"], "citedOrigin": copy.deepcopy(row.get("citedOrigin")),
            "sourceRevision": row["sourceRevision"], "sourceDigest": row["sourceDigest"],
            "taskId": row["taskId"], "attempt": raw.get("attempt") if raw else None,
            "inputDigest": row["inputDigest"], "outputDigest": item[2] if item else (observed_digests.get(cid) or (raw.get("outputDigest") if raw else None)),
            "packetPath": raw.get("packetPath") if raw else None,
            "packetDigest": item[2] if item else observed_digests.get(cid),
            "proposedGeneric": raw.get("proposedGeneric") if raw else None,
            "duplicateProof": copy.deepcopy(raw.get("duplicateProof")) if raw else None,
            "outcome": outcome, "reason": reason,
        })
    counts = {outcome: sum(row["outcome"] == outcome for row in decisions) for outcome in sorted(OUTCOMES)}
    return {
        "contractVersion": "curation-reconciliation-report-v1", "inventoryDigest": envelope["inventoryDigest"],
        "humanApproved": False, "accounted": len(decisions) == len(rows),
        "candidateCount": len(rows), "counts": counts, "decisions": decisions,
        "unknownReceipts": sorted(unknown, key=lambda value: (str(value.get("candidateId")), value["reason"])),
    }
