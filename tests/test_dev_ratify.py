"""Tests for gaia dev ratify command (G1 #1784, step 6-8)."""

import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gaia_cli.commands.dev.ratify import ratifyCommand
from gaia_cli.intakeAdapter import REASON_CODES, _canonicalDigest
from gaia_cli.curation.assessment import buildAssessment

# Matches the generics frozen into _makeDeferredMappedPacket()'s genericSnapshot.
# Ratify validates the packet against the LIVE registry (not the packet's own
# self-reported snapshot — see ratify.py), so tests must provide a registry dir
# whose gaia.json actually contains these skill ids, or every ratification
# would fail with UNTRUSTED_GENERIC_SNAPSHOT regardless of the scenario under test.
_LIVE_REGISTRY_SKILLS = [
    {
        "id": "test-skill",
        "name": "Test Skill",
        "description": "A test skill for mapping.",
        "type": "basic",
        "prerequisites": [],
    },
    {
        "id": "other-skill",
        "name": "Other Skill",
        "description": "Another test skill for mapping.",
        "type": "basic",
        "prerequisites": [],
    },
    {
        "id": "skill-a",
        "name": "Skill A",
        "description": "Prerequisite skill A for testing.",
        "type": "basic",
        "prerequisites": [],
    },
    {
        "id": "skill-b",
        "name": "Skill B",
        "description": "Prerequisite skill B for testing.",
        "type": "basic",
        "prerequisites": [],
    },
    {
        "id": "skill-c",
        "name": "Skill C",
        "description": "Prerequisite skill C for testing.",
        "type": "basic",
        "prerequisites": [],
    },
]


def _makeRegistryDir(tmp_path, skills=None):
    """Write a minimal registry/gaia.json under tmp_path and return its path."""
    registryRoot = tmp_path / "reg"
    registryDir = registryRoot / "registry"
    registryDir.mkdir(parents=True, exist_ok=True)
    with open(registryDir / "gaia.json", "w", encoding="utf-8") as f:
        json.dump({"skills": skills if skills is not None else _LIVE_REGISTRY_SKILLS}, f)
    return str(registryRoot)


def _makeDeferredMappedPacket(candidate_id="test/candidate", mapping_options=None):
    """Factory for a valid deferred+mapped test packet."""
    if mapping_options is None:
        mapping_options = [
            {
                "genericId": "test-skill",
                "rationale": "Test match",
                "similarity": 0.95,
                "matchTier": "strong",
            }
        ]

    generics = [
        {"id": s["id"], "name": s["name"], "kind": "generic"}
        for s in _LIVE_REGISTRY_SKILLS
    ]

    valid_sha256 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    return {
        "contractVersion": "discovery-packet-v2",
        "candidateId": candidate_id,
        "lifecycle": ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "deferred"],
        "artifactGate": "valid-skill",
        "source": {
            "canonicalUrl": f"https://github.com/{candidate_id}/blob/main/SKILL.md",
            "sourceLane": "source-repository",
            "hostRepository": f"https://github.com/{candidate_id}",
            "fetchedAt": "2026-09-11T12:00:00+00:00",
            "contentSha256": valid_sha256,
            "frontmatter": {
                "name": "Test Candidate",
                "description": "A test candidate skill implementation."
            },
        },
        "normalized": {
            "name": "Test Candidate",
            "description": "A test candidate skill.",
        },
        "exactDedupe": {"matched": False},
        "mappingOptions": mapping_options,
        "genericSnapshot": {
            "capturedAt": "2026-09-11T12:00:00+00:00",
            "command": "gaia dev list --generic --json",
            "generics": generics,
            "contentSha256": _canonicalDigest(generics),
            "mappingOptionsSha256": _canonicalDigest(mapping_options),
        },
        "decision": {
            "value": "DEFER",
            "reasonCode": "PREFILL_AWAITING_WORKER",
        },
        "flags": [],
    }


