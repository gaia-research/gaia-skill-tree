"""Executable contract tests for the discovery-only Gaia curation packet."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / ".claude/skills/gaia-curate"
VALIDATOR = CORE / "scripts/validate_discovery_packet.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_discovery_packet", VALIDATOR)
    assert spec and spec.loader, "validator module must be loadable"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def review_ready_packet() -> dict:
    generic_snapshot = [
        {"id": "example-capability", "kind": "generic", "name": "Example Capability"}
    ]
    return {
        "contractVersion": "discovery-packet-v1",
        "candidateId": "candidate-example-001",
        "lifecycle": ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"],
        "source": {
            "canonicalUrl": "https://github.com/example/repo/blob/main/skills/example/SKILL.md",
            "hostRepository": "https://github.com/example/repo",
            "sourceLane": "source-repository",
            "fetchedAt": "2026-07-13T00:00:00Z",
            "contentSha256": "a" * 64,
            "frontmatter": {
                "name": "Example Skill",
                "description": "A reusable example capability with an explicit operating boundary.",
            },
            "attribution": {"host": "example", "citedOrigin": None},
            "trendSignals": {"starsDelta7d": 12, "crossSourceRecurrence": 2},
        },
        "normalized": {
            "name": "Example Skill",
            "description": "A reusable example capability with an explicit operating boundary.",
        },
        "exactDedupe": {
            "matched": False,
            "matchedCandidateId": None,
            "matchedCanonicalUrl": None,
        },
        "mappingOptions": [
            {"genericId": "example-capability", "rationale": "Exact capability match."}
        ],
        "genericSnapshot": {
            "capturedAt": "2026-07-13T00:00:00Z",
            "command": "gaia dev list --generic --json",
            "generics": generic_snapshot,
            "contentSha256": hashlib.sha256(
                json.dumps(generic_snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "mappingOptionsSha256": "79c7341ef802e0e5cfb5cae84b0054f7977d3b5ed7be4297bc910cee41ccade1",
        },
        "decision": {
            "value": "MAP",
            "reasonCode": "MAP_EXISTING_GENERIC",
            "genericId": "example-capability",
        },
        "flags": [],
    }


def errors(packet: dict) -> list[str]:
    return load_validator().validate_packet(packet)


def test_accepts_review_ready_packet(review_ready_packet):
    assert errors(review_ready_packet) == []


def test_rejects_invalid_lifecycle_transition(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["lifecycle"] = ["discovered", "parsed", "review-ready"]
    assert "INVALID_LIFECYCLE_TRANSITION" in errors(packet)


def test_review_ready_requires_complete_lifecycle(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["lifecycle"] = ["discovered", "review-ready"]
    assert "INVALID_LIFECYCLE_TRANSITION" in errors(packet)


def test_rejects_empty_lifecycle_and_missing_source_provenance(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["lifecycle"] = []
    packet["source"] = {}
    found = errors(packet)
    assert "INVALID_LIFECYCLE_TRANSITION" in found
    assert "MISSING_SOURCE_PROVENANCE" in found


def test_allows_early_defer_before_fetch(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["lifecycle"] = ["discovered", "deferred"]
    packet["source"] = {
        "canonicalUrl": "https://example.com/lead",
        "sourceLane": "marketplace",
    }
    packet["normalized"] = {}
    packet["exactDedupe"] = {}
    packet["mappingOptions"] = []
    packet["decision"] = {
        "value": "DEFER",
        "reasonCode": "UPSTREAM_SKILL_UNRESOLVED",
    }
    assert errors(packet) == []


def test_rejects_unknown_luna_decision(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["decision"]["value"] = "ACCEPT"
    assert "UNKNOWN_DECISION" in errors(packet)


def test_map_must_select_one_supplied_generic(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["decision"]["genericId"] = "invented-by-worker"
    assert "INVALID_GENERIC_SELECTION" in errors(packet)


def test_review_ready_requires_normalized_name_and_description(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["normalized"] = {}
    assert "INVALID_NORMALIZED_CANDIDATE" in errors(packet)


def test_rejects_invalid_source_urls(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["source"]["canonicalUrl"] = "not-a-url"
    packet["source"]["hostRepository"] = "also-not-a-url"
    assert "INVALID_SOURCE_URL" in errors(packet)


def test_new_generic_requires_reviewable_proposal(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["decision"] = {
        "value": "NEW_GENERIC",
        "reasonCode": "NOVEL_CAPABILITY",
    }
    assert "INVALID_NEW_GENERIC_PROPOSAL" in errors(packet)

    packet["decision"]["proposal"] = {
        "name": "Example Capability",
        "description": "Performs one bounded and falsifiable capability.",
        "type": "basic",
    }
    assert errors(packet) == []


def test_terminal_state_must_match_decision(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["lifecycle"][-1] = "deferred"
    assert "INVALID_DECISION_STATE" in errors(packet)


def test_rejects_missing_fetched_frontmatter(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    del packet["source"]["frontmatter"]["description"]
    assert "MISSING_FETCHED_FRONTMATTER" in errors(packet)


def test_allows_malformed_artifact_to_reject_before_parse(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["lifecycle"] = ["discovered", "fetched", "rejected"]
    packet["source"].pop("frontmatter")
    packet["normalized"] = {}
    packet["mappingOptions"] = []
    packet["decision"] = {
        "value": "NOT_A_SKILL",
        "reasonCode": "REJECT_MISSING_FRONTMATTER",
    }
    assert errors(packet) == []


def test_rejects_more_than_three_mapping_options(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["mappingOptions"] *= 4
    assert "TOO_MANY_MAPPING_OPTIONS" in errors(packet)


def test_rejects_tampered_mapping_options_digest(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["genericSnapshot"]["mappingOptionsSha256"] = "f" * 64
    assert "INVALID_GENERIC_SNAPSHOT" in errors(packet)


def test_rejects_mapping_options_missing_from_generic_snapshot(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["genericSnapshot"]["generics"] = []
    assert "INVALID_GENERIC_SNAPSHOT" in errors(packet)


def test_accepts_duplicate_with_canonical_url_proof(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["lifecycle"][-1] = "rejected"
    packet["exactDedupe"] = {
        "matched": True,
        "matchedCandidateId": "candidate-existing-001",
        "matchedCanonicalUrl": "https://github.com/example/existing/blob/main/SKILL.md",
    }
    packet["decision"] = {
        "value": "DUPLICATE",
        "reasonCode": "DUPLICATE_CANONICAL_URL",
    }
    assert errors(packet) == []


def test_rejects_duplicate_without_deduplication_proof(review_ready_packet):
    packet = copy.deepcopy(review_ready_packet)
    packet["lifecycle"][-1] = "rejected"
    packet["exactDedupe"] = {"matched": True}
    packet["decision"] = {
        "value": "DUPLICATE",
        "reasonCode": "DUPLICATE_UNPROVEN",
    }
    assert "INVALID_DUPLICATE_PROOF" in errors(packet)


@pytest.mark.parametrize("field", ["evidence", "trustMagnitude", "tmScore", "stars", "grade", "class"])
def test_rejects_downstream_scoring_and_evidence_fields(review_ready_packet, field):
    packet = copy.deepcopy(review_ready_packet)
    packet[field] = "leak"
    assert "DOWNSTREAM_FIELD_FORBIDDEN" in errors(packet)


def test_mirror_directories_are_byte_identical():
    claude_root = ROOT / ".claude/skills"
    agents_root = ROOT / ".agents/skills"
    for claude_dir in sorted(claude_root.glob("gaia-curate*")):
        assert claude_dir.is_dir()
        agents_dir = agents_root / claude_dir.name
        assert agents_dir.is_dir(), f"missing mirror {agents_dir}"
        claude_files = sorted(
            path.relative_to(claude_dir)
            for path in claude_dir.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
        agents_files = sorted(
            path.relative_to(agents_dir)
            for path in agents_dir.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
        assert agents_files == claude_files
        for relative_path in claude_files:
            assert (agents_dir / relative_path).read_bytes() == (claude_dir / relative_path).read_bytes()


def test_review_ready_fixture_is_valid():
    fixture = CORE / "fixtures/review-ready-packet.json"
    assert errors(json.loads(fixture.read_text(encoding="utf-8"))) == []


def test_luna_viability_fixture_and_oracle_are_separate_and_bounded():
    page = json.loads((CORE / "fixtures/luna-viability-page.json").read_text())
    expected = json.loads((CORE / "fixtures/luna-viability-expected.json").read_text())
    assert len(page["candidates"]) == 5
    assert "decisions" not in page
    assert [row["candidateId"] for row in expected["decisions"]] == [
        row["candidateId"] for row in page["candidates"]
    ]
    assert {row["decision"] for row in expected["decisions"]} <= set(
        page["decisionVocabulary"]
    )
