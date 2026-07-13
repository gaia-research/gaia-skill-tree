#!/usr/bin/env python3
"""Validate one Gaia discovery packet without importing registry tooling."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


CONTRACT_VERSION = "discovery-packet-v1"
LIFECYCLE = ("discovered", "fetched", "parsed", "normalized", "deduped", "mapped")
FINAL_STATES = {"review-ready", "deferred", "rejected"}
DECISIONS = {"MAP", "NEW_GENERIC", "DUPLICATE", "NOT_A_SKILL", "DEFER"}
FORBIDDEN_FIELDS = {"evidence", "trustMagnitude", "tmScore", "stars", "grade", "class", "artifact_score"}
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _contains_forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in FORBIDDEN_FIELDS or _contains_forbidden(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden(item) for item in value)
    return False


def _valid_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_packet(packet: Any) -> list[str]:
    """Return stable error codes for a single, discovery-only candidate packet."""
    errors: list[str] = []
    if not isinstance(packet, dict):
        return ["MALFORMED_PACKET"]
    if packet.get("contractVersion") != CONTRACT_VERSION:
        errors.append("UNSUPPORTED_CONTRACT_VERSION")
    for field in ("candidateId", "lifecycle", "source", "normalized", "exactDedupe", "mappingOptions", "decision", "flags"):
        if field not in packet:
            errors.append("MISSING_REQUIRED_FIELD")
    if _contains_forbidden(packet):
        errors.append("DOWNSTREAM_FIELD_FORBIDDEN")

    candidate_id = packet.get("candidateId")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        errors.append("INVALID_CANDIDATE_ID")
    normalized = packet.get("normalized")
    if not isinstance(normalized, dict):
        errors.append("INVALID_NORMALIZED_CANDIDATE")
    if not isinstance(packet.get("exactDedupe"), dict):
        errors.append("INVALID_EXACT_DEDUPE")
    if not isinstance(packet.get("flags"), list):
        errors.append("INVALID_FLAGS")

    lifecycle = packet.get("lifecycle")
    final_state = None
    if not isinstance(lifecycle, list) or len(lifecycle) < 2 or len(lifecycle) != len(set(lifecycle)):
        errors.append("INVALID_LIFECYCLE_TRANSITION")
    elif lifecycle:
        final_state = lifecycle[-1]
        prefix = lifecycle[:-1] if final_state in FINAL_STATES else lifecycle
        valid_prefix = tuple(prefix) == LIFECYCLE[: len(prefix)] and len(prefix) >= 1
        if (
            not valid_prefix
            or final_state not in FINAL_STATES
            or (final_state == "review-ready" and tuple(prefix) != LIFECYCLE)
        ):
            errors.append("INVALID_LIFECYCLE_TRANSITION")

    normalized_stage = isinstance(lifecycle, list) and "normalized" in lifecycle
    if normalized_stage and (
        not isinstance(normalized, dict)
        or not isinstance(normalized.get("name"), str)
        or not normalized["name"].strip()
        or not isinstance(normalized.get("description"), str)
        or not normalized["description"].strip()
    ):
        errors.append("INVALID_NORMALIZED_CANDIDATE")

    source = packet.get("source")
    if not isinstance(source, dict):
        errors.append("MISSING_SOURCE")
    else:
        required_source = ("canonicalUrl", "sourceLane")
        if any(not isinstance(source.get(key), str) or not source[key].strip() for key in required_source):
            errors.append("MISSING_SOURCE_PROVENANCE")
        if source.get("sourceLane") not in {"marketplace", "source-repository", "github-topic"}:
            errors.append("INVALID_SOURCE_LANE")
        if not _valid_url(source.get("canonicalUrl")):
            errors.append("INVALID_SOURCE_URL")
        fetched = isinstance(lifecycle, list) and "fetched" in lifecycle
        if fetched:
            fetched_fields = ("hostRepository", "fetchedAt", "contentSha256")
            if any(not isinstance(source.get(key), str) or not source[key].strip() for key in fetched_fields):
                errors.append("MISSING_FETCHED_PROVENANCE")
            if not _valid_url(source.get("hostRepository")):
                errors.append("INVALID_SOURCE_URL")
            if not SHA256.fullmatch(str(source.get("contentSha256", ""))):
                errors.append("INVALID_CONTENT_HASH")
        frontmatter = source.get("frontmatter")
        parsed = isinstance(lifecycle, list) and "parsed" in lifecycle
        if parsed and (not isinstance(frontmatter, dict) or not isinstance(frontmatter.get("name"), str) or not frontmatter["name"].strip() or not isinstance(frontmatter.get("description"), str) or not frontmatter["description"].strip()):
            errors.append("MISSING_FETCHED_FRONTMATTER")

    options = packet.get("mappingOptions")
    if not isinstance(options, list):
        errors.append("INVALID_MAPPING_OPTIONS")
    elif len(options) > 3:
        errors.append("TOO_MANY_MAPPING_OPTIONS")
    elif any(
        not isinstance(option, dict)
        or not isinstance(option.get("genericId"), str)
        or not option["genericId"].strip()
        or not isinstance(option.get("rationale"), str)
        or not option["rationale"].strip()
        for option in options
    ):
        errors.append("INVALID_MAPPING_OPTIONS")

    mapped = isinstance(lifecycle, list) and "mapped" in lifecycle
    snapshot = packet.get("genericSnapshot")
    if mapped:
        canonical_options = json.dumps(
            options if isinstance(options, list) else [],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        options_digest = hashlib.sha256(canonical_options).hexdigest()
        if (
            not isinstance(snapshot, dict)
            or not isinstance(snapshot.get("capturedAt"), str)
            or not snapshot["capturedAt"].strip()
            or not SHA256.fullmatch(str(snapshot.get("contentSha256", "")))
            or not SHA256.fullmatch(str(snapshot.get("mappingOptionsSha256", "")))
            or snapshot.get("mappingOptionsSha256") != options_digest
        ):
            errors.append("INVALID_GENERIC_SNAPSHOT")

    decision = packet.get("decision")
    decision_value = decision.get("value") if isinstance(decision, dict) else None
    if decision_value not in DECISIONS:
        errors.append("UNKNOWN_DECISION")
    elif not isinstance(decision.get("reasonCode"), str) or not decision["reasonCode"].strip():
        errors.append("MISSING_REASON_CODE")
    elif final_state == "deferred" and decision_value != "DEFER":
        errors.append("INVALID_DECISION_STATE")
    elif final_state == "rejected" and decision_value not in {"DUPLICATE", "NOT_A_SKILL"}:
        errors.append("INVALID_DECISION_STATE")
    elif final_state == "review-ready" and decision_value not in {"MAP", "NEW_GENERIC"}:
        errors.append("INVALID_DECISION_STATE")

    if decision_value == "DUPLICATE":
        exact = packet.get("exactDedupe")
        has_proof = isinstance(exact, dict) and (
            _valid_url(exact.get("matchedCanonicalUrl"))
            or SHA256.fullmatch(str(exact.get("matchedContentSha256", ""))) is not None
        )
        if (
            not isinstance(lifecycle, list)
            or "deduped" not in lifecycle
            or not isinstance(exact, dict)
            or exact.get("matched") is not True
            or not has_proof
        ):
            errors.append("INVALID_DUPLICATE_PROOF")

    if decision_value == "MAP":
        selected = decision.get("genericId") if isinstance(decision, dict) else None
        option_ids = {
            option.get("genericId")
            for option in options
            if isinstance(option, dict)
        } if isinstance(options, list) else set()
        if not isinstance(selected, str) or selected not in option_ids:
            errors.append("INVALID_GENERIC_SELECTION")
    elif isinstance(decision, dict) and "genericId" in decision:
        errors.append("INVALID_GENERIC_SELECTION")

    if decision_value == "NEW_GENERIC":
        proposal = decision.get("proposal") if isinstance(decision, dict) else None
        if (
            not isinstance(proposal, dict)
            or not isinstance(proposal.get("name"), str)
            or not proposal["name"].strip()
            or not isinstance(proposal.get("description"), str)
            or not proposal["description"].strip()
            or proposal.get("type") not in {"basic", "fusion"}
        ):
            errors.append("INVALID_NEW_GENERIC_PROPOSAL")

    return sorted(set(errors))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_discovery_packet.py PACKET.json", file=sys.stderr)
        return 2
    try:
        packet = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"MALFORMED_PACKET: {exc}", file=sys.stderr)
        return 1
    errors = validate_packet(packet)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("VALID discovery-packet-v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
