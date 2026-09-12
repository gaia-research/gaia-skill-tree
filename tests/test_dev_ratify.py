"""Tests for gaia dev ratify command (G1 #1784, step 6-8)."""

import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gaia_cli.commands.dev.ratify import ratifyCommand
from gaia_cli.intakeAdapter import REASON_CODES, _canonicalDigest

# Matches the generics frozen into _makeDeferredMappedPacket()'s genericSnapshot.
# Ratify validates the packet against the LIVE registry (not the packet's own
# self-reported snapshot — see ratify.py), so tests must provide a registry dir
# whose gaia.json actually contains these skill ids, or every ratification
# would fail with UNTRUSTED_GENERIC_SNAPSHOT regardless of the scenario under test.
_LIVE_REGISTRY_SKILLS = [
    {"id": "test-skill", "name": "Test Skill", "type": "basic"},
    {"id": "other-skill", "name": "Other Skill", "type": "basic"},
]


def _makeRegistryDir(tmp_path):
    """Write a minimal registry/gaia.json under tmp_path and return its path."""
    registryRoot = tmp_path / "reg"
    registryDir = registryRoot / "registry"
    registryDir.mkdir(parents=True)
    with open(registryDir / "gaia.json", "w", encoding="utf-8") as f:
        json.dump({"skills": _LIVE_REGISTRY_SKILLS}, f)
    return str(registryRoot)


def _makeDeferredMappedPacket():
    """Factory for a valid deferred+mapped test packet."""
    # Create mappingOptions first
    mappingOptions = [
        {
            "genericId": "test-skill",
            "rationale": "Test match",
            "similarity": 0.95,
            "matchTier": "strong",
        }
    ]

    # Create generics
    generics = [
        {"id": "test-skill", "name": "Test Skill", "kind": "generic"},
        {"id": "other-skill", "name": "Other Skill", "kind": "generic"},
    ]

    # Valid SHA256 hash (all zeros for test)
    valid_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"

    return {
        "contractVersion": "discovery-packet-v2",
        "candidateId": "test/candidate",
        "lifecycle": ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "deferred"],
        "source": {
            "canonicalUrl": "https://github.com/test/candidate/blob/main/SKILL.md",
            "sourceLane": "source-repository",
            "hostRepository": "https://github.com/test/candidate",
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
        "mappingOptions": mappingOptions,
        "genericSnapshot": {
            "capturedAt": "2026-09-11T12:00:00+00:00",
            "command": "gaia dev list --generic --json",
            "generics": generics,
            "contentSha256": _canonicalDigest(generics),
            "mappingOptionsSha256": _canonicalDigest(mappingOptions),
        },
        "decision": {
            "value": "DEFER",
            "reasonCode": "PREFILL_AWAITING_WORKER",
        },
        "flags": [],
    }