def _makeAssessmentReceipt(packet, tmp_path, filename="assessment.json", registryPath="."):
    """Write an advisory principles assessment receipt for packet."""
    receipt = buildAssessment(packet, registryPath=registryPath)
    path = tmp_path / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(receipt, f)
    return str(path)


def _makeRatifyArgs(tmp_path, packet, packet_path, **kwargs):
    """Build args namespace for ratifyCommand with valid defaults."""
    registry = kwargs.get("registry") or _makeRegistryDir(tmp_path)
    assessment_path = kwargs.get("assessment") or _makeAssessmentReceipt(packet, tmp_path, registryPath=registry)
    base = {
        "packet_path": str(packet_path),
        "registry": registry,
        "decision": "MAP",
        "generic_id": "test-skill",
        "generic_name": "Test Skill",
        "generic_description": "A test skill for mapping.",
        "generic_type": "basic",
        "prereqs": None,
        "contributor": "test-contributor",
        "skill_name": "test-skill-impl",
        "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        "assessment": assessment_path,
        "reviewed_by": "alice",
        "approval_ref": "https://github.com/gaia-research/gaia-skill-tree/issues/123",
        "reason": "Verified human review passes principles.",
        "acknowledge_human_review": True,
    }
    base.update(kwargs)
    return type("Args", (), base)()


class TestRatifyMapDecision:
    """Test MAP ratification (existing generic mapping)."""

    def test_map_ratification_succeeds(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path)

        rc = ratifyCommand(args)
        assert rc == 0

        # Verify packet was written with l4Resolution + review-ready
        with open(packet_path) as f:
            updated = json.load(f)
        assert updated["lifecycle"][-1] == "review-ready"
        assert updated["decision"]["value"] == "MAP"
        assert updated["decision"]["reasonCode"] == REASON_CODES.L4_RATIFIED_MAP
        assert updated["decision"]["genericId"] == "test-skill"
        assert "l4Resolution" in updated
        assert updated["l4Resolution"]["status"] == "approved"

        # Verify humanReview metadata
        hr = updated["l4Resolution"]["humanReview"]
        assert hr["reviewedBy"] == "alice"
        assert hr["approvalRef"] == "https://github.com/gaia-research/gaia-skill-tree/issues/123"
        assert hr["rationale"] == "Verified human review passes principles."
        assert "reviewedAt" in hr
        assert "assessmentReceiptDigest" in hr
        assert hr["operatorOverride"] is False
        assert hr["humanOverride"] is True  # Proposal was DEFER, human ratified MAP
        assert "attestation" in hr

    def test_map_ratification_strips_prereq_whitespace(self, tmp_path):
        """--prereqs "foo, bar" (comma-space) must not fail kebab-case validation."""
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            decision="NEW_GENERIC",
            generic_id="fused-skill",
            generic_name="Fused Skill",
            generic_description="A fused skill combining multiple generics.",
            generic_type="fusion",
            prereqs="test-skill, other-skill",  # comma-space
            skill_name="fused-skill-impl",
        )

        rc = ratifyCommand(args)
        assert rc == 0
        with open(packet_path) as f:
            updated = json.load(f)
        assert updated["l4Resolution"]["generic"]["prerequisites"] == [
            "test-skill", "other-skill"
        ]

    def test_map_rejects_generic_id_absent_from_live_registry(self, tmp_path):
        """MAP must fail if the ratified generic id doesn't exist in the LIVE registry."""
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        registryRoot = tmp_path / "empty-reg"
        (registryRoot / "registry").mkdir(parents=True)
        with open(registryRoot / "registry" / "gaia.json", "w") as f:
            json.dump({"skills": [{"id": "unrelated-skill", "name": "Unrelated"}]}, f)

        assessment_path = _makeAssessmentReceipt(packet, tmp_path, registryPath=str(registryRoot))
        args = _makeRatifyArgs(tmp_path, packet, packet_path, registry=str(registryRoot), assessment=assessment_path)

        rc = ratifyCommand(args)
        assert rc == 1


