"""Tests for src/gaia_cli/intakeAdapter.py (RFC2 Gap B).

Covers the packet->intake-YAML mapping: MAP path, NEW_GENERIC basic,
NEW_GENERIC fusion (prerequisites present), suite fan-out (component + capstone),
and attributionScope derivation.
"""

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
            "sourceLane": "source-repository",
            "frontmatter": {"name": "Some Skill", "description": "Does a thing well."},
        },
        "normalized": {"name": "Some Skill", "description": "Does a thing well."},
        "exactDedupe": {"matched": False},
        "mappingOptions": [],
        "decision": {"value": "MAP", "reasonCode": "strong-match", "genericId": "research"},
        "flags": [],
    }
    packet.update(overrides)
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
    assert entry["id"] == "alice-some-skill"
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
    assert entry["name"] == "Some Skill"  # normalized wins over proposal


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
        }
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
        }
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
    scopes = {s["id"]: s["attributionScope"] for s in result["skills"]}
    assert scopes["alice-component-a"] == "suite-component"
    assert scopes["alice-capstone"] == "suite-wide"


def test_build_intake_yaml_single_packet():
    result = buildIntakeYaml(_basePacket())
    assert len(result["skills"]) == 1
    assert result["skills"][0]["id"] == "alice-some-skill"
