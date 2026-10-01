"""Tests for src/gaia_cli/intakeAdapter.py (RFC2 Gap B).

Covers the packet->intake-YAML mapping: MAP path, NEW_GENERIC basic,
NEW_GENERIC fusion (prerequisites present), suite fan-out (component + capstone),
and attributionScope derivation.
"""

import hashlib
import json
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "src")
)

from gaia_cli.intakeAdapter import (  # noqa: E402
    attributionScopeForRole,
    buildIntakeSkill,
    buildIntakeYaml,
    candidateSlug,
    isDiscoveryPacket,
    validateL4Resolution,
)


def _basePacket(**overrides):
    packet = {
        "contractVersion": "discovery-packet-v2",
        "candidateId": "alice/some-skill",
        "lifecycle": [
            "discovered", "fetched", "parsed", "normalized",
            "deduped", "mapped", "review-ready",
        ],
        "source": {
            "canonicalUrl": "https://github.com/alice/some-skill/blob/main/SKILL.md",
            "hostRepository": "https://github.com/alice/some-skill",
            "sourceLane": "source-repository",
            "fetchedAt": "2026-07-29T00:00:00Z",
            "contentSha256": "a" * 64,
            "frontmatter": {"name": "Some Skill", "description": "Does a thing well."},
        },
        "normalized": {"name": "Some Skill", "description": "Does a thing well."},
        "exactDedupe": {"matched": False},
        "mappingOptions": [{
            "genericId": "research", "rationale": "Frozen strong match.",
            "similarity": 0.9, "matchTier": "strong",
        }],
        "decision": {"value": "MAP", "reasonCode": "strong-match", "genericId": "research"},
        "flags": [],
    }
    packet.update(overrides)
    options = packet["mappingOptions"]
    generics = [{"id": "research", "kind": "generic"}]
    digest = lambda value: hashlib.sha256(  # noqa: E731
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    packet.setdefault("genericSnapshot", {
        "capturedAt": "2026-07-29T00:00:00Z",
        "command": "gaia dev list --generic --json",
        "generics": generics,
        "contentSha256": digest(generics),
        "mappingOptionsSha256": digest(options),
    })
    packet.setdefault("l4Resolution", {
        "status": "approved",
        "generic": {
            "id": (packet.get("decision") or {}).get("genericId", "new-generic"),
            "name": "Vendor Neutral Capability",
            "description": "A human-ratified vendor-neutral capability description.",
            "type": "basic",
            "prerequisites": [],
        },
        "named": {"contributor": "alice", "skillName": "some-skill"},
        "skillFileUrl": "https://github.com/alice/some-skill/blob/main/SKILL.md",
    })
    return packet


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def test_is_discovery_packet_detects_contract_version():
    assert isDiscoveryPacket(_basePacket()) is True
    assert isDiscoveryPacket({"skills": []}) is False
    assert isDiscoveryPacket({}) is False
    assert isDiscoveryPacket("nope") is False


def test_candidate_slug_kebabs_contributor_slash():
    assert candidateSlug("alice/some-skill") == "alice-some-skill"
    assert candidateSlug("Foo/Bar") == "foo-bar"


def test_attribution_scope_derivation():
    assert attributionScopeForRole("capstone") == "suite-wide"
    assert attributionScopeForRole("component") == "suite-component"
    assert attributionScopeForRole(None) == "standalone"
    assert attributionScopeForRole("nonsense") == "standalone"


# --------------------------------------------------------------------------- #
# MAP path
# --------------------------------------------------------------------------- #

def test_map_path_references_existing_generic():
    entry = buildIntakeSkill(_basePacket())
    assert entry["id"] == "research"
    assert entry["candidateId"] == "alice/some-skill"
    assert entry["type"] == "basic"
    assert entry["prerequisites"] == []
    assert entry["mapsToGeneric"] == "research"
    assert entry["attributionScope"] == "standalone"
    # Provenance reference (not a strength claim).
    assert len(entry["evidence"]) == 1
    assert entry["evidence"][0]["type"] == "repo"
    assert entry["evidence"][0]["grade"] == "C"


def test_map_missing_generic_id_raises():
    packet = _basePacket(
        decision={"value": "MAP", "reasonCode": "x"}
    )
    with pytest.raises(ValueError, match="genericId"):
        buildIntakeSkill(packet)


# --------------------------------------------------------------------------- #
# NEW_GENERIC basic
# --------------------------------------------------------------------------- #

def test_new_generic_basic():
    packet = _basePacket(
        decision={
            "value": "NEW_GENERIC",
            "reasonCode": "no-match",
            "proposal": {
                "name": "New Basic Skill",
                "description": "A brand new basic capability.",
                "type": "basic",
            },
        }
    )
    entry = buildIntakeSkill(packet)
    assert entry["type"] == "basic"
    assert entry["prerequisites"] == []
    assert "mapsToGeneric" not in entry
    assert entry["name"] == "Vendor Neutral Capability"


# --------------------------------------------------------------------------- #
# NEW_GENERIC fusion
# --------------------------------------------------------------------------- #

def test_new_generic_fusion_carries_prerequisites():
    packet = _basePacket(
        decision={
            "value": "NEW_GENERIC",
            "reasonCode": "novel-fusion",
            "proposal": {
                "name": "Fused Skill",
                "description": "Combines two capabilities.",
                "type": "fusion",
                "prerequisites": ["research", "planning"],
            },
        },
        l4Resolution={
            "status": "approved",
            "generic": {
                "id": "fused-skill", "name": "Fused Skill",
                "description": "Combines two vendor-neutral capabilities.",
                "type": "fusion", "prerequisites": ["research", "planning"],
            },
            "named": {"contributor": "alice", "skillName": "some-skill"},
            "skillFileUrl": "https://github.com/alice/some-skill/blob/main/SKILL.md",
        },
    )
    entry = buildIntakeSkill(packet)
    assert entry["type"] == "fusion"
    assert entry["prerequisites"] == ["research", "planning"]


def test_new_generic_fusion_without_prerequisites_raises():
    packet = _basePacket(
        decision={
            "value": "NEW_GENERIC",
            "reasonCode": "novel-fusion",
            "proposal": {
                "name": "Fused Skill",
                "description": "Combines two capabilities.",
                "type": "fusion",
            },
        },
        l4Resolution={
            "status": "approved",
            "generic": {
                "id": "fused-skill", "name": "Fused Skill",
                "description": "Combines two vendor-neutral capabilities.",
                "type": "fusion",
            },
            "named": {"contributor": "alice", "skillName": "some-skill"},
            "skillFileUrl": "https://github.com/alice/some-skill/blob/main/SKILL.md",
        },
    )
    with pytest.raises(ValueError, match="prerequisites"):
        buildIntakeSkill(packet)


# --------------------------------------------------------------------------- #
# Non-intake decisions rejected
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("value", ["DEFER", "DUPLICATE", "NOT_A_SKILL"])
def test_non_intake_decisions_rejected(value):
    packet = _basePacket(decision={"value": value, "reasonCode": "x"})
    with pytest.raises(ValueError, match="not intake-eligible"):
        buildIntakeSkill(packet)


# --------------------------------------------------------------------------- #
# Suite fan-out
# --------------------------------------------------------------------------- #

def test_suite_component_scope():
    packet = _basePacket(
        candidateId="alice/component-a",
        suite={"role": "component", "suiteId": "alice-suite"},
    )
    entry = buildIntakeSkill(packet)
    assert entry["suite"]["role"] == "component"
    assert entry["suite"]["suiteId"] == "alice-suite"
    assert entry["attributionScope"] == "suite-component"


def test_suite_capstone_scope_and_component_ids():
    packet = _basePacket(
        candidateId="alice/capstone",
        suite={
            "role": "capstone",
            "suiteId": "alice-suite",
            "componentCandidateIds": ["alice/component-a", "alice/component-b"],
        },
    )
    entry = buildIntakeSkill(packet)
    assert entry["suite"]["role"] == "capstone"
    assert entry["suite"]["componentCandidateIds"] == [
        "alice/component-a", "alice/component-b",
    ]
    assert entry["attributionScope"] == "suite-wide"


def test_suite_fan_out_build_intake_yaml():
    component = _basePacket(
        candidateId="alice/component-a",
        suite={"role": "component", "suiteId": "alice-suite"},
    )
    capstone = _basePacket(
        candidateId="alice/capstone",
        suite={
            "role": "capstone",
            "suiteId": "alice-suite",
            "componentCandidateIds": ["alice/component-a"],
        },
    )
    result = buildIntakeYaml([component, capstone])
    assert "skills" in result
    assert len(result["skills"]) == 2
    assert [s["attributionScope"] for s in result["skills"]] == [
        "suite-component", "suite-wide",
    ]


def test_resolved_packet_validates_against_v2_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schemaPath = os.path.join(
        os.path.dirname(__file__), "..", ".agents", "skills", "gaia-curate",
        "schemas", "discovery-packet-v2.schema.json",
    )
    with open(schemaPath, encoding="utf-8") as handle:
        schema = json.load(handle)
    jsonschema.validate(_basePacket(), schema)


def test_post_l4_handoff_rejects_listing_or_tree_url():
    packet = _basePacket()
    packet["l4Resolution"]["skillFileUrl"] = "https://github.com/alice/repo/tree/main/skills/x"
    with pytest.raises(ValueError, match="exact GitHub blob URL"):
        buildIntakeSkill(packet)


@pytest.mark.parametrize("filename", ["skill.md", "Skill.md"])
def test_post_l4_handoff_requires_case_sensitive_skill_filename(filename):
    packet = _basePacket()
    packet["l4Resolution"]["skillFileUrl"] = (
        f"https://github.com/alice/repo/blob/main/{filename}"
    )
    with pytest.raises(ValueError, match="ending in SKILL.md"):
        buildIntakeSkill(packet)


def test_post_l4_handoff_requires_frozen_snapshot_digest():
    packet = _basePacket()
    packet["genericSnapshot"]["contentSha256"] = "0" * 64
    with pytest.raises(ValueError, match="frozen generics"):
        buildIntakeSkill(packet)


def test_new_generic_uses_human_ratified_identity_not_candidate_slug():
    packet = _basePacket(
        candidateId="vendor/flashy-product",
        decision={
            "value": "NEW_GENERIC", "reasonCode": "NEW_GENERIC_NO_MATCH",
            "proposal": {"name": "Flashy Product", "description": "Vendor prose here.", "type": "basic"},
        },
        l4Resolution={
            "status": "approved",
            "generic": {
                "id": "durable-context-retrieval", "name": "Durable Context Retrieval",
                "description": "Retrieves durable context across bounded agent sessions.",
                "type": "basic", "prerequisites": [],
            },
            "named": {"contributor": "vendor", "skillName": "flashy-product"},
            "skillFileUrl": "https://github.com/vendor/repo/blob/abc123/SKILL.md",
        },
    )
    entry = buildIntakeSkill(packet)
    assert entry["id"] == "durable-context-retrieval"
    assert entry["named"]["skill_name"] == "flashy-product"


def test_build_intake_yaml_single_packet():
    result = buildIntakeYaml(_basePacket())
    assert len(result["skills"]) == 1
    assert result["skills"][0]["id"] == "research"
    assert result["curationHandoff"]["contractVersion"] == "curation-handoff-v1"


# --------------------------------------------------------------------------- #
# Human Review Attestation & Boundary Enforcement Tests
# --------------------------------------------------------------------------- #

def _addValidHumanReview(packet, assessment_path=None, receipt_digest=None):
    valid_sha = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    packet["artifactGate"] = "valid-skill"
    if "source" not in packet:
        packet["source"] = {}
    packet["source"]["contentSha256"] = valid_sha
    packet["source"]["canonicalUrl"] = packet["l4Resolution"]["skillFileUrl"]
    packet["l4Resolution"]["humanReview"] = {
        "reviewedBy": "curator-alice",
        "approvalRef": "https://github.com/gaia-research/gaia-skill-tree/issues/999",
        "rationale": "Human review confirms candidate meets all principles.",
        "reviewedAt": "2026-09-11T12:00:00Z",
        "assessmentPath": assessment_path or "/tmp/portable-laptop-path/assessment.json",
        "assessmentReceiptDigest": receipt_digest or valid_sha,
        "operatorOverride": False,
        "humanOverride": False,
        "attestation": "Local file attestation; does not cryptographically authenticate a human.",
    }
    return packet


def test_validate_l4_resolution_legacy_read_without_human_review_accepted():
    """Default validation preserves legacy read compatibility."""
    packet = _basePacket()
    assert "humanReview" not in packet["l4Resolution"]
    errors = validateL4Resolution(packet, requireHumanReview=False)
    assert errors == []
    entry = buildIntakeSkill(packet, requireHumanReview=False)
    assert entry["id"] == "research"


def test_validate_l4_resolution_require_human_review_missing_rejects():
    """Push boundary requires explicit human review attestation."""
    packet = _basePacket()
    assert "humanReview" not in packet["l4Resolution"]
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert any("legacy packet must be human-ratified with gaia dev ratify" in e for e in errors)
    with pytest.raises(ValueError, match="legacy packet must be human-ratified with gaia dev ratify"):
        buildIntakeSkill(packet, requireHumanReview=True)


def test_validate_l4_resolution_with_valid_human_review_succeeds():
    """Packet with valid humanReview attestation passes requireHumanReview=True."""
    packet = _basePacket()
    _addValidHumanReview(packet)
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert errors == []
    entry = buildIntakeSkill(packet, requireHumanReview=True)
    assert entry["id"] == "research"


def test_validate_l4_resolution_human_review_field_validations():
    """Validates nonempty fields, digest regex, attestation, and source binding."""
    # Test empty reviewedBy
    packet = _basePacket()
    _addValidHumanReview(packet)
    packet["l4Resolution"]["humanReview"]["reviewedBy"] = ""
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert any("humanReview.reviewedBy" in e for e in errors)

    # Test empty approvalRef
    packet = _basePacket()
    _addValidHumanReview(packet)
    packet["l4Resolution"]["humanReview"]["approvalRef"] = "   "
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert any("humanReview.approvalRef" in e for e in errors)

    # Test empty rationale
    packet = _basePacket()
    _addValidHumanReview(packet)
    packet["l4Resolution"]["humanReview"]["rationale"] = ""
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert any("humanReview.rationale" in e for e in errors)

    # Test empty reviewedAt
    packet = _basePacket()
    _addValidHumanReview(packet)
    packet["l4Resolution"]["humanReview"]["reviewedAt"] = ""
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert any("humanReview.reviewedAt" in e for e in errors)

    # Test malformed assessmentReceiptDigest
    packet = _basePacket()
    _addValidHumanReview(packet)
    packet["l4Resolution"]["humanReview"]["assessmentReceiptDigest"] = "not-a-sha256"
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert any("assessmentReceiptDigest" in e for e in errors)

    # Test empty attestation
    packet = _basePacket()
    _addValidHumanReview(packet)
    packet["l4Resolution"]["humanReview"]["attestation"] = ""
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert any("humanReview.attestation" in e for e in errors)

    # Test artifactGate must be valid-skill
    packet = _basePacket()
    _addValidHumanReview(packet)
    packet["artifactGate"] = "not-a-skill"
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert any("artifactGate" in e for e in errors)

    # Test skillFileUrl must match source.canonicalUrl
    packet = _basePacket()
    _addValidHumanReview(packet)
    packet["l4Resolution"]["skillFileUrl"] = "https://github.com/alice/other-repo/blob/main/SKILL.md"
    errors = validateL4Resolution(packet, requireHumanReview=True)
    assert any("skillFileUrl does not match packet source.canonicalUrl" in e for e in errors)


def test_validate_l4_resolution_local_receipt_integrity(tmp_path):
    """When assessment receipt file is accessible locally, verify digest and bindings."""
    receipt = {
        "candidateId": "alice/some-skill",
        "candidateSourceDigest": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "advisory": True,
    }
    receipt_bytes = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()

    receipt_file = tmp_path / "receipt.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    # Matching receipt succeeds
    packet = _basePacket()
    _addValidHumanReview(packet, assessment_path=str(receipt_file), receipt_digest=receipt_sha)
    packet["source"]["contentSha256"] = receipt["candidateSourceDigest"]
    assert validateL4Resolution(packet, requireHumanReview=True) == []

    # Corrupted digest fails
    packet_corrupt = _basePacket()
    _addValidHumanReview(packet_corrupt, assessment_path=str(receipt_file), receipt_digest="f" * 64)
    errors = validateL4Resolution(packet_corrupt, requireHumanReview=True)
    assert any("digest mismatch" in e for e in errors)

    # Mismatch candidateId binding fails
    receipt_bad_cand = dict(receipt, candidateId="bob/other-skill")
    bad_cand_file = tmp_path / "bad_cand.json"
    bad_cand_file.write_text(json.dumps(receipt_bad_cand), encoding="utf-8")
    bad_cand_sha = hashlib.sha256(json.dumps(receipt_bad_cand, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    packet_bad_cand = _basePacket()
    _addValidHumanReview(packet_bad_cand, assessment_path=str(bad_cand_file), receipt_digest=bad_cand_sha)
    errors = validateL4Resolution(packet_bad_cand, requireHumanReview=True)
    assert any("does not match packet candidateId" in e for e in errors)

    # Non-existent receipt file is accepted (portable packet)
    packet_portable = _basePacket()
    _addValidHumanReview(packet_portable, assessment_path="/does/not/exist/on/this/laptop/assessment.json")
    assert validateL4Resolution(packet_portable, requireHumanReview=True) == []