class TestRatifyNewGenericDecision:
    """Test NEW_GENERIC ratification (create new generic node)."""

    def test_new_generic_basic_succeeds(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            decision="NEW_GENERIC",
            generic_id="new-skill",
            generic_name="New Skill",
            generic_description="A newly created generic skill.",
            generic_type="basic",
            skill_name="new-skill-impl",
        )

        rc = ratifyCommand(args)
        assert rc == 0

        with open(packet_path) as f:
            updated = json.load(f)
        assert updated["lifecycle"][-1] == "review-ready"
        assert updated["decision"]["value"] == "NEW_GENERIC"
        assert updated["decision"]["reasonCode"] == REASON_CODES.L4_RATIFIED_NEW_GENERIC
        assert "genericId" not in updated["decision"]

    def test_new_generic_fusion_with_prereqs(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            decision="NEW_GENERIC",
            generic_id="fused-skill",
            generic_name="Fused Skill",
            generic_description="A fused skill combining multiple generics.",
            generic_type="fusion",
            prereqs="skill-a,skill-b,skill-c",
            skill_name="fused-skill-impl",
        )

        rc = ratifyCommand(args)
        assert rc == 0

        with open(packet_path) as f:
            updated = json.load(f)
        assert updated["l4Resolution"]["generic"]["type"] == "fusion"
        assert updated["l4Resolution"]["generic"]["prerequisites"] == [
            "skill-a", "skill-b", "skill-c"
        ]


class TestHumanReviewEnforcement:
    """Test explicit human acknowledgement and review metadata requirements."""

    def test_reject_without_acknowledge_human_review_even_with_operator_override(self, tmp_path, monkeypatch):
        """Must reject if --acknowledge-human-review is missing, even with operator override."""
        monkeypatch.setenv("GAIA_OPERATOR_OVERRIDE", "1")
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            acknowledge_human_review=False,
        )

        rc = ratifyCommand(args)
        assert rc == 1

    def test_reject_without_reviewer_or_approval_ref_or_reason(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        # Missing reviewed_by
        args1 = _makeRatifyArgs(tmp_path, packet, packet_path, reviewed_by="")
        assert ratifyCommand(args1) == 1

        # Missing approval_ref
        args2 = _makeRatifyArgs(tmp_path, packet, packet_path, approval_ref="")
        assert ratifyCommand(args2) == 1

        # Missing reason
        args3 = _makeRatifyArgs(tmp_path, packet, packet_path, reason="")
        assert ratifyCommand(args3) == 1

    def test_operator_override_recorded_in_attestation(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GAIA_OPERATOR_OVERRIDE", "1")
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path)
        assert ratifyCommand(args) == 0

        with open(packet_path) as f:
            updated = json.load(f)
        assert updated["l4Resolution"]["humanReview"]["operatorOverride"] is True

    def test_operator_override_exact_env_one(self, tmp_path, monkeypatch):
        """GAIA_OPERATOR_OVERRIDE must be exactly '1' to be True."""
        monkeypatch.setenv("GAIA_OPERATOR_OVERRIDE", "0")
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path)
        assert ratifyCommand(args) == 0

        with open(packet_path) as f:
            updated = json.load(f)
        assert updated["l4Resolution"]["humanReview"]["operatorOverride"] is False