class TestRatifyMapDecision:
    """Test MAP ratification (existing generic mapping)."""

    def test_map_ratification_succeeds(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "MAP",
            "generic_id": "test-skill",
            "generic_name": "Test Skill",
            "generic_description": "A test skill for mapping.",
            "generic_type": "basic",
            "prereqs": None,
            "contributor": "test-contributor",
            "skill_name": "test-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

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

    def test_map_ratification_strips_prereq_whitespace(self, tmp_path):
        """--prereqs "foo, bar" (comma-space) must not fail kebab-case validation."""
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "NEW_GENERIC",
            "generic_id": "fused-skill",
            "generic_name": "Fused Skill",
            "generic_description": "A fused skill combining multiple generics.",
            "generic_type": "fusion",
            "prereqs": "test-skill, other-skill",  # comma-space, not comma-only
            "contributor": "test-contributor",
            "skill_name": "fused-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

        rc = ratifyCommand(args)
        assert rc == 0
        with open(packet_path) as f:
            updated = json.load(f)
        assert updated["l4Resolution"]["generic"]["prerequisites"] == [
            "test-skill", "other-skill"
        ]

    def test_map_rejects_generic_id_absent_from_live_registry(self, tmp_path):
        """MAP must fail if the ratified generic id doesn't exist in the LIVE registry,
        even if it matches the packet's own (potentially stale) frozen snapshot."""
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        # registry dir intentionally does NOT contain "test-skill"
        registryRoot = tmp_path / "empty-reg"
        (registryRoot / "registry").mkdir(parents=True)
        with open(registryRoot / "registry" / "gaia.json", "w") as f:
            json.dump({"skills": [{"id": "unrelated-skill", "name": "Unrelated"}]}, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": str(registryRoot),
            "decision": "MAP",
            "generic_id": "test-skill",
            "generic_name": "Test Skill",
            "generic_description": "A test skill for mapping.",
            "generic_type": "basic",
            "prereqs": None,
            "contributor": "test-contributor",
            "skill_name": "test-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

        rc = ratifyCommand(args)
        assert rc == 1  # test-skill is not in the live registry snapshot


class TestRatifyNewGenericDecision:
    """Test NEW_GENERIC ratification (create new generic node)."""

    def test_new_generic_basic_succeeds(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "NEW_GENERIC",
            "generic_id": "new-skill",
            "generic_name": "New Skill",
            "generic_description": "A newly created generic skill.",
            "generic_type": "basic",
            "prereqs": None,
            "contributor": "test-contributor",
            "skill_name": "new-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

        rc = ratifyCommand(args)
        assert rc == 0

        with open(packet_path) as f:
            updated = json.load(f)
        assert updated["lifecycle"][-1] == "review-ready"
        assert updated["decision"]["value"] == "NEW_GENERIC"
        assert updated["decision"]["reasonCode"] == REASON_CODES.L4_RATIFIED_NEW_GENERIC
        assert "genericId" not in updated["decision"]  # NEW_GENERIC doesn't set genericId

    def test_new_generic_fusion_with_prereqs(self, tmp_path):
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "NEW_GENERIC",
            "generic_id": "fused-skill",
            "generic_name": "Fused Skill",
            "generic_description": "A fused skill combining multiple generics.",
            "generic_type": "fusion",
            "prereqs": "skill-a,skill-b,skill-c",
            "contributor": "test-contributor",
            "skill_name": "fused-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

        rc = ratifyCommand(args)
        assert rc == 0

        with open(packet_path) as f:
            updated = json.load(f)
        assert updated["l4Resolution"]["generic"]["type"] == "fusion"
        assert updated["l4Resolution"]["generic"]["prerequisites"] == [
            "skill-a", "skill-b", "skill-c"
        ]


class TestRatifyValidationFailures:
    """Test validation failures and error reporting."""

    def test_ratify_rejects_unmapped_packet(self, tmp_path):
        """Packet without 'mapped' in lifecycle should be rejected."""
        packet = _makeDeferredMappedPacket()
        packet["lifecycle"] = ["discovered", "deferred"]  # Remove 'mapped'
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "MAP",
            "generic_id": "test-skill",
            "generic_name": "Test Skill",
            "generic_description": "A test skill.",
            "generic_type": "basic",
            "prereqs": None,
            "contributor": "test-contributor",
            "skill_name": "test-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

        rc = ratifyCommand(args)
        assert rc == 1  # Should fail

    def test_ratify_rejects_missing_generic_snapshot(self, tmp_path):
        """Packet without genericSnapshot should fail validation."""
        packet = _makeDeferredMappedPacket()
        del packet["genericSnapshot"]
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "MAP",
            "generic_id": "test-skill",
            "generic_name": "Test Skill",
            "generic_description": "A test skill.",
            "generic_type": "basic",
            "prereqs": None,
            "contributor": "test-contributor",
            "skill_name": "test-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

        rc = ratifyCommand(args)
        assert rc == 1  # Should fail due to missing snapshot

    def test_ratify_rejects_invalid_description_length(self, tmp_path):
        """Generic description must be at least 10 characters."""
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "MAP",
            "generic_id": "test-skill",
            "generic_name": "Test Skill",
            "generic_description": "Short",  # Too short
            "generic_type": "basic",
            "prereqs": None,
            "contributor": "test-contributor",
            "skill_name": "test-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

        rc = ratifyCommand(args)
        assert rc == 1  # Should fail

    def test_ratify_rejects_invalid_skill_url(self, tmp_path):
        """Skill file URL must be a GitHub blob URL ending in SKILL.md."""
        packet = _makeDeferredMappedPacket()
        packet_path = tmp_path / "test.json"
        with open(packet_path, "w") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "MAP",
            "generic_id": "test-skill",
            "generic_name": "Test Skill",
            "generic_description": "A test skill.",
            "generic_type": "basic",
            "prereqs": None,
            "contributor": "test-contributor",
            "skill_name": "test-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/README.md",  # Wrong file
        })()

        rc = ratifyCommand(args)
        assert rc == 1  # Should fail


class TestRatifyFileHandling:
    """Test file reading/writing and error cases."""

    def test_ratify_rejects_missing_packet_file(self, tmp_path):
        args = type("Args", (), {
            "packet_path": str(tmp_path / "nonexistent.json"),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "MAP",
            "generic_id": "test-skill",
            "generic_name": "Test Skill",
            "generic_description": "A test skill.",
            "generic_type": "basic",
            "prereqs": None,
            "contributor": "test-contributor",
            "skill_name": "test-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

        rc = ratifyCommand(args)
        assert rc == 1

    def test_ratify_rejects_malformed_json(self, tmp_path):
        packet_path = tmp_path / "malformed.json"
        with open(packet_path, "w") as f:
            f.write("{invalid json")

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "registry": _makeRegistryDir(tmp_path),
            "decision": "MAP",
            "generic_id": "test-skill",
            "generic_name": "Test Skill",
            "generic_description": "A test skill.",
            "generic_type": "basic",
            "prereqs": None,
            "contributor": "test-contributor",
            "skill_name": "test-skill-impl",
            "skill_file_url": "https://github.com/test/candidate/blob/main/SKILL.md",
        })()

        rc = ratifyCommand(args)
        assert rc == 1
