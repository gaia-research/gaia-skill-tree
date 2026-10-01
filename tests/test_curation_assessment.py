"""Tests for curation principles assessment (CURATION-UPGRADE.md)."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gaia_cli.curation.assessment import (
    CONTRACT_VERSION,
    AUTHORITY,
    REQUIRED_EIGHT_PRINCIPLES,
    QUESTION_SCHEMA,
    loadPrinciples,
    getRubricDigest,
    assessmentInputDigest,
    candidateSourceDigest,
    buildAssessment,
    validateAssessment,
    assessCommand,
    extractSemanticInputs,
)
from gaia_cli.jev import JevClient, PINNED_MODEL, DEFAULT_ENDPOINT


def _make_test_packet(
    candidate_id="testcontrib/test-skill",
    name="Test Skill",
    description="A test candidate skill implementation for graph operations.",
    mapping_options=None,
    content_sha="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    trend_signals=None,
):
    if mapping_options is None:
        mapping_options = [
            {
                "genericId": "graph-traversal",
                "similarity": 0.88,
                "matchTier": "strong",
                "rationale": "High similarity to graph algorithms.",
            }
        ]

    packet = {
        "contractVersion": "discovery-packet-v2",
        "candidateId": candidate_id,
        "lifecycle": ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "deferred"],
        "artifactGate": "valid-skill",
        "source": {
            "canonicalUrl": f"https://github.com/{candidate_id}/blob/main/SKILL.md",
            "sourceLane": "source-repository",
            "hostRepository": f"https://github.com/{candidate_id}",
            "fetchedAt": "2026-09-11T12:00:00+00:00",
            "contentSha256": content_sha,
            "frontmatter": {
                "name": name,
                "description": description,
            },
        },
        "normalized": {
            "name": name,
            "description": description,
        },
        "exactDedupe": {"matched": False},
        "mappingOptions": mapping_options,
        "genericSnapshot": {
            "capturedAt": "2026-09-11T12:00:00+00:00",
            "command": "gaia dev list --generic --json",
            "generics": [
                {
                    "id": "graph-traversal",
                    "name": "Graph Traversal",
                    "kind": "generic",
                    "description": "Algorithms for navigating graphs and trees.",
                }
            ],
            "contentSha256": "0" * 64,
            "mappingOptionsSha256": "0" * 64,
        },
        "decision": {
            "value": "DEFER",
            "reasonCode": "PREFILL_AWAITING_WORKER",
        },
        "flags": [],
    }

    if trend_signals is not None:
        packet["source"]["trendSignals"] = trend_signals

    return packet


def _make_test_registry(tmp_path, skills=None):
    """Create a minimal temporary registry layout with canonical nodes."""
    if skills is None:
        skills = [
            {
                "id": "graph-traversal",
                "name": "Graph Traversal",
                "description": "Algorithms for navigating graphs and trees.",
                "type": "basic",
                "prerequisites": [],
            },
            {
                "id": "tree-search",
                "name": "Tree Search",
                "description": "Algorithms for tree search and exploration.",
                "type": "basic",
                "prerequisites": [],
            },
        ]
    reg_root = tmp_path / "test_reg"
    nodes_dir = reg_root / "registry" / "nodes" / "basic"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    for s in skills:
        node_file = nodes_dir / f"{s['id']}.json"
        node_file.write_text(json.dumps(s, indent=2), encoding="utf-8")
    return str(reg_root)


def _make_transport_response(body_bytes, choice_map=None, confidence=0.90, model=PINNED_MODEL):
    """Build a valid Jev response payload matching question criteria distributions."""
    req = json.loads(body_bytes)
    answers = {}
    for qid, q in req.get("questions", {}).items():
        opts = list(q["criteria"].keys())
        if choice_map and qid in choice_map:
            choice = choice_map[qid]
        else:
            choice = opts[0]
        if len(opts) == 1:
            probs = {choice: 1.0}
        else:
            p_rest = round(0.10 / (len(opts) - 1), 4)
            probs = {opt: p_rest for opt in opts}
            probs[choice] = round(1.0 - sum(p for k, p in probs.items() if k != choice), 4)
        answers[qid] = {
            "type": "choice",
            "choice": choice,
            "confidence": confidence,
            "probabilities": probs,
        }
    resp = {
        "model": model,
        "usage": {"input_tokens": 120, "output_tokens": 30},
        "answers": answers,
    }
    return 200, json.dumps(resp).encode("utf-8")


class TestPrinciplesRubric:
    """Contract and principles rubric validation."""

    def test_load_principles_contains_eight_principles(self):
        rubric = loadPrinciples()
        assert rubric["contractVersion"] == "curation-principles-v1"
        assert rubric["authority"] == AUTHORITY
        principles = rubric["principles"]
        for p in REQUIRED_EIGHT_PRINCIPLES:
            assert p in principles, f"Principle '{p}' missing from principles contract"

    def test_rubric_digest_deterministic(self):
        rubric = loadPrinciples()
        d1 = getRubricDigest(rubric)
        d2 = getRubricDigest(rubric)
        assert d1 == d2
        assert len(d1) == 64


class TestAssessmentDigests:
    """Semantic input and candidate source digest calculations."""

    def test_source_sha_preserved_vs_candidate_semantic_digest_different(self):
        """Same source bytes preserve source digest, while different candidate metadata changes semantic digest."""
        sha = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
        p1 = _make_test_packet(candidate_id="alice/foo", name="Foo", content_sha=sha)
        p2 = _make_test_packet(candidate_id="bob/bar", name="Bar", content_sha=sha)

        # Source digest is purely from source.contentSha256
        assert candidateSourceDigest(p1) == sha
        assert candidateSourceDigest(p2) == sha
        assert candidateSourceDigest(p1) == candidateSourceDigest(p2)

        # Semantic input digest incorporates candidate identity and metadata
        assert assessmentInputDigest(p1) != assessmentInputDigest(p2)

    def test_topology_and_metric_independence(self):
        """Stargazers, commits, and trust metrics must not affect semanticInputSha256."""
        p1 = _make_test_packet()
        p2 = _make_test_packet(
            trend_signals={"stargazers": 12000, "commits": 500, "contributors": 42}
        )
        p2["evidence"] = [{"grade": "S", "trust": 300, "url": "https://example.com"}]
        p2["trustMagnitude"] = 280

        d1 = assessmentInputDigest(p1)
        d2 = assessmentInputDigest(p2)
        assert d1 == d2, "Metric contamination: popularity signals altered semantic input digest"

    def test_semantic_changes_alter_digest(self):
        p1 = _make_test_packet(description="Original description")
        p2 = _make_test_packet(description="Different semantic description")
        assert assessmentInputDigest(p1) != assessmentInputDigest(p2)


class TestCorpusShaInvalidation:
    """Corpus SHA changes in nodes, prereqs, or new neighbors invalidate assessment."""

    def test_corpus_sha_change_nodes_invalidate(self, tmp_path):
        skills1 = [
            {"id": "graph-traversal", "name": "Graph Traversal", "description": "Desc 1", "type": "basic", "prerequisites": []}
        ]
        reg1 = _make_test_registry(tmp_path / "r1", skills1)
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg1)
        assert validateAssessment(receipt, packet, registryPath=reg1) == []

        # Modified node description in catalog
        skills2 = [
            {"id": "graph-traversal", "name": "Graph Traversal", "description": "Updated Desc", "type": "basic", "prerequisites": []}
        ]
        reg2 = _make_test_registry(tmp_path / "r2", skills2)
        errors = validateAssessment(receipt, packet, registryPath=reg2)
        assert any("catalogSha256 mismatch or stale" in e for e in errors)
        assert any("semanticInputSha256 mismatch or stale" in e for e in errors)

    def test_corpus_sha_change_prereqs_invalidate(self, tmp_path):
        skills1 = [
            {"id": "graph-traversal", "name": "Graph Traversal", "description": "Navigating graphs", "type": "basic", "prerequisites": []}
        ]
        reg1 = _make_test_registry(tmp_path / "r1", skills1)
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg1)

        # Node prerequisites changed in catalog
        skills2 = [
            {"id": "graph-traversal", "name": "Graph Traversal", "description": "Navigating graphs", "type": "fusion", "prerequisites": ["tree-search"]}
        ]
        reg2 = _make_test_registry(tmp_path / "r2", skills2)
        errors = validateAssessment(receipt, packet, registryPath=reg2)
        assert any("catalogSha256 mismatch or stale" in e for e in errors)

    def test_corpus_sha_change_new_neighbor_invalidate(self, tmp_path):
        skills1 = [
            {"id": "graph-traversal", "name": "Graph Traversal", "description": "Graph navigation", "type": "basic", "prerequisites": []}
        ]
        reg1 = _make_test_registry(tmp_path / "r1", skills1)
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg1)

        # Added new generic neighbor to catalog
        skills2 = [
            {"id": "graph-traversal", "name": "Graph Traversal", "description": "Graph navigation", "type": "basic", "prerequisites": []},
            {"id": "new-neighbor", "name": "New Neighbor", "description": "A new neighbor capability", "type": "basic", "prerequisites": []},
        ]
        reg2 = _make_test_registry(tmp_path / "r2", skills2)
        errors = validateAssessment(receipt, packet, registryPath=reg2)
        assert any("catalogSha256 mismatch or stale" in e for e in errors)


class TestBuildAssessment:
    """Assessment construction and deterministic logic."""

    def test_build_assessment_structure_and_authority(self, tmp_path):
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg)

        assert receipt["contractVersion"] == CONTRACT_VERSION
        assert receipt["authority"] == AUTHORITY
        assert receipt["candidateId"] == "testcontrib/test-skill"
        assert receipt["candidateSourceDigest"] == candidateSourceDigest(packet)
        assert receipt["semanticInputSha256"] == assessmentInputDigest(packet, registryPath=reg)

        principles = receipt["principles"]
        for p in REQUIRED_EIGHT_PRINCIPLES:
            assert p in principles

        assert receipt["uncertainty"]["level"] == "review-required"
        assert receipt["proposedDisposition"]["value"] == "DEFER"
        assert receipt["proposedDisposition"]["advisoryOnly"] is True

        # Jev off by default
        assert receipt["jevAdvice"]["status"] == "skipped"
        assert receipt["jevAdvice"]["reason"] == "jev_off"

    def test_assess_does_not_forge_l4_or_mutate_packet(self, tmp_path):
        """Assessment must never write l4Resolution or mutate the packet dictionary."""
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet()
        packet_copy = json.loads(json.dumps(packet))
        assert "l4Resolution" not in packet

        receipt = buildAssessment(packet, registryPath=reg)
        assert packet == packet_copy
        assert "l4Resolution" not in packet
        assert "l4Resolution" not in receipt

    def test_empty_recall_does_not_claim_automatic_novelty(self, tmp_path):
        """Empty recall must result in DEFER/possible-new-generic and review-required uncertainty."""
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet(mapping_options=[])
        receipt = buildAssessment(packet, registryPath=reg)

        assert receipt["retrievedGenerics"] == []
        assert receipt["uncertainty"]["emptyRecall"] is True
        assert receipt["uncertainty"]["level"] == "review-required"
        assert receipt["principles"]["relation"]["relation"] == "unknown"
        assert receipt["proposedDisposition"]["value"] == "DEFER"
        assert receipt["proposedDisposition"]["reasonCode"] == "NO_RECALL_POSSIBLE_NEW_GENERIC"
        assert receipt["proposedDisposition"]["targetGenericId"] is None

    def test_principles_doctrine_and_baseline_evaluations(self, tmp_path):
        """Baseline evaluations retain unknown; similarity/required tool prose/named neighbor flags no ontology."""
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet(
            description="Algorithms for navigating graphs and trees. Requires tool XYZ and depends on product ABC.",
            mapping_options=[
                {
                    "genericId": "graph-traversal",
                    "similarity": 0.99,
                    "matchTier": "strong",
                    "rationale": "Identical description text match.",
                }
            ],
        )
        receipt = buildAssessment(packet, registryPath=reg)

        # Same description does not auto-reject or claim ontology
        assert receipt["proposedDisposition"]["value"] == "DEFER"
        assert receipt["proposedDisposition"]["advisoryOnly"] is True

        # Baseline relation, atomicity, shape retain unknown without human/advice
        assert receipt["principles"]["relation"]["relation"] == "unknown"
        assert receipt["principles"]["atomicity"]["type"] == "unknown"
        assert receipt["principles"]["artifact_packaging"]["shape"] == "unknown"

        # Overlap notes caution against equating similarity with identity
        overlap = receipt["principles"]["overlap"]
        assert "Scores never imply identity or novelty" in overlap["notes"]

        # Topology independence confirms exclusion of popularity
        topo = receipt["principles"]["topology_independence"]
        assert "rank, popularity and evidence excluded" in topo["inputs"]


class TestValidateAssessment:
    """Assessment verification and staleness detection."""

    def test_fresh_assessment_passes_validation(self, tmp_path):
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg)
        errors = validateAssessment(receipt, packet, registryPath=reg)
        assert errors == []

    def test_stale_assessment_rejected_on_packet_drift(self, tmp_path):
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet(description="Initial text")
        receipt = buildAssessment(packet, registryPath=reg)

        drifted_packet = _make_test_packet(description="Updated text after human edit")
        errors = validateAssessment(receipt, drifted_packet, registryPath=reg)
        assert any("receipt semanticInputSha256 mismatch or stale" in e for e in errors)

    def test_mismatched_candidate_rejected(self, tmp_path):
        reg = _make_test_registry(tmp_path)
        p1 = _make_test_packet(candidate_id="alice/skill-a")
        p2 = _make_test_packet(candidate_id="bob/skill-b")
        receipt = buildAssessment(p1, registryPath=reg)

        errors = validateAssessment(receipt, p2, registryPath=reg)
        assert any("candidateId mismatch or stale" in e for e in errors)

    def test_wrong_contract_or_authority_rejected(self, tmp_path):
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg)

        bad_contract = receipt.copy()
        bad_contract["contractVersion"] = "curation-assessment-v0"
        assert any("contractVersion mismatch or stale" in e for e in validateAssessment(bad_contract, packet, registryPath=reg))

        bad_auth = receipt.copy()
        bad_auth["authority"] = "binding"
        assert any("authority mismatch or stale" in e for e in validateAssessment(bad_auth, packet, registryPath=reg))

    def test_reject_forged_authority(self, tmp_path):
        """Receipt containing human authority fields must be rejected."""
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg)

        forged1 = json.loads(json.dumps(receipt))
        forged1["l4Resolution"] = {"status": "approved"}
        assert "receipt contains forbidden human authority fields" in validateAssessment(forged1, packet, registryPath=reg)

        forged2 = json.loads(json.dumps(receipt))
        forged2["humanReview"] = {"reviewedBy": "alice"}
        assert "receipt contains forbidden human authority fields" in validateAssessment(forged2, packet, registryPath=reg)

        forged3 = json.loads(json.dumps(receipt))
        forged3["ratifiedBy"] = "alice"
        assert "receipt contains forbidden human authority fields" in validateAssessment(forged3, packet, registryPath=reg)

        forged4 = json.loads(json.dumps(receipt))
        forged4["decisionAuthority"] = "model"
        assert "receipt contains forbidden human authority fields" in validateAssessment(forged4, packet, registryPath=reg)


class TestNativeJevIntegration:
    """Native JevClient transport tests with realistic distributions and failure modes."""

    def test_native_jev_transport_success_two_calls_map_candidate(self, tmp_path, monkeypatch):
        """Native JevClient evaluates 2 calls max, inspects payload, returns MAP_CANDIDATE."""
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        recorded_calls = []

        def transport(url, headers, body_bytes, timeout):
            assert url == DEFAULT_ENDPOINT
            assert headers["Authorization"] == "Bearer synthetic-test-token-123"
            payload = json.loads(body_bytes)
            assert payload["model"] == PINNED_MODEL
            # No popularity fields sent in state
            state_str = json.dumps(payload["state"])
            assert "stargazers" not in state_str
            assert "trendsignals" not in state_str.lower()
            assert "trustmagnitude" not in state_str.lower()
            assert "evidence" not in payload["state"]

            recorded_calls.append(payload)
            # Call 1: target="graph-traversal", relation="narrower", shape="single"
            # Call 2: transferability="yes", distinction="material", atomicity="basic"
            choice_map = {
                "target": "graph-traversal",
                "relation": "narrower",
                "shape": "single",
                "transferability": "yes",
                "distinction": "material",
                "atomicity": "basic",
            }
            return _make_transport_response(body_bytes, choice_map=choice_map)

        client.transport = transport
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)

        assert len(recorded_calls) == 2
        advice = receipt["jevAdvice"]
        assert advice["status"] == "advisory"
        assert advice["reason"] == "ok"
        assert advice["model"] == PINNED_MODEL
        assert advice["questionSchema"] == QUESTION_SCHEMA
        assert len(advice["calls"]) == 2
        assert advice["answers"]["target"]["choice"] == "graph-traversal"
        assert advice["disagreement"] is False

        # Proposal updated to MAP_CANDIDATE
        proposal = receipt["proposedDisposition"]
        assert proposal["value"] == "MAP_CANDIDATE"
        assert proposal["targetGenericId"] == "graph-traversal"
        assert proposal["reasonCode"] == "JEV_SEMANTIC_PROPOSAL"
        assert proposal["advisoryOnly"] is True

        assert validateAssessment(receipt, packet, registryPath=reg) == []

    def test_native_jev_target_none_produces_new_generic_candidate(self, tmp_path, monkeypatch):
        """When Jev answers target=NONE, proposal becomes NEW_GENERIC_CANDIDATE."""
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        def transport(url, headers, body_bytes, timeout):
            choice_map = {
                "target": "NONE",
                "relation": "orthogonal",
                "shape": "single",
                "transferability": "yes",
                "distinction": "material",
                "atomicity": "basic",
            }
            return _make_transport_response(body_bytes, choice_map=choice_map)

        client.transport = transport
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)

        assert receipt["jevAdvice"]["status"] == "advisory"
        assert receipt["proposedDisposition"]["value"] == "NEW_GENERIC_CANDIDATE"
        assert receipt["proposedDisposition"]["targetGenericId"] is None
        assert receipt["proposedDisposition"]["reasonCode"] == "JEV_SEMANTIC_PROPOSAL"

    def test_native_jev_disagreement_flagged(self, tmp_path, monkeypatch):
        """When target choice differs from strongest neighbor, disagreement is flagged."""
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        # Two options: strongest is graph-traversal, second is tree-search
        options = [
            {"genericId": "graph-traversal", "similarity": 0.90, "matchTier": "strong"},
            {"genericId": "tree-search", "similarity": 0.85, "matchTier": "strong"},
        ]
        packet = _make_test_packet(mapping_options=options)

        def transport(url, headers, body_bytes, timeout):
            choice_map = {
                "target": "tree-search",  # Differs from strongest (graph-traversal)
                "relation": "narrower",
                "shape": "single",
                "transferability": "yes",
                "distinction": "material",
                "atomicity": "basic",
            }
            return _make_transport_response(body_bytes, choice_map=choice_map)

        client.transport = transport
        receipt = buildAssessment(packet, registryPath=reg, client=client)

        assert receipt["jevAdvice"]["disagreement"] is True
        assert receipt["uncertainty"]["jevDisagreement"] is True
        assert receipt["proposedDisposition"]["value"] == "MAP_CANDIDATE"
        assert receipt["proposedDisposition"]["targetGenericId"] == "tree-search"

    def test_native_jev_low_confidence_fallback(self, tmp_path, monkeypatch):
        """Confidence below threshold triggers fallback with semantic_uncertainty."""
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        def transport(url, headers, body_bytes, timeout):
            # Low confidence 0.65 (< 0.75)
            return _make_transport_response(body_bytes, confidence=0.65)

        client.transport = transport
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)

        assert receipt["jevAdvice"]["status"] == "fallback"
        assert receipt["jevAdvice"]["reason"] == "semantic_uncertainty"
        assert receipt["jevAdvice"]["fallback"]["agent"] == "worker-luna"
        assert receipt["proposedDisposition"]["value"] == "DEFER"

    def test_native_jev_unsure_or_unknown_fallback(self, tmp_path, monkeypatch):
        """Choice 'UNSURE' triggers fallback with semantic_uncertainty."""
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        def transport(url, headers, body_bytes, timeout):
            choice_map = {"target": "UNSURE"}
            return _make_transport_response(body_bytes, choice_map=choice_map, confidence=0.90)

        client.transport = transport
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)

        assert receipt["jevAdvice"]["status"] == "fallback"
        assert receipt["jevAdvice"]["reason"] == "semantic_uncertainty"
        assert receipt["proposedDisposition"]["value"] == "DEFER"

    def test_native_jev_missing_api_key_fallback(self, tmp_path, monkeypatch):
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)

        assert receipt["jevAdvice"]["status"] == "fallback"
        assert receipt["jevAdvice"]["reason"] == "missing_api_key"
        assert receipt["proposedDisposition"]["value"] == "DEFER"

    def test_native_jev_budget_exceeded_fallback(self, tmp_path, monkeypatch):
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        # Set monthly limit smaller than reservation amount (0.003)
        client = JevClient(state_dir, live=True, maxCalls=2, monthlyLimitUsd=0.001)
        client.initializeBudget()

        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)

        assert receipt["jevAdvice"]["status"] == "fallback"
        assert receipt["jevAdvice"]["reason"] == "budget_exceeded"
        assert receipt["proposedDisposition"]["value"] == "DEFER"

    def test_native_jev_http_failure_fallback(self, tmp_path, monkeypatch):
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        # HTTP 500
        client.transport = lambda url, headers, body, timeout: (500, b"Server Error")
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)
        assert receipt["jevAdvice"]["status"] == "fallback"
        assert receipt["jevAdvice"]["reason"] == "http_500"

        # HTTP 429
        client.transport = lambda url, headers, body, timeout: (429, b"Too Many Requests")
        receipt429 = buildAssessment(packet, registryPath=reg, client=client)
        assert receipt429["jevAdvice"]["status"] == "fallback"
        assert receipt429["jevAdvice"]["reason"] == "http_429"

    def test_native_jev_timeout_fallback(self, tmp_path, monkeypatch):
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        def transport(url, headers, body, timeout):
            raise TimeoutError("Connection timed out")

        client.transport = transport
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)
        assert receipt["jevAdvice"]["status"] == "fallback"
        assert receipt["jevAdvice"]["reason"] == "timeout"

    def test_native_jev_malformed_client_response_fallback(self, tmp_path, monkeypatch):
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        # Transport returns invalid json
        client.transport = lambda url, headers, body, timeout: (200, b"{malformed json")
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)
        assert receipt["jevAdvice"]["status"] == "fallback"
        assert receipt["jevAdvice"]["reason"] == "invalid_response"

        # Transport returns wrong model
        client.transport = lambda url, headers, body, timeout: (
            200, json.dumps({"model": "wrong-model", "answers": {}, "usage": {}}).encode("utf-8")
        )
        receipt_wrong = buildAssessment(packet, registryPath=reg, client=client)
        assert receipt_wrong["jevAdvice"]["status"] == "fallback"
        assert receipt_wrong["jevAdvice"]["reason"] == "invalid_response"


class TestJevCachingAndInvalidation:
    """Cache hits prevent transport calls; model/rubric/schema changes invalidate cache."""

    def test_real_cache_repeat_avoids_transport(self, tmp_path, monkeypatch):
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=10)
        client.initializeBudget()

        transport_calls = []

        def transport(url, headers, body_bytes, timeout):
            transport_calls.append(len(body_bytes))
            choice_map = {
                "target": "graph-traversal",
                "relation": "narrower",
                "shape": "single",
                "transferability": "yes",
                "distinction": "material",
                "atomicity": "basic",
            }
            return _make_transport_response(body_bytes, choice_map=choice_map)

        client.transport = transport
        packet = _make_test_packet()

        # First run: 2 calls to transport (call 1 + call 2)
        receipt1 = buildAssessment(packet, registryPath=reg, client=client)
        assert len(transport_calls) == 2
        assert receipt1["jevAdvice"]["calls"][0]["cached"] is False
        assert receipt1["jevAdvice"]["calls"][1]["cached"] is False

        # Second run with identical state: both calls served from cache; 0 new transport calls
        receipt2 = buildAssessment(packet, registryPath=reg, client=client)
        assert len(transport_calls) == 2  # No new transport calls!
        assert receipt2["jevAdvice"]["calls"][0]["cached"] is True
        assert receipt2["jevAdvice"]["calls"][1]["cached"] is True

    def test_cache_invalidation_on_semantic_state_change(self, tmp_path, monkeypatch):
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=10)
        client.initializeBudget()

        transport_calls = []

        def transport(url, headers, body_bytes, timeout):
            transport_calls.append(len(body_bytes))
            choice_map = {
                "target": "graph-traversal",
                "relation": "narrower",
                "shape": "single",
                "transferability": "yes",
                "distinction": "material",
                "atomicity": "basic",
            }
            return _make_transport_response(body_bytes, choice_map=choice_map)

        client.transport = transport
        p1 = _make_test_packet(description="Original description")
        buildAssessment(p1, registryPath=reg, client=client)
        assert len(transport_calls) == 2

        # Candidate description changed -> state changed -> cache miss -> new transport calls
        p2 = _make_test_packet(description="Altered candidate description requiring new evaluation")
        buildAssessment(p2, registryPath=reg, client=client)
        assert len(transport_calls) == 4


class TestAssessCommandCLI:
    """CLI execution for `gaia dev assess`."""

    def test_assess_command_default_output(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet(candidate_id="alice/graph-tool")
        packet_path = tmp_path / "packet.json"
        with open(packet_path, "w", encoding="utf-8") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "output": None,
            "jev": "off",
            "state_dir": str(tmp_path / ".gaia" / "jev"),
            "registry": reg,
        })()

        rc = assessCommand(args)
        assert rc == 0

        expected_output = tmp_path / "generated-output" / "curation" / "alice-graph-tool.assessment.json"
        assert expected_output.is_file()

        with open(expected_output, "r", encoding="utf-8") as f:
            receipt = json.load(f)
        assert receipt["contractVersion"] == CONTRACT_VERSION

        # Verify packet was NOT mutated
        with open(packet_path, "r", encoding="utf-8") as f:
            unmodified_packet = json.load(f)
        assert "l4Resolution" not in unmodified_packet

    def test_assess_command_custom_output(self, tmp_path):
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet(candidate_id="alice/graph-tool")
        packet_path = tmp_path / "packet.json"
        with open(packet_path, "w", encoding="utf-8") as f:
            json.dump(packet, f)

        custom_output = str(tmp_path / "custom" / "receipt.json")
        args = type("Args", (), {
            "packet_path": str(packet_path),
            "output": custom_output,
            "jev": "off",
            "state_dir": str(tmp_path / ".gaia" / "jev"),
            "registry": reg,
        })()

        rc = assessCommand(args)
        assert rc == 0
        assert Path(custom_output).is_file()

    def test_assess_command_rejects_canonical_output_path(self, tmp_path):
        packet = _make_test_packet()
        packet_path = tmp_path / "packet.json"
        with open(packet_path, "w", encoding="utf-8") as f:
            json.dump(packet, f)

        canonical_dest = str(tmp_path / "registry" / "nodes" / "bad.json")
        args = type("Args", (), {
            "packet_path": str(packet_path),
            "output": canonical_dest,
            "jev": "off",
            "state_dir": str(tmp_path / ".gaia" / "jev"),
            "registry": str(tmp_path),
        })()

        rc = assessCommand(args)
        assert rc == 1

    def test_assess_command_rejects_oversized_packet(self, tmp_path):
        packet_path = tmp_path / "oversized.json"
        # Over 2 MB
        with open(packet_path, "w", encoding="utf-8") as f:
            f.write(" " * 2_000_001)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "output": None,
            "jev": "off",
            "state_dir": str(tmp_path / ".gaia" / "jev"),
            "registry": str(tmp_path),
        })()

        assert assessCommand(args) == 1

    def test_assess_command_rejects_invalid_candidate_id(self, tmp_path):
        packet = _make_test_packet(candidate_id="invalid/candidate/extra/slashes")
        packet_path = tmp_path / "bad_id.json"
        with open(packet_path, "w", encoding="utf-8") as f:
            json.dump(packet, f)

        args = type("Args", (), {
            "packet_path": str(packet_path),
            "output": None,
            "jev": "off",
            "state_dir": str(tmp_path / ".gaia" / "jev"),
            "registry": str(tmp_path),
        })()

        assert assessCommand(args) == 1


class TestJevPrinciplesWiring:
    """P1-A: Jev advisory answers are wired into the canonical principles surface."""

    def test_advisory_answers_populate_principles(self, tmp_path, monkeypatch):
        """When Jev returns advisory status, answer choices populate principles fields."""
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        def transport(url, headers, body_bytes, timeout):
            choice_map = {
                "target": "graph-traversal",
                "relation": "narrower",
                "shape": "suite",
                "transferability": "yes",
                "distinction": "material",
                "atomicity": "fusion",
            }
            return _make_transport_response(body_bytes, choice_map=choice_map)

        client.transport = transport
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)

        assert receipt["jevAdvice"]["status"] == "advisory"
        p = receipt["principles"]
        assert p["relation"]["relation"] == "narrower"
        assert p["artifact_packaging"]["shape"] == "suite"
        assert p["transferability"]["evaluation"] == "yes"
        assert p["material_distinction"]["evaluation"] == "material"
        assert p["atomicity"]["type"] == "fusion"

    def test_jev_off_principles_remain_unknown(self, tmp_path):
        """With Jev off (no client), all principle fields stay unknown."""
        reg = _make_test_registry(tmp_path)
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=None)

        assert receipt["jevAdvice"]["status"] == "skipped"
        p = receipt["principles"]
        assert p["relation"]["relation"] == "unknown"
        assert p["artifact_packaging"]["shape"] == "unknown"
        assert p["transferability"]["evaluation"] == "unknown"
        assert p["material_distinction"]["evaluation"] == "unknown"
        assert p["atomicity"]["type"] == "unknown"

    def test_jev_fallback_principles_remain_unknown(self, tmp_path, monkeypatch):
        """With Jev fallback (low confidence), principle fields stay unknown."""
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        def transport(url, headers, body_bytes, timeout):
            return _make_transport_response(body_bytes, confidence=0.50)

        client.transport = transport
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)

        assert receipt["jevAdvice"]["status"] == "fallback"
        p = receipt["principles"]
        assert p["relation"]["relation"] == "unknown"
        assert p["artifact_packaging"]["shape"] == "unknown"
        assert p["transferability"]["evaluation"] == "unknown"
        assert p["material_distinction"]["evaluation"] == "unknown"
        assert p["atomicity"]["type"] == "unknown"

    def test_advisory_receipt_validates_with_wired_principles(self, tmp_path, monkeypatch):
        """A receipt built with Jev advisory passes validation (principles match)."""
        reg = _make_test_registry(tmp_path)
        state_dir = tmp_path / "jev_state"
        monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-token-123")

        client = JevClient(state_dir, live=True, maxCalls=2)
        client.initializeBudget()

        def transport(url, headers, body_bytes, timeout):
            choice_map = {
                "target": "graph-traversal",
                "relation": "same",
                "shape": "single",
                "transferability": "yes",
                "distinction": "material",
                "atomicity": "basic",
            }
            return _make_transport_response(body_bytes, choice_map=choice_map)

        client.transport = transport
        packet = _make_test_packet()
        receipt = buildAssessment(packet, registryPath=reg, client=client)
        errors = validateAssessment(receipt, packet, registryPath=reg)
        assert errors == []