class TestAssessmentVerificationInRatify:
    """Test assessment receipt verification and staleness detection in ratify."""

    def test_reject_missing_assessment_receipt_file(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            assessment=str(tmp_path / "nonexistent-receipt.json"),
        )
        rc = ratifyCommand(args)
        assert rc == 1

    def test_reject_stale_or_mismatched_assessment(self, tmp_path):
        """If packet description drifted after assessment was taken, ratify must reject."""
        registry = _makeRegistryDir(tmp_path)
        packet = _makeDeferredMappedPacket()
        assessment_path = _makeAssessmentReceipt(packet, tmp_path, registryPath=registry)

        drifted_packet = _makeDeferredMappedPacket()
        drifted_packet["normalized"]["description"] = "Drifted candidate description after assessment."
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(drifted_packet, f)

        args = _makeRatifyArgs(
            tmp_path,
            drifted_packet,
            packet_path,
            registry=registry,
            assessment=assessment_path,
        )

        rc = ratifyCommand(args)
        assert rc == 1

    def test_ratify_fail_closed_if_validator_unavailable(self, tmp_path):
        """Ratify must fail closed if discovery packet validator is unavailable."""
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path)

        with patch("gaia_cli.commands.dev.ratify._importPacketValidator", return_value=None):
            rc = ratifyCommand(args)
            assert rc == 1


class TestRatifyValidationFailures:
    """Test validation failures and error reporting."""

    def test_ratify_rejects_unmapped_packet(self, tmp_path):
        """Packet without 'mapped' in lifecycle should be rejected."""
        packet = _makeDeferredMappedPacket()
        packet["lifecycle"] = ["discovered", "deferred"]
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path)

        rc = ratifyCommand(args)
        assert rc == 1

    def test_ratify_rejects_missing_generic_snapshot(self, tmp_path):
        """Packet without genericSnapshot should fail validation."""
        packet = _makeDeferredMappedPacket()
        del packet["genericSnapshot"]
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path)

        rc = ratifyCommand(args)
        assert rc == 1

    def test_ratify_rejects_invalid_description_length(self, tmp_path):
        """Generic description must be at least 10 characters."""
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            generic_description="Short",
        )

        rc = ratifyCommand(args)
        assert rc == 1

    def test_ratify_rejects_invalid_skill_url(self, tmp_path):
        """Skill file URL must be a GitHub blob URL ending in SKILL.md."""
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            skill_file_url="https://github.com/test/candidate/blob/main/README.md",
        )

        rc = ratifyCommand(args)
        assert rc == 1


