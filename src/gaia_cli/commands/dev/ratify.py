"""L4 ratification of discovery packets (RFC2 closure).

The human-approved ratification seam: converts a deferred+mapped packet into
a review-ready packet carrying l4Resolution (vendor-neutral generic, exact
named implementation, upstream SKILL.md provenance, and humanReview attestation).
The packet then flows to gaia push --from-file for intake mapping.

Pre-flight validates the ratified state before writing (CLI Pre-Flight Rule);
a single validation failure prevents the write.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any

from gaia_cli.intakeAdapter import (
    REASON_CODES,
    SKILL_ID_RE,
    _canonicalDigest,
    _isExactSkillBlob,
    validateL4Resolution,
)
from gaia_cli.prefill import buildGenericSnapshot, selfValidatePacket, _importPacketValidator
from gaia_cli.curation.assessment import validateAssessment, loadGenericSemantics


def _splitPrereqs(prereqs):
    """Split a comma-separated prereqs string, stripping whitespace per item."""
    if not prereqs:
        return []
    return [item.strip() for item in prereqs.split(",") if item.strip()]


def ratifyCommand(args):
    """`gaia dev ratify` — append l4Resolution to a deferred+mapped packet.

    Reads a discovery packet, validates that it is deferred+mapped, applies
    the human's ratification (genericId, generic name/description/type/prereqs,
    contributor, skillName, skillFileUrl, and humanReview attestation metadata),
    sets lifecycle to review-ready, and writes the packet back atomically.

    Mutating: requires GAIA_OPERATOR_OVERRIDE (require_operator gate).
    """
    packetPath = args.packet_path
    decision = args.decision
    genericId = args.generic_id
    genericName = getattr(args, "generic_name", None)
    genericDesc = getattr(args, "generic_description", None)
    genericType = getattr(args, "generic_type", None)
    prereqs = getattr(args, "prereqs", None)
    contributor = args.contributor
    skillName = args.skill_name
    skillFileUrl = getattr(args, "skill_file_url", None)

    if decision not in ("MAP", "NEW_GENERIC"):
        print(
            f"Ratification rejected: invalid decision '{decision}'; must be 'MAP' or 'NEW_GENERIC'.",
            file=sys.stderr,
        )
        return 1

    if not SKILL_ID_RE.fullmatch(genericId):
        print(
            f"Ratification rejected: generic_id '{genericId}' must be a vendor-neutral kebab-case id.",
            file=sys.stderr,
        )
        return 1

    if not contributor or not str(contributor).strip() or "/" in str(contributor):
        print("Ratification rejected: contributor is required and cannot contain '/'.", file=sys.stderr)
        return 1

    if not skillName or not SKILL_ID_RE.fullmatch(str(skillName)):
        print(f"Ratification rejected: skill_name '{skillName}' must be kebab-case.", file=sys.stderr)
        return 1

    # Human review acknowledgement check
    # Must reject without explicit human review acknowledgement even when operator override exists
    ack_human = getattr(args, "acknowledge_human_review", False)
    if not ack_human:
        print(
            "Ratification rejected: --acknowledge-human-review is required to acknowledge explicit human review.",
            file=sys.stderr,
        )
        return 1

    reviewed_by = getattr(args, "reviewed_by", None)
    if not reviewed_by or not str(reviewed_by).strip():
        print("Ratification rejected: --reviewed-by is required.", file=sys.stderr)
        return 1

    approval_ref = getattr(args, "approval_ref", None)
    if not approval_ref or not str(approval_ref).strip():
        print("Ratification rejected: --approval-ref is required.", file=sys.stderr)
        return 1

    reason = getattr(args, "reason", None)
    if not reason or not str(reason).strip():
        print("Ratification rejected: --reason is required.", file=sys.stderr)
        return 1

    assessment_path = getattr(args, "assessment", None)
    if not assessment_path or not os.path.exists(assessment_path):
        print(
            f"Ratification rejected: assessment receipt not found at '{assessment_path}'.",
            file=sys.stderr,
        )
        return 1

    # Load the packet
    if not os.path.exists(packetPath):
        print(f"Packet not found: {packetPath}", file=sys.stderr)
        return 1

    try:
        with open(packetPath, "r", encoding="utf-8") as f:
            packet = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to read packet: {exc}", file=sys.stderr)
        return 1

    if not isinstance(packet, dict):
        print("Ratification rejected: packet must be a JSON object.", file=sys.stderr)
        return 1

    # Validate packet is deferred+mapped
    if "mapped" not in packet.get("lifecycle", []):
        print(
            "Packet must include 'mapped' in lifecycle (must be prefilled and "
            "worker-processed first).",
            file=sys.stderr,
        )
        return 1

    if packet.get("artifactGate") != "valid-skill":
        print("Ratification rejected: artifactGate must be 'valid-skill'.", file=sys.stderr)
        return 1

    source = packet.get("source")
    if not isinstance(source, dict):
        print("Ratification rejected: packet missing source object.", file=sys.stderr)
        return 1

    content_sha = source.get("contentSha256")
    if not content_sha or not isinstance(content_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", content_sha):
        print("Ratification rejected: valid non-empty source contentSha256 is required.", file=sys.stderr)
        return 1

    canonical_url = source.get("canonicalUrl")
    if not canonical_url or not _isExactSkillBlob(canonical_url):
        print(
            "Ratification rejected: packet source canonicalUrl must be an exact GitHub blob URL ending in SKILL.md.",
            file=sys.stderr,
        )
        return 1

    # Ensure ratify source URL is tied to packet source URL/digest
    if skillFileUrl is None or not str(skillFileUrl).strip():
        skillFileUrl = canonical_url
    elif skillFileUrl != canonical_url:
        print(
            f"Ratification rejected: --skill-file-url '{skillFileUrl}' does not match packet source canonicalUrl '{canonical_url}'.",
            file=sys.stderr,
        )
        return 1

    if not _isExactSkillBlob(skillFileUrl):
        print("Ratification rejected: skillFileUrl must be an exact GitHub blob URL ending in SKILL.md.", file=sys.stderr)
        return 1

    # Load and validate assessment receipt
    try:
        with open(assessment_path, "r", encoding="utf-8") as f:
            receipt = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Ratification rejected: failed to read assessment receipt: {exc}", file=sys.stderr)
        return 1

    registry_path = getattr(args, "registry", ".") or "."
    try:
        live_catalog = loadGenericSemantics(registry_path)
    except Exception as exc:
        print(f"Ratification rejected: failed to load live generic semantics: {exc}", file=sys.stderr)
        return 1

    split_prereqs = _splitPrereqs(prereqs)

    if decision == "MAP":
        if genericId not in live_catalog:
            print(f"Ratification rejected: target generic '{genericId}' does not exist in live registry.", file=sys.stderr)
            return 1
        live_node = live_catalog[genericId]

        # Resolve genericName from live node if omitted; reject on mismatch (no mutating ontology via MAP)
        if genericName is None or not str(genericName).strip():
            genericName = live_node.get("name")
        elif live_node.get("name") is not None and live_node["name"] != genericName:
            print(
                f"Ratification rejected: approved generic name '{genericName}' does not match live node name '{live_node['name']}'.",
                file=sys.stderr,
            )
            return 1

        # Resolve genericType from live node if omitted; reject on mismatch
        if genericType is None:
            genericType = live_node.get("type", "basic")
        elif live_node.get("type") is not None and live_node["type"] != genericType:
            print(
                f"Ratification rejected: approved generic type '{genericType}' does not match live node type '{live_node['type']}'.",
                file=sys.stderr,
            )
            return 1
        if genericType not in ("basic", "fusion"):
            print(
                f"Ratification rejected: generic_type must be 'basic' or 'fusion'.",
                file=sys.stderr,
            )
            return 1

        # Resolve genericDesc from live node if omitted; reject on mismatch
        if genericDesc is None or not str(genericDesc).strip():
            genericDesc = live_node.get("description")
        elif live_node.get("description") is not None and live_node["description"] != genericDesc:
            print(
                "Ratification rejected: approved generic description does not match live node description.",
                file=sys.stderr,
            )
            return 1

        # Resolve prerequisites from live node if omitted; reject on mismatch
        if prereqs is None:
            split_prereqs = list(live_node.get("prerequisites") or [])
        else:
            live_prereqs = sorted(live_node.get("prerequisites") or [])
            approved_prereqs = sorted(split_prereqs if genericType == "fusion" else [])
            if live_prereqs != approved_prereqs:
                print(
                    "Ratification rejected: approved generic prerequisites do not match live node prerequisites.",
                    file=sys.stderr,
                )
                return 1

        if genericType == "basic" and split_prereqs:
            print(
                f"Ratification rejected: basic generic cannot have prerequisites (found: {split_prereqs}).",
                file=sys.stderr,
            )
            return 1

    elif decision == "NEW_GENERIC":
        if genericId in live_catalog:
            print(f"Ratification rejected: generic id '{genericId}' already exists in live registry.", file=sys.stderr)
            return 1
        if not genericName or not str(genericName).strip():
            print("Ratification rejected: --generic-name is required for NEW_GENERIC.", file=sys.stderr)
            return 1
        if not genericDesc or len(str(genericDesc).strip()) < 10:
            print(
                "Ratification rejected: --generic-description is required for NEW_GENERIC (at least 10 characters).",
                file=sys.stderr,
            )
            return 1
        if not genericType or genericType not in ("basic", "fusion"):
            print(
                "Ratification rejected: --generic-type must be 'basic' or 'fusion' for NEW_GENERIC.",
                file=sys.stderr,
            )
            return 1

        if genericType == "basic" and split_prereqs:
            print(
                f"Ratification rejected: basic generic cannot have prerequisites (found: {split_prereqs}).",
                file=sys.stderr,
            )
            return 1
        if genericType == "fusion":
            if not split_prereqs:
                print("Ratification rejected: fusion generic requires prerequisites.", file=sys.stderr)
                return 1
            if genericId in split_prereqs:
                print(
                    f"Ratification rejected: NEW_GENERIC prerequisites cannot self-reference the new generic id '{genericId}'.",
                    file=sys.stderr,
                )
                return 1
            for prereq_id in split_prereqs:
                if prereq_id not in live_catalog:
                    print(
                        f"Ratification rejected: prerequisite '{prereq_id}' does not exist in live registry.",
                        file=sys.stderr,
                    )
                    return 1

    assessment_errors = validateAssessment(receipt, packet, registry_path)
    if assessment_errors:
        print("Ratification rejected: assessment verification failed:", file=sys.stderr)
        for err in assessment_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # Fail closed if packet validator is unavailable
    packet_validator = _importPacketValidator()
    if packet_validator is None:
        print(
            "Ratification rejected: discovery packet validator is unavailable; failing closed.",
            file=sys.stderr,
        )
        return 1

    receipt_bytes = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    receipt_digest = hashlib.sha256(receipt_bytes).hexdigest()
    operator_override = os.environ.get("GAIA_OPERATOR_OVERRIDE") == "1"
    prior_proposal = receipt.get("proposedDisposition")

    # Record human override bool: choice differs proposal
    human_override = True
    if isinstance(prior_proposal, dict):
        prop_val = prior_proposal.get("value")
        prop_target = prior_proposal.get("targetGenericId")
        if prop_val == "MAP_CANDIDATE" and decision == "MAP":
            if prop_target is None or prop_target == genericId:
                human_override = False
        elif prop_val == "NEW_GENERIC_CANDIDATE" and decision == "NEW_GENERIC":
            human_override = False

    # Local file attestation; does not claim cryptographic authentication of a human
    human_review = {
        "reviewedBy": reviewed_by.strip(),
        "approvalRef": approval_ref.strip(),
        "rationale": reason.strip(),
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
        "assessmentPath": assessment_path,
        "assessmentReceiptDigest": receipt_digest,
        "operatorOverride": operator_override,
        "humanOverride": human_override,
        "priorProposal": prior_proposal,
        "attestation": "Local file attestation; does not cryptographically authenticate a human.",
    }

    # Pre-flight: build the ratified state and validate it before writing
    ratified = {
        "l4Resolution": {
            "status": "approved",
            "generic": {
                "id": genericId,
                "name": genericName,
                "description": genericDesc,
                "type": genericType,
            },
            "named": {
                "contributor": contributor,
                "skillName": skillName,
            },
            "skillFileUrl": skillFileUrl,
            "humanReview": human_review,
        }
    }

    if genericType == "fusion":
        ratified["l4Resolution"]["generic"]["prerequisites"] = split_prereqs
    elif genericType == "basic":
        ratified["l4Resolution"]["generic"]["prerequisites"] = []

    # Merge into packet
    testPacket = packet.copy()
    testPacket.update(ratified)
    # Replace 'deferred' with 'review-ready' in lifecycle
    lifecycle = list(packet.get("lifecycle", []))
    if "deferred" in lifecycle:
        lifecycle[lifecycle.index("deferred")] = "review-ready"
    elif "review-ready" not in lifecycle:
        lifecycle.append("review-ready")
    testPacket["lifecycle"] = lifecycle

    # Set the decision reasonCode to L4-ratified
    testPacket["decision"] = {
        "value": decision,
        "reasonCode": (
            REASON_CODES.L4_RATIFIED_MAP
            if decision == "MAP"
            else REASON_CODES.L4_RATIFIED_NEW_GENERIC
        ),
    }
    if decision == "MAP":
        testPacket["decision"]["genericId"] = genericId
    else:  # NEW_GENERIC
        # For NEW_GENERIC, include the proposal in the decision
        proposal = {
            "name": genericName,
            "description": genericDesc,
            "type": genericType,
            "prerequisites": split_prereqs if genericType == "fusion" else [],
        }
        testPacket["decision"]["proposal"] = proposal

    # Pre-flight validation
    resolutionErrors = validateL4Resolution(testPacket, requireHumanReview=True)
    if resolutionErrors:
        print("Ratification validation failed:", file=sys.stderr)
        for err in resolutionErrors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # Self-validate the packet against the LIVE registry's generic snapshot —
    # not the packet's own frozen genericSnapshot. Comparing a snapshot to
    # itself is tautological; ratify is the final gate before intake, so it
    # must confirm the MAP target (or NEW_GENERIC collision-freedom) still
    # holds against the registry as it stands right now. A registry that has
    # drifted since prefill correctly fails here with UNTRUSTED/INVALID
    # GENERIC_SNAPSHOT, telling the operator to re-run prefill.
    liveSnapshot = buildGenericSnapshot(args.registry)
    liveGenerics = liveSnapshot["generics"] if liveSnapshot else []
    selfValidateErrors = selfValidatePacket(testPacket, trustedGenerics=liveGenerics)
    if selfValidateErrors:
        print("Packet self-validation failed:", file=sys.stderr)
        for err in selfValidateErrors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # Pre-flight passed — write the packet atomically
    packet.update(ratified)
    packet["lifecycle"] = testPacket["lifecycle"]
    # Copy the final decision from testPacket (which was validated)
    packet["decision"] = testPacket["decision"]

    packet_dir = os.path.dirname(os.path.abspath(packetPath))
    temp_path = os.path.join(packet_dir, f".{os.path.basename(packetPath)}.tmp.{os.getpid()}.{time.time_ns()}")
    try:
        content = json.dumps(packet, indent=2)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, packetPath)
    except OSError as exc:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        print(f"Failed to write packet: {exc}", file=sys.stderr)
        return 1

    print(f"Ratified {packetPath}")
    print(f"  Decision: {decision} (reasonCode: {testPacket['decision']['reasonCode']})")
    print(f"  Generic: {genericId} ({genericName})")
    print(f"  Named: {contributor}/{skillName}")
    print(f"  Reviewed by: {reviewed_by} (ref: {approval_ref})")
    return 0
