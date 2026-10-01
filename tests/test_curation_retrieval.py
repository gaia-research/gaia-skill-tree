"""Tests for bounded retrieval config, semantic fingerprinting, and cache validation.

Mocked encoder throughout; no network access or live HuggingFace downloads.
"""

from __future__ import annotations

import copy
import json
import math
import os
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def isolatedEncoderModule(monkeypatch):
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = MagicMock()
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    clearModelCache()
    yield
    clearModelCache()

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from gaia_cli.curation.retrieval import (
    ENCODER_CONTRACT,
    clearModelCache,
    clear_model_cache,
    embeddingStatus,
    embedding_status,
    getModelCache,
    getModelCacheDir,
    getSentenceTransformer,
    loadRetrievalConfig,
    load_retrieval_config,
    saveEmbeddingsAtomic,
    semanticFingerprint,
    semantic_fingerprint,
    validateEmbeddingsData,
    validateVector,
    verify_model_pooling,
)
from gaia_cli.embeddings import embed_skills, generate_embeddings, load_skills
from gaia_cli.semantic_search import (
    cosine_similarity,
    embed_query,
    load_embeddings,
    search,
    search_precomputed,
)


class MockSentenceTransformer:
    """Mock SentenceTransformer that generates deterministic vectors without network."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", **kwargs: Any):
        self.model_name = model_name
        self.kwargs = kwargs
        self.encode_call_count = 0
        self.training = False
        self.eval_call_count = 0
        if "bge" in model_name.lower():
            self.pooling = "cls"
        elif "qwen" in model_name.lower():
            self.pooling = "last_token"
        else:
            self.pooling = "mean"

    def eval(self) -> MockSentenceTransformer:
        self.training = False
        self.eval_call_count += 1
        return self

    def train(self, mode: bool = True) -> MockSentenceTransformer:
        self.training = mode
        return self

    def encode(
        self,
        texts: list[str],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
    ) -> Any:
        self.encode_call_count += 1
        dim = 1024 if "qwen" in self.model_name.lower() else 384
        import numpy as np

        vectors = []
        for t in texts:
            val = (len(t) % 10) / 10.0 + 0.1
            vec = np.full(dim, val, dtype=float)
            if normalize_embeddings:
                norm = float(np.linalg.norm(vec))
                if norm > 0:
                    vec = vec / norm
            vectors.append(vec)
        return np.array(vectors)


class TestLoadRetrievalConfig:
    """Tests for loadRetrievalConfig / load_retrieval_config."""

    def test_default_config_is_all_minilm(self):
        cfg = loadRetrievalConfig()
        assert cfg["modelId"] == "all-MiniLM-L6-v2"
        assert cfg["revision"] == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
        assert cfg["backend"] == "torch"
        assert cfg["dimensions"] == 384
        assert cfg["normalize"] is True
        assert cfg["pooling"] == "mean"
        assert cfg["textTemplate"] == "{name}: {description}"
        assert cfg["queryPrefix"] == ""
        assert cfg["candidate"] is False

    def test_candidate_config_bge_small(self):
        cfg = loadRetrievalConfig(modelName="BAAI/bge-small-en-v1.5")
        assert cfg["modelId"] == "BAAI/bge-small-en-v1.5"
        assert cfg["revision"] == "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
        assert cfg["dimensions"] == 384
        assert cfg["normalize"] is True
        assert cfg["pooling"] == "cls"
        assert "Represent this sentence" in cfg["queryPrefix"]
        assert cfg["candidate"] is True

    def test_candidate_short_alias_resolution(self):
        cfg = loadRetrievalConfig(modelName="bge-small-en-v1.5")
        assert cfg["modelId"] == "BAAI/bge-small-en-v1.5"

    def test_candidate_config_qwen3(self):
        cfg = loadRetrievalConfig(modelName="Qwen3")
        assert cfg["modelId"] == "Qwen/Qwen3-Embedding-0.6B"
        assert cfg["revision"] == "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
        assert cfg["dimensions"] == 1024
        assert cfg["normalize"] is True
        assert cfg["pooling"] == "last_token"
        assert cfg["candidate"] is True

    def test_candidate_config_qwen_canonical(self):
        cfg = loadRetrievalConfig(modelName="Qwen/Qwen3-Embedding-0.6B")
        assert cfg["modelId"] == "Qwen/Qwen3-Embedding-0.6B"
        assert cfg["revision"] == "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"

    def test_unknown_model_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown retrieval model 'unknown-model-xyz'"):
            loadRetrievalConfig(modelName="unknown-model-xyz")

    def test_api_aliases_parity(self):
        cfg1 = loadRetrievalConfig()
        cfg2 = load_retrieval_config()
        assert cfg1["modelId"] == cfg2["modelId"]
        assert cfg1["textTemplate"] == cfg2["text_template"]

    def test_corrupt_canonical_json_raises_value_error(self, tmp_path):
        data_dir = tmp_path / "data" / "curation"
        data_dir.mkdir(parents=True)
        (data_dir / "retrieval.json").write_text("corrupted json {{{{")

        with pytest.raises(ValueError, match="Corrupt canonical retrieval configuration"):
            loadRetrievalConfig(registryPath=tmp_path)


class TestSemanticFingerprint:
    """Tests for semanticFingerprint / semantic_fingerprint."""

    @pytest.fixture
    def sample_skills(self):
        return [
            {"id": "skill-b", "name": "Skill B", "description": "Second skill."},
            {"id": "skill-a", "name": "Skill A", "description": "First skill."},
        ]

    def test_deterministic_sha256(self, sample_skills):
        fp1 = semanticFingerprint(sample_skills)
        fp2 = semanticFingerprint(sample_skills)
        assert len(fp1) == 64
        assert fp1 == fp2

    def test_sorting_invariance(self):
        s1 = [
            {"id": "skill-a", "name": "Skill A", "description": "First skill."},
            {"id": "skill-b", "name": "Skill B", "description": "Second skill."},
        ]
        s2 = [
            {"id": "skill-b", "name": "Skill B", "description": "Second skill."},
            {"id": "skill-a", "name": "Skill A", "description": "First skill."},
        ]
        assert semanticFingerprint(s1) == semanticFingerprint(s2)

    def test_non_semantic_metadata_invariance(self):
        """Altering stars, level, TM, date, or evidence does NOT change the fingerprint."""
        s1 = [
            {
                "id": "skill-a",
                "name": "Skill A",
                "description": "Desc.",
                "stars": 3,
                "level": 3,
                "tm": 150.0,
                "date": "2026-01-01",
                "evidence": [{"grade": "A"}],
            }
        ]
        s2 = [
            {
                "id": "skill-a",
                "name": "Skill A",
                "description": "Desc.",
                "stars": 5,
                "level": 6,
                "tm": 999.0,
                "date": "2026-09-09",
                "evidence": [{"grade": "S"}],
            }
        ]
        assert semanticFingerprint(s1) == semanticFingerprint(s2)

    def test_description_change_changes_fingerprint(self):
        s1 = [{"id": "skill-a", "name": "Skill A", "description": "Description 1"}]
        s2 = [{"id": "skill-a", "name": "Skill A", "description": "Description 2"}]
        assert semanticFingerprint(s1) != semanticFingerprint(s2)

    def test_name_change_changes_fingerprint(self):
        s1 = [{"id": "skill-a", "name": "Name 1", "description": "Desc"}]
        s2 = [{"id": "skill-a", "name": "Name 2", "description": "Desc"}]
        assert semanticFingerprint(s1) != semanticFingerprint(s2)

    def test_config_change_changes_fingerprint(self, sample_skills):
        fp_minilm = semanticFingerprint(sample_skills, config="all-MiniLM-L6-v2")
        fp_bge = semanticFingerprint(sample_skills, config="BAAI/bge-small-en-v1.5")
        assert fp_minilm != fp_bge

    def test_dimensions_change_changes_fingerprint(self, sample_skills):
        cfg1 = loadRetrievalConfig("all-MiniLM-L6-v2")
        cfg2 = copy.deepcopy(cfg1)
        cfg2["dimensions"] = 512
        assert semanticFingerprint(sample_skills, config=cfg1) != semanticFingerprint(sample_skills, config=cfg2)

    def test_revision_change_changes_fingerprint(self, sample_skills):
        cfg1 = loadRetrievalConfig("all-MiniLM-L6-v2")
        cfg2 = copy.deepcopy(cfg1)
        cfg2["revision"] = "different_sha_revision"
        assert semanticFingerprint(sample_skills, config=cfg1) != semanticFingerprint(sample_skills, config=cfg2)

    def test_query_prefix_change_changes_fingerprint(self, sample_skills):
        cfg1 = loadRetrievalConfig("all-MiniLM-L6-v2")
        cfg2 = copy.deepcopy(cfg1)
        cfg2["queryPrefix"] = "Query prefix: "
        assert semanticFingerprint(sample_skills, config=cfg1) != semanticFingerprint(sample_skills, config=cfg2)

    def test_pooling_aliases_normalization_same_fingerprint(self, sample_skills):
        """Equivalent pooling aliases produce identical semanticFingerprint."""
        fp1 = semanticFingerprint(sample_skills, {"modelId": "all-MiniLM-L6-v2", "pooling": "mean"})
        fp2 = semanticFingerprint(sample_skills, {"modelId": "all-MiniLM-L6-v2", "pooling": "mean_tokens"})
        assert fp1 == fp2

        fp_cls1 = semanticFingerprint(sample_skills, {"modelId": "BAAI/bge-small-en-v1.5", "pooling": "cls"})
        fp_cls2 = semanticFingerprint(sample_skills, {"modelId": "BAAI/bge-small-en-v1.5", "pooling": "cls_token"})
        assert fp_cls1 == fp_cls2

        fp_last1 = semanticFingerprint(sample_skills, {"modelId": "Qwen/Qwen3-Embedding-0.6B", "pooling": "last_token"})
        fp_last2 = semanticFingerprint(sample_skills, {"modelId": "Qwen/Qwen3-Embedding-0.6B", "pooling": "lasttoken"})
        assert fp_last1 == fp_last2

    def test_model_alias_normalization_same_fingerprint(self, sample_skills):
        """Model alias in config produces same fingerprint as canonical modelId."""
        fp1 = semanticFingerprint(sample_skills, {"modelId": "all-MiniLM-L6-v2"})
        fp2 = semanticFingerprint(sample_skills, {"modelId": "sentence-transformers/all-MiniLM-L6-v2"})
        assert fp1 == fp2

    def test_fingerprint_changes_when_encoder_contract_changes(self, sample_skills, monkeypatch):
        """Semantic fingerprint incorporates ENCODER_CONTRACT constant; changes bust cache."""
        assert ENCODER_CONTRACT == "sentence-transformers-eval-single-thread-v2"
        fp_baseline = semanticFingerprint(sample_skills)
        monkeypatch.setattr("gaia_cli.curation.retrieval.ENCODER_CONTRACT", "sentence-transformers-eval-v0-drift")
        fp_drifted = semanticFingerprint(sample_skills)
        assert fp_baseline != fp_drifted

    def test_evaluation_cache_hash_changes_when_encoder_contract_changes(self, monkeypatch):
        """Evaluation config hash incorporates ENCODER_CONTRACT to invalidate pre-eval caches."""
        from gaia_cli.curation.evaluation import _compute_config_hash

        cfg = {"modelId": "all-MiniLM-L6-v2", "backend": "torch", "dimensions": 384}
        h_baseline = _compute_config_hash(cfg)
        monkeypatch.setattr("gaia_cli.curation.retrieval.ENCODER_CONTRACT", "sentence-transformers-eval-v0-drift")
        h_drifted = _compute_config_hash(cfg)
        assert h_baseline != h_drifted


class TestEmbeddingStatus:
    """Tests for embeddingStatus / embedding_status."""

    def test_missing_artifact(self, tmp_path):
        res = embeddingStatus(registryPath=tmp_path, artifactPath=tmp_path / "nonexistent.json")
        assert res["status"] == "missing"
        assert "not found" in res["reason"]
        assert res["fingerprint"] is None

    def test_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json at all {{{")
        res = embeddingStatus(artifactPath=bad_file)
        assert res["status"] == "invalid"
        assert "Could not parse embeddings JSON" in res["reason"]

    def test_invalid_non_finite_vector(self, tmp_path):
        art_path = tmp_path / "embeddings.json"
        art_path.write_text('{"model": "all-MiniLM-L6-v2", "dimensions": 3, "entries": [{"id": "skill-a", "vector": [1.0, NaN, 0.0]}], "fingerprint": "abcd1234"}')
        res = embeddingStatus(artifactPath=art_path)
        assert res["status"] == "invalid"
        assert "non-finite" in res["reason"]

    def test_invalid_vector_dimension_mismatch(self, tmp_path):
        art_path = tmp_path / "embeddings.json"
        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "entries": [
                {"id": "skill-a", "vector": [1.0, 0.0]}
            ],
            "fingerprint": "abcd1234",
        }
        art_path.write_text(json.dumps(data))
        res = embeddingStatus(artifactPath=art_path)
        assert res["status"] == "invalid"
        assert "dimension mismatch" in res["reason"]

    def test_legacy_artifact_is_stale_unverified(self, tmp_path):
        """Legacy artifacts without fingerprint are reported stale and unverified."""
        art_path = tmp_path / "embeddings.json"
        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "generatedAt": "2026-04-29",
            "encoderContract": ENCODER_CONTRACT,
            "entries": [
                {"id": "skill-a", "vector": [1.0, 0.0, 0.0]}
            ],
        }
        art_path.write_text(json.dumps(data))
        res = embeddingStatus(registryPath=tmp_path, artifactPath=art_path)
        assert res["status"] == "stale"
        assert "Legacy artifact missing semantic fingerprint; unverified" in res["reason"]
        assert res["fingerprint"] is None

    def test_artifact_contract_mismatch_is_stale(self, tmp_path):
        """Artifacts with missing or mismatched encoderContract are reported stale."""
        art_path = tmp_path / "embeddings.json"
        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "generatedAt": "2026-04-29",
            "fingerprint": "fake-fp-1234",
            "entries": [
                {"id": "skill-a", "vector": [1.0, 0.0, 0.0]}
            ],
        }
        art_path.write_text(json.dumps(data))
        res = embeddingStatus(registryPath=tmp_path, artifactPath=art_path)
        assert res["status"] == "stale"
        assert "Encoder contract mismatch" in res["reason"]

    def test_fresh_status_when_fingerprint_matches(self, tmp_path):
        nodes_dir = tmp_path / "registry" / "nodes" / "basic"
        nodes_dir.mkdir(parents=True)
        (nodes_dir / "web-search.json").write_text(
            json.dumps({"id": "web-search", "name": "Web Search", "description": "Search the web."})
        )

        cfg = loadRetrievalConfig(tmp_path)
        skills = load_skills(tmp_path)
        fp = semanticFingerprint(skills, cfg)

        art_path = tmp_path / "registry" / "embeddings.json"
        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "generatedAt": "2026-10-01",
            "encoderContract": ENCODER_CONTRACT,
            "fingerprint": fp,
            "entries": [
                {"id": "web-search", "vector": [0.1, 0.2, 0.3]}
            ],
        }
        art_path.write_text(json.dumps(data))

        res = embeddingStatus(registryPath=tmp_path, artifactPath=art_path, config=cfg)
        assert res["status"] == "fresh"
        assert res["fingerprint"] == fp

    def test_stale_status_when_skill_edited(self, tmp_path):
        nodes_dir = tmp_path / "registry" / "nodes" / "basic"
        nodes_dir.mkdir(parents=True)
        node_file = nodes_dir / "web-search.json"
        node_file.write_text(
            json.dumps({"id": "web-search", "name": "Web Search", "description": "Original description."})
        )

        cfg = loadRetrievalConfig(tmp_path)
        skills = load_skills(tmp_path)
        old_fp = semanticFingerprint(skills, cfg)

        art_path = tmp_path / "registry" / "embeddings.json"
        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "encoderContract": ENCODER_CONTRACT,
            "fingerprint": old_fp,
            "entries": [{"id": "web-search", "vector": [0.1, 0.2, 0.3]}],
        }
        art_path.write_text(json.dumps(data))

        node_file.write_text(
            json.dumps({"id": "web-search", "name": "Web Search", "description": "FRESHLY EDITED description."})
        )

        res = embeddingStatus(registryPath=tmp_path, artifactPath=art_path, config=cfg)
        assert res["status"] == "stale"
        assert "fingerprint mismatch" in res["reason"].lower()

    def test_status_rejects_empty_entries_with_copied_fingerprint(self, tmp_path):
        nodes_dir = tmp_path / "registry" / "nodes" / "basic"
        nodes_dir.mkdir(parents=True)
        (nodes_dir / "calc.json").write_text(
            json.dumps({"id": "calc", "name": "Calc", "description": "Calc"})
        )
        cfg = loadRetrievalConfig(tmp_path)
        skills = load_skills(tmp_path)
        fp = semanticFingerprint(skills, cfg)

        art_path = tmp_path / "embeddings.json"
        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 384,
            "encoderContract": ENCODER_CONTRACT,
            "fingerprint": fp,
            "entries": [],
        }
        art_path.write_text(json.dumps(data))
        res = embeddingStatus(registryPath=tmp_path, artifactPath=art_path, config=cfg)
        assert res["status"] == "stale"
        assert "empty entries" in res["reason"].lower()

    def test_status_rejects_truncated_entry_set(self, tmp_path):
        nodes_dir = tmp_path / "registry" / "nodes" / "basic"
        nodes_dir.mkdir(parents=True)
        (nodes_dir / "s1.json").write_text(json.dumps({"id": "s1", "name": "S1", "description": "D1"}))
        (nodes_dir / "s2.json").write_text(json.dumps({"id": "s2", "name": "S2", "description": "D2"}))

        cfg = loadRetrievalConfig(tmp_path)
        skills = load_skills(tmp_path)
        fp = semanticFingerprint(skills, cfg)

        art_path = tmp_path / "embeddings.json"
        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "encoderContract": ENCODER_CONTRACT,
            "fingerprint": fp,
            "entries": [{"id": "s1", "vector": [1.0, 0.0, 0.0]}],
        }
        art_path.write_text(json.dumps(data))
        res = embeddingStatus(registryPath=tmp_path, artifactPath=art_path, config=cfg)
        assert res["status"] == "stale"
        assert "truncated" in res["reason"].lower()

    def test_status_rejects_duplicate_entry_ids(self, tmp_path):
        art_path = tmp_path / "embeddings.json"
        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "entries": [
                {"id": "skill-a", "vector": [1.0, 0.0, 0.0]},
                {"id": "skill-a", "vector": [0.0, 1.0, 0.0]},
            ],
            "fingerprint": "fp123",
        }
        art_path.write_text(json.dumps(data))
        res = embeddingStatus(artifactPath=art_path)
        assert res["status"] == "invalid"
        assert "duplicate" in res["reason"].lower()

    def test_status_rejects_config_fingerprint_disagreement(self, tmp_path):
        nodes_dir = tmp_path / "registry" / "nodes" / "basic"
        nodes_dir.mkdir(parents=True)
        (nodes_dir / "s1.json").write_text(json.dumps({"id": "s1", "name": "S1", "description": "D1"}))

        art_path = tmp_path / "embeddings.json"
        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "encoderContract": ENCODER_CONTRACT,
            "fingerprint": "different-fake-fp",
            "config": {
                "backend": "torch",
                "dimensions": 3,
                "modelId": "all-MiniLM-L6-v2",
                "normalize": True,
                "pooling": "mean",
                "queryPrefix": "",
                "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
                "textTemplate": "{name}: {description}",
            },
            "entries": [{"id": "s1", "vector": [1.0, 0.0, 0.0]}],
        }
        art_path.write_text(json.dumps(data))
        res = embeddingStatus(registryPath=tmp_path, artifactPath=art_path)
        assert res["status"] == "invalid"
        assert "disagreement" in res["reason"].lower()


class TestValidationAndSearchSafety:
    """Tests for vector validation and pure-Python zip truncation prevention."""

    def test_cosine_similarity_dimension_mismatch(self):
        with pytest.raises(ValueError, match="Vector dimension mismatch"):
            cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])

    def test_cosine_similarity_non_finite_nan(self):
        with pytest.raises(ValueError, match="non-finite value"):
            cosine_similarity([1.0, float("nan")], [1.0, 0.0])

    def test_cosine_similarity_non_finite_inf(self):
        with pytest.raises(ValueError, match="non-finite value"):
            cosine_similarity([1.0, float("inf")], [1.0, 0.0])

    def test_cosine_similarity_rejects_bool(self):
        with pytest.raises(ValueError, match="boolean value"):
            cosine_similarity([True, 1.0], [0.5, 0.5])

    def test_cosine_similarity_rejects_zero_dimension(self):
        with pytest.raises(ValueError, match="zero dimensions"):
            cosine_similarity([], [])

    def test_validate_vector_rejects_bool(self):
        with pytest.raises(ValueError, match="boolean value"):
            validateVector([True, 0.5])

    def test_validate_vector_rejects_zero_dimension(self):
        with pytest.raises(ValueError, match="zero dimensions"):
            validateVector([])

    def test_search_precomputed_query_dimension_mismatch(self):
        embeddings = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "entries": [{"id": "s1", "vector": [1.0, 0.0, 0.0]}],
        }
        with pytest.raises(ValueError, match="dimension .* does not match"):
            search_precomputed([1.0, 0.0], embeddings)

    def test_search_precomputed_entry_dimension_mismatch_prevents_zip_truncation(self):
        embeddings = {
            "entries": [
                {"id": "short-vec", "vector": [1.0, 0.0]},
            ]
        }
        query_vector = [1.0, 0.0, 0.0]
        with pytest.raises(ValueError, match="dimension .* does not match"):
            search_precomputed(query_vector, embeddings)

    def test_search_precomputed_entry_non_finite(self):
        embeddings = {
            "entries": [
                {"id": "bad-vec", "vector": [1.0, float("nan"), 0.0]},
            ]
        }
        with pytest.raises(ValueError, match="non-finite value"):
            search_precomputed([1.0, 0.0, 0.0], embeddings)

    def test_search_precomputed_rejects_bool(self):
        embeddings = {
            "entries": [
                {"id": "bool-vec", "vector": [1.0, True, 0.0]},
            ]
        }
        with pytest.raises(ValueError, match="boolean value"):
            search_precomputed([1.0, 0.0, 0.0], embeddings)

    def test_search_model_mismatch_raises_value_error(self, tmp_path):
        art_path = tmp_path / "embeddings.json"
        art_path.write_text(json.dumps({
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "entries": [{"id": "s1", "vector": [1.0, 0.0, 0.0]}],
        }))

        with pytest.raises(ValueError, match="Model mismatch"):
            search("test query", str(art_path), config={"modelId": "BAAI/bge-small-en-v1.5"})

    def test_search_rejects_differing_semantic_config(self, tmp_path):
        art_path = tmp_path / "embeddings.json"
        art_path.write_text(json.dumps({
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "config": {
                "backend": "torch",
                "dimensions": 3,
                "modelId": "all-MiniLM-L6-v2",
                "normalize": True,
                "pooling": "mean",
                "queryPrefix": "",
                "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
            },
            "entries": [{"id": "s1", "vector": [1.0, 0.0, 0.0]}],
        }))

        with pytest.raises(ValueError, match="revision"):
            search("test", str(art_path), config={"revision": "different_sha"})

        with pytest.raises(ValueError, match="normalize"):
            search("test", str(art_path), config={"normalize": False})

        with pytest.raises(ValueError, match="pooling"):
            search("test", str(art_path), config={"pooling": "cls"})

        with pytest.raises(ValueError, match="queryPrefix"):
            search("test", str(art_path), config={"queryPrefix": "differing prefix"})

    @patch("sentence_transformers.SentenceTransformer", side_effect=MockSentenceTransformer)
    def test_search_uses_stored_artifact_config(self, mock_cls, tmp_path):
        art_path = tmp_path / "embeddings.json"
        art_path.write_text(json.dumps({
            "model": "BAAI/bge-small-en-v1.5",
            "dimensions": 384,
            "config": {
                "backend": "torch",
                "dimensions": 384,
                "modelId": "BAAI/bge-small-en-v1.5",
                "normalize": True,
                "pooling": "cls",
                "queryPrefix": "Represent this sentence for searching relevant passages: ",
                "revision": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
            },
            "entries": [{"id": "s1", "vector": [0.1] * 384}],
        }))

        results = search("test query", str(art_path))
        assert len(results) == 1
        assert results[0]["id"] == "s1"

    def test_missing_embeddings_diagnostic_mentions_gaia_dev_embed(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="gaia dev embed"):
            load_embeddings(str(tmp_path / "nonexistent.json"))

    def test_search_explicit_config_alias_canonicalization_no_mismatch(self, tmp_path):
        """Passing alias like sentence-transformers/all-MiniLM-L6-v2 does not cause false mismatch."""
        skills = [{"id": "automated-testing", "name": "Automated Testing", "description": "Testing desc"}]
        cfg = loadRetrievalConfig(modelName="all-MiniLM-L6-v2")
        fp = semanticFingerprint(skills, cfg)
        entries = [{"id": "automated-testing", "vector": [1.0] + [0.0] * 383}]
        emb_path = tmp_path / "embeddings.json"
        saveEmbeddingsAtomic(
            entries=entries,
            outputPath=str(emb_path),
            modelName="all-MiniLM-L6-v2",
            dimensions=384,
            fingerprint=fp,
            config=cfg,
        )

        with patch("gaia_cli.semantic_search.embed_query", return_value=[1.0] + [0.0] * 383):
            results = search(
                "query",
                str(emb_path),
                config={"modelId": "sentence-transformers/all-MiniLM-L6-v2"},
            )
            assert len(results) == 1
            assert results[0]["id"] == "automated-testing"


class TestModelCacheAndExecution:
    """Tests for model caching and generation orchestration (mocked encoder)."""

    def setup_method(self):
        clearModelCache()

    def teardown_method(self):
        clearModelCache()

    @patch("sentence_transformers.SentenceTransformer", side_effect=MockSentenceTransformer)
    def test_model_cache_reuses_instances(self, mock_cls):
        m1 = getSentenceTransformer("all-MiniLM-L6-v2")
        m2 = getSentenceTransformer("all-MiniLM-L6-v2")
        assert m1 is m2
        assert mock_cls.call_count == 1

    def test_mocked_train_mode_model_eval_called_fresh_and_cache_hit(self):
        """getSentenceTransformer calls model.eval() on fresh instantiation AND on cache hit."""
        class MockTrainModeModel:
            def __init__(self, model_name: str = "all-MiniLM-L6-v2", **kwargs: Any):
                self.model_name = model_name
                self.kwargs = kwargs
                self.training = True
                self.eval_call_count = 0
                self.pooling = "mean"

            def eval(self):
                self.training = False
                self.eval_call_count += 1
                return self

            def train(self, mode: bool = True):
                self.training = mode
                return self

        clearModelCache()
        with patch("sentence_transformers.SentenceTransformer", side_effect=MockTrainModeModel) as mock_cls:
            # 1. Fresh instantiation: model starts in train mode; getSentenceTransformer must call eval()
            m1 = getSentenceTransformer("all-MiniLM-L6-v2")
            assert mock_cls.call_count == 1
            assert m1.training is False
            assert m1.eval_call_count == 1

            # 2. Simulate model being placed back in train mode (e.g. external mutation or native ST behavior)
            m1.train(True)
            assert m1.training is True

            # 3. Cache hit: getSentenceTransformer must call eval() again before returning
            m2 = getSentenceTransformer("all-MiniLM-L6-v2")
            assert m2 is m1
            assert mock_cls.call_count == 1  # Reused from cache
            assert m2.training is False
            assert m2.eval_call_count == 2

    @patch("sentence_transformers.SentenceTransformer", side_effect=MockSentenceTransformer)
    def test_clear_model_cache(self, mock_cls):
        m1 = getSentenceTransformer("all-MiniLM-L6-v2")
        clearModelCache()
        m2 = getSentenceTransformer("all-MiniLM-L6-v2")
        assert m1 is not m2
        assert mock_cls.call_count == 2

    @patch("sentence_transformers.SentenceTransformer", side_effect=MockSentenceTransformer)
    def test_loader_passes_actual_kwargs(self, mock_cls, monkeypatch):
        monkeypatch.setenv("GAIA_MODEL_CACHE", "/custom/model/cache")
        model = getSentenceTransformer(
            modelName="BAAI/bge-small-en-v1.5",
            revision="custom-rev-123",
            backend="onnx",
        )
        assert model.kwargs["backend"] == "onnx"
        assert model.kwargs["revision"] == "custom-rev-123"
        assert model.kwargs["cache_folder"] == "/custom/model/cache"

    def test_loader_unsupported_backend_fails(self):
        with pytest.raises(ValueError, match="Unsupported backend 'unsupported_backend'"):
            getSentenceTransformer(backend="unsupported_backend")

    def test_pooling_verification_model_native_match_and_recorded(self):
        mock_model = MockSentenceTransformer("all-MiniLM-L6-v2")
        verified = verify_model_pooling(mock_model, "mean", model_id="all-MiniLM-L6-v2")
        assert verified == "mean"

    def test_pooling_verification_rejects_unsupported_config(self):
        mock_model = MockSentenceTransformer("all-MiniLM-L6-v2")
        with pytest.raises(ValueError, match="Unsupported pooling mode 'unknown_pool'"):
            verify_model_pooling(mock_model, "unknown_pool")

    def test_pooling_verification_rejects_model_native_mismatch(self):
        mock_model = MockSentenceTransformer("all-MiniLM-L6-v2")
        with pytest.raises(ValueError, match="Model pooling mismatch"):
            verify_model_pooling(mock_model, "cls")

    @patch("sentence_transformers.SentenceTransformer", side_effect=MockSentenceTransformer)
    def test_explicit_revision_not_overridden_by_none(self, mock_cls):
        model = getSentenceTransformer("all-MiniLM-L6-v2", revision="explicit-sha-123")
        assert model.kwargs["revision"] == "explicit-sha-123"

        embed_query("test", revision="explicit-query-sha")
        m = getSentenceTransformer("all-MiniLM-L6-v2", revision="explicit-query-sha")
        assert m.kwargs["revision"] == "explicit-query-sha"

    @patch("sentence_transformers.SentenceTransformer", side_effect=MockSentenceTransformer)
    def test_same_model_alias_cache_hit(self, mock_cls):
        """Calling getSentenceTransformer with alias or canonical modelId hits same cache."""
        clearModelCache()
        m1 = getSentenceTransformer("all-MiniLM-L6-v2")
        m2 = getSentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        assert m1 is m2
        assert mock_cls.call_count == 1
        assert len(getModelCache()) == 1

    @patch("sentence_transformers.SentenceTransformer", side_effect=MockSentenceTransformer)
    def test_explicit_revision_overrides_and_forwards(self, mock_cls):
        """Explicit revision arg forwards and overrides default pinned revision."""
        clearModelCache()
        model = getSentenceTransformer("all-MiniLM-L6-v2", revision="explicit-sha-456")
        assert model.kwargs["revision"] == "explicit-sha-456"
        assert ("all-MiniLM-L6-v2", "explicit-sha-456", "torch") in getModelCache()

    def test_load_skills_fails_on_malformed_canonical_node_json(self, tmp_path):
        nodes_dir = tmp_path / "registry" / "nodes" / "basic"
        nodes_dir.mkdir(parents=True)
        (nodes_dir / "bad.json").write_text("not valid json at all {{{")

        with pytest.raises(ValueError, match="Malformed canonical node JSON"):
            load_skills(str(tmp_path))

    def test_load_skills_fails_on_missing_id_in_canonical_node(self, tmp_path):
        nodes_dir = tmp_path / "registry" / "nodes" / "basic"
        nodes_dir.mkdir(parents=True)
        (nodes_dir / "no_id.json").write_text(json.dumps({"name": "No ID"}))

        with pytest.raises(ValueError, match="missing or invalid 'id'"):
            load_skills(str(tmp_path))

    def test_generate_embeddings_reuses_fresh_artifact(self, tmp_path):
        instances = []

        def make_mock(model_name="all-MiniLM-L6-v2", **kwargs):
            m = MockSentenceTransformer(model_name, **kwargs)
            instances.append(m)
            return m

        with patch("sentence_transformers.SentenceTransformer", side_effect=make_mock):
            nodes_dir = tmp_path / "registry" / "nodes" / "basic"
            nodes_dir.mkdir(parents=True)
            (nodes_dir / "calc.json").write_text(
                json.dumps({"id": "calc", "name": "Calculator", "description": "Performs math."})
            )

            out_path = str(tmp_path / "registry" / "embeddings.json")

            # 1. First run generates
            res1 = generate_embeddings(registry_path=str(tmp_path), output_path=out_path)
            assert res1["status"] == "fresh"
            assert os.path.exists(out_path)
            assert len(instances) == 1
            first_call_count = instances[0].encode_call_count

            # 2. Second run reuses fresh artifact (force=False)
            res2 = generate_embeddings(registry_path=str(tmp_path), output_path=out_path, force=False)
            assert res2["status"] == "fresh"
            assert instances[0].encode_call_count == first_call_count

            # 3. Third run with force=True regenerates
            res3 = generate_embeddings(registry_path=str(tmp_path), output_path=out_path, force=True)
            assert res3["status"] == "fresh"
            assert instances[0].encode_call_count > first_call_count

    @patch("sentence_transformers.SentenceTransformer", side_effect=MockSentenceTransformer)
    def test_embed_query_and_skills_share_config(self, mock_cls, tmp_path):
        cfg = loadRetrievalConfig(modelName="BAAI/bge-small-en-v1.5")
        q_vec = embed_query("hello search", config=cfg)
        assert len(q_vec) == 384

        skills = [{"id": "s1", "name": "S1", "description": "D1"}]
        entries, dim = embed_skills(skills, config=cfg)
        assert dim == 384
        assert len(entries[0]["vector"]) == 384


class TestAtomicWrite:
    """Tests for saveEmbeddingsAtomic."""

    def test_atomic_write_creates_valid_file(self, tmp_path):
        out_path = tmp_path / "subdir" / "embeddings.json"
        entries = [{"id": "s1", "vector": [0.1, 0.2]}]
        saveEmbeddingsAtomic(
            entries=entries,
            outputPath=out_path,
            modelName="all-MiniLM-L6-v2",
            dimensions=2,
            fingerprint="test-fp-1234",
            config={"modelId": "all-MiniLM-L6-v2"},
        )
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert data["fingerprint"] == "test-fp-1234"
        assert data["model"] == "all-MiniLM-L6-v2"
        assert len(data["entries"]) == 1
        assert len(list(tmp_path.glob("**/*.tmp*"))) == 0

    def test_atomic_write_uses_exclusive_random_tempfile_collision_safe(self, tmp_path):
        out_path = tmp_path / "embeddings.json"
        entries = [{"id": "s1", "vector": [0.1, 0.2]}]

        created_temps = []
        original_named_temp = saveEmbeddingsAtomic.__globals__["tempfile"].NamedTemporaryFile

        def track_named_temp(*args, **kwargs):
            tf = original_named_temp(*args, **kwargs)
            created_temps.append(tf.name)
            return tf

        with patch("tempfile.NamedTemporaryFile", side_effect=track_named_temp):
            saveEmbeddingsAtomic(
                entries=entries,
                outputPath=out_path,
                modelName="all-MiniLM-L6-v2",
                dimensions=2,
                fingerprint="fp1",
            )

        assert len(created_temps) == 1
        # Confirms temporary file was in the same parent dir with exclusive random prefix
        temp_file = Path(created_temps[0])
        assert temp_file.parent == out_path.parent
        assert temp_file.name.startswith("embeddings.json.tmp.")


class TestDeterminismContract:
    """The single-thread/eval contract must actually execute, not just exist.

    Enforcement is reached through ``sys.modules.get("torch")``, which is only
    populated because sentence-transformers imports torch transitively. If that
    ever becomes a lazy import, the contract would silently evaporate.
    """

    def _installFakeTorch(self, monkeypatch):
        torch = types.ModuleType("torch")
        torch.set_num_threads = MagicMock()
        monkeypatch.setitem(sys.modules, "torch", torch)
        return torch

    def test_set_num_threads_pinned_on_fresh_load_and_cache_hit(self, monkeypatch):
        from gaia_cli.curation import retrieval

        torch = self._installFakeTorch(monkeypatch)
        model = MagicMock()
        model.pooling = "mean"
        module = types.ModuleType("sentence_transformers")
        module.SentenceTransformer = MagicMock(return_value=model)
        monkeypatch.setitem(sys.modules, "sentence_transformers", module)
        clearModelCache()

        retrieval.getSentenceTransformer()
        assert torch.set_num_threads.call_args_list == [call(1)], (
            "fresh load must pin torch to a single thread"
        )
        model.eval.assert_called()

        torch.set_num_threads.reset_mock()
        retrieval.getSentenceTransformer()
        assert torch.set_num_threads.call_args_list == [call(1)], (
            "cache-hit reuse must re-assert single-thread pinning"
        )
        assert model.eval.called, "cache-hit reuse must re-assert evaluation mode"