class TestRatifyHardening:
    """Bounded hardening tests for ratifyCommand."""

    def test_ratify_rejects_invalid_decision(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path, decision="DEFER")
        assert ratifyCommand(args) == 1

        args2 = _makeRatifyArgs(tmp_path, packet, packet_path, decision="INVALID")
        assert ratifyCommand(args2) == 1

    def test_ratify_rejects_invalid_generic_type(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path, generic_type="composite")
        assert ratifyCommand(args) == 1

    def test_ratify_rejects_basic_with_prereqs(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            generic_type="basic",
            prereqs="skill-a,skill-b",
        )
        assert ratifyCommand(args) == 1

    def test_ratify_rejects_malformed_packet_non_object(self, tmp_path):
        packet_path = tmp_path / "list_packet.json"
        with open(packet_path, "w") as f:
            json.dump(["not", "an", "object"], f)

        dummy_packet = _makeDeferredMappedPacket()
        args = _makeRatifyArgs(tmp_path, dummy_packet, packet_path)
        assert ratifyCommand(args) == 1

    def test_ratify_rejects_missing_or_invalid_artifact_gate(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet["artifactGate"] = "rejected-missing-frontmatter"
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path)
        assert ratifyCommand(args) == 1

    def test_ratify_rejects_empty_or_invalid_source_content_hash(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet["source"]["contentSha256"] = ""
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = _makeRatifyArgs(tmp_path, packet, packet_path)
        assert ratifyCommand(args) == 1

        packet["source"]["contentSha256"] = "short-hash"
        with open(packet_path, "w") as f:
            json.dump(packet, f)
        args2 = _makeRatifyArgs(tmp_path, packet, packet_path)
        assert ratifyCommand(args2) == 1

    def test_map_node_metadata_mismatch_rejected(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        # Mismatched name
        args1 = _makeRatifyArgs(tmp_path, packet, packet_path, generic_name="Mismatched Name")
        assert ratifyCommand(args1) == 1

        # Mismatched type
        args2 = _makeRatifyArgs(tmp_path, packet, packet_path, generic_type="fusion", prereqs="skill-a")
        assert ratifyCommand(args2) == 1

        # Mismatched description
        args3 = _makeRatifyArgs(tmp_path, packet, packet_path, generic_description="Completely different description.")
        assert ratifyCommand(args3) == 1

    def test_new_generic_prereqs_checks(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        # Prereq missing from live registry
        args1 = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            decision="NEW_GENERIC",
            generic_id="new-fusion",
            generic_name="New Fusion",
            generic_description="Fusion with nonexistent prereq.",
            generic_type="fusion",
            prereqs="nonexistent-skill",
            skill_name="impl",
        )
        assert ratifyCommand(args1) == 1

        # Self-referencing prereq
        args2 = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            decision="NEW_GENERIC",
            generic_id="self-ref",
            generic_name="Self Ref",
            generic_description="Self referencing prereq.",
            generic_type="fusion",
            prereqs="self-ref",
            skill_name="impl",
        )
        assert ratifyCommand(args2) == 1

        # Collision with existing live generic id
        args3 = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            decision="NEW_GENERIC",
            generic_id="test-skill",
            generic_name="Collision",
            generic_description="Collides with existing generic.",
            generic_type="basic",
            skill_name="impl",
        )
        assert ratifyCommand(args3) == 1

    def test_human_override_tracking_and_prior_proposal(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        registry = _makeRegistryDir(tmp_path)
        receipt_path = _makeAssessmentReceipt(packet, tmp_path, registryPath=registry)

        # Modify receipt's proposedDisposition to MAP_CANDIDATE to test-skill
        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt_data = json.load(f)
        receipt_data["proposedDisposition"] = {
            "value": "MAP_CANDIDATE",
            "targetGenericId": "test-skill",
            "reasonCode": "JEV_SEMANTIC_PROPOSAL",
            "advisoryOnly": True,
        }
        with open(receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt_data, f)

        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        # 1. Human agrees with MAP to test-skill -> humanOverride is False
        args_agree = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            registry=registry,
            assessment=receipt_path,
            decision="MAP",
            generic_id="test-skill",
        )
        assert ratifyCommand(args_agree) == 0

        with open(packet_path, "r", encoding="utf-8") as f:
            res_agree = json.load(f)
        hr_agree = res_agree["l4Resolution"]["humanReview"]
        assert hr_agree["humanOverride"] is False
        assert hr_agree["priorProposal"]["value"] == "MAP_CANDIDATE"

        # 2. Human ratifies NEW_GENERIC instead -> humanOverride is True
        with open(packet_path, "w") as f:
            json.dump(packet, f)
        args_override = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
            registry=registry,
            assessment=receipt_path,
            decision="NEW_GENERIC",
            generic_id="brand-new-skill",
            generic_name="Brand New Skill",
            generic_description="Brand new skill description here.",
            generic_type="basic",
            skill_name="brand-new-impl",
        )
        assert ratifyCommand(args_override) == 0

        with open(packet_path, "r", encoding="utf-8") as f:
            res_override = json.load(f)
        hr_override = res_override["l4Resolution"]["humanReview"]
        assert hr_override["humanOverride"] is True


class TestRatifyFileHandling:
    """Test file reading/writing and error cases."""

    def test_ratify_rejects_missing_packet_file(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        args = _makeRatifyArgs(
            tmp_path,
            packet,
            tmp_path / "nonexistent.json",
        )

        rc = ratifyCommand(args)
        assert rc == 1

    def test_ratify_rejects_malformed_json(self, tmp_path):
        packet_path = tmp_path / "malformed.json"
        with open(packet_path, "w") as f:
            f.write("{invalid json")

        packet = _makeDeferredMappedPacket()
        args = _makeRatifyArgs(
            tmp_path,
            packet,
            packet_path,
        )

        rc = ratifyCommand(args)
        assert rc == 1
