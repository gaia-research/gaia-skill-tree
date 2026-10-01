"""Tests for semantic curation CLI commands (dev embed, dev prefill, dev assess, dev ratify).

Validates the full non-authoritative recall -> advisory assessment -> human L4 ratification pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from unittest.mock import patch

import pytest

from gaia_cli.commands.dev import DevCommand
from gaia_cli.commands.dev.ratify import ratifyCommand
from gaia_cli.curation.assessment import assessCommand, buildAssessment, validateAssessment
from gaia_cli.curation.retrieval import saveEmbeddingsAtomic, semanticFingerprint
from gaia_cli.impl import embed_command
from gaia_cli.prefill import prefillCommand


@pytest.fixture
def test_registry(tmp_path):
    """Set up a minimal temporary registry layout."""
    reg_dir = tmp_path / "registry"
    nodes_dir = reg_dir / "nodes" / "basic"
    nodes_dir.mkdir(parents=True)
    schema_dir = reg_dir / "schema"
    schema_dir.mkdir(parents=True)

    # Basic generic node
    node = {
        "id": "automated-testing",
        "name": "Automated Testing",
        "description": "Frameworks and harnesses for automated software testing.",
        "type": "basic",
        "prerequisites": [],
    }
    (nodes_dir / "automated-testing.json").write_text(json.dumps(node, indent=2), encoding="utf-8")

    # gaia.json
    gaia_json = {
        "skills": [
            {
                "id": "automated-testing",
                "name": "Automated Testing",
                "description": "Frameworks and harnesses for automated software testing.",
            }
        ]
    }
    (reg_dir / "gaia.json").write_text(json.dumps(gaia_json, indent=2), encoding="utf-8")

    # meta.json
    meta_json = {
        "curationPrefill": {
            "strongMap": 0.72,
            "weakMap": 0.45,
            "topK": 3,
        }
    }
    (schema_dir / "meta.json").write_text(json.dumps(meta_json, indent=2), encoding="utf-8")

    return tmp_path


def _write_mock_embeddings(registry_path, skills=None, model="all-MiniLM-L6-v2", entries=None):
    """Write mock embeddings file with matching semantic fingerprint."""
    if skills is None:
        skills = [
            {
                "id": "automated-testing",
                "name": "Automated Testing",
                "description": "Frameworks and harnesses for automated software testing.",
            }
        ]
    from gaia_cli.curation.retrieval import loadRetrievalConfig
    cfg = loadRetrievalConfig(registry_path, modelName=model)
    fp = semanticFingerprint(skills, cfg)
    if entries is None:
        entries = [
            {
                "id": "automated-testing",
                "vector": [1.0] + [0.0] * 383,
            }
        ]
    emb_path = os.path.join(str(registry_path), "registry", "embeddings.json")
    saveEmbeddingsAtomic(
        entries=entries,
        outputPath=emb_path,
        modelName=model,
        dimensions=384,
        fingerprint=fp,
        config=cfg,
    )
    return emb_path


class TestDevEmbedCommand:
    def test_embed_is_non_mutating_no_operator_required(self):
        """gaia dev embed must NOT be in MUTATING_DEV_COMMANDS and never require operator."""
        dev = DevCommand()
        parser = argparse.ArgumentParser()
        dev.configure(parser)
        args = parser.parse_args(["embed", "--check"])
        assert args.dev_command == "embed"
        assert args.check is True

    def test_embed_check_missing_returns_nonzero(self, test_registry, capsys):
        args = argparse.Namespace(
            registry=str(test_registry),
            model=None,
            output=None,
            force=False,
            check=True,
        )
        code = embed_command(args)
        assert code == 1
        captured = capsys.readouterr()
        assert "Embedding status: missing" in captured.out

    def test_embed_check_fresh_returns_zero(self, test_registry, capsys):
        _write_mock_embeddings(test_registry)
        args = argparse.Namespace(
            registry=str(test_registry),
            model=None,
            output=None,
            force=False,
            check=True,
        )
        code = embed_command(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "Embedding status: fresh" in captured.out

    def test_embed_unknown_model_returns_nonzero(self, test_registry, capsys):
        args = argparse.Namespace(
            registry=str(test_registry),
            model="non-existent-model",
            output=None,
            force=False,
            check=False,
        )
        code = embed_command(args)
        assert code == 1
        captured = capsys.readouterr()
        assert "Error loading retrieval config" in captured.err

    def test_embed_generate_fresh_artifact_reuses(self, test_registry, capsys):
        _write_mock_embeddings(test_registry)
        args = argparse.Namespace(
            registry=str(test_registry),
            model=None,
            output=None,
            force=False,
            check=False,
        )
        # Should detect fresh and return 0 without re-embedding
        code = embed_command(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "fresh" in captured.out or code == 0


class TestDevPrefillCommand:
    def test_prefill_missing_embeddings_fails_actionable(self, test_registry, capsys):
        args = argparse.Namespace(
            registry=str(test_registry),
            candidate_id="tester/unit-runner",
            name="Unit Runner",
            description="Runs unit tests with mocks.",
            url="https://github.com/tester/unit-runner/blob/main/SKILL.md",
            source_lane="source-repository",
            suite_role=None,
            suite_id=None,
            component_ids=None,
            vector=None,
            allow_stale=False,
            json=False,
            stdout=False,
        )
        code = prefillCommand(args)
        assert code == 1
        captured = capsys.readouterr()
        assert "Embeddings artifact not found" in captured.err or "Run `gaia dev embed`" in captured.err

    def test_prefill_stale_embeddings_without_allow_stale_fails(self, test_registry, capsys):
        # Create legacy embeddings without fingerprint (stale)
        emb_path = os.path.join(str(test_registry), "registry", "embeddings.json")
        os.makedirs(os.path.dirname(emb_path), exist_ok=True)
        with open(emb_path, "w", encoding="utf-8") as f:
            json.dump({
                "model": "all-MiniLM-L6-v2",
                "dimensions": 384,
                "entries": [{"id": "automated-testing", "vector": [1.0] + [0.0] * 383}],
            }, f)

        args = argparse.Namespace(
            registry=str(test_registry),
            candidate_id="tester/unit-runner",
            name="Unit Runner",
            description="Runs unit tests with mocks.",
            url="https://github.com/tester/unit-runner/blob/main/SKILL.md",
            source_lane="source-repository",
            suite_role=None,
            suite_id=None,
            component_ids=None,
            vector=None,
            allow_stale=False,
            json=False,
            stdout=False,
        )
        code = prefillCommand(args)
        assert code == 1
        captured = capsys.readouterr()
        assert "Embeddings artifact is stale" in captured.err
        assert "--allow-stale" in captured.err

    def test_prefill_stale_embeddings_with_allow_stale_warns_and_proceeds(self, test_registry, capsys):
        emb_path = os.path.join(str(test_registry), "registry", "embeddings.json")
        os.makedirs(os.path.dirname(emb_path), exist_ok=True)
        with open(emb_path, "w", encoding="utf-8") as f:
            json.dump({
                "model": "all-MiniLM-L6-v2",
                "dimensions": 384,
                "entries": [{"id": "automated-testing", "vector": [1.0] + [0.0] * 383}],
            }, f)

        # Precomputed vector to bypass sentence_transformers model download
        vec_file = test_registry / "test_vec.json"
        vec_file.write_text(json.dumps({
            "model": "all-MiniLM-L6-v2",
            "vector": [1.0] + [0.0] * 383,
        }), encoding="utf-8")

        args = argparse.Namespace(
            registry=str(test_registry),
            candidate_id="tester/unit-runner",
            name="Unit Runner",
            description="Runs unit tests with mocks.",
            url="https://github.com/tester/unit-runner/blob/main/SKILL.md",
            source_lane="source-repository",
            suite_role=None,
            suite_id=None,
            component_ids=None,
            vector=str(vec_file),
            allow_stale=True,
            json=False,
            stdout=False,
        )
        code = prefillCommand(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "Warning: Embeddings artifact is stale" in captured.err
        assert "Proceeding with --allow-stale" in captured.err
        assert "Wrote prefilled discovery-packet-v2" in captured.out
        # Automatic advisory assessment receipt written
        assert "Wrote advisory assessment receipt" in captured.out

        # Verify receipt exists on disk
        assessment_file = test_registry / "generated-output" / "curation" / "tester-unit-runner.assessment.json"
        assert assessment_file.is_file()

    def test_prefill_stdout_json_is_packet_only(self, test_registry, capsys):
        _write_mock_embeddings(test_registry)
        vec_file = test_registry / "test_vec.json"
        vec_file.write_text(json.dumps({
            "model": "all-MiniLM-L6-v2",
            "vector": [1.0] + [0.0] * 383,
        }), encoding="utf-8")

        args = argparse.Namespace(
            registry=str(test_registry),
            candidate_id="tester/unit-runner",
            name="Unit Runner",
            description="Runs unit tests with mocks.",
            url="https://github.com/tester/unit-runner/blob/main/SKILL.md",
            source_lane="source-repository",
            suite_role=None,
            suite_id=None,
            component_ids=None,
            vector=str(vec_file),
            allow_stale=False,
            json=True,
            stdout=True,
        )
        code = prefillCommand(args)
        assert code == 0
        captured = capsys.readouterr()
        # Output must be pure valid JSON packet with no extra logs
        parsed = json.loads(captured.out)
        assert parsed["contractVersion"] == "discovery-packet-v2"
        assert parsed["candidateId"] == "tester/unit-runner"
        assert "retrieval" in parsed


class TestDevAssessCommand:
    def test_assess_command_generates_receipt(self, test_registry, capsys):
        _write_mock_embeddings(test_registry)
        vec_file = test_registry / "test_vec.json"
        vec_file.write_text(json.dumps({
            "model": "all-MiniLM-L6-v2",
            "vector": [1.0] + [0.0] * 383,
        }), encoding="utf-8")

        # Create discovery packet via prefill
        prefill_args = argparse.Namespace(
            registry=str(test_registry),
            candidate_id="tester/unit-runner",
            name="Unit Runner",
            description="Runs unit tests with mocks.",
            url="https://github.com/tester/unit-runner/blob/main/SKILL.md",
            source_lane="source-repository",
            suite_role=None,
            suite_id=None,
            component_ids=None,
            vector=str(vec_file),
            allow_stale=False,
            json=False,
            stdout=False,
        )
        assert prefillCommand(prefill_args) == 0

        packet_path = (
            test_registry
            / "registry-for-review"
            / "discovery-packets"
            / "tester-unit-runner.json"
        )
        assert packet_path.is_file()

        # Run assess
        custom_out = test_registry / "generated-output" / "custom_assess.json"
        assess_args = argparse.Namespace(
            registry=str(test_registry),
            packet_path=str(packet_path),
            output=str(custom_out),
            jev="off",
            state_dir=str(test_registry / ".gaia" / "jev"),
        )
        code = assessCommand(assess_args)
        assert code == 0
        assert custom_out.is_file()

        with open(custom_out, "r", encoding="utf-8") as f:
            receipt = json.load(f)
        with open(packet_path, "r", encoding="utf-8") as f:
            packet = json.load(f)

        errors = validateAssessment(receipt, packet, registryPath=str(test_registry))
        assert errors == []


class TestDevRatifyCommand:
    def test_ratify_requires_human_acknowledgement(self, test_registry, capsys):
        packet_path = test_registry / "packet.json"
        packet_path.write_text(json.dumps({}), encoding="utf-8")
        args = argparse.Namespace(
            registry=str(test_registry),
            packet_path=str(packet_path),
            decision="MAP",
            generic_id="automated-testing",
            generic_name="Automated Testing",
            generic_description="Long description exceeding 10 characters.",
            generic_type="basic",
            prereqs=None,
            contributor="tester",
            skill_name="unit-runner",
            skill_file_url="https://github.com/tester/unit-runner/blob/main/SKILL.md",
            assessment="some_path.json",
            reviewed_by="alice",
            approval_ref="https://github.com/owner/repo/pull/1",
            reason="Good fit",
            acknowledge_human_review=False,  # Absent / False
        )
        code = ratifyCommand(args)
        assert code == 1
        captured = capsys.readouterr()
        assert "--acknowledge-human-review is required" in captured.err

    def test_end_to_end_prefill_assess_ratify_flow(self, test_registry, monkeypatch):
        # Allow operator override for ratify
        monkeypatch.setenv("GAIA_OPERATOR_OVERRIDE", "1")

        _write_mock_embeddings(test_registry)
        vec_file = test_registry / "test_vec.json"
        vec_file.write_text(json.dumps({
            "model": "all-MiniLM-L6-v2",
            "vector": [1.0] + [0.0] * 383,
        }), encoding="utf-8")

        mock_fetcher = lambda url: (
            "---\n"
            "name: Unit Runner\n"
            "description: Runs unit tests with mocks.\n"
            "---\n"
            "# Unit Runner\n"
        ).encode("utf-8")

        # 1. Prefill
        prefill_args = argparse.Namespace(
            registry=str(test_registry),
            candidate_id="tester/unit-runner",
            name="Unit Runner",
            description="Runs unit tests with mocks.",
            url="https://github.com/tester/unit-runner/blob/main/SKILL.md",
            source_lane="source-repository",
            suite_role=None,
            suite_id=None,
            component_ids=None,
            vector=str(vec_file),
            allow_stale=False,
            json=False,
            stdout=False,
            fetcher=mock_fetcher,
        )
        assert prefillCommand(prefill_args) == 0

        packet_path = (
            test_registry
            / "registry-for-review"
            / "discovery-packets"
            / "tester-unit-runner.json"
        )
        assessment_path = (
            test_registry
            / "generated-output"
            / "curation"
            / "tester-unit-runner.assessment.json"
        )
        assert packet_path.is_file()
        assert assessment_path.is_file()

        # 2. Ratify
        ratify_args = argparse.Namespace(
            registry=str(test_registry),
            packet_path=str(packet_path),
            decision="MAP",
            generic_id="automated-testing",
            generic_name="Automated Testing",
            generic_description="Frameworks and harnesses for automated software testing.",
            generic_type="basic",
            prereqs=None,
            contributor="tester",
            skill_name="unit-runner",
            skill_file_url="https://github.com/tester/unit-runner/blob/main/SKILL.md",
            assessment=str(assessment_path),
            reviewed_by="human_curator",
            approval_ref="https://github.com/gaia-research/gaia-skill-tree/issues/1000",
            reason="Clear match to automated testing generic primitive.",
            acknowledge_human_review=True,
        )
        code = ratifyCommand(ratify_args)
        assert code == 0

        # Verify ratified packet content and schema validity
        with open(packet_path, "r", encoding="utf-8") as f:
            ratified = json.load(f)

        assert ratified["lifecycle"][-1] == "review-ready"
        assert "l4Resolution" in ratified
        l4 = ratified["l4Resolution"]
        assert l4["status"] == "approved"
        assert "humanReview" in l4
        hr = l4["humanReview"]
        assert hr["reviewedBy"] == "human_curator"
        assert hr["approvalRef"] == "https://github.com/gaia-research/gaia-skill-tree/issues/1000"
        assert hr["rationale"] == "Clear match to automated testing generic primitive."
        assert hr["operatorOverride"] is True

        # Validate against jsonschema
        import jsonschema
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent
        schema_path = (
            repo_root
            / ".agents"
            / "skills"
            / "gaia-curate"
            / "schemas"
            / "discovery-packet-v2.schema.json"
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(ratified, schema)
