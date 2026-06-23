"""Tests for embedding generation and semantic search (mocked — no model required)."""
import json
import os
import sys
import math
import importlib
import pytest
pytestmark = [pytest.mark.integration]


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestCosineSimilarity:
    """Tests for the cosine_similarity helper in semantic_search.py."""

    def test_identical_vectors(self):
        """Cosine similarity of a vector with itself is 1.0."""
        from gaia_cli.semantic_search import cosine_similarity

        v = [1.0, 0.0, 0.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        """Cosine similarity of orthogonal vectors is 0.0."""
        from gaia_cli.semantic_search import cosine_similarity

        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(cosine_similarity(a, b)) < 1e-6

    def test_opposite_vectors(self):
        """Cosine similarity of anti-parallel vectors is -1.0."""
        from gaia_cli.semantic_search import cosine_similarity

        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_zero_vector_returns_zero(self):
        """Cosine similarity returns 0.0 when either vector is zero."""
        from gaia_cli.semantic_search import cosine_similarity

        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0

    def test_both_zero_vectors_returns_zero(self):
        """Cosine similarity returns 0.0 when both vectors are zero."""
        from gaia_cli.semantic_search import cosine_similarity

        assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0

    def test_similar_vectors_high_score(self):
        """Nearly-parallel vectors have a score close to 1.0."""
        from gaia_cli.semantic_search import cosine_similarity

        a = [1.0, 0.1, 0.0]
        b = [0.9, 0.1, 0.0]
        score = cosine_similarity(a, b)
        assert score > 0.9

    def test_symmetry(self):
        """cosine_similarity(a, b) == cosine_similarity(b, a)."""
        from gaia_cli.semantic_search import cosine_similarity

        a = [0.3, 0.7, 0.1]
        b = [0.8, 0.2, 0.4]
        assert abs(cosine_similarity(a, b) - cosine_similarity(b, a)) < 1e-9


class TestSearchPrecomputed:
    """Tests for search_precomputed in semantic_search.py."""

    @pytest.fixture
    def sample_embeddings(self):
        return {
            "model": "test",
            "dimensions": 3,
            "generatedAt": "2026-04-29",
            "entries": [
                {"id": "skill-a", "vector": [1.0, 0.0, 0.0]},
                {"id": "skill-b", "vector": [0.9, 0.1, 0.0]},
                {"id": "skill-c", "vector": [0.0, 1.0, 0.0]},
                {"id": "skill-d", "vector": [0.0, 0.0, 1.0]},
            ],
        }

    def test_returns_top_k_results(self, sample_embeddings):
        """search_precomputed returns at most top_k results."""
        from gaia_cli.semantic_search import search_precomputed

        query_vector = [1.0, 0.0, 0.0]
        results = search_precomputed(query_vector, sample_embeddings, top_k=2)
        assert len(results) == 2

    def test_results_sorted_by_score_descending(self, sample_embeddings):
        """Results are ordered highest score first."""
        from gaia_cli.semantic_search import search_precomputed

        query_vector = [1.0, 0.0, 0.0]
        results = search_precomputed(query_vector, sample_embeddings, top_k=4)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_best_match_is_correct(self, sample_embeddings):
        """The closest skill to the query is ranked first."""
        from gaia_cli.semantic_search import search_precomputed

        query_vector = [1.0, 0.0, 0.0]
        results = search_precomputed(query_vector, sample_embeddings, top_k=4)
        assert results[0]["id"] == "skill-a"

    def test_result_structure(self, sample_embeddings):
        """Each result has 'id' and 'score' keys."""
        from gaia_cli.semantic_search import search_precomputed

        results = search_precomputed([1.0, 0.0, 0.0], sample_embeddings, top_k=2)
        for r in results:
            assert "id" in r
            assert "score" in r
            assert isinstance(r["score"], float)

    def test_empty_embeddings_returns_empty(self):
        """search_precomputed returns [] when there are no entries."""
        from gaia_cli.semantic_search import search_precomputed

        embeddings = {
            "model": "test",
            "dimensions": 3,
            "generatedAt": "2026-04-29",
            "entries": [],
        }
        results = search_precomputed([1.0, 0.0, 0.0], embeddings, top_k=5)
        assert results == []

    def test_top_k_larger_than_entries(self, sample_embeddings):
        """search_precomputed returns all entries when top_k exceeds count."""
        from gaia_cli.semantic_search import search_precomputed

        results = search_precomputed([1.0, 0.0, 0.0], sample_embeddings, top_k=100)
        assert len(results) == 4  # only 4 entries exist


class TestLoadEmbeddings:
    """Tests for load_embeddings in semantic_search.py."""

    def test_loads_valid_embeddings_file(self, tmp_path):
        """load_embeddings successfully reads a valid embeddings JSON file."""
        from gaia_cli.semantic_search import load_embeddings

        data = {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 3,
            "generatedAt": "2026-04-29",
            "entries": [{"id": "web-search", "vector": [0.1, 0.2, 0.3]}],
        }
        path = tmp_path / "embeddings.json"
        path.write_text(json.dumps(data))

        loaded = load_embeddings(str(path))
        assert loaded["model"] == "all-MiniLM-L6-v2"
        assert len(loaded["entries"]) == 1

    def test_raises_file_not_found(self, tmp_path):
        """load_embeddings raises FileNotFoundError for a missing file."""
        from gaia_cli.semantic_search import load_embeddings

        with pytest.raises(FileNotFoundError):
            load_embeddings(str(tmp_path / "nonexistent.json"))


class TestComputeSimilarityScript:
    """Tests for compute_similarity in scripts/computeSimilarity.py."""

    def test_compute_similarity_produces_valid_output(self, tmp_path):
        """compute_similarity writes a valid similarity.json file."""
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        from computeSimilarity import compute_similarity

        embeddings = {
            "model": "test",
            "dimensions": 3,
            "generatedAt": "2026-04-29",
            "entries": [
                {"id": "a", "vector": [1.0, 0.0, 0.0]},
                {"id": "b", "vector": [0.9, 0.1, 0.0]},
                {"id": "c", "vector": [0.0, 0.0, 1.0]},
            ],
        }
        embeddings_path = str(tmp_path / "embeddings.json")
        output_path = str(tmp_path / "similarity.json")

        with open(embeddings_path, "w", encoding="utf-8") as f:
            json.dump(embeddings, f)

        compute_similarity(embeddings_path, output_path, threshold=0.3)

        assert os.path.exists(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "pairs" in data
        assert "generatedAt" in data
        assert "threshold" in data
        assert data["threshold"] == 0.3

    def test_compute_similarity_finds_similar_pair(self, tmp_path):
        """compute_similarity includes the a-b pair (cos ~0.99) above threshold."""
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        from computeSimilarity import compute_similarity

        embeddings = {
            "model": "test",
            "dimensions": 3,
            "generatedAt": "2026-04-29",
            "entries": [
                {"id": "a", "vector": [1.0, 0.0, 0.0]},
                {"id": "b", "vector": [0.9, 0.1, 0.0]},
                {"id": "c", "vector": [0.0, 0.0, 1.0]},
            ],
        }
        embeddings_path = str(tmp_path / "embeddings.json")
        output_path = str(tmp_path / "similarity.json")

        with open(embeddings_path, "w", encoding="utf-8") as f:
            json.dump(embeddings, f)

        compute_similarity(embeddings_path, output_path, threshold=0.3)

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        pair_keys = {(p["a"], p["b"]) for p in data["pairs"]}
        assert ("a", "b") in pair_keys, "Expected a-b pair to be above threshold"

    def test_compute_similarity_excludes_below_threshold(self, tmp_path):
        """compute_similarity omits pairs with score below threshold."""
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        from computeSimilarity import compute_similarity

        embeddings = {
            "model": "test",
            "dimensions": 3,
            "generatedAt": "2026-04-29",
            "entries": [
                {"id": "a", "vector": [1.0, 0.0, 0.0]},
                {"id": "c", "vector": [0.0, 0.0, 1.0]},  # orthogonal to a
            ],
        }
        embeddings_path = str(tmp_path / "embeddings.json")
        output_path = str(tmp_path / "similarity.json")

        with open(embeddings_path, "w", encoding="utf-8") as f:
            json.dump(embeddings, f)

        compute_similarity(embeddings_path, output_path, threshold=0.3)

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # a and c are orthogonal (score=0), so no pairs should appear
        assert len(data["pairs"]) == 0

    def test_compute_similarity_sorted_descending(self, tmp_path):
        """compute_similarity output pairs are sorted by score descending."""
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        from computeSimilarity import compute_similarity

        embeddings = {
            "model": "test",
            "dimensions": 2,
            "generatedAt": "2026-04-29",
            "entries": [
                {"id": "a", "vector": [1.0, 0.0]},
                {"id": "b", "vector": [0.9, 0.1]},
                {"id": "c", "vector": [0.5, 0.5]},
            ],
        }
        embeddings_path = str(tmp_path / "embeddings.json")
        output_path = str(tmp_path / "similarity.json")

        with open(embeddings_path, "w", encoding="utf-8") as f:
            json.dump(embeddings, f)

        compute_similarity(embeddings_path, output_path, threshold=0.1)

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        scores = [p["score"] for p in data["pairs"]]
        assert scores == sorted(scores, reverse=True)


class TestEmbeddingsLoader:
    """Tests for load_skills in src/gaia_cli/embeddings.py."""

    def test_load_skills_from_gaia_json(self, tmp_path):
        """load_skills reads skills from registry/gaia.json."""
        from gaia_cli.embeddings import load_skills

        graph_dir = tmp_path / "registry"
        graph_dir.mkdir()
        gaia_data = {
            "skills": [
                {"id": "web-search", "name": "Web Search", "description": "Searches the web."},
                {"id": "code-gen", "name": "Code Gen", "description": "Generates code."},
            ]
        }
        (graph_dir / "gaia.json").write_text(json.dumps(gaia_data))

        skills = load_skills(str(tmp_path))
        ids = [s["id"] for s in skills]
        assert "web-search" in ids
        assert "code-gen" in ids

    def test_load_skills_returns_empty_on_missing_gaia(self, tmp_path):
        """load_skills returns an empty list when gaia.json does not exist."""
        from gaia_cli.embeddings import load_skills

        skills = load_skills(str(tmp_path))
        assert isinstance(skills, list)
        assert len(skills) == 0

    def test_save_embeddings_creates_valid_json(self, tmp_path):
        """save_embeddings writes a correctly structured embeddings JSON file."""
        from gaia_cli.embeddings import save_embeddings

        entries = [
            {"id": "web-search", "vector": [0.1, 0.2, 0.3]},
            {"id": "code-gen", "vector": [0.4, 0.5, 0.6]},
        ]
        output_path = str(tmp_path / "registry" / "embeddings.json")
        save_embeddings(entries, output_path, model_name="test-model", dimensions=3)

        assert os.path.exists(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["model"] == "test-model"
        assert data["dimensions"] == 3
        assert len(data["entries"]) == 2
        assert "generatedAt" in data
