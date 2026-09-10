"""L4 ratification of discovery packets (RFC2 closure).

The human-approved ratification seam: converts a deferred+mapped packet into
a review-ready packet carrying l4Resolution (vendor-neutral generic, exact
named implementation, upstream SKILL.md provenance). The packet then flows to
gaia push --from-file for intake intake mapping.

Pre-flight validates the ratified state before writing (CLI Pre-Flight Rule);
a single validation failure prevents the write.
"""

import json
import os
import sys

from gaia_cli.intakeAdapter import REASON_CODES, validateL4Resolution, _canonicalDigest
from gaia_cli.prefill import selfValidatePacket


def ratifyCommand(args):
    """`gaia dev ratify` — append l4Resolution to a deferred+mapped packet.

    Reads a discovery packet, validates that it is deferred+mapped, applies
    the human's ratification (genericId, generic name/description/type/prereqs,
    contributor, skillName, skillFileUrl), sets lifecycle to review-ready,
    and writes the packet back.

    Mutating: requires GAIA_OPERATOR_OVERRIDE (require_operator gate).
    """
    packetPath = args.packet_path
    decision = args.decision
    genericId = args.generic_id
    genericName = args.generic_name
    genericDesc = args.generic_description
    genericType = args.generic_type
    prereqs = args.prereqs
    contributor = args.contributor
    skillName = args.skill_name
    skillFileUrl = args.skill_file_url

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

    # Validate packet is deferred+mapped
    if "mapped" not in packet.get("lifecycle", []):
        print(
            "Packet must include 'mapped' in lifecycle (must be prefilled and "
            "worker-processed first).",
            file=sys.stderr,
        )
        return 1

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
        }
    }

    if genericType == "fusion" and prereqs:
        ratified["l4Resolution"]["generic"]["prerequisites"] = prereqs.split(",")
    elif genericType == "basic":
        ratified["l4Resolution"]["generic"]["prerequisites"] = []

    # Merge into packet
    test_packet = packet.copy()
    test_packet.update(ratified)
    # Replace 'deferred' with 'review-ready' in lifecycle
    lifecycle = list(packet.get("lifecycle", []))
    if "deferred" in lifecycle:
        lifecycle[lifecycle.index("deferred")] = "review-ready"
    elif "review-ready" not in lifecycle:
        lifecycle.append("review-ready")
    test_packet["lifecycle"] = lifecycle

    # Set the decision reasonCode to L4-ratified
    test_packet["decision"] = {
        "value": decision,
        "reasonCode": (
            REASON_CODES.L4_RATIFIED_MAP
            if decision == "MAP"
            else REASON_CODES.L4_RATIFIED_NEW_GENERIC
        ),
    }
    if decision == "MAP":
        test_packet["decision"]["genericId"] = genericId
    else:  # NEW_GENERIC
        # For NEW_GENERIC, include the proposal in the decision
        proposal = {
            "name": genericName,
            "description": genericDesc,
            "type": genericType,
        }
        if genericType == "fusion" and prereqs:
            proposal["prerequisites"] = prereqs.split(",")
        elif genericType == "basic":
            proposal["prerequisites"] = []
        test_packet["decision"]["proposal"] = proposal

    # Pre-flight validation
    resolutionErrors = validateL4Resolution(test_packet)
    if resolutionErrors:
        print("Ratification validation failed:", file=sys.stderr)
        for err in resolutionErrors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # Self-validate the packet
    selfValidateErrors = selfValidatePacket(test_packet)
    if selfValidateErrors:
        print("Packet self-validation failed:", file=sys.stderr)
        for err in selfValidateErrors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # Pre-flight passed — write the packet
    try:
        # Apply the ratification to the original packet
        packet.update(ratified)
        # Replace 'deferred' with 'review-ready' in lifecycle
        lifecycle = list(packet.get("lifecycle", []))
        if "deferred" in lifecycle:
            lifecycle[lifecycle.index("deferred")] = "review-ready"
        elif "review-ready" not in lifecycle:
            # Fallback: append review-ready if neither deferred nor review-ready is present
            lifecycle.append("review-ready")
        packet["lifecycle"] = lifecycle
        # Copy the final decision from test_packet (which was validated)
        packet["decision"] = test_packet["decision"]

        with open(packetPath, "w", encoding="utf-8") as f:
            json.dump(packet, f, indent=2)
    except OSError as exc:
        print(f"Failed to write packet: {exc}", file=sys.stderr)
        return 1

    print(f"Ratified {packetPath}")
    print(f"  Decision: {decision} (reasonCode: {test_packet['decision']['reasonCode']})")
    print(f"  Generic: {genericId} ({genericName})")
    print(f"  Named: {contributor}/{skillName}")
    return 0
